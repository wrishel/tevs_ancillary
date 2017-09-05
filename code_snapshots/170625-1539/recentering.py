import pdb
import sys
import Image

class RecenteringException(Exception):
    pass

def recenter(logger,image,xp,yp,x2p,y2p,x_marginp,y_marginp,x_ltp,y_ltp,twp,thp):
    # recenter vertically
    xp -= x_marginp
    yp -= y_marginp
    x2p += x_marginp
    y2p += y_marginp
    window_width_with_margins = x2p - xp
    window_height_with_margins = y2p - yp
    x_vcrop = (xp+x2p)/2
    center_vline_crop = (x_vcrop,yp,x_vcrop+1,y2p)
    vline = image.crop(center_vline_crop)
    #print "Boundary area w/margins: %d %d %d %d" % (xp,yp,x2p,y2p)
    #print "Sample vline uses crop: %s",center_vline_crop
    vdata = vline.getdata()
    # vdata now has a vertical stripe of pixels 
    # from the center of the proposed target region + margins
    # locate first black pixel
    first_black = -1
    boxbottom_offset = -1
    boxtop_offset = -1
    boxleft_offset = -1
    boxright_offset = -1
    for position,datum in enumerate(vdata):
        # handle tuple or integer data
        try:
            datum = datum[0]
        except:
            pass
        if datum < 128:
            first_black = position
            break

    #print "first_black", first_black
    if first_black < 0: 
        logger.warning("No black found to recenter.")
        raise RecenteringException

    if first_black < (2*y_ltp):
        #  black near top; find last set of black pixels 
        #  that is long enough to represent line of thickness lt
        #  by searching pixels backwards
        #print "First black near top"
        try:
            vdata = list(vdata)
            vdata.reverse()
            contig = 0
            boxbottom_offset = -1
            for position,datum in enumerate(vdata):
                # handle tuple or integer data
                try:
                    datum = datum[0]
                except:
                    pass
                if datum < 128:
                    contig += 1
                else:
                    contig = 0
                if contig >= (y_ltp-1):
                    boxbottom_offset = position - contig
                    break
        except Exception,e:
            print e
        # handle that case and return
        boxtop_offset = window_height_with_margins - (boxbottom_offset + thp)
        #print "top_offset, top_offset, thp",boxtop_offset,boxbottom_offset,thp
    else:
        #take a horizontal sampling 
        # at twice the line thickness ABOVE the black pixel
        # to see if the black pixel would be a box bottom or box top
        test_y = yp+first_black-(2*y_ltp)
        hline_cropbox = (xp,test_y,x2p,test_y+1)
        hline = image.crop(hline_cropbox)
        #print "Test horizontal line at:",hline_cropbox
        hdata = hline.getdata()
        # and see if there's enough contig black pixels to make a line
        black_count = 0
        for datum in hdata:
            try:
                datum = datum[0]
            except:
                pass
            if datum < 128:
                black_count += 1
                if black_count > x_ltp:
                    break
        if black_count > x_ltp:
            # first_black from top was BOTTOM OF BOX, increment y
            #print "black_count",black_count,"FIRST BLACK IS BOTTOM OF BOX"
            bottom_at = first_black + y_ltp
            boxbottom_offset = window_height_with_margins - bottom_at
            boxtop_offset = window_height_with_margins - (thp + boxbottom_offset)
            boxbottom_offset = window_height_with_margins - (boxtop_offset + thp) 
        else:
            # first_black was TOP OF BOX, decrement y
            #print "black_count",black_count,"FIRST BLACK IS TOP OF BOX"
            boxtop_offset = first_black
            boxbottom_offset = window_height_with_margins - (boxtop_offset + thp)
    increment_y = ((boxtop_offset - boxbottom_offset)/2)
    #print "boxtop_offset, boxbottom_offset, increment_y,", boxtop_offset, boxbottom_offset, increment_y



    # now recenter horizontally
    y_hcrop = (yp+y2p)/2
    center_hline_crop = (xp,y_hcrop,x2p,y_hcrop+1)
    hline = image.crop(center_hline_crop)
    #print "Boundary area w/margins: %d %d %d %d" % (xp,yp,x2p,y2p)
    #print "Sample hline uses crop: %s",center_hline_crop
    hdata = hline.getdata()
    # hdata now has a horizontal stripe of pixels 
    # from the center of the proposed target region + margins
    # locate first black pixel
    first_black = -1
    potential_first_black = -1
    contig = 0
    for position,datum in enumerate(hdata):
        # handle tuple or integer data
        try:
            datum = datum[0]
        except:
            pass
        if datum < 128:
            contig = contig + 1
            if contig >= y_ltp:
                first_black = position
                break
        if datum >= 128:
            # found a thin black
            if contig > 0:
                logger.debug("Found black, but too thin to be box edge.")
            contig = 0
    if first_black < 0:
        logger.warning("No black found to recenter.")
        raise RecenteringException

    if first_black < (2*x_ltp):
        #  black near left; find last set of black pixels 
        #  that is long enough to represent line of thickness lt
        #  by searchi1ng pixels backwards
        print "First black near left"
        hdata = list(hdata)
        hdata.reverse()
        contig = 0
        for position,datum in enumerate(hdata):
            # handle tuple or integer data
            try:
                datum = datum[0]
            except:
                pass
            if datum < 128:
                contig += 1
            else:
                contig = 0
            if contig >= (y_ltp-1):
                boxright_offset = position - contig
                break
        # handle that case and return
        boxleft_offset = window_width_with_margins - (boxright_offset+twp)
        print "boxleft_offset",boxleft_offset,
        print "boxright_offset",boxright_offset,
        #if abs(boxleft_offset-boxright_offset)>20:
        #    pdb.set_trace()
        #print "twp",twp
    else:
        #take a vertical sampling 
        # at twice the line thickness LEFT of the black pixel
        # to see if the black pixel would be a box left or box right

        test_x = xp+first_black-(2*x_ltp)
        vline_cropbox = (test_x,yp,test_x+1,y2p)
        vline = image.crop(vline_cropbox)
        #print "Test vertical line at:",vline_cropbox
        vdata = vline.getdata()
        # and see if there's enough contig black pixels to make a line
        black_count = 0
        for datum in vdata:
            try:
                datum = datum[0]
            except:
                pass
            if datum < 128:
                black_count += 1
                if black_count > y_ltp:
                    break
        if black_count > x_ltp:
            # first_black was RIGHT OF BOX, or routine was fooled
            # by thinking the column line was more box
            # increment x
            #print "black_count",black_count,"FIRST BLACK IS RIGHT OF BOX"
            right_at = first_black + x_ltp
            boxright_offset = right_at 
            boxleft_offset = window_width_with_margins - (twp+boxright_offset)
        else:
            # first_black was LEFT OF BOX, decrement y
            #print "black_count",black_count,"FIRST BLACK IS LEFT OF BOX"
            left_at = first_black
            boxleft_offset = left_at
            boxright_offset = window_width_with_margins - (twp+boxleft_offset)
    increment_x = ((boxleft_offset - boxright_offset)/2)
    #print "boxleft_offset, boxright_offset, increment_x,", boxleft_offset, boxright_offset, increment_x
    # take away the margins you added
    xp += x_marginp
    yp += y_marginp
    x2p -= x_marginp
    y2p -= y_marginp
    # under no circumstances shift by 20 pixels or more
    # Do not shift at all if this appears
    if abs(increment_y) > 15:
        logger.warning("increment_y HIGH at %d" % (increment_y,))
    if abs(increment_x) > 15:
        logger.warning("increment_x HIGH at %d" % (increment_x,))
    if abs(increment_y) > 20:
        logger.warning("increment_y %d TOO HIGH, halving" % (increment_r,))
        increment_x = increment_x/2
    if abs(increment_x) > 20:
        logger.warning("increment_x %d TOO HIGH, halving" % (increment_x,))
        increment_x = increment_x/2
    return xp+increment_x,yp+increment_y,x2p+increment_x,y2p+increment_y

if __name__ == "__main__":
    
    print "Recentering",sys.argv[1]
    image = Image.open(sys.argv[1])
    print "Zone (10,10,120,70), 5 pix margins, 2 pix linewidth, target 100x45."
    try:
        newx,newy,newx2,newy2 = recenter(image,10,10, 120, 70, 5, 5, 2, 2, 100, 45)
        print sys.argv[1],"gets newzone",newx,newy,newx2,newy2
    except Exception,e:
        print e
