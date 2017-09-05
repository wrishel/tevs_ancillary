    def generate_transition_list_from_lines(self,image,regionlist,column_bounds,lines):
        """given a set of horizontal split lines, gen contests from column"""
        ccontest_default = "No current contest"
        ccontest = ccontest_default
        cjurisdiction_default = "No current jurisdiction"
        cjurisdiction = cjurisdiction_default
        contest_instance = None
        for n in range(len(lines)):
            this_y = lines[n][1]
            try:
                next_y = lines[n+1][1]
            except IndexError:
                next_y = image.size[1]-1
            self.get_title_and_votes_from(image,regionlist,
                                          (column_bounds[0],
                                           this_y,
                                           column_bounds[1],
                                           next_y))
            self.log.debug( "Retrieve title and votes in zone  %d,%d to %d,%d" % (column_bounds[0],this_y,column_bounds[1],next_y))
        # filter regionlist to contain only contests with choices
        # set jurisdiction based on previous rejected "contest"
        rejectedlist = [x for x in regionlist if len(x.choices)==0]
        #print "Rejections",[x.description for x in rejectedlist]
        regionlist = [x for x in regionlist if len(x.choices)>0]
        return regionlist

    def generate_transition_list_from_zones(self,image,regionlist,column_bounds,left,middle):
        """ given the pair of zone lists, generate a comprehensive list

        We should then be able to merge these sets of split information:
        anything where we find solid black or halftone is a definite break
        which may be followed either by another black or halftone area, by
        a description area, or by a vote area.
        """
        ccontest_default = "No current contest"
        ccontest = ccontest_default
        cjurisdiction_default = "No current jurisdiction"
        cjurisdiction = cjurisdiction_default
        contest_instance = None
        for n in range(len(left)):
            this_y = left[n][0]
            try:
                next_zone = left[n+1]
            except IndexError:
                next_zone = [0,'X']
            next_y = next_zone[0]
            rel_end = next_y - (const.dpi/10)
            if left[n][1]=='B' or left[n][1]=='G':
                self.log.debug("%s zone at %d to %d %s" % (left[n][1],
                                                           this_y,
                                                           next_y,
                                                           next_zone))
                # if it's a legitimage gray zone and the next zone is white,
                # that white zone is a voting area (or empty)
                if (next_y - this_y) > (const.dpi/4):
                    crop = image.crop((column_bounds[0],
                                       this_y,
                                       column_bounds[1],
                                       next_y))
                    crop = Image.eval(crop,elim_halftone)
                    cjurisdiction = ocr.tesseract(crop)
                    cjurisdiction = cjurisdiction.replace("\n","//").strip()
                    self.log.debug( "Jurisdiction %s" % (cjurisdiction,))
                    cjurisdiction = ocr.clean_ocr_text(cjurisdiction)
                    self.log.debug( "Cleaned Jurisdiction %s" % (cjurisdiction,))
            if left[n][1]=='W':
                self.get_title_and_votes_from(image,regionlist,
                                         (column_bounds[0],
                                          this_y,
                                          column_bounds[1],
                                          next_y))
                self.log.debug( "White zone at %d to %d %s" % (this_y,next_y,next_zone))
        # filter regionlist to contain only contests with choices
        regionlist = [x for x in regionlist if len(x.choices)>0]
        return regionlist

    def get_dark_zones(self,crop,dark_intensity=192):
        """ return starting and ending y offsets of dark areas in crop"""
        in_dark = False
        dark_zones = []
        dark_start = 0
        dark_end = 0
        for y in range(crop.size[1]-1):
            linecrop = crop.crop((const.dpi/10,
                                  y,
                                  crop.size[0] - (const.dpi/10),
                                  y+1))
            linestat = ImageStat.Stat(linecrop)
            if (linestat.extrema[0][0] < dark_intensity) and not in_dark:
                in_dark = True
                dark_start = y
            elif (linestat.extrema[0][0] >= dark_intensity) and in_dark:
                in_dark = False
                dark_end = y
                dark_zones.append([dark_start,dark_end])
        return dark_zones

    def get_dark_zones(self,crop,dark_intensity=192):
        """ return starting and ending y offsets of dark areas in crop"""
        in_dark = False
        dark_zones = []
        dark_start = 0
        dark_end = 0
        for y in range(crop.size[1]-1):
            linecrop = crop.crop((const.dpi/10,
                                  y,
                                  crop.size[0] - (const.dpi/10),
                                  y+1))
            linestat = ImageStat.Stat(linecrop)
            if (linestat.extrema[0][0] < dark_intensity) and not in_dark:
                in_dark = True
                dark_start = y
            elif (linestat.extrema[0][0] >= dark_intensity) and in_dark:
                in_dark = False
                dark_end = y
                dark_zones.append([dark_start,dark_end])
        return dark_zones

    def get_contests_and_votes_from(self,image,regionlist,croplist):
        """ given an area known to contain votes and desc text, return info

        The cropped area will contain contest descriptions and voting areas.
        Unfortunately, the contest descriptions are not indented away from
        the oval voting areas.  So...  we crop looking for white line splits,
        and then treat every line as either part of a contest or as a vote
        line, depending on whether we find a pattern of white indicating
        the line contains only an oval and a single word, YES or NO.
        """
        ov_off = adj(const.vote_target_horiz_offset_inches)
        ov_end = ov_off + adj(const.target_width_inches)

        txt_off = adj(const.candidate_text_horiz_offset_inches)

        contests = []
        contest_string = ""
        crop = image.crop(croplist)
        # indent by 1/10" to avoid edges, then crop single pixel lines,
        # finding beginning and end of zones which include dark pixels
        # now check each dark zone to see if it is a vote op 
        # or if it is descriptive text; vote ops will have an oval
        # in the oval channel beginning at ov_off
        # and extending until ov_end
        dark_zones = self.get_dark_zones(crop,dark_intensity=160)
        contest_created = False
        for dz in dark_zones:
            zonecrop1 = crop.crop((const.dpi/10,
                                    dz[0],
                                    crop.size[0]-(const.dpi/10), 
                                    dz[1]))
            zonecrop2 = crop.crop((ov_end,
                                    dz[0],
                                    txt_off, 
                                    dz[1]))
            zone2stat = ImageStat.Stat(zonecrop2)
            zonecrop3 = crop.crop((txt_off,
                                    dz[0],
                                    txt_off + const.dpi,
                                    dz[1]))
            zone1text = ocr.tesseract(zonecrop1)
            zone1text = ocr.clean_ocr_text(zone1text)
            zone3text = ocr.tesseract(zonecrop3)
            zone3text = ocr.clean_ocr_text(zone3text)
            intensity_suggests_voteop = False
            length_suggests_voteop = False
            if zone2stat.mean[0]>244: intensity_suggests_voteop = True
            if len(zone3text)<6: length_suggests_voteop = True
            if not intensity_suggests_voteop and not length_suggests_voteop:
                contest_created = False
                contest_string += zone1text.replace("\n","/")
            elif intensity_suggests_voteop and length_suggests_voteop:
                # create contest if none created, then
                if not contest_created:
                    contest_created = True
                    self.log.debug("Creating contest %s" % (contest_string,))
                    regionlist.append(Ballot.Contest(croplist[0],
                                                     croplist[1]+dz[0],
                                                     croplist[2],
                                                     croplist[1]+dz[1],
                                                     0,
                                                     contest_string))
                    contest_string = ""
                # add voteop to contest
                choice_string = zone3text
                self.log.debug("Adding choice %s" % (choice_string,))
                regionlist[-1].append(
                    Ballot.Choice(
                        croplist[0]+ov_off,
                        croplist[1]+ dz[0],
                        choice_string
                        )
                    )

            else:
                if contest_created:
                    contest_string += zone1text.replace("\n","//")
                else:
                    self.log.debug( "Problem determining whether contest or choice")
                    self.log.debug("Gap mean values %s" % (zone2stat.mean,))
                    self.log.debug("Zone3 text %s" % (zone3text,))
                    self.log.debug("Contest string: %s" % (contest_string,))
        return dark_zones

    def get_title_and_votes_from(self,image,regionlist,croplist,last_title="NO TITLE"):
        """ given an area known to contain contest title and votes, return info

        The cropped area will contain a title area at the top, 
        followed by voting areas.  Voting areas will
        contain ovals in the oval column.  Descriptive text to the right of
        the ovals will be assigned to each oval based on being at or below
        the oval.

        """
        ov_off = adj(const.vote_target_horiz_offset_inches)
        ov_ht = adj(const.target_height_inches)
        ov_wd = adj(const.target_width_inches)
        ov_end = ov_off + ov_wd
        txt_off = adj(const.candidate_text_horiz_offset_inches)


        choices = []
        crop = image.crop(croplist)
        if croplist[2]==0 or croplist[3]==0:
            return []

        dark_zones = self.get_dark_zones(crop)

        next_dark_zones = dark_zones[1:]
        next_dark_zones.append([crop.size[1]-2,crop.size[1]-1])
        skipcount = 0


        # for each dark zone, determine the first dark x
        encountered_oval = False
        dzstyle = []
        for dz in dark_zones:
            # crop each dark strip
            # losing the area to the left of the possible vote target
            # and an equivalent area on the right
            dzcrop = crop.crop((ov_off,
                                dz[0],
                                crop.size[0]-ov_off,
                                dz[1]))

            firstx = dzcrop.size[0]
            lastx = 0
            for y in range(dzcrop.size[1]):
                for x in range(dzcrop.size[0]):
                    p0 = dzcrop.getpixel((x,y))
                    if p0[0] < 192:
                        firstx = min(firstx,x)
                        lastx = max(lastx,x)
            lastxindent = dzcrop.size[0]-lastx

            # unfortunately, it is hard to tell a filled oval from a title
            # that begins about the same x offset as ovals; we will
            # recognize that titles come first and are symmetric
            # ovals start at a defined offset and will have a minimum height
            # and, if empty, will match a particular dark/light pattern
            symmetric = (abs(firstx-lastxindent) < adj(0.05))
            tall_enough = (dz[1]-dz[0] >= int(ov_ht * .8))

            ov_pat = oval_pattern(dzcrop,ov_ht,ov_wd,txt_off-ov_off)

            if not encountered_oval and not ov_pat:
                dzstyle.append("T")

            elif tall_enough and firstx <= adj(0.02):
                dzstyle.append("V")
                encountered_oval = True

            elif ((firstx >= (txt_off - ov_off - adj(0.02))) and not tall_enough):
                dzstyle.append("W")
            else:
                dzstyle.append("-")


        contest_instance = None
        choice = None
        title_array = []
        contest_created = False
        for index,style in enumerate(dzstyle):
            if style=="T":
                titlezone = crop.crop((adj(0.1),
                                      dark_zones[index][0],
                                      crop.size[0]-adj(0.1),
                                      dark_zones[index][1]))
                zonetext = ocr.tesseract(titlezone)
                zonetext = ocr.clean_ocr_text(zonetext)
                zonetext = zonetext.strip()
                zonetext = zonetext.replace("\n","//").strip()
                title_array.append(zonetext)
            elif style=="V":
                if title_array is not None:
                    zonetext = "/".join(title_array)
                    title_array = None
                    if len(zonetext) < 4:zonetext = last_title
                    contest_instance = Ballot.Contest(croplist[0], 
                                                  croplist[1],
                                                  croplist[2],
                                                  croplist[3], 
                                                  0,
                                                  zonetext[:80])
                    contest_created = True
                    regionlist.append(contest_instance)
                if not contest_created:
                    print "WARNING: Choice but no contest."
                    pdb.set_trace()
                    continue
                choicezone = crop.crop((txt_off,
                                      dark_zones[index][0],
                                      crop.size[0]-adj(0.1),
                                      dark_zones[index][1]))
                zonetext = ocr.tesseract(choicezone)
                zonetext = ocr.clean_ocr_text(zonetext)
                zonetext = zonetext.strip()
                zonetext = zonetext.replace("\n","//").strip()

                # find the y at which the actual oval begins 
                # which may be lower than the dark_zone start
                choice_y = dark_zones[index][0]

                # Look up to 0.2 inches beneath beginning of dark zone
                # for an oval darkening the oval region
                contig = 0
                for adj_y in range(adj(0.2)):
                    ovalcrop = crop.crop((ov_off,
                                          choice_y+adj_y,
                                          ov_end,
                                          choice_y+adj_y+1))
                    ovalstat = ImageStat.Stat(ovalcrop)
                    if ovalstat.extrema[0][0] < 240:
                        contig += 1
                        if contig > adj(0.03):
                            choice_y += (adj_y-adj(0.03))
                            found = True
                            break
                    else:
                        contig = 0

                choice = Ballot.Choice(croplist[0]+ov_off, 
                                       croplist[1]+choice_y, 
                                       zonetext)
                contest_instance.append(choice)
                #if zonetext.startswith("Randy"):
                #    print "Randy"
                #    pdb.set_trace()
                #    print "Randy"
            elif style=="W" and len(dzstyle)>(index+1) and dzstyle[index+1] in "W-":
                if title_array is not None:
                    title_array = None

                try:
                    choice.description = "Writein"
                except:
                    pass
        return regionlist

    def get_left_edge_zones(self, page, column_x):
        """ return a set of pairs, (y_value, letter) for zone starts"""
        letters = []
        left = column_x + adj(0.03)
        right = left + adj(0.03)
        im = page.image
        stripe = im.crop((left,0,right,im.size[1]-1))
        lastletter = "W"
        lastred = 255
        lastdarkest = 255
        for y in range(stripe.size[1]-(const.dpi/2)):
            crop = stripe.crop((0,y,1,y+(const.dpi/32)))
            stat = ImageStat.Stat(crop)
            red = stat.mean[0]
            darkest = stat.extrema[0][0]
            if (red < 32) and (darkest < 32) and (lastred >= 32):
                if lastletter <> "B":
                    if lastletter == "G" and letters[-1][0]>(y-adj(0.1)):
                        letters = letters[:-1]
                    letters.append((y,"B"))
                    lastletter = "B"
            elif red >= 32 and red < 240 and darkest < 224:
                if lastletter <> "G":
                    letters.append((y,"G"))
                    lastletter = "G"
            elif red >=240:
                if lastletter <> "W":
                    if lastletter == "G" and letters[-1][0]>(y-adj(0.1)):
                        letters = letters[:-1]
                    letters.append((y,"W"))
                    lastletter = "W"
            lastred = red
            lastdarkest = darkest
        self.log.debug("Left edge zones: %s" % (letters,))
        return letters

    def get_middle_zones(self, page, column_x):
        """ return a set of pairs, (y_value, letter) for zone starts"""
        letters = []
        left = column_x
        right = left + adj(0.5)
        im = page.image
        stripe = im.crop((left,0,right,im.size[1]-1))
        lastletter = "W"
        lastred = 255
        lastdarkest = 255
        for y in range(stripe.size[1]-(const.dpi/2)):
            crop = stripe.crop((0,y,1,y+(const.dpi/4)))
            stat = ImageStat.Stat(crop)
            red = stat.mean[0]
            darkest = stat.extrema[0][0]
            if (darkest < 128) and lastletter == "W":
                letters.append((y+(const.dpi/4),"B"))
                lastletter = "B"
            elif (darkest >= 128) and lastletter == "B":
                letters.append((y,"W"))
                lastletter = "W"
        return letters



    def build_layout(self, page, back=False):
        """ get layout and ocr information from ess ballot
    The column markers represent the vote oval x offsets.
    The columns actually begin .14" before.
    We search the strip between the column edge and the vote ovals,
    looking for intensity changes that represent region breaks
    such as Jurisdiction and Contest changes.

    Unfortunately, there may be a full-ballot-width column at the top,
    containing instructions.  Random text in the instructions will trigger
    various false region breaks.

    More unfortunately, there is an inconsistency in the way jurisdictions
    and contests are handled.  (It looks good to humans.)

    Contests may begin with a black text on grey header (generally 
    following Jurisdictions as white text on black.  Contests with only
    Yes and No choices begin with black text on white background, and
    may precede either a white text on black zone OR another contest.

    The contest titles are hard to differentiate from contest descriptions,
    which can be lengthy.

    Finally, contest descriptions can continue BELOW the voting area
    of the contest.

    We make one necessary assumption, and that is that the vote area in
    such YES/NO contests will have text extending no more than halfway
    into the column, while any text will extend, except for its last line,
    more than halfway into the column.

    We'll take a vertical stripe beginning at the column center and
    of width 1/2", and look for the presence of black or gray pixels 
    in zones 1/4" tall, enough to span one and a half text lines.
    This should allow us to capture continuous vertical stretches of text
    without repeatedly finding "text", "no text".

    We'll take another vertical stripe at the very start of the column,
    from .03" for .03".  This is the extreme margin, and should allow us
    to capture zones with black headlines and grey backgrounds.  Halftoned
    areas are tricky -- they may contain no pixels more than half dark.

    We'll test for pixels of 224 or below, and an average intensity over
    a block of 240 or below.

    We should then be able to merge these sets of split information:
    anything where we find solid black or halftone is a definite break
    which may be followed either by another black or halftone area, by
    a description area, or by a vote area.

    Black, gray, and white zones are located by reading the thin margin strip.
    They must be stored in such a way that there preceding zone color is
    also available.  If the preceding zone color is gray, the white zone
    is a Vote zone.  If the preceding color zone is black, the white zone
    will contain Descriptions and YesNoVote zones.
    White zones can be analyzed by the thick center strip, combined
    with the last reading.  Where the white zone follows gray 
    center strip has text, the white zone is a Description, where the
    center strip has no text, the white zone is a YesNoVote zone.

    The five types of zones (Black, Desc, Vote1, YesNoVote, Gray) will have the
    following possible sequences.

    B -> G,D,V (capture black as Jurisdiction AND Contest)

    G -> D,V (capture G as Contest)

    D -> V,Y,B (capture D as Contest)
           
    V -> B,D (capture V as sequence of votes for current Contest)
    
    Y -> B,D (capture Y as sequence of votes for current Contest)

    When we find a vote area, it will be followed by a black or gray 
    divider or by a new description area.

    Description areas may likewise be followed by vote areas or black or gray.

    in unbroken regions, any areas with their right halves empty 
    will be presumed to represent either blank areas or voting locations.

        """
        ov_off = adj(const.vote_target_horiz_offset_inches)
        self.log.debug( "Entering build_layout.")

        regionlist = []
        n = 0
        # column_markers returns a location 0.14" into the column
        ref_pt = [0,0]
        ref_pt[0] = page.xoff + 2
        ref_pt[1] = page.yoff - 2
        if back:
            ref_pt[0] = page.landmarks[1][0]
            ref_pt[1] = page.landmarks[1][1] - 2
            self.log.debug( "Building BACK layout" )
        self.log.debug("Reference point: %s" % ( ref_pt,))

        columns = column_markers(page)
        try:
            column_width = columns[1][0] - columns[0][0]
        except IndexError:
            column_width = page.image.size[0] - const.dpi
        regionlist = []
        for cnum, column in enumerate(columns):
            print "Entering column",cnum
            column_x = column[0] - ov_off
            # determine the zones at two offsets into the column
            left_edge_zones = self.get_left_edge_zones(page,column_x)
            middle_zones = self.get_middle_zones(page,column_x+(column_width/2))
            # find solid lines in column XXX
            a,b,c,d = 0,0,0,0
            column_crop = page.image.crop((column_x,
                                           0,
                                           column_x + column_width,
                                           page.image.size[1] - adj(0.5)
                    ))
            column_crop.save("/tmp/column_crop.jpg")
            try:
                horizontal_lines = []
                advance_y_by = page.landmarks[0][1]
                last_y_offset = 0
                while True:
                    l = find_line(column_crop,starty = advance_y_by,threshold=64)
                    if l is None:
                        a = 0
                        b = 0 
                        c = 0
                        d = 0
                        advance_y_by += 300
                    else:
                        a = l[0]
                        b = l[1]
                        c = l[2]
                        d = l[3]
                        advance_y_by = (b + adj(0.1))
                    # grab lines that extend across 90% of column width
                    if a < adj(0.06) and c > int(column_crop.size[0]*.9):
                        horizontal_lines.append(l)
                        self.log.debug("Found line, %s %d %d %d %d" % (column_x,a,b,c,d))
                        contest_crop = column_crop.crop((0,
                                          last_y_offset,
                                          column_crop.size[0]-1,
                                          b))
                        contest_crop.save("/tmp/contest_crop_%d_%d.jpg" % (column_x,last_y_offset))
                        last_y_offset = b
                    if advance_y_by >= (page.image.size[1] - adj(0.5)):
                        break
            except Exception,e:
                print e
                pdb.set_trace()
            
            self.log.debug("Column %d at x offset %d" % (cnum,column_x))
            self.log.debug("Lines within column %s" % (horizontal_lines,))
            self.generate_transition_list_from_lines(
                page.image,
                regionlist,
                (column_x,
                column_x+column_width),
                horizontal_lines)
            """self.generate_transition_list_from_zones(
                page.image,
                regionlist,
                (column_x,
                column_x+column_width),
                left_edge_zones,
                middle_zones
                )"""
        return regionlist

