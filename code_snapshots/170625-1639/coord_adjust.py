# Given an image and a crop region, together with a margin width
# and margin height and a target width and target height in pixels 
# 1. search for right angled edges in the image's crop region;
# 2. for each such edge, determine whether the arms of the angle
#    can be extended to the edge of the crop region, or for a given
#    length in each direction;
# 3. when such extension is possible for a right angled edge,
#    return a new region that would place the edge one margin width
#    and one margin height into the new region

import Image
import pdb

def ul_extend(seq, w, h, scan_x, scan_y):
    """Return (scan_x, scan_y) if dark lines extend from a point 
       two pixels below and two pixels to the right of that point 
       to the right and to the bottom of the image; else return None."""
    h_line = True
    v_line = True
    y = scan_y+2 
    counter = 0
    for x in range(scan_x+2,w):
        if counter >= (w/2):
            break
        counter = counter+1
        if seq[(y*w)+x][0] > 96:
            h_line = False
    x = scan_x+2 
    counter = 0
    for y in range(scan_y+2,h):
        if counter >= (h/2):
            break
        counter = counter+1
        if seq[(y*w)+x][0] > 96:
            v_line = False
    if h_line and v_line:
        return (scan_x, scan_y)
    else:
        return None

def ll_extend(seq, w, h, scan_x, scan_y):
    """Return (scan_x, scan_y) if dark lines extend from a point 
       two pixels above and two pixels to the right of that point 
       to the right and to the bottom of the image; else return None."""
    h_line = True
    v_line = True
    y = scan_y-2 
    counter = 0
    for x in range(scan_x+2,w):
        if counter >= (w/2):
            break
        counter = counter+1
        if seq[(y*w)+x][0] > 96:
            h_line = False
    x = scan_x+2
    counter = 0
    for y in range(scan_y-2,0,-1):
        if counter >= (h/2):
            break
        counter = counter+1
        if seq[(y*w)+x][0] > 96:
            v_line = False
    if h_line and v_line:
        return (scan_x, scan_y)
    else:
        return None

def ur_extend(seq, w, h, scan_x, scan_y):
    """Return (scan_x, scan_y) if dark lines extend from a point 
       two pixels below and two pixels to the left of that point 
       to the right and to the bottom of the image; else return None."""
    h_line = True
    v_line = True
    y = scan_y + 2
    counter = 0
    for x in range(scan_x-2,0,-1):
        if counter >= (w/2):
            break
        counter = counter+1
        if seq[(y*w)+x][0] > 96:
            h_line = False
    x = scan_x - 2
    counter = 0
    for y in range(scan_y+2,h):
        if counter >= (h/2):
            break
        counter = counter+1
        if seq[(y*w)+x][0] > 96:
            v_line = False
    if h_line and v_line:
        return (scan_x, scan_y)
    else:
        return None

def lr_extend(seq, w, h, scan_x, scan_y):
    """Return (scan_x, scan_y) if dark lines extend from a point 
       two pixels above and two pixels to the left of that point 
       to the right and to the bottom of the image; else return None."""
    h_line = True
    v_line = True
    y = scan_y - 2
    counter = 0
    for x in range(scan_x-2,0,-1):
        if counter >= (w/2):
            break
        counter = counter+1
        if seq[(y*w)+x][0] > 96:
            h_line = False
    x = scan_x -2
    counter = 0
    for y in range(scan_y-2,0,-1):
        if counter >= (h/2):
            break
        counter = counter+1
        if seq[(y*w)+x][0] > 96:
            v_line = False
    if h_line and v_line:
        return (scan_x, scan_y)
    else:
        return None

def coord_adjust(image,
                 margin_w,margin_h,
                 target_w,target_h):
    """Return an upper left coordinate that completely encloses the target
       within the crop box anchored at the new coordinate."""
    seq = list(image.getdata())
    w,h = image.size
    for scan_x in range(w-5):
        for scan_y in range(h-5):
            # check each point for each of four patterns
            # corresponding to ulc, urc, lrc, llc of target
            # until a point is found that forms a proper corner
            if (seq[(scan_y*w)+scan_x][0]>192
                and seq[(scan_y*w)+scan_x+2][0]>192
                and seq[(scan_y*w)+scan_x+4][0]>192
                and seq[((scan_y+2)*w)+scan_x][0]>192
                and seq[((scan_y+4)*w)+scan_x][0]>192
                and seq[((scan_y+2)*w)+scan_x+2][0]<64
                and seq[((scan_y+2)*w)+scan_x+4][0]<64
                and seq[((scan_y+4)*w)+scan_x+2][0]<64):
                # we might have an upper left corner, 
                # check to right and below
                coord = ul_extend(seq, w, h, scan_x+2, scan_y+2)
                if coord is not None:
                    return(coord[0] , 
                           coord[1] )
            if (seq[((scan_y+4)*w)+scan_x][0]>192
                and seq[((scan_y+4)*w)+scan_x+2][0]>192
                and seq[((scan_y+4)*w)+scan_x+4][0]>192
                and seq[((scan_y+2)*w)+scan_x][0]>192
                and seq[((scan_y+0)*w)+scan_x][0]>192
                and seq[((scan_y+2)*w)+scan_x+2][0]<128
                and seq[((scan_y+2)*w)+scan_x+4][0]<64
                and seq[((scan_y+0)*w)+scan_x+2][0]<64):
                # we might have a lower left corner, 
                # check to right and below
                coord = ll_extend(seq,w,h,scan_x+2,scan_y+2)
                if coord is not None:
                    return(coord[0] , 
                           coord[1] - target_h)
            if (seq[(scan_y*w)+scan_x+4][0]>192
                and seq[(scan_y*w)+scan_x+2][0]>192
                and seq[(scan_y*w)+scan_x+0][0]>192
                and seq[((scan_y+2)*w)+scan_x+4][0]>192
                and seq[((scan_y+4)*w)+scan_x+4][0]>192
                and seq[((scan_y+2)*w)+scan_x+2][0]<128
                and seq[((scan_y+2)*w)+scan_x+0][0]<64
                and seq[((scan_y+4)*w)+scan_x+2][0]<64):
                # we might have an upper right corner, 
                #check to left and below
                coord = ur_extend(seq,w,h,scan_x+2,scan_y+2)
                if coord is not None:
                    return(coord[0] - target_w, 
                           coord[1] )
            if (seq[((scan_y+4)*w)+scan_x+4][0]>192
                and seq[((scan_y+4)*w)+scan_x+2][0]>192
                and seq[((scan_y+4)*w)+scan_x+0][0]>192
                and seq[((scan_y+2)*w)+scan_x+4][0]>192
                and seq[((scan_y+0)*w)+scan_x+4][0]>192
                and seq[((scan_y+2)*w)+scan_x+2][0]<128
                and seq[((scan_y+2)*w)+scan_x+0][0]<64
                and seq[((scan_y+0)*w)+scan_x+2][0]<64):
                # we might have a lower right corner, 
                #check to left and below
                coord = lr_extend(seq,w,h,scan_x+2,scan_y+2)
                if coord is not None:
                    return(coord[0] - target_w,
                           coord[1] - target_h)
    return None

if __name__ == "__main__":
    im = Image.open("/tmp/test_ul.jpg")
    print "Test ul"
    print coord_adjust(im,10,9,40,30)
    im = Image.open("/tmp/test_ll.jpg")
    print "Test ll"
    print coord_adjust(im,10,9,40,30)
    im = Image.open("/tmp/test_ur.jpg")
    print "Test ur"
    print coord_adjust(im,10,9,40,30)
    im = Image.open("/tmp/test_lr.jpg")
    print "Test lr"
    print coord_adjust(im,10,9,40,30)
    im = Image.open("/tmp/test_diag.jpg")
    print "Test diag"
    print coord_adjust(im,10,9,40,30)
    im = Image.open("/tmp/test_vcent.jpg")
    print "Test vcent"
    print coord_adjust(im,10,9,40,30)
    im = Image.open("/tmp/test_hcent.jpg")
    print "Test hcent"
    print coord_adjust(im,10,9,40,30)
