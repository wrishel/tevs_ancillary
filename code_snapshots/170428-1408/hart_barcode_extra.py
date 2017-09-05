# hart_barcode.py
import Image, ImageStat
import pdb
import sys
import logging

"""
 Hart ballots use I25 -- interleaved two of five, where two of every five
   bars or spaces are wide (Wikipedia). The first digit is encoded in bars,
   the second digit in spaces.  Start code is four narrows, nnnn; end code
   is WIDE, narrow, narrow -- Wnn.  
   Digt|Line width
   0	n	n	W	W	n
   1	W	n	n	n	W
   2	n	W	n	n	W
   3	W	W	n	n	n
   4	n	n	W	n	W
   5	W	n	W	n	n
   6	n	W	W	n	n
   7	n	n	n	W	W
   8	W	n	n	W	n
   9	n	W	n	W	n
"""
class BarcodeException(Exception):
    "Raised if barcode not properly interpreted"
    pass

def hart_barcode(image,x,y,w,h):
    """read a vertical barcode on a hart ballot, as in getbarcode in PILB"""
    numeric_whites_list = []
    numeric_blacks_list = []
    whites_list = []
    blacks_list = []
    whitethresh = 128
    croplist = (x,y,x+w,y+h)
    crop = image.crop(croplist)
    # 1) scan down all lines, deciding white or black
    firsttime = True
    last_was_white = True
    whitecount = 0
    blackcount = 0
    for y in range(crop.size[1]-1,0,-1):
        linecroplist = (0,y,crop.size[0],y+1)
        linecrop = crop.crop(linecroplist)
        linemean = ImageStat.Stat(linecrop).mean[0]
        if linemean > whitethresh:
            if last_was_white:
                whitecount += 1
            else:
                blacks_list.append(blackcount)
                blackcount = 0
                whitecount = 1
                last_was_white = True
        else:
            if not last_was_white:
                blackcount += 1
            else:
                if firsttime: firsttime = False
                else:
                    whites_list.append(whitecount)
                    whitecount = 0
                    blackcount = 1
                    last_was_white = False
    # 2) determine average length of blacks, whites;
    # replace original lengths with True for narrow, False for wide
    if len(blacks_list)<37 or len(whites_list)<38:
        print "Lengths",len(whites_list),len(blacks_list)
        print "whites_list",whites_list
        print "blacks_list",blacks_list
        raise BarcodeException
    bsum = 0
    avg = 0
    for b in blacks_list:
        bsum += b
    avg = bsum/len(blacks_list)
    # convert wide -->True, narrow-->False
    numeric_blacks_list = blacks_list
    blacks_list = map(lambda el: el >= avg, blacks_list)    
    wsum = 0
    avg = 0
    for w in whites_list[1:]:
        wsum += w
    avg = wsum/len(whites_list[1:])
    print "Avg",avg
    # after trimming initial white (not part of bar code)
    # first two whites, first two blacks must be narrow 
    whites_list = whites_list[1:]
    # convert wide -->True, narrow-->False
    numeric_whites_list = whites_list
    whites_list = map(lambda el: el >= avg, whites_list)
    # first two whites, first two blacks should be narrow (False)
    if (blacks_list[0] 
            or blacks_list[1] 
            or whites_list[0] 
            or whites_list[1]):
        logging.getLogger('').debug("Problem with bar code: not finding start group.")
    # process seven groups of five blacks, five whites
    # expect exactly two wides
    values = [0,0,0,0,0,0,0, 0,0,0,0,0,0,0]
    for group in range(7):
        bvalue = 0
        wvalue = 0
        bwides = 0
        wwides = 0
        if blacks_list[2+(group*5)+0]:
            bvalue += 1
            bwides += 1
        if blacks_list[2+(group*5)+1]:
            bvalue += 2
            bwides += 1
        if blacks_list[2+(group*5)+2]:
            bvalue += 4
            bwides += 1
        if blacks_list[2+(group*5)+3]:
            bvalue += 7
            bwides += 1
        if blacks_list[2+(group*5)+4]:
            bwides += 1
        if bvalue == 11: bvalue = 0
        if whites_list[2+(group*5)+0]:
            wwides += 1
            wvalue += 1
        if whites_list[2+(group*5)+1]:
            wwides += 1
            wvalue += 2
        if whites_list[2+(group*5)+2]:
            wwides += 1
            wvalue += 4
        if whites_list[2+(group*5)+3]:
            wwides += 1
            wvalue += 7
        if whites_list[2+(group*5)+4]:
            wwides += 1
        if wvalue == 11: wvalue = 0
        values[group*2] = bvalue
        values[1+(group*2)] = wvalue
    if values[3] != 0 or bwides != 2 or wwides != 2:
        print "numeric_whites_list",numeric_whites_list
        print "numeric_blacks_list",numeric_blacks_list
        print "whites_list",whites_list
        print "blacks_list",whites_list
        raise BarcodeException
    retval = "%d%d%d%d%d%d%d%d%d%d%d%d%d%d" % (
        values[0],values[1],values[2],values[3],values[4],values[5],values[6],
values[7],values[8],values[9],values[10],values[11],values[12],values[13])
    return (retval)

if __name__ == "__main__":
    if len(sys.argv)<6:
        print "usage: python hartbarcode.py image x y w h"
        sys.exit(1)
    image = Image.open(sys.argv[1])
    x,y,w,h = int(sys.argv[2]),int(sys.argv[3]),int(sys.argv[4]),int(sys.argv[5])
    try:
        barcode = hart_barcode(image,x,y,w,h)
        print barcode
    except BarcodeException:
        print sys.argv[2]
        try:
            barcode = hart_barcode(image.rotate(180),x,y,w,h)
            print barcode
        except BarcodeException:
            print "Failed to get required stripes on both image and rotated image."
            pdb.set_trace()
    sys.exit(0)
