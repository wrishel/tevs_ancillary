class BoxList(object):
    def __init__(self,vline_endpoints,hline_endpoints,image=None):
        """given lists of line segments, discover and store boxes they form"""
        genviz = True
        self.veps = vline_endpoints
        self.heps = hline_endpoints
        
        self.cornerlist = []
        self.crosslist = []
        self.boxlist = []
        self.image = image
        # create a new image matching size of old image
        if genviz:
            viz = Image.new("RGB",self.image.size,(255,255,255))
            drawviz = ImageDraw.Draw(viz)
        tenth = 0
        last_cornerlist_length = 0
        true_pass = 0
        new_heps = []
        new_veps = []
        while True:
            self.veps.extend(new_veps)
            self.heps.extend(new_heps)
            new_heps = []
            new_veps = []

            for vep in self.veps:
                #print [v for v in self.veps if v[0]<150]
                vep_seg = LineSegment(vep[0],vep[1],
                                      vep[2],vep[3])
                if genviz:
                    drawviz.line((vep[0],vep[1],
                                  vep[2],vep[3]),fill=(255,0,0))
                newsegs = []
                for hep in self.heps:
                    hep_seg = LineSegment(hep[0],hep[1],hep[2],hep[3])
                    #if hep[1]>2350 and hep[1]<2450:
                    #    print "At 100,2400"
                    #    pdb.set_trace()
                    if genviz:
                        drawviz.line((hep[0],hep[1],hep[2],hep[3]),fill=(0,0,0))
                    vep_hep = vep_seg.joins_at(hep_seg)
                    hep_vep = hep_seg.joins_at(vep_seg)
                    if vep_hep is not None:
                        # break the lines at this point
                        # if segments long enough,
                        # put two new lines into array of vep
                        # put two new lines into array of hep
                        self.cornerlist.append(vep_hep)
                        newheps,newveps = break_hep_and_vep(hep,vep,vep_hep)
                        if genviz:
                            drawviz.rectangle((vep_hep.x-10,
                                               vep_hep.y-10,
                                               vep_hep.x+10,
                                               vep_hep.y+10),
                                              outline=(255,0,0))
                    elif hep_vep is not None:
                        # break the lines at this point
                        # if segments long enough,
                        # put two new lines into array of vep
                        # put two new lines into array of hep
                        self.cornerlist.append(hep_vep)
                        newheps,newveps = break_hep_and_vep(hep,vep,hep_vep)
                        if genviz:
                            drawviz.rectangle((hep_vep.x-10,
                                               hep_vep.y-10,
                                               hep_vep.x+10,
                                               hep_vep.y+10),
                                              outline=(0,255,0))
                        # now need to repeat from just past this corner
                    else:
                        vep_hep = vep_seg.crosses_at(hep_seg)
                        if vep_hep is not None:
                            # break the lines at this point
                            # if segments long enough,
                            # put two new lines into array of vep
                            # put two new lines into array of hep
                            self.cornerlist.append(Corner(vep_hep.x,vep_hep.y))
                            newheps,newveps = break_hep_and_vep(hep,vep,vep_hep)
                            if genviz:
                                drawviz.rectangle((vep_hep.x-10,
                                                   vep_hep.y-10,
                                                   vep_hep.x+10,
                                                   vep_hep.y+10),
                                                  outline=(0,0,255))


            new_heps.extend(newheps)
            new_veps.extend(newveps)
            self.cornerlist.extend(self.crosslist)
            # eliminate near duplicates from cornerlist
            corner_dict = {}
            for corner in self.cornerlist:
                corner_dict[(corner.x/5,corner.y/5)] = corner
            self.cornerlist = corner_dict.values()
            cornerlist_length = len(self.cornerlist)
            if cornerlist_length == last_cornerlist_length:
                break
            last_cornerlist_length = cornerlist_length
            true_pass = true_pass + 1
            if true_pass > 1:
                print "TRUE PASS",true_pass
            if true_pass > 5:
                pdb.set_trace()
                break
        # determine whether each corner has lines extending n,s,e,w
        fifteenth = 20
        extension_requires = 100
        for corner in self.cornerlist:
            #corner.fill_compass_from(self.image)
            corner.set_compass_from_veps(self.veps,
                                         threshold=fifteenth)
            corner.set_compass_from_heps(self.heps,
                                         threshold=fifteenth,
                                         extension_requires=extension_requires)

        # eliminate near duplicates from cornerlist, snap to mod 5
        corner_dict = {}
        for corner in self.cornerlist:
            corner_dict[( int(round(corner.x/5.)),
                          int(round(corner.y/5.))) ] = corner
        self.cornerlist = corner_dict.values()

        if genviz:
            for corner in self.cornerlist:
                fillred = 0
                fillgreen = 0
                fillblue = 0

                if corner.n or corner.s:
                    fillred=128
                else:
                    fillred=0

                if corner.e or corner.w:
                    fillblue=128
                else:
                    fillblue=0
                if corner.n:
                    drawviz.rectangle(
                        (corner.x-2,corner.y,corner.x+2,corner.y-75),
                        fill=(fillred,fillgreen,fillblue))
                if corner.s:
                    drawviz.rectangle(
                        (corner.x-2,corner.y,corner.x+2,corner.y+75),
                        fill=(fillred,fillgreen,fillblue))
                if corner.e:
                    drawviz.rectangle(
                        (corner.x,corner.y-2,corner.x+75,corner.y+2),
                        fill=(fillred,fillgreen,fillblue))
                if corner.w:
                    drawviz.rectangle(
                        (corner.x,corner.y-2,corner.x-75,corner.y+2),
                        fill=(fillred,fillgreen,fillblue))


        # sort corners, crosses by default sort, x1
        self.cornerlist.sort(key = lambda p: p.x)
        self.crosslist.sort()
        # find zones of similar x's
        dpi = 300
        threshold = dpi/8
        min_box_height = dpi/6
        min_box_width = dpi
        zonesize = dpi/8
        zone = 0
        zonechanges = [0]
        for index,p in enumerate(self.cornerlist):
            if abs(p.x - zone)>zonesize:
                zonechanges.append(index)
                zone = p.x
        zonechanges.append(1000000)
        # divide corners into zones by x
        # sort the x zone into y order
        # for every point in a given x zone
        # search the points in the x zone
        # and its immediate neighbor zones to find the nearest y value
        # that's the boxes lower corner if the y diff is > threshold

        # The resulting Corners should be combined into vertical
        # line segments tagged with the direction(s) they join at
        # both the top and bottom.  A vertical line segment 
        # forms a complete side of a box ONLY if it joins in e on both
        # ends, or joins on w at both ends.  Likewise, a horizontal
        # line segment forms a complete box only if both ends have joins
        # with n or both ends have joins with s.
        # to form the side of a box if bot

        height_dict = {}
        
        for zci in range(len(zonechanges)-1):
            #if zci>0 and zci<(len(zonechanges)-2):
            #    corners = self.cornerlist[zonechanges[zci-1]:zonechanges[zci+2]]
            #else:
            corners = self.cornerlist[zonechanges[zci]:zonechanges[zci+1]]
            corners.sort(key = lambda p: p.y)
            for corner1_index,corner1 in enumerate(corners):
                p1 = Point(corner1.x,corner1.y)
                min_ydiff = 1000000
                closest_point = None
                #if p1.y >1800 and p1.y< 2000 and p1.x < 100:pdb.set_trace()
                for corner2 in corners[corner1_index+1:]:
                    p2 = Point(corner2.x,corner2.y)
                    # guaranteed non-negative if list sorted on y
                    ydiff = (p2.y - p1.y)
                    assert ydiff>=0
                    if (ydiff < min_ydiff 
                        and ydiff >= min_box_height 
                        and corner1.workswith(corner2)):
                        min_ydiff = ydiff
                        closest_point = Point(p2.x,p2.y)
                # now have closest_point to p1 with greater y; diff is height
                try:
                    if closest_point is not None:
                        height_dict[(p1.x,p1.y)] = closest_point.y - p1.y
                        if genviz:
                            height_of_rect = closest_point.y - p1.y
                            drawviz.rectangle((p1.x,p1.y,p1.x+5,p1.y+height_of_rect),fill=(255,0,0))
                    #else:
                    #    height_dict[(p1.x,p1.y)] = 1
                except AttributeError,e:
                    #height_dict[(p1.x,p1.y)] = 1
                    print e
                    pdb.set_trace()
                    pass

        # divide corners into zones by y
        # sort the y zone into x order
        # for every point in a given y zone
        # search the points in the y zone to find the nearest x value
        # that's the boxes right corner if the x diff is > threshold
        zonechanges = [0]
        zone = 0
        self.cornerlist.sort(key = lambda p: p.y)
        for index,p in enumerate(self.cornerlist):
            if abs(p.y - zone)>zonesize:
                zonechanges.append(index)
                zone = p.y
        zonechanges.append(1000000)
        width_dict = {}
        for zci in range(len(zonechanges)-1):
            #if zci>0 and zci<(len(zonechanges)-2):
            #    corners = self.cornerlist[zonechanges[zci-1]:zonechanges[zci+2]]
            #else:
            corners = self.cornerlist[zonechanges[zci]:zonechanges[zci+1]]
            corners.sort(key = lambda p: p.x)
            for corner1_index,corner1 in enumerate(corners):
                p1 = Point(corner1.x,corner1.y)
                #if p1.y >1800 and p1.y< 2000 and p1.x < 100:
                #    print corners[corner1_index+1:]
                #    pdb.set_trace()
                min_xdiff = 1000000
                closest_point = None
                for corner2 in corners[corner1_index+1:]:
                    p2 = Point(corner2.x,corner2.y)
                    # guaranteed non-negative if list sorted on x
                    xdiff = (p2.x - p1.x)
                    assert xdiff >=0
                    if (xdiff < min_xdiff 
                        and xdiff >= min_box_width 
                        and corner1.workswith(corner2)):
                        min_xdiff = xdiff
                        closest_point = Point(p2.x,p2.y)
                # now have closest_point to p1 with greater x; diff is width
                try:
                    if closest_point is not None:
                        width_dict[(p1.x,p1.y)] = closest_point.x - p1.x
                        if genviz:
                            width_of_rect = closest_point.x - p1.x
                            drawviz.rectangle((p1.x,p1.y,p1.x+width_of_rect,p1.y+5),fill=(0,0,255))
                except AttributeError,e:
                    print e
                    pdb.set_trace()

        #print height_dict
        #print width_dict
        #print "Height dict keys",len(height_dict.keys())
        #print "Width dict keys",len(width_dict.keys())
        self.height_dict = height_dict
        self.width_dict = width_dict
        hdk = height_dict.keys()
        wdk = width_dict.keys()
        for p in self.cornerlist:
            if (p.x,p.y) in height_dict and (p.x,p.y) in width_dict:
                try:
                    if genviz:
                        drawviz.line((p.x,
                                     p.y,
                                     p.x+width_dict[(p.x,p.y)],
                                     p.y+height_dict[(p.x,p.y)]))
                    self.boxlist.append(
                        (p.x,
                         p.y,
                         width_dict[(p.x,p.y)],
                         height_dict[(p.x,p.y)])
                        )
                except KeyError:
                    print type(p)
                    pdb.set_trace()
        # if boxes differ only within a threshold 
        # on their x, y, height and width, 
        # replace both with a new box using the lower x and y
        # and the higher width and height

        threshold = 30
        merged_boxes = []
        deleted_indices = []
        for index1 in range(len(self.boxlist)):
            if index1 in deleted_indices: pass
            for index2 in range(index1+1,len(self.boxlist)):
                if index2 in deleted_indices: pass
                if (
                    (abs(self.boxlist[index1][0] 
                        - self.boxlist[index2][0]) < threshold)
                and
                    (abs(self.boxlist[index1][1] 
                        - self.boxlist[index2][1]) < threshold)
                and
                    (abs(self.boxlist[index1][2] 
                        - self.boxlist[index2][2]) < threshold*2)
                and
                    (abs(self.boxlist[index1][3] 
                        - self.boxlist[index2][3]) < threshold*2)
                ):
                    # replace index1 and index2 with a merge
                    if not (index1 in deleted_indices and index2 in deleted_indices):
                        merged_boxes.append( (min(self.boxlist[index1][0],
                                                  self.boxlist[index2][0]),
                                              min(self.boxlist[index1][1],
                                                  self.boxlist[index2][1]),
                                              max(self.boxlist[index1][2],
                                                  self.boxlist[index2][2]),
                                              max(self.boxlist[index1][3],
                                                  self.boxlist[index2][3]))
                                             )
                        deleted_indices.append(index1)
                        deleted_indices.append(index2)
                    if genviz:
                        drawviz.line((merged_boxes[-1][0],
                                     merged_boxes[-1][1]+merged_boxes[-1][3],
                                     merged_boxes[-1][0]+merged_boxes[-1][2],
                                     merged_boxes[-1][1]),
                                     fill=(0,255,0))
        #print "Deleted indices",len(deleted_indices)
        #print "Merges",len(merged_boxes)
        for b in range(len(self.boxlist)):
            if b not in deleted_indices:
                merged_boxes.append(self.boxlist[b])
                if genviz:
                    drawviz.line((merged_boxes[-1][0],
                                  merged_boxes[-1][1]+merged_boxes[-1][3],
                                  merged_boxes[-1][0]+merged_boxes[-1][2],
                                  merged_boxes[-1][1]),
                                 fill=(255,0,255))
        self.boxlist = merged_boxes
        # sort on x (with slip) then y
        self.boxlist.sort(key = lambda b: (b[0]/100)*1000000 + b[1])
        #print "Final boxlist length",len(self.boxlist)
        if genviz:
            viz.save("/tmp/viz.jpg")
 

    def __repr__(self):
        return __repr__(self.boxlist)
            
class LineSegment(object):
    def __init__(self,x1, y1, x2, y2,left_corner="L",right_corner="R"):
        self.startx = x1
        self.starty = y1
        self.endx = x2
        self.endy = y2
        self.left_corner_type = left_corner
        self.right_corner_type = right_corner

    #def __init__(self,endpoints,left_corner="L",right_corner="R"):
    #    self.startx = endpoints[0][0]
    #    self.starty = endpoints[0][1]
    #    self.endx = endpoints[1][0]
    #    self.endy = endpoints[1][1]
    #    self.left_corner_type = left_corner
    #    self.right_corner_type = right_corner

    def __repr__(self):
        return "Line type %s-%s from (%d,%d) to (%d,%d)" % (
            self.left_corner_type,
            self.right_corner_type,
            self.startx,
            self.starty,
            self.endx,
            self.endy)

    def crosses(self,other):
        """do 2 lines intersect; from bryceboe.com"""
        # we can shift the vline forward and back to look for joins
        # we can shift the hline up and down to look for joins 
        return intersect(
            self.startx,self.starty,self.endx,self.endy,
            other.startx,other.starty,other.endx,other.endy
            )
    def crosses_at(self,other):
        if not self.crosses(other):
            return None
        return intersect_loc(self.startx,self.starty,self.endx,self.endy,other.startx,other.starty,other.endx,other.endy)

    def right(self,rightpix=15):
        return LineSegment(self.startx+rightpix,self.starty,self.endx+rightpix,self.endy)
    def down(self,downpix=15):
        return LineSegment(self.startx,self.starty+downpix,self.endx,self.endy+downpix)
    def left(self,leftpix=15):
        return self.right(-leftpix)
    def up(self,uppix=15):
        return self.down(-uppix)

    def joins(self,other):
        """ does crossing change if a line segment's main axis is slightly shifted?"""
        other_is_horizontal = False
        other_width = abs(other.endx - other.startx)
        other_height = abs(other.endy - other.starty)
        if other_width > other_height:
            other_is_horizontal = True
        # the equivalent of shifting the other 
        # followed by self.crosses(other) is
        # shifting self in the opposite direction
        # followed by other.crosses(shiftedself)
        #
        # if other is horizontal, we don't move it left or right,
        # we move ourself
        if other_is_horizontal:
            self_shiftedright = self.right()
            self_shiftedleft = self.left()
            other_shiftedup = other.up()
            other_shifteddown = other.down()
            if (other.crosses(self_shiftedright) 
                != other.crosses(self_shiftedleft)):
                return True
            if (self.crosses(other_shiftedup) != 
                self.crosses(other_shifteddown)):
                return True
        else:
            self_shiftedup = self.up()
            self_shifteddown = self.down()
            other_shiftedleft = other.left()
            other_shiftedright = other.right()
            if (self.crosses(other_shiftedright) 
                != self.crosses(other_shiftedleft)):
                return True
            if (other.crosses(self_shiftedup) != 
                other.crosses(self_shifteddown)):
                return True
            
        return False

    def nearest(self,point):
        """return closest endpoint on self to other"""
        corner = None
        xdiff = abs(self.startx - point.x)
        ydiff = abs(self.starty - point.y)
        start_diff = xdiff+ydiff
        corner = "S"
        xdiff = abs(self.endx - point.x)
        ydiff = abs(self.endy - point.y)
        end_diff = xdiff+ydiff
        if end_diff < start_diff:
            return Point(self.endx,self.endy)
        return Point(self.startx,self.starty)
            

    def joins_at(self,other):
        other_is_horizontal = False
        other_width = abs(other.endx - other.startx)
        other_height = abs(other.endy - other.starty)
        if other_width > other_height:
            other_is_horizontal = True
        retx = 0
        rety = 0
        if other_is_horizontal:
            self_shiftedleft = self.left()
            self_shiftedright = self.right()
            for o in (other,other.up(),other.down()):
                lc = o.crosses(self_shiftedleft)
                rc = o.crosses(self_shiftedright)
                if lc or rc:
                    try:
                        p1 = o.crosses_at(self_shiftedleft)
                        p2 = o.crosses_at(self_shiftedright)
                        if p1 is not None:
                            retx = p1.x
                            rety = p1.y
                        else:
                            retx = p2.x
                            rety = p2.y
                    except Exception as e:
                        print e
                    break
        else:
            other_shiftedleft = other.left()
            other_shiftedright = other.right()
            for s in (self,self.up(),self.down()):
                lc = s.crosses(other_shiftedleft)
                rc = s.crosses(other_shiftedright)
                if lc or rc:
                    p1 = s.crosses_at(other_shiftedleft)
                    p2 = s.crosses_at(other_shiftedright)
                    if p1 is not None:
                        retx = p1.x
                        rety = p1.y
                    else:
                        retx = p2.x
                        rety = p2.y
                    break
        if retx==0 and rety==0:
            return None
        #pdb.set_trace()
        c = Corner(retx,rety)
        return c
        

class WideZone(object):
    def __init__(self,
                 start_row,
                 end_row,
                 start_x_at_start_row,
                 end_x_at_start_row,
                 end_x_guard_at_start_row,
                 start_x_at_end_row,
                 end_x_at_end_row,
                 end_x_guard_at_end_row):
        self.start_row = start_row
        self.end_row = end_row
        self.start_x_at_start_row = start_x_at_start_row
        self.end_x_at_start_row = end_x_at_start_row
        self.end_x_guard_at_start_row = end_x_guard_at_start_row
        self.start_x_at_end_row = start_x_at_end_row
        self.end_x_at_end_row = end_x_at_end_row
        self.end_x_guard_at_end_row = end_x_guard_at_end_row

    def __repr__(self):
        return "Widezone, rows %d to %d, cols %d to %d to %d, %d to %d to %d" % (
                 self.start_row,
                 self.end_row,
                 self.start_x_at_start_row,
                 self.end_x_at_start_row,
                 self.end_x_guard_at_start_row,
                 self.start_x_at_end_row,
                 self.end_x_at_end_row,
                 self.end_x_guard_at_end_row)
            

class LightZone(object):
    def __init__(self,start,end,row,height=1):
        self.start = start
        self.end = end
        self.row = row
        self.height = height

    def __repr__(self):
        return "LightZone XS %d, XE %d, RS %d, RC %d" % (
            self.start,
            self.end,
            self.row,
            self.height)

class Point(object):
    def __init__(self,x,y):
        self.x = x
        self.y = y

    def __repr__(self):
        return "(%d,%d)" % (self.x,self.y)

class Corner(object):
    def __init__(self,x,y,direction=None):
        self.x = x
        self.y = y
        self.n = False
        self.e = False
        self.s = False
        self.w = False
        self.direction = direction

    def __repr__(self):
        return "(%d,%d, N %s S %s E %s W %s Dir %s)" % (self.x,self.y,self.n,self.s,self.e,self.w,self.direction)

    def set_compass_from_veps(self,veps,threshold=20):
        """set north and south on corner based on which lines go through"""
        # relevant vep will have x values within threshold
        relevant = [x for x in veps if abs(x[0] - self.x) < threshold]
        for l in relevant:
            # if vep begins before corner and ends after, set n & s
            assert l[1]<l[3]
            if ( l[1] < (self.y - threshold) 
                 and l[3] > (self.y + threshold) ):
                self.n, self.s = True,True
            # if vep begins before corner and end at or near, set n
            if ( l[1] < (self.y + threshold)
                   and l[3] > (self.y - threshold) ):
                self.n = True
            # if vep ends after corner and begins at or near, set s
            if ( l[3] > (self.y + threshold)
                   and l[1] < (self.y + threshold) ):
                self.s = True

    def set_compass_from_heps(self,heps,threshold=310,extension_requires=100):
        """set east and west on corner based on which lines go through"""
        # relevant hep will have y values within threshold
        relevant = [y for y in heps if abs(y[1] - self.y)<threshold]
        for l in relevant:
            # if hep begins well before corner and ends after, set e & w
            if ( l[0] < (self.x - extension_requires) 
                 and l[2] > (self.x + extension_requires) ):
                self.w, self.e = True,True
            # if hep begins well before corner and end at or near, set w
            if ( l[0] < (self.x - extension_requires)
                   and l[2] > (self.x - threshold) ):
                self.w = True
            # if hep ends well after corner and begins at or near, set e
            if ( l[2] > (self.x + extension_requires)
                   and l[0] < (self.x + threshold) ):
                self.e = True

    def fill_compass_from(self,image,pass2=False):
        """check for lines near the specified x,y, given the image"""
        #print "Entering fill compass from"
        region_size = 28
        half_region = region_size/2
        crop = image.crop((self.x-half_region,self.y-half_region,
                           self.x+half_region,self.y+half_region))
        data = list(crop.getdata())
        row_darkcounts = []
        for y in range(crop.size[1]):
            row_darkcounts.append(0)
        col_darkcounts = []
        for x in range(crop.size[0]):
            col_darkcounts.append(0)
        row_count = 0
        col_count = 0
        stride = crop.size[0]
        for num,pix in enumerate(data):
            row_count = num/stride
            col_count = num%stride
            if pix[0]<192:
                row_darkcounts[row_count] += 1
                col_darkcounts[col_count] += 1
        vline_passing = []
        hline_passing = []
        moveup = 0
        moveleft = 0
        for num,row_darkcount in enumerate(row_darkcounts):
            if row_darkcount > 0 and row_darkcount <= (half_region/2):
                #This row is probably participating in a vertical line
                vline_passing.append(num)
            if row_darkcount>(half_region/2):
                if abs(half_region-num)>abs(moveup):
                    moveup = half_region - num

            if row_darkcount>((half_region*3)/2):
                if pass2:
                    self.e = True
                    self.w = True
        for num,col_darkcount in enumerate(col_darkcounts):
            if col_darkcount > 0 and col_darkcount <= (half_region/2):
                #This col is probably participating in a horz line
                hline_passing.append(num)
            if col_darkcount>(half_region/2):
                if abs(half_region-num)>abs(moveleft):
                    moveleft = half_region - num
            if col_darkcount>((half_region*3)/2):
                if pass2:
                    self.n = True
                    self.s = True

        if not pass2:
            self.y = self.y - moveup
            self.x = self.x - moveleft
        try:
            if pass2:
                if (vline_passing[0]+vline_passing[-1])<region_size:
                    self.n = True
                else:
                    self.s = True
        except IndexError:
            pass
        try:
            if pass2:
                if (hline_passing[0]+hline_passing[-1])<region_size:
                    self.w = True
                else:
                    self.e = True
        except IndexError:
            pass
        if not pass2:
            self.fill_compass_from(image,True)
            

                
    def workswith(self,other,threshold=75):
        """are these two points on a dark line segment? """
        d1 = self.direction
        d2 = other.direction
        #if self.x > 1010 and self.x < 1040 and self.y>2220 and self.y < 2240:
        #    print "Does",self,"work with",other
        #    pdb.set_trace()

        # consider different compass points depending on main axis
        if abs(self.x - other.x)<abs(self.y-other.y):
            horizontal = False
        else:
            horizontal = True


        if horizontal:
            if (self.e and other.w and (self.x + threshold)< other.x) or (self.w and other.e and (other.x + threshold) < self.x):
                if ((self.s and other.s) or (self.n and other.n)) and abs(self.y - other.y) < (threshold/2):
                    return True
        else:
            if (self.n and other.s and (other.y+threshold) < self.y) or (self.s and other.n and (self.y + threshold) < other.y):
                if ((self.e and other.e) or (self.w and other.w)) and abs(self.x - other.x) < (threshold/2):
                    return True
        return False
        
def ccw(Ax,Ay,Bx,By,Cx,Cy):
        return (Cy-Ay)*(Bx-Ax) > (By-Ay)*(Cx-Ax)        

def intersect(Ax,Ay,Bx,By,Cx,Cy,Dx,Dy):
        return ( ( ccw(Ax,Ay,Cx,Cy,Dx,Dy) != ccw(Bx,By,Cx,Cy,Dx,Dy) )
                 and ( ccw(Ax,Ay,Bx,By,Cx,Cy) != ccw(Ax,Ay,Bx,By,Dx,Dy) ) )

def intersect_loc(x1,y1,x2,y2,x3,y3,x4,y4):
    x12 = x1 - x2
    x34 = x3 - x4
    y12 = y1 - y2
    y34 = y3 - y4

    c = x12 * y34 - y12 * x34

    if (abs(c) < 0.01):
        return None
    
    a = x1 * y2 - y1 * x2
    b = x3 * y4 - y3 * x4

    x = (a * x34 - b * x12) / c
    y = (a * y34 - b * y12) / c

    return Point(x,y)


class Node(object):
    def __init__(self,v,h,nodetype="X",i=None):
        self.v = v
        self.h = h
        self.nodetype = nodetype
        self.intersection = i

    def intersect(self):
        """determine point at which v and h touch or cross"""
        return Point(0,0)

    def location(self):
        #determine location of line intersection or pull from cache and return
        if self.intersection is not None:
            return self.intersection
        self.intersection = self.intersect()
        return self.intersection

    def __repr__(self):
        return "%s %s %s, isect %s" % (self.v,self.nodetype,self.h,self.intersection)
    

class Box(object):
    def __init__(self,ulc_node,urc_node,llc_node,lrc_node):
        self.x = 0
        self.y = 0
        self.w = 0
        self.h = 0

def break_hep_and_vep(hep,vep,corner,threshold=30):
    """generate up to four line segments from two, splitting them at corner"""
    # if hep's start is on the corner, don't break hep
    rethep,retvep = [],[]
    do_hep,do_vep = True,True
    if abs(hep[0]-corner.x)<threshold and abs(hep[1]-corner.y)<threshold:
        do_hep=False
    if abs(hep[2]-corner.x)<threshold and abs(hep[3]-corner.y)<threshold:
        do_hep=False
    # if vep's start is on the corner, don't break vep
    if abs(vep[0]-corner.x)<threshold and abs(vep[1]-corner.y)<threshold:
        do_vep=False
    if abs(vep[2]-corner.x)<threshold and abs(vep[3]-corner.y)<threshold:
        do_vep=False
    if do_hep:
        rethep.append((hep[0],hep[1],corner.x,corner.y))
        rethep.append((corner.x,corner.y,hep[2],hep[3]))
    if do_vep:
        retvep.append((vep[0],vep[1],corner.x,corner.y))
        retvep.append((corner.x,corner.y,vep[2],vep[3]))
    return rethep,retvep

class ColumnList(object):
    """given list of potential boxes"""
    def __init__(self,boxes,image=None,color=(255,0,0),offset=0):
        self.pboxes = boxes
        self.image = image
        genviz = True
        if genviz:
            self.viz = Image.new("RGB",self.image.size,(255,255,255))
            drawviz = ImageDraw.Draw(self.viz)
            for box in self.pboxes:
                drawviz.rectangle([x+offset for x in box.bbox],
                                  outline=color)
                drawviz.line([x + offset for x in box.bbox],fill=color)
            self.viz.save("/tmp/viz%d.jpg" % (offset,))

def intensity(x):
    """return intensity assuming three color pixel x"""
    return int(round((x[0]+x[1]+x[2])/3.0))
def merge_endpoints(vh_endpoints):
    tenth = 30
    #print
    #print vh_endpoints
    #print
    round_factor = 5
    tmp_dict = {}
    for ep in vh_endpoints:
            x_offset = int(round(float(ep[0][0])/round_factor))
            if (x_offset not in tmp_dict.keys()):
                tmp_dict[x_offset] = [(ep[0][1],ep[1][1])]
            else:
                tmp_dict[x_offset].append(
                    (ep[0][1],ep[1][1])
                    )
    x_offsets = tmp_dict.keys()
    x_offsets.sort()
    ret_endpoints = []
    for x_offset in x_offsets:
            to_be_merged = tmp_dict[x_offset]
            to_be_merged.sort()
            #print "X offset %d to be merged %s" % (x_offset,to_be_merged)
            mlist = list(merge(to_be_merged))
            for m in mlist:
                ret_endpoints.append((x_offset*round_factor,m[0],
                                      x_offset*round_factor,m[1])) 
    return ret_endpoints

        
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

