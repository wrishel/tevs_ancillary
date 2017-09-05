import Image
import sys

"""
Earlier routines split the contest target area into target and text zones.

We feed each zone into darkstripes to build lists of dark
stripes (start,end) vertical offsets into these zones.

These are then associated with one another in target_and_text.
"""

def dark(data,offset,offset_to_compare,threshold):
    try:
        retval = ( 
            (data[offset][0] < threshold) 
            or (data[offset][0] < (data[offset_to_compare][0] - 24)) )
    except:
        retval = (
            (data[offset] < threshold) 
            or (data[offset] < (data[offset_to_compare] - 24)) )
    return retval

def darkstripes(im,threshold=232):
    """return array of starting, ending vertical offsets of non-blank stripes"""
    in_dark = False
    is_tuple = False
    data = im.getdata()
    dark_start = 0
    darkpix_count = 0
    dark_contig = 0
    dark_zones = []
    try:
        data[0][0]
        is_tuple = True
    except:
        pass
    for y in range(im.size[1]):
        line_dark = False
        darkpix_count = 0
        trim = 2
        min_darkpix_for_dark_line = 2
        for x in range(trim,im.size[0]-trim):
            offset = (y*im.size[0])+x
            if x>2:
                offset_to_compare = offset - 2
            else:
                offset_to_compare = offset
            if ( dark(data,offset,offset_to_compare,threshold) ):
                    line_dark = True
                    break
        if line_dark and in_dark:
            dark_contig += 1
        elif line_dark and (not in_dark):
            dark_start = y
            dark_contig = 0
            in_dark = True
        elif (not line_dark) and in_dark:
            dark_zones.append((dark_start,dark_start+dark_contig))
            dark_contig = 0
            in_dark = False
        elif (not line_dark) and (not in_dark):
            pass
    if in_dark:
        dark_zones.append((dark_start,dark_start+dark_contig))
    return dark_zones

if __name__ == "__main__":
    if len(sys.argv)!=2:
        print "usage: python darkstripes.py image"
    im = None
    try:
        im = Image.open(sys.argv[1])
    except:
        print "Could not open",sys.argv[1],"as image."
        sys.exit(0)
    print darkstripes(im)
