"""
Tasks:

Given image and dpi, and expecting a fixed 1/4" between vertical dashes...

1)  At image.size[1]/2 (halfway down) look for dash pattern at a series 
of indents into the image. 
"""
import pdb
import Image
import sys

class SomeException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

def dark(p):
    return p[0]<128

def up_one(y,dpi):
    return y - (dpi/4)

def down_one(y,dpi):
    return y + (dpi/4)

def find_middle_dash(image,dpi,indents):
    test_y = image.size[1]/2
    spacing = dpi/4
    retval = None
    for indent in indents:
        for inc_y in range(dpi/4): 
            p0 = image.getpixel((indent,inc_y+test_y))
            p1 = image.getpixel((indent,inc_y+test_y+(spacing/2)))
            p2 = image.getpixel((indent,inc_y+test_y+spacing))
            # break when one pixel is dark and the other two light
            # leaving the x,y of the dark pixel
            if dark(p0) and not dark(p1) and dark(p2):
                retval = (indent,inc_y+test_y)
                break
            elif not dark(p0) and dark(p1) and not dark(p2):
                retval = (indent,inc_y+test_y+(spacing/2))
                break
        if retval is not None:
            break
    # now move up until pixel is white
    for dec_y in range(dpi/16):
        p0 = image.getpixel((retval[0],retval[1]-dec_y))
        if not dark(p0):
            dec_y_by = dec_y
            break

    # and move left until pixel is white
    for dec_x in range(dpi/2):
        p0 = image.getpixel((retval[0]-dec_x,retval[1]))
        if not dark(p0):
            dec_x_by = dec_x
            break

    # handle case where dashes move off image
    # TODO: locate other end, subtract dash length
    if dec_x_by > retval[0]:
        dec_x_by = retval[0]

    # go down 3 pixels, then left or right to a dark pixel
    retval = (retval[0]-dec_x_by,3+retval[1]-dec_y_by)
    if dark(image.getpixel((retval[0]-3,retval[1]))):
        retval = (retval[0]-3,retval[1])
    elif dark(image.getpixel((retval[0]+3,retval[1]))):
        retval = (retval[0]+3,retval[1])
            
    # now move left until retval is white (or end)
    # now move right until retval is white (or end)
    return retval

def find_dash_bbox(image,dpi,x,y):
    "given x,y in dash, find upper right corner of dash"
    "search up until not dark, search down until not dark"
    top_y = y
    bottom_y = y
    left_x = x
    right_x = x
    # top and bottom
    for y_inc in range(dpi/12):
        y_sum = min(image.size[1]-1, y + y_inc)
        p = image.getpixel((x,y_sum))
        if not dark(p):
            bottom_y = y_sum
            break
    for y_inc in range(dpi/12):
        y_sum = max(0, y - y_inc)
        p = image.getpixel((x,y_sum))
        if not dark(p):
            top_y = y_sum
            break
    if bottom_y == top_y:
        return None
    #left and right
    center_y = (top_y+bottom_y)/2
    for x_inc in range(dpi/4):
        x_sum = min(image.size[0]-1, x + x_inc)
        p = image.getpixel((x_sum,center_y))
        if not dark(p) or (x_sum == image.size[0]-1):
            right_x = x_sum
            break
    for x_inc in range(dpi/4):
        x_sum = max(0, x - x_inc)
        p = image.getpixel((x_sum,center_y))
        if not dark(p) or x_sum == 0:
            left_x = x_sum
            break
    return(left_x,top_y,right_x,bottom_y)

def find_dashes(image,dpi):
    """given an image file and its dpi, build two dashlists"""
    left_indents = [dpi/16,
                    2*dpi/16,
                    3*dpi/16,
                    4*dpi/16,
                    5*dpi/16]
    w = image.size[0]
    right_indents = [w-dpi/16,
                     w-(2*dpi/16),
                     w-(3*dpi/16),
                     w-(4*dpi/16),
                     w-(5*dpi/16)]

    left_dashlist = []
    right_dashlist = []
    left_middle_dash = find_middle_dash(image,dpi,left_indents)
    right_middle_dash = find_middle_dash(image,dpi,right_indents)
    if left_middle_dash is None or right_middle_dash is None:
      raise SomeException("middle dash search failed")
    
   # find left dashes from center upwards
    new_x = left_middle_dash[0]
    new_y = left_middle_dash[1]
    while(new_y > 0):
        left_bbox = find_dash_bbox(image,dpi,new_x,new_y)
        print "Left bbox",left_bbox
        if left_bbox is None:
            break
        left_dashlist.append(left_bbox)
        print "Left dashlist",left_dashlist
        # go up to center of bbox one above, adjust
        new_x = (left_bbox[0]+left_bbox[2])/2
        new_y = up_one((left_bbox[1]+left_bbox[3])/2,dpi)
        
   # find left dashes beneath center
    new_x = left_middle_dash[0]
    new_y = left_middle_dash[1]+(dpi/4)
    while(new_y < image.size[1]):
        left_bbox = find_dash_bbox(image,dpi,new_x,new_y)
        if left_bbox is None:
            break
        left_dashlist.append(left_bbox)
        # go up to center of bbox one above, adjust
        new_x = (left_bbox[0]+left_bbox[2])/2
        new_y = down_one((left_bbox[1]+left_bbox[3])/2,dpi)

    # find right dashes from center upwards
    new_x = right_middle_dash[0]
    new_y = right_middle_dash[1]
    while(new_y > 0):
        right_bbox = find_dash_bbox(image,dpi,new_x,new_y)
        if right_bbox is None:
            break
        right_dashlist.append(right_bbox)
        # go up to center of bbox one above, adjust
        new_x = (right_bbox[0]+right_bbox[2])/2
        new_y = up_one((right_bbox[1]+right_bbox[3])/2,dpi)

    # find right dashes beneath center
    new_x = right_middle_dash[0]
    new_y = right_middle_dash[1]+(dpi/4)
    while(new_y < image.size[1]):
        right_bbox = find_dash_bbox(image,dpi,new_x,new_y)
        if right_bbox is None:
            break
        right_dashlist.append(right_bbox)
        # go up to center of bbox one above, adjust
        new_x = (right_bbox[0]+right_bbox[2])/2
        new_y = down_one((right_bbox[1]+right_bbox[3])/2,dpi)
 
    # sort left and right dashlists into y order
    sorted_left = sorted(left_dashlist,key=lambda uly: int(uly[1]))
    sorted_right = sorted(right_dashlist,key=lambda uly: int(uly[1]))
    print "LEFT"
    print sorted_left[0:3]
    print sorted_left[-3:-1]
    print "RIGHT"
    print sorted_right[0:3]
    print sorted_right[-3:-1]

    # perform whatever sanity checks seem appropriate here
    # marks should be evenly spaced, 
    # tilts from left to right should not vary much
    # except for first/last inches, due to physical deskew on entry 
    if len(sorted_left) != len(sorted_right):
        raise SomeException("Dash list lengths do not match: %s %s" % (
                sorted_left,
                sorted_right)
                            )

    try:
        # SANITY CHECKS
        pass
    except Exception:
        pass
    return sorted_left, sorted_right

def find_code(bottom_left,bottom_right):
    start_left_x = bottom_left[0] + (dpi/4)
    start_top_y = bottom_left[1]
    end_left_x = bottom_right[0]
    end_top_y = bottom_right[1]
    num_dashes = ((end_left_x - start_left_x)*4./dpi)
    print "%d dashes from (%d,%d) to (%d,%d)" % (num_dashes,
                                                 start_left_x, start_top_y,
                                                 end_left_x, end_top_y)
    accum = 0
    for n in range(num_dashes):
        # interpolate n/num_dashes from start to end values
        accum = accum * 2
        delta_x = ((end_left_x-start_left_x)*n)/num_dashes
        delta_y = ((end_top_y-start_top_y)*n)/num_dashes
        this_x = start_left_x + delta_x
        this_y = start_top_y + delta_y
        center_x = this_x + ((3*dpi)/32)
        center_y = this_y + (dpi/32)
        p = image.getpixel((center_x,center_y))
        if p[0]<128:
            state = "DARK"
            accum += 1
        else:
            state = "LITE"
        #print "%02d: (%d,%d) %08x %s %s" % (n,center_x,center_y,accum,state,p)
    return accum


"""
2)  Determine the first indent at which the pattern repeats.

3)  Determine the x offset of the left dash's inside edge.  
    Determine the y offset of the left dash's upper edge. 
    Append (x,y) to left landmark list.

4)  Move up and down by pattern distance, repeat (3).  
    Adjust search to left or right based on change in x offset.

5)  Sort list by y.

6)  Repeat 3-5 for right edge.

Left list[n] and right list[n] are now two endpoints 
of line which will touch tops of vote opportunities.  

The last entries will be the two endpoints of a line 
which will touch the tops of the style coding marks.

The vote opportunities will be at consistent horizontal offsets
from the x values of the line.  Each set of consistent horizontal
offsets will correspond to a column. 
"""
if __name__ == "__main__":
    if len(sys.argv) < 3: 
        print "usage: python diebold_edges.py dpi filename"
        sys.exit(-1)
    try:
        dpi = int(sys.argv[1])
    except ValueError:
        print "usage: python diebold_edges.py dpi filename"
        sys.exit(-2)
    try:
        filename = sys.argv[2]
        image = Image.open(filename).convert("RGB")
    except Exception:
        print "Problem opening %s for image." % (filename,)
        sys.exit(-3)
    try:
        pdb.set_trace()
        for x in range(100):
            left,right = find_dashes(image,dpi)
        pdb.set_trace()
    except SomeException,e:
        print e

    for x in range(100):
        code = find_code(left[-1],right[-1])
    print "%08x" % (code,)

