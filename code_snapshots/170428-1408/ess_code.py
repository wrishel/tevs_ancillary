import Image
import Ballot
from BallotRegions import Point, Landmarks
import config
import const
import math
import pdb
import sys
from find_line import find_line

def block_type(image,pixtocheck,x,y):
    """check pixcount pix starting at x,y; return code from avg intensity"""
    intensity = 0
    for testx in range(x,x+pixtocheck):
        intensity += image.getpixel((testx,y))[0]
    intensity = intensity/pixtocheck
    if intensity > 192:
        retval = 0
    elif intensity > 64:
        retval = 1
    else:
        retval = 2
    return retval

def adjust_ulc(image,left_x,top_y,max_adjust=5):
    """ brute force adjustment to locate precise b/w boundary corner"""
    target_intensity = 255
    gray50pct = 128
    gray25pct = 64
    orig_adj = max_adjust
    while max_adjust > 0 and target_intensity > gray50pct:
        max_adjust -= 1
        left_target_intensity = image.getpixel((left_x-2,top_y))[0]
        target_intensity = image.getpixel((left_x,top_y))[0]
        right_target_intensity = image.getpixel((left_x+2,top_y))[0]
        above_target_intensity = image.getpixel((left_x,top_y-2))[0]
        above_right_target_intensity = image.getpixel((left_x+2,top_y-2))[0]
        above_left_target_intensity = image.getpixel((left_x-2,top_y-2))[0]
        below_target_intensity = image.getpixel((left_x,top_y+2))[0]
        below_left_target_intensity = image.getpixel((left_x-2,top_y+2))[0]
        below_right_target_intensity = image.getpixel((left_x+2,top_y+2))[0]
        #print above_left_target_intensity,above_target_intensity,above_right_target_intensity
        #print left_target_intensity,target_intensity,right_target_intensity
        #print below_left_target_intensity,below_target_intensity,below_right_target_intensity
        changed = False
        if below_target_intensity > gray25pct and target_intensity > gray25pct:
            left_x += 2
            changed = True
        elif below_left_target_intensity <= gray50pct:
            left_x -= 2
            changed = True
        if right_target_intensity > gray25pct and target_intensity > gray25pct:
            top_y += 2
            changed = True
        elif above_right_target_intensity <= 127:
            top_y -= 2
            changed = True
        if not changed:
            break
    if max_adjust == 0 and changed == True:
        e = "could not fine adj edge at (%d, %d) after %d moves" % (left_x,
                                                                    top_y,
                                                                    orig_adj)
        raise Ballot.BallotException, e
    return (left_x,top_y)



def ess_code(image,landmark_x,landmark_y):
    """ Determine the layout code by getting it from the user

    The layout code must be determined on a vendor specific basis;
    it is usually a series of dashes or a bar code at a particular
    location on the ballot.

    Layout codes may appear on both sides of the ballot, or only
    on the fronts.  If the codes appear only on the front, you can
    file the back layout under a layout code generated from the
    front's layout code.
    """
    # if front, starting point is 13/15" before plus horizontal offset,
    # and same level as vertical offset
    adj = lambda a: int(round(const.dpi * a))
    front_adj_x = adj(-(13./15.))
    front_adj_y = adj(0.0)
    barcode,tm = timing_marks(image,
                              landmark_x + front_adj_x,
                              landmark_y + front_adj_y,
                              const.dpi)
                                  
    return barcode,tm

def timing_marks(image,x,y,dpi=300):
    """locate timing marks and code, starting from closest to ulc symbol"""
    # go out from + towards left edge by 1/8", whichever is closer
    # down from + target to first dark, then left to first white
    # and right to last white, allowing a pixel of "tilt"

    adj = lambda f: int(round(const.dpi * f))

    retlist = []
    half = adj(0.5)
    third = adj(0.33)
    qtr = adj(0.25)
    down = adj(0.33)
    sixth = adj(0.167)
    twelfth = adj(0.083)
    gray50pct = 128

    left_x = x
    top_y = y
    retlist.append( (left_x,top_y) )
    # now go down 1/2" and find next ulc, checking for drift
    top_y += half
    for n in range(adj(0.1)):
        try:
            pix = image.getpixel((left_x+adj(0.1),top_y + n))
            if pix[0] > 128:
                top_y = top_y + 1
        except IndexError:
            print "pixel out of range"
            pdb.set_trace()
    code_string = ""
    zero_block_count = 0
    while True:
        if top_y > (image.size[1] - const.dpi):
            break
        (left_x,top_y) = adjust_ulc(image,left_x,top_y)
        # check for large or small block to side of timing mark
        block = block_type(image,qtr,left_x+half,top_y+twelfth)
        if block==0: 
            zero_block_count += 1
        elif block==1:
            code_string = "%s%dA" % (code_string,zero_block_count)
            zero_block_count = 0
        elif block==2:
            code_string = "%s%dB" % (code_string,zero_block_count)
            zero_block_count = 0
            
        retlist.append((left_x,top_y))
        # now go down repeated 1/3" and find next ulc's until miss
        top_y += third
    # try finding the last at 1/2" top to top
    left_x = retlist[-1][0]
    top_y = retlist[-1][1]
    top_y += half
    (left_x,top_y) = adjust_ulc(image,left_x,top_y)
    retlist.append((left_x,top_y))
    
    return (code_string, retlist)

def find_front_landmarks(im):
        """find the left and right corners of the uppermost line"""
        iround = lambda a: int(round(float(a)))
        adj = lambda a: int(round(const.dpi * a))
        width = adj(0.75)
        height = adj(0.75)
        # for testing, fall back to image argument if can't get from page
        # generate ulc, urc, lrc, llc coordinate pairs
        landmarks = []

        # use corners of top and bottom lines in preference to circled-plus
        # as the circled plus are often missed due to clogging, etc...
        try:
            a,b,c,d = find_line(im,im.size[0]/2,100,
                                threshold=64,black_sufficient=True)
            #self.log.debug("Top line coords (%d,%d)(%d,%d)" % (a,b,c,d))
        except Exception:
            pass
        else:
            landmarks.append(Point(a,b))
            landmarks.append(Point(c,d))

        try:
            # changing search start from 1/3" above bottom to 1/14" above
            a,b,c,d = find_line(im,im.size[0]/2,im.size[1]-adj(0.07),-adj(0.75),
                                threshold=64,black_sufficient=True)
            #self.log.debug("Top line coords (%d,%d)(%d,%d)" % (a,b,c,d))
        except Exception:
            pass
        else:
            landmarks.append(Point(c,d))
            landmarks.append(Point(a,b))

        try:
            x,y = landmarks[0].x,landmarks[0].y
            longdiff_a = landmarks[3].y - landmarks[0].y
            shortdiff_a = landmarks[3].x - landmarks[0].x
            hypot = math.sqrt(longdiff_a*longdiff_a + shortdiff_a*shortdiff_a)
            r_a = float(shortdiff_a)/float(longdiff_a)
            longdiff_b = landmarks[1].x - landmarks[0].x
            shortdiff_b = landmarks[0].y - landmarks[1].y
            hypot = math.sqrt(longdiff_b*longdiff_b + shortdiff_b*shortdiff_b)
            r_b = float(shortdiff_b)/float(longdiff_b)
            magnitude_r = min(abs(r_a),abs(r_b))
            if r_a < 0. and r_b < 0.:
                sign_r = -1
            else:
                sign_r = 1
            r = magnitude_r * sign_r
        except IndexError:
            # page without landmarks; if this is a back page, it's ok
            raise Ballot.BallotException

        if abs(r) > 0.1: 
            #self.log.info("Tangent is unreasonably high, at %f." % (r,))
            print "Tangent is unreasonably high, at %f." % (r,)
            #pdb.set_trace()
        # we depend on back landmarks being processed after front
        landmarks = Landmarks(landmarks[0],landmarks[1],landmarks[2],landmarks[3])
        return landmarks
        #return r,x,y,hypot
    


if __name__ == "__main__":
    
    if len(sys.argv)<2:
        print "usage python ess_code.py filename"
    config.get()
    image = Image.open(sys.argv[1]).convert("RGB")
    landmarks = find_front_landmarks(image)
    print landmarks
    print "Note: coding information is available only on fronts,"
    print "Failure to retrieve code can be treated as a non-front"
    pdb.set_trace()
    landmark_x = landmarks[0][0]
    landmark_y = landmarks[0][1]
    if landmark_x < (2.*const.dpi)/3.:
        barcode = "No barcode, this is a back"
        tm = "No tm retrieved."
    else:    
        barcode,tm = ess_code(image,landmark_x,landmark_y)
    print barcode
    print tm
