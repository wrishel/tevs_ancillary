"""
To find the dashes closest to the bottom of a diebold image:
1) Start at the lower left corner (* or lower right corner).
2) For each value of x, look for zones with approximately dash height of 
   contiguous darkness, keeping track of the start of each contiguous
   darkness.  If none is found after n inches, proceed to next x.
3) If one or more candidate zones are found, starting with the lowest zone,
   take the y value half dash height above the beginning y value of the zone, 
   and proceed rightwards (*) until a contiguous zone of light is encountered.  
   This zone must be approximately 1/15" or you disqualify the candidate.
   Note the beginning x value of the light zone -- it is the end of the 
   candidate zone, and the beginning of the candidate dash would be located
   (1/4" - 1/15" before).  
   There should be a contiguous zone of dark following the light zone.  
   That should be approximately (1/4" - 1/15") or you disqualify the candidate.
(*) For right bottom corner, proceed leftwards.
"""
import pdb
import Image
import sys

def is_dark(im,x,y,threshold=128):
    p = im.getpixel((x,y))
    try:
        p[0]
        return (p[0] < threshold)
    except:
        return (p < threshold)

def coords_horiz_pattern_ok(im,x,y,dpi,threshold=128,left=True,top=True):
    """Given a candidate that might be a dash, investigate horizontally."""
    # incr until light
    half_dash_height = dpi/32
    x_light_at = None
    x_light_ends_at = None
    x_dark_at = None
    second_x_dark_ends_at = None
    passes_total_length_test = False
    passes_length_ratio_test = False
    if left: 
        incr = 1
        end_x = x + (dpi/3)
    else: 
        incr = -1
        end_x = x - (dpi/3)
    for x_light in range(x,end_x,incr):
        dark_pixel = is_dark(im,x_light,y)
        if not dark_pixel:
            x_light_at = x_light
            break
    # we were called with y set to halfway up the dash from its bottom;
    # the upper limit of the dash is at y - half_dash_height;
    # if we are at left moving rightwards, 
    # we subtract dash length from where x turned light;
    # otherwise, moving leftwards, we return x at which dash turned light
    if top: incr_y = -1
    else: incr_y = -1
    if x_light_at is None: 
        return None
    elif incr > 0:
        return (x_light_at - incr*(3*dpi/16),y - half_dash_height )
    else:
        return (x_light_at, y - half_dash_height )
    """
    # found potential start of light after dash
    if left: 
        end_x = x_light_at + (dpi/5)
    else:
        end_x = x_light_at - (dpi/5)
    for x_dark in range(x_light_at,end_x,incr):
        dark_pixel = is_dark(im,x_dark,y)
        if dark_pixel:
            x_light_ends_at = x_dark
            break
    if x_light_ends_at is None: 
        return False
    if left:
        end_x = x_light_ends_at + (dpi/3)
    else:
        end_x = x_light_ends_at - (dpi/3)
    for x_light in range(x_light_ends_at, end_x, incr):
        dark_pixel = is_dark(im,x_light,y)
        if not dark_pixel:
            second_x_dark_ends_at = x_light
            break
    if second_x_dark_ends_at is None:
        return None
    if (abs(second_x_dark_ends_at - x_light_at) - (dpi/4)) <= (dpi/40):
        passes_total_length_test = True
    if not passes_total_length_test:
        return None
    light_length = abs(x_light_at - x_light_ends_at)
    # found potential start of next dash, determine length
    dark_length = abs(x_light_ends_at - second_x_dark_ends_at)
    if ((3*light_length)-dark_length) < dpi/40:
        return (x_light_at - dark_length, y)
    """
def get_bottom_dash(im,dpi,threshold=128,left=True):
    """Return ulc of lowest diebold dash in image at left or right, or None."""
    dash_height = dpi/16
    half_dash_height = dpi/32
    start_y = im.size[1] - 1
    end_y = start_y - dpi
    min_candidate_height = dpi/32
    max_candidate_height = dpi/16 + (dpi/32)
    incr_y = -1
    if left:
        start_x = 0
        end_x = start_x + dpi
        incr_x = 1
    else:
        start_x = im.size[0] - 1
        end_x = start_x - dpi
        incr_x = -1
    encounter = 0
    skip = 0
    for x in range(start_x,end_x,incr_x):
        # 2) above
        if skip > 0: 
            skip -= 1
            continue
        dash_pattern_xy = None
        in_dark = False
        contig_dark = 0
        exceeds_min_candidate_height = False
        exceeds_max_candidate_height = False
        for y in range(start_y, end_y, incr_y):
            dark_pixel = is_dark(im,x,y)
            if not in_dark and dark_pixel:
                in_dark = True
                contig_dark = 1
                first_dark_y = y
            elif in_dark and dark_pixel:
                contig_dark += 1
            elif not dark_pixel:
                in_dark = False
                if ( contig_dark > min_candidate_height 
                     and contig_dark <= max_candidate_height):
                    exceeds_min_candidate_height = True
                    break
                if contig_dark > max_candidate_height:
                    exceeds_min_candidate_height = False
                    exceeds_max_candidate_height = False
                    contig_dark = 0
                    continue
                    # the y value is the candidate's top, 
                    # but the x value is somewhere inside
        if exceeds_min_candidate_height and not exceeds_max_candidate_height:
            """Try moving inboard by 1/50", then repeating the whole process 
            without exiting loop.  That will avoid getting triggered by higher
            dashes when there is some tilt causing higher dashes to be encountered
            at more outboard x values than lower dashes."""
            if encounter == 0:
                encounter = 1
                skip = dpi/50
                continue
            #print "Entering coords_horiz_pattern_ok"
            #print x,first_dark_y, first_dark_y + (incr_y * half_dash_height)
            # First confirm that there is a light pixel above and below
            # the presumptive dash.
            dash_pattern_xy = None
            outside_pix1_dark = is_dark(im,
                                   x + (incr_x * (dpi/50)), 
                                   y + ((incr_y * 3 * dash_height)/2))
            outside_pix2_dark = is_dark(im,
                                   x + (incr_x * (dpi/50)), 
                                   y + ((incr_y * 3 * dash_height)/2))

            if not (outside_pix1_dark or outside_pix2_dark):
                dash_pattern_xy = coords_horiz_pattern_ok(
                    im,
                    x,
                    first_dark_y + (incr_y * half_dash_height),
                    dpi,
                    threshold,
                    left)
            if dash_pattern_xy is not None:
                return dash_pattern_xy
    return dash_pattern_xy

def get_dash(im,dpi,threshold=128,left=True,top=True):
    """Return ulc of lowest diebold dash in image at left or right, or None."""
    dash_height = dpi/16
    half_dash_height = dpi/32
    if top:
        start_y = dpi/4
        end_y = dpi
        incr_y = 1
    else:
        start_y = im.size[1] - (dpi/4)
        end_y = start_y - dpi
        incr_y = -1
    min_candidate_height = dpi/32
    max_candidate_height = dpi/16 + (dpi/32)
    if left:
        start_x = 0
        end_x = start_x + dpi
        incr_x = 1
    else:
        start_x = im.size[0] - 1
        end_x = start_x - dpi
        incr_x = -1
    encounter = 0
    skip = 0
    for x in range(start_x,end_x,incr_x):
        # 2) above
        if skip > 0: 
            skip -= 1
            continue
        dash_pattern_xy = None
        in_dark = False
        contig_dark = 0
        exceeds_min_candidate_height = False
        exceeds_max_candidate_height = False
        for y in range(start_y, end_y, incr_y):
            dark_pixel = is_dark(im,x,y)
            if not in_dark and dark_pixel:
                in_dark = True
                contig_dark = 1
                first_dark_y = y
            elif in_dark and dark_pixel:
                contig_dark += 1
            elif not dark_pixel:
                in_dark = False
                if ( contig_dark > min_candidate_height 
                     and contig_dark <= max_candidate_height):
                    exceeds_min_candidate_height = True
                    break
                if contig_dark > max_candidate_height:
                    exceeds_min_candidate_height = False
                    exceeds_max_candidate_height = False
                    contig_dark = 0
                    continue
                    # the y value is the candidate's top, 
                    # but the x value is somewhere inside
        if exceeds_min_candidate_height and not exceeds_max_candidate_height:
            """Try moving inboard by 1/50", then repeating the whole process 
            without exiting loop.  That will avoid getting triggered by higher
            dashes when there is some tilt causing higher dashes to be encountered
            at more outboard x values than lower dashes."""
            if encounter == 0:
                encounter = 1
                skip = dpi/50
                continue
            #print "Entering coords_horiz_pattern_ok"
            #print x,first_dark_y, first_dark_y + (incr_y * half_dash_height)
            dash_pattern_xy = coords_horiz_pattern_ok(
                        im,
                        x,
                        first_dark_y + (incr_y * half_dash_height),
                        dpi,
                        threshold,
                        left=left,
                        top=top)
            if dash_pattern_xy is not None:
                return dash_pattern_xy
    return dash_pattern_xy

def dash_code(im,dpi,start_x,start_y,end_x,end_y):
    code = []
    accum = 0
    w = im.size[0]
    for n in range(34):
        x = int(float(n*w)/(34))+start_x+(dpi/32)
        if x > (w-1) or x < 0:
            continue
        
        # scan at halfway down dashes
        y =  int(round((((34-n)*start_y)+(n*end_y))/34.)) + (dpi/32) 
        p = im.getpixel((x,y))
        try:
            p_intensity = p[0]
        except:
            p_intensity = p
        #print x,y,p_intensity<128
        if p_intensity<128:
            accum += 1
        accum *= 2
    print "%x" % accum
    return accum

if __name__ == "__main__":
    if len(sys.argv)<3:
        print "Usage: python diebold_bottom_dashes filename dpi"
        sys.exit(0)
    im = Image.open(sys.argv[1])
    dpi = int(sys.argv[2])
    print "Getting left dash of %s, %d dpi." % (sys.argv[1],dpi)
    try:
        (llx,lly) = get_dash(im,dpi,left=True,top=False)
        #print "Get dash (bottom) (%d,%d)" % (lx,ly)
        (ulx,uly) = get_dash(im,dpi,left=True,top=True)
        #print "Get dash (top) (%d,%d)" % (rx,ry)
    except Exception, e:
        print e
        print "Could not find bottom left dash."
    print "Getting right dash of %s, %d dpi." % (sys.argv[1],dpi)
    try:
        (lrx,lry) = get_dash(im,dpi,left=False,top=False)
        #print "Get dash (bottom) (%d,%d)" % (x,y)
        (urx,ury) = get_dash(im,dpi,left=False,top=True)
        #print "Get dash (top) (%d,%d)" % (x,y)
    except Exception, e:
        print "Could not find bottom right dash."
    print "UL (%d, %d) UR (%d, %d) LR (%d, %d) LL (%d,%d)" % (ulx,uly,urx,ury,lrx,lry,llx,lly)
    cd = dash_code(im,dpi,llx,lly,lrx,lry)

