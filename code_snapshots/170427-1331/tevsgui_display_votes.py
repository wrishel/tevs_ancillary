import const
import pdb
import os.path

INDEX_CONTEST = 3
INDEX_CHOICE = 4
INDEX_XCOORD = 22
INDEX_YCOORD = 23
INDEX_INTENSITY = 7
INDEX_WAS_VOTED = 26
INDEX_AMBIGUOUS = 27

text_size="medium"

class Vote(object):
    def __init__(self,str):
        # split the str into fields, and set values based on field contents
        try:
            fields = str.split(",")
            self.contest = fields[INDEX_CONTEST]
            self.choice = fields[INDEX_CHOICE]
            self.xcoord = int(float(fields[INDEX_XCOORD]))
            self.ycoord = int(float(fields[INDEX_YCOORD]))
            self.intensity = int(float(fields[INDEX_INTENSITY]))
            self.was_voted = fields[INDEX_WAS_VOTED]=="True"
            self.ambiguous = fields[INDEX_AMBIGUOUS]=="True"
        except Exception,e:
            print Exception,e
            print fields
    def xcoord(self):
        return self._xcoord

    def ycoord(self):
        return self._ycoord

class DBVote(Vote):
    def __init__(self):
        # split the str into fields, and set values based on field contents
        pass

    def xcoord(self):
        return self._xcoord

    def ycoord(self):
        return self._ycoord


class BallotVotes(object):
    def __init__(self,imagenumber,dbc=None):
        self.ballot_id = None
        if const.use_db:
            # query the database for the voteops matching file number
            dbfileroot = const.root+"/unproc"
            dbfilename = "%s/%03d/%06d.jpg" % (
                dbfileroot,imagenumber/1000,imagenumber)
            results = dbc.query("select contest_text,choice_text,adjusted_x,adjusted_y,(red_mean_intensity+green_mean_intensity+blue_mean_intensity)/3., (red_darkest_pixels+red_darkish_pixels+green_darkest_pixels+green_darkish_pixels+blue_darkest_pixels+blue_darkish_pixels)/3.0,was_voted, suspicious, overvoted, filename, ballots.ballot_id from voteops join ballots on voteops.ballot_id = ballots.ballot_id where filename like '%s'" % (dbfilename,) )
            # unpack results
            #INDEX_CONTEST = 3
            #INDEX_CHOICE = 4
            #INDEX_XCOORD = 22
            #INDEX_YCOORD = 23
            #INDEX_INTENSITY = 7
            #INDEX_WAS_VOTED = 26
            #INDEX_AMBIGUOUS = 27
            self.votelist = []

            if results is not None and len(results)>0:
                for fields in results:
                    v = DBVote()
                    v.contest = fields[0]
                    v.choice = fields[1]
                    v.xcoord = int(float(fields[2]))
                    v.ycoord = int(float(fields[3]))
                    v.intensity = int(float(fields[4]))
                    v.darkpix = int(float(fields[5]))
                    v.was_voted = fields[6]
                    v.ambiguous = fields[7]
                    v.overvoted = fields[8]
                    v.filename = fields[9]
                    self.ballot_id = fields[10]
                    self.votelist.append(v)    

        else:
            # open and read the data file, line by line

            imagenumberstr = "%06d." % imagenumber
            datafilename = const.resultsformatstring % (imagenumber/1000,imagenumber)
            df = None
            try:
                df = open(datafilename,"r")
            except:
                try:
                    datafilename = const.resultsformatstring % ((imagenumber-1)/1000,imagenumber-1)
                    df = open(datafilename,"r")
                except:
                    print "Could not open",datafilename,"either"
            self.votelist = []
            for line in df.readlines():
                if (line.find(imagenumberstr)>-1):
                    self.votelist.append(Vote(line))
            df.close()


    def paint(self,main_app,drawarea,orig_width,orig_height,imagedpi,overlay_votes, overlay_choices, overlay_contests, overlay_stats=False):

        gc = main_app.gc
        red = main_app.red
        green = main_app.green
        blue = main_app.blue
        purple = main_app.purple
        cyan = main_app.cyan
        drawable = drawarea.window
        w,h = drawable.get_size()
        xscalefactor = float(w)/orig_width
        yscalefactor = float(h)/orig_height
        drawarea.xscalefactor = xscalefactor
        drawarea.yscalefactor = yscalefactor
        # The vote coordinate in the database is actually the coordinate
        # of the crop box's upper left corner (it includes the margin)
        for v in self.votelist:
            scaledx = int(round(
                    (v.xcoord)
                    *xscalefactor) )
            scaledy = int(round(
                    (v.ycoord)
                    *yscalefactor) )
            oval_height = int(
                (const.target_height_inches  + (2*const.margin_height_inches)) 
                * imagedpi * yscalefactor)
            oval_width = int(
                (const.target_width_inches  + (2*const.margin_width_inches)) 
                * imagedpi * xscalefactor)
            scaledx += int(round(
                    const.hotspot_x_offset_inches * imagedpi * xscalefactor))
            scaledy += int(round(
                    const.hotspot_y_offset_inches * imagedpi * yscalefactor))

            #box_height = int(round(oval_height * yscalefactor))
            #box_width = int(round(oval_width * xscalefactor))
            #box_height += 1
            #box_width += 1
            cmap = drawable.get_colormap()
            if v.was_voted:
                gc.set_foreground(red)
            else:
                gc.set_foreground(green)
            if v.ambiguous and v.was_voted:
                gc.set_foreground(purple)
            if v.ambiguous and not v.was_voted:
                gc.set_foreground(blue)
            if v.overvoted:
                gc.set_foreground(cyan)
            if overlay_votes:
                drawable.draw_rectangle(gc,False,
                                        scaledx,
                                        scaledy,
                                        oval_width+1,
                                        oval_height+1)
                try:
                    if v.overvoted:
                        drawable.draw_rectangle(gc,False,
                                                scaledx-2,
                                                scaledy-2,
                                                oval_width+4,
                                                oval_height+4)
                except Exception as e:
                    print e
                    pdb.set_trace()
            if not (overlay_votes or overlay_choices or overlay_contests or overlay_stats):
                continue
            bg_markup_color="white"
            if v.was_voted:
                markup_color="red"
            else:
                markup_color="blue"
            if v.ambiguous:
                markup_color="yellow"
                bg_markup_color="black"
            try:
                if v.overvoted:
                    markup_color="white"
                    bg_markup_color="blue"
            except Exception as e:
                print e
                pdb.set_trace()
            if overlay_choices:
                choicetext = v.choice.replace("dquot",'"').replace("squot","'")[:25]
            else:
                choicetext = ""
            if overlay_contests:
                contesttext = v.contest.replace("dquot",'"').replace("squot","'")[:25]
            else:
                contesttext = ""
            if overlay_choices and overlay_contests:
                text = "%s\n%s" % (contesttext,choicetext)
            else:
                text = "%s%s" % (contesttext,choicetext)
            if overlay_stats:
                if len(text)>2:
                    text += "\n"
                text = text+"Int:%d, Dark:%d" % (v.intensity,v.darkpix)
            #if text.startswith("v"):text=text[1:]
            markup = drawarea.create_pango_layout("a")
            markup.set_markup(
                """<span size="%s" foreground="%s" background="%s">%s</span>""" % (
                    text_size,markup_color,bg_markup_color,text
                    )
                )
            # draw markup at lower right of vote oval, offset by 5 pix 
            drawable.draw_layout(gc,
                               scaledx+2*oval_width,
                               scaledy,
                               markup)

