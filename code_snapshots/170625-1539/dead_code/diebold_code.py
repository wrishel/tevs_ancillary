import pdb
import sys
import Image

def start_of_first_dash(im,dpi,start_y=100,end_y=200):
    entered_dash = False
    dash_x_start = None
    dash_y_start = None
    for x in range(dpi/2):
        count = 0
        for y in range(start_y,end_y):
            p = im.getpixel((x,y))
            if p[0]<128:
                count = count + 1
                if count > dpi/32 and dash_y_start is None:
                    # check to see if the dash extends horizontally
                    # to a white region of correct size followed by
                    # a dark region of correct size
                    dark_length = 0
                    light_length = 0
                    for x2 in range(x,x+dpi/4):
                        p = im.getpixel((x2,y))
                        if p[0]<128:
                            dark_length += 1
                        else:
                            light_length += 1
                    # after studying 1/4", you should have a full dash cycle,
                    # which should have 3/4 dark and 1/4 light
                    if abs(dark_length - ((3*dpi)/16) ) < 10:
                        if abs(light_length - (dpi/16)) < 10:
                               dash_y_start = y+1-count
                               entered_dash = True
                               break
        if entered_dash:
            # we entered into a dark zone with sufficient vertical height;
            # now determine where this zone starts horizontally;
            # we require that black zones extend horizontally for at least 1/10"
            # to qualify as a real dash, so if this extends less than 1/10",
            # it is a cut off early dash or an artifact and we must determine
            # which.  If it's a cut off early dash, we subtract dash width
            # to find the real start point, which will be negative.
            # If it's an artifact, we need to reset entered_dash to False,
            # reset dash_y_start to None, and continue.
            contig_dark = 0
            last_x = x + ((dpi*55)/300)
            for x2 in range(x,x+(dpi/6)):
                p = im.getpixel((x2,dash_y_start + (dpi/32)))
                if p[0]>128:
                    last_x = x2
                    break
                contig_dark = contig_dark + 1
                
            if contig_dark > (dpi/10):
                # it's a good dash, report x2 less dash width
                dash_x_start = last_x - ((dpi*55)/300)
                break
            else:
                dash_y_start = None
                entered_dash = False
        if entered_dash:
            break

    return (dash_x_start,dash_y_start)
             
def start_of_last_dash(im,dpi,start_y=100,end_y=200):
    entered_dash = False
    dash_x_start = None
    dash_y_start = None
    for x in range(im.size[0]-1,im.size[0]-(dpi/2),-1):
        count = 0
        for y in range(start_y,end_y):
            p = im.getpixel((x,y))
            if p[0]<128:
                count = count + 1
                if count > dpi/32 and dash_y_start is None:
                    dash_y_start = y+1-count
                    entered_dash = True
                    break
        if count < dpi/32 and entered_dash:
            exited_dash_at_x = x
            dash_x_start = exited_dash_at_x 
            break
    return (dash_x_start,dash_y_start)
            


def diebold_tm(im,dpi):
    dx,dy = start_of_first_dash(im,dpi,start_y=(dpi/3),end_y=(2*dpi/3))
    last_dash_x, last_dash_y = start_of_last_dash(im,dpi,start_y=(dpi/3),end_y=(2*dpi/3))
    left_list=[(dx,dy)]
    right_list = [(last_dash_x,last_dash_y)]
    # sample rows starting at approx 1/4" intervals at center of first dash
    # adjust as necessary
    next_x = dx + int(float(3*dpi)/32)
    next_y = dy
    for index in range(int(im.size[1]*4/dpi)-3):
        next_y = next_y + int(dpi/4) - 2
        
        for n in range(5):
            p = im.getpixel((next_x,next_y))
            if p[0]<128:
                left_list.append((next_x-int(float(3*dpi)/32),next_y))
                break
            next_y += 1
            if n==4:
                pleft = [255,255,255]
                pright = [255,255,255]
                if next_x > 5:
                    pleft = im.getpixel((next_x-5,next_y))
                if next_x < (im.size[0]-5):
                    pright = im.getpixel((next_x+5,next_y))
                if pright[0]<128:
                    next_x = next_x + 5
                elif pleft[0]<128:
                    next_x = next_x - 5

    next_x = last_dash_x + int(float(3*dpi)/32)
    next_y = last_dash_y
    for index in range(int(im.size[1]*4/dpi)-3):
        next_y = next_y + int(dpi/4) - 2
        for n in range(5):
            p = im.getpixel((next_x,next_y))
            if p[0]<128:
                right_list.append((next_x+int(float(3*dpi/32)),next_y))
                break
            next_y += 1
            if n==4:
                pleft = [255,255,255]
                pright = [255,255,255]
                if next_x > 5:
                    pleft = im.getpixel((next_x-5,next_y))
                if next_x < (im.size[0]-5):
                    pright = im.getpixel((next_x+5,next_y))
                if pleft[0]<128:
                    next_x = next_x - 5
                elif pright[0]<128:
                    next_x = next_x + 5
    #print "Left",left_list
    #print "Right",right_list
    return left_list, right_list

# not used; use code in basicdiebold_ballot_side.py
def diebold_code(im,dpi,start_y=None,end_y=None):
    w,h = im.size
    #print w,h
    code = []
    # find end of first dash
    entered_dash = False
    exited_dash_at_x = -1
    if start_y is None:
        start_y = h-(2*dpi/3)
    if end_y is None:
        end_y = h-(dpi/3)
    dash_x_start,dash_y_start = start_of_first_dash(im,dpi,start_y,end_y)
    for n in range(34*2):
        x = int(float(n*w)/(34*2))+dash_x_start+(dpi/32)
        if x > (w-1) or x < 0:
            code.append((x,dash_y_start+1,1))
            continue
        
        count = 0
        last_dark_y = dash_y_start + 1
        for y in range(start_y,end_y):
            p = im.getpixel((x,y))
            if p[0]<128:
                count = count + 1
                if count > (dpi/24):
                    break
            else:
                count = 0
                pass
        if count > dpi/24:
            code.append((x,y,0))
            last_dark_y = y
        else:
            code.append((x,last_dark_y,1))
    if len(code)<(34*2):
        return None
    # get the first and the last x,y pairs where dark; intermediate y values
    # must interpolate those pairs reasonably to be kept
    first_y = code[0][1]
    last_y = code[-1][1]
    newcode = []
    for x,y,dark in code:
        portion_crossed = float(x)/w
        likely_y = (first_y * (1-portion_crossed)) + (last_y * (portion_crossed))
        if abs((y-likely_y) > (dpi/20)):
            #this is bogus
            print y, likely_y, dpi/20
            newcode.append( 1 )
        else:
            newcode.append(dark)
    # combine the two samples
    accum = 0
    for x in range(0,len(newcode)-1,2):
        accum = accum << 1
        code_sum = newcode[x]+newcode[x+1] 
        if code_sum==0:
            accum += 1
        if code_sum==1:
            print "Problem with code position %d" % (x,)
            print code
            accum += 1
            raise "Bad diebold code"
    return accum
if __name__=="__main__":
    i = Image.open(sys.argv[1])
    if i.mode == 'L':
        i = i.convert('RGB')
    l,r = diebold_tm(i,300)
    print "Left tm",l
    print "Right tm",r

    code = diebold_code(i,300,100,200)
    print "Top %d %x" % (code,code)
    code = diebold_code(i)
    print "Bottom %d %x" % (code,code)

