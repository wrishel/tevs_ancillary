# decompose.py, part of TEVS
# Decompose provides classes for the generic decomposition
# of a ballot image to columns, contest boxes, and text lines,
# and for the location of wider than average and tinted "blobs" 
# on the individual text lines.
# On ballots which enclose contests within boxes,  
# this provides a semi-automatic way of generating templates.
# It will be necessary to supplement this with bottom-up
# analysis, for example:
# vertically aligned blobs near the start or end of a contest box
# are likely part of a column of vote ops, and any other blobs on 
# lines containing those blobs are likely not vote ops;
# text similar to "YES", "NO", and "Writein" is probably 
# OCR misreads of those words if they appear in the bottom two
# lines;
# contest boxes containing header text but no vote ops, or 
# vice versa, may need to be merged.
# Where the ballot type is known, code based on a bit of 
# supplemental information
# (such as the size of vote ops or their offset from the box edge)
# can improve the OCR capability substantially.


import Image
import ImageStat
import pdb
import pickle
import ocr
import os
import sys

class NoLineException(Exception):
    "Raised if no vertical line is found in image"
    pass

class Blob(object):
    def __init__(self,line,dpi,start_x,end_x,row,age=0):
        self.line = line
        self.start_x = start_x
        self.dpi = dpi
        self.end_x = end_x
        self.row = row
        self.age = age
        self.row_incr = 0
        self.max_tint = 0

    def get_max_tint(self):
        max_tint = 0
        for x in range(self.start_x, self.end_x):
            for y in range(self.row+1,self.row+2):
                pix = self.line.image.getpixel((x,y))
                tint = abs(pix[0]-pix[1])
                tint = max(tint,abs(pix[1]-pix[2]))
                tint = max(tint,abs(pix[2]-pix[0]))
                max_tint = max(max_tint,tint)
        return max_tint
                           

    def __repr__(self):
        return "Blob/target dpi %d (%d, %d) to (%d,%d +), max_tint %d" % (
            self.dpi, 
            self.start_x,
            self.row - self.age + 1,
            self.end_x,
            self.row,
            self.max_tint)

def remove_dups(blob_list):
    """put all in dictionary once, keying on start x,y ret values from dict"""
    tmp_dict = {}
    for blob in blob_list:
        key = (blob.row,blob.start_x)
        if key in tmp_dict:
            continue
        tmp_dict[key] = blob
    blob_list = tmp_dict.values()
    blob_list.sort(key = lambda x: x.row)
    return blob_list


class Line(object):
    def __init__(self, box, image, dpi, x1, y1, x2, y2):
        self.box = box
        self.image = image
        self.dpi = dpi
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.w = self.x2 - self.x1 
        self.h = self.y2 - self.y1 
        self.text_list = []
        self.blob_list = self.populate_blobs(
            image,self.dpi,min_width_divisor=20)
        self.blob_list = self.filter_blob_list_for_tinted()
        indent = dpi/25

        # no blob? probable header line
        if self.blob_list is None or len(self.blob_list) == 0:
            self.text_list.append( 
                self.get_text_starting_at(indent,self.image).strip() 
                )
            if self.text_list[-1].find("Cynthia")>-1:
                pdb.set_trace()

        # one blob? probable vertical aligned choice
        elif len(self.blob_list) == 1: 
            self.text_list.append(
                self.get_text_starting_at(
                    self.blob_list[0].end_x + (2*indent),
                    image = self.image)
                )

        # multiple blobs? possible horizontal aligned choices on 1 line
        # if the length is two or more and they begin at same height,
        # get the zone after the first and before the second, 
        # after the second and before the third, etc...
        # need to create choice out of each of these
        else:
            last_blob_end = 0
            self.text = ""
            for index,b in enumerate(self.blob_list):
                print "Max tint",b.get_max_tint()
                zone_start = last_blob_end 
                zone_end = b.start_x
                last_blob_end = b.end_x
                assert image.size[1]>0
                if (zone_end - zone_start) <= (2*indent):
                    continue
                cropimage = self.image.crop(
                    (zone_start,
                     0,
                     zone_end-1,
                     image.size[1]
                     )
                    )
                self.text_list.append(
                    self.get_text_starting_at((2*indent),cropimage))
            if (image.size[0] - self.blob_list[-1].end_x) > (2*indent):
                cropimage = self.image.crop(
                    (self.blob_list[-1].end_x,
                     0,
                     image.size[0],
                     image.size[1]
                     )
                    )
                self.text_list.append( 
                    self.get_text_starting_at((2*indent),cropimage)
                    )

    def get_text_starting_at(self,start_x,image):
        if image.size[0]<1:
            return ""
        if image.size[1]<1:
            return ""
        if start_x >= image.size[0]:
            return ""
        cropimage = image.crop((start_x,0,image.size[0],image.size[1]))
        text = ocr.tesseract(cropimage)
        try:
            text = text.strip()
        except:
            pass
        return text

    def filter_blob_list_for_tinted(self):
        max_tint = 0
        total_tint = 0
        if len(self.blob_list)<1:return []
        for b in self.blob_list:
            b.max_tint = b.get_max_tint()
            if b.max_tint > max_tint:
                blob_with_max_tint = b
            total_tint += b.max_tint
        avg_tint = total_tint/len(self.blob_list)
        if max_tint > (4 * avg_tint):
            return [b]
        else:
            return self.blob_list

    def populate_blobs(self,image,dpi,
                       dark_threshold=216,
                       min_width_divisor=6,
                       max_width_divisor=2,
                       min_age_divisor=16,
                       max_age_divisor=8):    
        """return list of locations of contig dark pixel clumps

        pixels must be darker than dark_threshold, 
        must accumulate to line of min_width < length < max_width 
        and must reach that within max_age rows;
        columns of first 1/20" of image f are skipped;
        requires light pixel slightly to upper left of blob 
        to prevent grayscale regions from generating many blobs
        """
        min_width = dpi/min_width_divisor
        max_width = dpi/max_width_divisor
        min_age = dpi/min_age_divisor
        max_age = dpi/max_age_divisor
        #print "Min max age",min_age, max_age
        col_skip = dpi/50
        blob_list = []
        in_dark = False
        dark_length = 0
        output_blobs = []
        skip = 0
        # check each new dark zone to see if it extends one on the previous line
        # if so, enter the extended version on the new line, keep an aging value

        # at end of each line, discard any zones that have reached max_age
        # but not reached min_span
        for index,p in enumerate(image.getdata()):
            row = index / image.size[0]
            col = index % image.size[0]
            if skip>0:
                skip = skip - 1
                continue
            if col<col_skip:
                continue
            # reinitialize dark at start of handled part of row
            if col==col_skip and row > 0:
                # dark zones don't span lines
                in_dark = False
                dark_length = 0
                # age every stored blob as each line is passed, delete ancient
                #print "Length of blob list",len(blob_list)
                for z in blob_list:
                    z.age = z.age + 1
                    if z.row_incr:
                        z.row = z.row + z.row_incr

                # blobs must meet two conditions: they must be wide enough but
                # and they also must keep 
                # blobs that are wide enough when young but don't keep connecting
                # additional rows are deleted from the list of potential outputs
                # newborn blobs (age==1) will never have an added row but are kept
                blob_list = [z for z in blob_list 
                             if z.age < max_age 
                             and (z.row_incr > 0 or z.age==1)]
                for z in blob_list:
                    z.row_incr = 0
                #print "Length of output list pre-transfer",len(output_blobs)
                output_blobs.extend([z for z in blob_list  
                                     if (z.end_x - z.start_x)>min_width 
                                     and (z.end_x - z.start_x)<max_width
                                     and z.age >= min_age])
                #if len(output_blobs)>0: print "Before",row, output_blobs
                output_blobs = remove_dups(output_blobs)
                #if len(output_blobs)>0: 
                #    print "After",row, output_blobs
                #    #pdb.set_trace()
                blob_list = [z for z in blob_list 
                             if (z.end_x - z.start_x)<=min_width 
                             or (z.end_x - z.start_x)>= max_width
                             or z.age < min_age]
                #print "Length of blob list post-removal",len(blob_list)

            if (p[0]+p[1]+p[2])<(dark_threshold*3):
                if in_dark:
                    dark_length = dark_length+1
                else:
                    in_dark = True
                    dark_length = 1 # start_x = end_x less (dark_length-1)
            else:
                if in_dark:
                    in_dark=False
                    # build zone if it doesn't extend any
                    merged = False
                    for z in blob_list:
                        if ((row == (z.row+1)) 
                        and  
                            (  ((col-dark_length+1) <= (z.end_x + 1)) 
                               and (col >= (z.start_x-1))
                               )
                            ):
                            z.row_incr = 1
                            # don't increment row until 
                            # after multiple possible merges
                            #z.row = z.row+1
                            z.start_x = min(col-dark_length+1,z.start_x)
                            z.end_x = max(col,z.end_x)
                            merged = True
                    # initiate oval only if several dark pix together on line
                    if not merged and dark_length > (dpi/64):
                        # avoid grayscale problems
                        # only create a blob if you can find
                        # a very light pixel nearby
                        if row > (dpi/30) and (col-dark_length)>(dpi/20) and col<(image.size[0]-(dpi/20)):
                            p1 = image.getpixel((col-dark_length-(dpi/25),row-(dpi/30)))
                            p2 = image.getpixel((col-dark_length-(dpi/25)-1,row-(dpi/30)))
                            p3 = image.getpixel((col-dark_length-(dpi/25)-2,row-(dpi/30)))
                            p4 = image.getpixel((col+(dpi/25),row-(dpi/60)))
                            p5 = image.getpixel((col+(dpi/25)+1,row-(dpi/60)))
                            if (
                                (p1[0]+p1[1]+p1[2]) > (dark_threshold*3) 
                                or (p2[0]+p2[1]+p2[2]) > (dark_threshold*3)
                                or (p3[0]+p3[1]+p3[2]) > (dark_threshold*3)
                                or (p4[0]+p4[1]+p4[2]) > (dark_threshold*3)
                                or (p5[0]+p5[1]+p5[2]) > (dark_threshold*3)
                                    ):
                                z = Blob(self,
                                         self.dpi,
                                         col-dark_length+1,
                                         col,
                                         row)
                                blob_list.append(z)
                            else:
                                pass
                        else:
                            z = Blob(self,
                                     self.dpi,
                                     col-dark_length+1,
                                     col,
                                     row)
                            blob_list.append(z)
                            # dark areas will generate huge blob lists
                            # no reasonable ballot should have contests
                            # generating more than 100 blobs per row
                            if len(blob_list)>(100*max_age):
                                return []
                    pass
                else:
                    pass

        widths = []
        for b in output_blobs:
            widths.append(b.end_x - b.start_x + 1)
        widths.sort()
        total_width = 0
        for w in widths:
            total_width += w
        if len(widths)>0:
            avg_width = total_width/len(widths)
            print avg_width
            #print output_blobs
            output_blobs = [x for x in output_blobs if (x.end_x - x.start_x) > (1.75 * avg_width)]
            output_blobs.sort()
        else:
            return []



        return output_blobs
        

    def __repr__(self):
        if self.blob_list is None: self.blob_list = []
        retstr = "Line, x1=%d, y1= %d, x2= %d, y2=%d, targets=%d\n    text=%s\n" % (
            self.x1,self.y1,
            self.x2,self.y2,
            len(self.blob_list),
            "!".join(self.text_list))
        for l in self.blob_list:
            retstr += l.__repr__()
            retstr += "\n"
        return retstr

class Box(object):
    def __init__(self, column, image, dpi, x1, y1, x2, y2):
        self.column = column
        self.image = image
        self.dpi = dpi
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.w = self.x2 - self.x1 
        self.h = self.y2 - self.y1 
        self.line_list = []
        self.header_text = None
        self.choice_list = []
        
        self.line_list = self.populate_lines(image,self.dpi)

    def populate_lines(self,image,dpi):
        gaps = []
        lines = []
        # to separate lines on halftone, must use a low darkness threshold
        # but to handle weak prints, must use a high one (*sigh*)
        # this will need to be fed in or determined on a situational basis
        darkness_threshold = 96

        for y in range(3,image.size[1]-4):
            zone0 = image.crop((dpi/16,y-3,image.size[0]-(dpi/16),y-2))
            zone1 = image.crop((dpi/16,y,image.size[0]-(dpi/16),y+1))
            stat0 = ImageStat.Stat(zone0)
            stat1 = ImageStat.Stat(zone1)
            min0 = stat0.extrema[0][0]
            min1 = stat1.extrema[0][0]
            last_gap = 0
            if ( min1>=darkness_threshold 
                 and ( min0<darkness_threshold ) ) :
                if y == 447: pdb.set_trace()
                gaps.append(y)

        last_gap = 0
        if len(gaps)==0:
            lines.append(Line(
                    self,
                    image,
                    dpi,
                    0,0,image.size[0],image.size[1]))
        for gap in gaps:
            # print last_gap,"to",gap
            # no text if less than 1/16" tall, probably write-in underline
            if (gap-last_gap) < (dpi/16):
                last_gap = gap
                continue
            lines.append(Line(
                    self,
                    image.crop((0,max(0,last_gap),image.size[0],gap+1)),
                    dpi,
                    0,last_gap,image.size[0],gap+1))
            last_gap = gap
        return lines


    def __repr__(self):
        retstr = "ContestBox, dpi = %d, x1 = %d, y1 = %d, x2 = %d, y2 = %d\n" % (
            self.dpi, self.x1, self.y1, self.x2, self.y2)
        for l in self.line_list:
            retstr += l.__repr__()
            retstr += "\n"
        return retstr

class Column(object):
    def __init__(self, side, image, dpi, x1, y1, x2, y2):
        self.side = side
        self.image = image
        self.dpi = dpi
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.w = self.x2 - self.x1 
        self.h = self.y2 - self.y1 
        
        self.box_list = self.populate_boxes(image,self.dpi)

    def populate_boxes(self,image,dpi,inboard=10):
        lines = []
        # horizontal lines should be quite dark
        darkness_threshold = 64
        skip = (dpi/16)
        for y in range((dpi/60)+1,image.size[1]-(dpi/60)-1):
            pix0 = image.getpixel((inboard,y-(dpi/60)))
            pix1 = image.getpixel((inboard,y))
            pix2 = image.getpixel((inboard,y+(dpi/60)))
            # we don't want to keep triggering in continuous dark areas
            if ( intensity(pix1)<darkness_threshold 
                 and ( intensity(pix0)>=darkness_threshold 
                      or intensity(pix2)>=darkness_threshold ) 
                 and dark_on_right(
                    image,dpi,y,darkness_threshold,inboard) ) :
                # don't append lines within skip of last line
                if len(lines)>0 and y >= (lines[-1]+skip):
                    lines.append(y)
                if len(lines)==0:
                    lines.append(y)
                
        # run through lines and consolidate sequences 
        # that are separated by exactly skip; these must be 
        # zones of solid black, perhaps with text in white
        if len(lines)>1:
            for index in range(len(lines)-1):
                if (lines[index+1]-lines[index]) == skip:
                    print lines
                    pdb.set_trace()
                
        last_l = 0
        box_list = []
        lines.append(image.size[1]-1)
        for l in lines:
            print last_l,"to",l
            boximage = image.crop((0,last_l,image.size[0],l))
            box_list.append(Box(self,boximage,self.dpi,0,last_l,image.size[0],l)) 
            last_l = l
        return box_list


    def __repr__(self):
        retstr = "Column, dpi = %d, x1 = %d, y1 = %d, x2 = %d, y2 = %d\n" % (
            self.dpi, self.x1, self.y1, self.x2, self.y2)
        for b in self.box_list:
            retstr += b.__repr__()
            retstr += "\n"
        return retstr

class Side(object):
    def __init__(self,image,dpi):
        self.image = image
        self.dpi = int(dpi)
        self.original_tangent = 0
        self.column_list = []

        try:
            self.original_tangent = get_tangent(image,dpi=dpi)
        except NoLineException,e:
            print e
            sys.exit(0)
        self.image = self.image.rotate(-self.original_tangent*360./6.28)
        #print "Rotated %f degrees." % (-median_tangent*360./6.28)
        #image.save("/tmp/rot.jpg")

        tlist_to_merge = []
        skip = 0
        print "Forward pass"
        y, active_tlist,inactive_tlist = find_intensity_boundaries(
            image,
            dpi/30, #5, # narrow for line search
            dpi,  # min to constitute line
            dpi/5, # gap of this size breaks
            starting_x = dpi/30,
            max_width = image.size[0]-(dpi/30)
            )
        skip = (dpi/16)
        tlist_to_merge.extend(inactive_tlist)
        tlist_to_merge.extend(active_tlist)
        print "Backward pass"
        y, active_tlist,inactive_tlist = find_intensity_boundaries(
            image, 
            dpi/30, #5, # narrow for line search
            dpi,
            dpi/5,
            starting_x = dpi/30,
            search_forwards=False,
            max_width = image.size[0]-(dpi/30)
            )

        # reject any lines within 1/6" of edge
        sixth = dpi/6
        tlist_to_merge = [x for x in tlist_to_merge 
                 if ((x.startx > sixth) and (x.startx < image.size[0]-sixth))]

        #for v in tlist_to_merge: print v
        #pdb.set_trace()
        #print "Merging %d line fragments." % (len(tlist_to_merge),)
        v_endpoints = merge_transition_list(tlist_to_merge)
        # lines must be at least dpi tall to count
        v_endpoints = [x for x in v_endpoints if x[1] < (x[3]-dpi)]  
        #for v in v_endpoints: print v
        #pdb.set_trace()

        """v_endpoints = [[331, 205, 331, 4050], 
                       [1023, 910, 1023, 4045], 
                       [1714, 910, 1714, 4045], 
                       [2405, 205, 2405, 4045]]

        """
        self.column_list = []
        for i in range(len(v_endpoints)-1):
            second_boxbottom = -1
            second_boxright = -1
            j = i+1
            boxleft = v_endpoints[i][0]
            boxright = v_endpoints[j][0]
            boxbottom = v_endpoints[i][3]
            boxtop = max(v_endpoints[i][1],v_endpoints[j][1])
            if v_endpoints[i][1]<=(v_endpoints[j][1]-(dpi/10)):
                second_boxtop = min(v_endpoints[i][1],v_endpoints[j][1])
                second_boxbottom = max(v_endpoints[i][1],v_endpoints[j][1])
                # search remainder of list for new[1] = i[1]
                for k in range(j+1,len(v_endpoints)):
                    if abs(v_endpoints[i][1]-v_endpoints[k][1])<(dpi/10):
                        second_boxright = v_endpoints[k][0]
            box = [boxleft,boxtop,boxright,boxbottom]
            if second_boxbottom>=0 and second_boxright >=0:
                second_box = [boxleft,
                              second_boxtop,
                              second_boxright,
                              second_boxbottom]
                #print "Boxlist gets second box",second_box
                column_image = image.crop(second_box)
                self.column_list.append( 
                    Column(self,
                           column_image, 
                           self.dpi,
                           boxleft, 
                           second_boxtop, 
                           second_boxright, 
                           second_boxbottom) )
            #print "Boxlist gets",box
            column_image = image.crop(box)
            self.column_list.append( 
                Column( self,
                        column_image, self.dpi, 
                        boxleft, boxtop, boxright, boxbottom )
                )
        #for box in self.column_list:
        #    try:
        #        print "B>",box
        #        image.crop(box).save(
        #            "/tmp/column_%d_%d_%d_%d.jpg" % (box[0],box[1],box[2],box[3]))
        #    except Exception, e:
        #        print e
    def __repr__(self):
        retstr = "Side, dpi= %d\n" % (self.dpi,)
        for c in self.column_list:
            retstr += c.__repr__()
            retstr += "\n"
        return retstr

class Transition(object):
    def __init__(self,x, y, min_line_break_length):
        self.startx = x
        self.starty = y
        self.endx = x
        self.endy = y
        self.min_line_break_length = min_line_break_length

    def __repr__(self):
        return "Line from (%d,%d) to (%d,%d)" % (self.startx,
                                           self.starty,
                                           self.endx,
                                           self.endy)
    def endpoints(self):
        return ((self.startx,self.starty),(self.endx,self.endy))

    def isactive(self):
        return abs(self.endx-self.startx) < self.min_line_break_length

def intensity(x):
    """return intensity assuming three color pixel x"""
    return int(round((x[0]+x[1]+x[2])/3.0))

def dark_on_right(image,dpi,y_at_left,darkness_threshold,inboard):
    start_y = max(3,y_at_left - (image.size[0]/10))
    end_y = min(image.size[1]-1,y_at_left + (image.size[0]/10))
    check_x = image.size[0] - inboard
    retval = False
    for y in range(start_y,end_y):
        try:
            p = image.getpixel((check_x,y))
        except IndexError, e:
            print check_x,y,"y at left",y_at_left
            print e
        if intensity(p) < darkness_threshold:
            retval = True
            break
    return retval


def offset_of_tlist_entry_with_x_y_slip_n(tlist,x,y,n=15):
    for offset,t in enumerate(tlist):
        if t.endx > (x-n) and t.endx < (x+n) and t.endy > (y-n) and t.endy < (y+n):
            return offset
    return -1

def move_inactive_transitions(y, min_line_break_length,active,inactive):
    delete_from_active = []
    for t in active:
        if abs(y - t.endy) >= min_line_break_length:
            inactive.append(t)
            delete_from_active.append(t)
    for t in delete_from_active:
        active.remove(t)


def find_intensity_boundaries(image, 
                              skip_between_lines, 
                              min_extent, 
                              min_line_break_length,
                              required_intensity_drop=50, 
                              intensity_drop_span=2, 
                              search_forwards=True,
                              starting_x = 0,
                              max_width = None):
    """return list of intensity boundaries meeting or exceeding min_extent"""
    idrop = intensity_drop_span
    if max_width is None:
        max_width = image.size[0] - idrop
    else:
        pass
    active_tlist = []
    inactive_tlist = []
    if starting_x>0:
        xrange_start = starting_x + idrop
        xrange_end = min(starting_x + idrop + max_width,image.size[0]-1)
    else:
        xrange_start = 1+idrop
        xrange_end = max_width
    xrange_incr = 1
    if not search_forwards:
        xrange_start, xrange_end = xrange_end, xrange_start
        xrange_incr = -1

    for y in range(0, image.size[1], skip_between_lines):
        move_inactive_transitions(y, 
                                  min_line_break_length, 
                                  active_tlist, 
                                  inactive_tlist)

        xrange_end = min(xrange_end,image.size[0]-abs(idrop+1)) 
        for x in range(xrange_start, xrange_end, xrange_incr):
            #if y>500 and x > 48:
            #    print x,y,min_line_break_length
            #    print active_tlist
            #    print inactive_tlist
            #    pdb.set_trace()
                
            for z in range(idrop):
                try:
                    pix1 = image.getpixel((x,y))
                    pix2 = image.getpixel((
                            x+((z+1)*xrange_incr),
                            y
                            ))
                except IndexError,e:
                    print x,y,image.size
                    print e
                if (intensity(pix1) >= 
                    (intensity(pix2) + required_intensity_drop)):
                    offset = offset_of_tlist_entry_with_x_y_slip_n(
                        active_tlist,
                        x,
                        y - skip_between_lines,
                        2)
                    if offset>-1:
                        active_tlist[offset].endx = x
                        active_tlist[offset].endy = y
                    else:
                        active_tlist.append(
                            Transition(x,y,min_line_break_length)
                            )
    active_good = [x for x in active_tlist if (x.endy - x.starty)>min_extent]
    inactive_good = [x for x in inactive_tlist 
                     if (x.endy - x.starty)>min_extent]
    #print y
    #print active_good
    #print inactive_good
    #pdb.set_trace()
    return y,active_good,inactive_good

def get_tangent(image,dpi):
    # scan only the first four inches looking for vertical lines
    print "Get tangent"
    y, active_tlist,inactive_tlist = find_intensity_boundaries(
        image, 
        10, # wide for simple rotation check
        int(dpi)*2, 
        25,
        max_width=dpi*2)
    print y, active_tlist, inactive_tlist
    pdb.set_trace()
    if len(inactive_tlist)==0:
        raise NoLineException("No line in first two inches.")
    tangents = []
    for line in inactive_tlist:
        tangents.append((line.endx-line.startx)/float(line.endy-line.starty))
    tangents.sort()
    #print "Tangents of lines > 2 dpi",tangents
    try:
        median_tangent = tangents[len(tangents)/2]
    except Exception, e:
        print e
        for line in inactive_tlist:
            tangents.append((line.endx-line.startx)/float(line.endy-line.starty))
        tangents.sort()
        #print "Tangents of all lines",tangents
        median_tangent = tangents[len(tangents)/2]
    return median_tangent


def merge(times):
    """thank you stackoverflow user samplebias"""
    saved = list(times[0])
    for st, en in sorted([sorted(t) for t in times]):
        if st <= saved[1]:
            saved[1] = max(saved[1], en)
        else:
            yield tuple(saved)
            saved[0] = st
            saved[1] = en
    yield tuple(saved)

def merge_transition_list(tlist_to_merge):
    v_endpoints = []
    tlist_to_merge.sort(key = lambda x: x.startx)
    split_indices = [0]
    lastx = 0
    for (index,line) in enumerate(tlist_to_merge):
        if (line.startx - lastx)>50: 
            split_indices.append(index)
        lastx = line.startx
    print split_indices
    print "^Split indices"
    #pdb.set_trace()
    for split_loc_index in range(len(split_indices)):
        try:
            end = split_indices[split_loc_index+1]
        except IndexError:
            end = -1
        sublist_to_merge = tlist_to_merge[split_indices[split_loc_index]:end]
        #print "Sublist_to_merge",sublist_to_merge
        # from the sublist, take the startx of the middle value
        # for every line in the zone
        if len(sublist_to_merge)>0:
            median_x = sublist_to_merge[len(sublist_to_merge)/2].startx
            endpoint_ys = [(t.starty,t.endy) for t in sublist_to_merge]
            endpoint_ys.sort()
            endpoint_ys2 = list(merge(endpoint_ys))
            endpoint_ys = endpoint_ys2
            new_endpoints = [[median_x,min(t[0],t[1]),median_x,max(t[0],t[1])] for t in endpoint_ys]
            v_endpoints.extend(new_endpoints)
            #print "Median x",median_x
            #print "New endpoints",new_endpoints
    #print "Tentative list",v_endpoints
    # for each x value, see if the endpoint of any line 
    # is within 1/10" of the start of the next; if so,
    # merge them.
    tmp_dict = {}
    tenth = 30
    for line in v_endpoints:
        if line[0] in tmp_dict:
            tmp_dict[line[0]].append(line)
        else:
            tmp_dict[line[0]]=[line]
    xkeys = tmp_dict.keys()
    xkeys.sort()
    final_endpoints = []
    for x in xkeys:
        lines = tmp_dict[x]
        lines.sort(key = lambda l: l[1])
        for index in range(1,len(lines)):
            if abs(lines[index][1] - lines[index-1][3]) < tenth:
                lines[index-1][3] = lines[index][3]
                lines[index][1] = -1
        # ensure each output set of end coordinates begins with low vals,
        # and ends with high vals
        final_endpoints.extend(
            [ [ min(x[0],x[2]),min(x[1],x[3]),max(x[0],x[2]),max(x[1],x[3]) ] 
              for x in lines if x[1] >= 0]
            )
    return final_endpoints


if __name__ == "__main__":
    dpi = int(sys.argv[1])
    if len(sys.argv)<3:
        print "usage columns.py dpi file"
    darkness_threshold = 208
    use_tint_test, use_wide_bounded_test = False,False
    bloblist, tinted_rows = None, None
    # other tests can be added, e.g. for arrows
    image = Image.open(sys.argv[2]).convert("RGB")
    basename = os.path.basename(sys.argv[2])
    s = Side(image,dpi)
    txtfile = open("/tmp/%s.txt" % (basename,),"w")
    txtfile.write("%s"%(s,))
    txtfile.close()
    print "Wrote side"
    pdb.set_trace()
    #picklefile = open("/tmp/side.pickle","w")
    #pickle.dump(s,picklefile)
    #picklefile.close()
    # A landmark is a block of black whose dimensions are at least 1/16"
    # by 1/16", and which is surrounded above, below, and to the inside
    # by white.
    # The landmark's location is defined as it's inside corner: bottom
    # corner if on top, top if on bottom; right corner if at left, left 
    # if at right.

    # We capture the uppermost and lowermost landmarks in the region
    # not taken up by columns.  If no landmarks are found on the left,
    # we continue to inspect the right.

    # In addition to noting the landmark's location, we note the x,y
    # displacement of that location from the upper left corner of the
    # closest column.
