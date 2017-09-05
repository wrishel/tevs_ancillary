#!/usr/bin/env python
import sys
import Image
import pdb

"""
We must extend the Zone class so that it keeps a history of the prior
lines contributing to it, and so that it can calculate attributes
of the blob off of that history.

We need a Line class to keep all blobs of what a human would read as
a line, with functions to calculate things like average blob width and
height, top of line, bottom of line.
"""


class Line(object):
    def __init__(self):
        self.zones = []
        self.x1 = None
        self.x2 = None
        self.y1 = None
        self.y2 = None
        

class Zone(object):
    def __init__(self,start_x,end_x,row):
        self.start_x = start_x 
        self.end_x = end_x
        self.row = row
        self.age = 0
        self.row_incr = 0
        self.touched = True

    def __repr__(self):
        return "Blob x1 %d x2 %d y1 %d ht %d rowinc %d" % (
            self.start_x,
            self.end_x,
            self.row + 1 - self.age,
            self.age,self.row_incr)

class ZoneWHistory(Zone):
    def __init__(self,start_x,end_x,row):
        Zone.__init__(self,start_x,end_x,row)
        self.history = []
        self.vertical_legs = 0
        self.horizontal_legs = 0
        self.forward_diagonal_legs = 0
        self.backward_diagonal_legs = 0
        self.curves = 0

    def extend(self,start_x,end_x):
        """add the current value to the history, update current value"""
        pass

    def analyze(self):
        """based on values in history, complete legs fields"""
        pass

    def __repr__(self):
        Zone.__repr__(self)
        pass

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

def big_blobs(f,
              dpi=300,
              dark_threshold=192,
              min_width_divisor=6,
              max_width_divisor=2,
              min_age_divisor=16,
              max_age_divisor=7):    
    """return list of locations of contig dark pixel clumps

     pixels must be darker than dark_threshold, 
     must accumulate to line of min_width < length < max_width 
     and must reach that within max_age rows;
     lines of first 1/5" of image f are skipped;
     lines of bottom 1/10" of image f are skipped;
     columns of first 1/10" 1/20" !!! of image f are skipped;
     requires light pixel slightly to upper left of blob 
     to prevent grayscale regions from generating many blobs
    """
    min_width = dpi/min_width_divisor
    max_width = dpi/max_width_divisor
    min_age = dpi/min_age_divisor
    max_age = dpi/max_age_divisor
    #print "Min max age",min_age, max_age
    col_skip = dpi/20
    blob_list = []
    in_dark = False
    dark_length = 0
    output_blobs = []
    skip = 0
    # check each new dark zone to see if it extends one on the previous line
    # if so, enter the extended version on the new line, keep an aging value

    # at end of each line, discard any zones that have reached max_age
    # but not reached min_span
    lastp = (255,255,255)
    pixeldata = f.getdata()
    next_index = 0
    for p in pixeldata:
        row = next_index / f.size[0]
        col = next_index % f.size[0]
        # from here on, index is the offset of the NEXT pixel
        next_index += 1
        if skip>0:
            skip = skip - 1
            continue
        if row<(dpi/5):
            skip = f.size[0]
            continue
        if row>(f.size[1]-1):#(dpi/40)):
            skip = f.size[0]
            continue
        if col<col_skip:
            continue

        # reinitialize dark at start of handled part of row
        # IF FIRST UNSKIPPED PIXEL OF UNSKIPPED ROW, INITIALIZE FOR ROW
        if col==col_skip and row > 0:
            #if (row % 100) == 0:
            #    print row
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
            #print "Row",row,"col",col
            #print "blob_list pre-filter",blob_list
            # TEST: extend output blobs only if a blob is greater
            # than min_age, less than max_age, and not touched
            output_blobs.extend([z for z in blob_list  
                                 if (z.end_x - z.start_x)>min_width 
                                 and (z.end_x - z.start_x)<max_width
                                 and z.age >= min_age 
                                 and z.age <= max_age
                                 and not z.touched])
            blob_list = [z for z in blob_list 
                         if z.age <= (max_age+1) 
                         and (z.row_incr > 0 or z.age==1)]
            for z in blob_list:
                z.row_incr = 0
            #print "output list pre-transfer",output_blobs

            output_blobs = remove_dups(output_blobs)
            #print "output list post-transfer",output_blobs
            #TEST: Do not eliminate blobs until age exceeds max_age+1
            blob_list = [z for z in blob_list 
                         if (z.end_x - z.start_x)<=min_width 
                         or (z.end_x - z.start_x)>= max_width
                         or z.age < min_age
                         #
                         or z.age <= max_age+1]
            #print "Length of blob list post-removal",len(blob_list)
            # set touched false for every blob;
            # later, set touch true only if it extends to new row
            for z in blob_list:
                z.touched = False

        # dark?  extend dark or initiate new dark zone
        if (p[0]+p[1]+p[2])<(dark_threshold*3):
            if in_dark:
                dark_length = dark_length+1
            else:
                in_dark = True
                dark_length = 1 # start_x = end_x less (dark_length-1)

        # light but last one dark? allow one pixel to miss w/o cancelling dark
        # and count the skipped pixel if the next one is dark as well
        elif ((lastp[0]+lastp[1]+lastp[2])<(dark_threshold*3)) and in_dark:
            try:
                nextp = pixeldata[next_index]
                if (nextp[0]+nextp[1]+nextp[2])<(dark_threshold*3):
                    dark_length = dark_length+1
            except IndexError:
                pdb.set_trace()
        # light twice?
        else:
            # wrap up any previous darkness by creating a Zone
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
                        z.touched = True
                        merged = True
                # initiate oval only if several dark pix together on line
                if not merged and dark_length > (dpi/64):
                    # avoid grayscale problems
                    # only create a blob if you can find
                    # a very light pixel nearby
                    if row > (dpi/30) and (col-dark_length)>(dpi/20) and col<(f.size[0]-(dpi/20)):
                        p1 = f.getpixel((col-dark_length-(dpi/25),row-(dpi/30)))
                        p2 = f.getpixel((col-dark_length-(dpi/25)-1,row-(dpi/30)))
                        p3 = f.getpixel((col-dark_length-(dpi/25)-2,row-(dpi/30)))
                        p4 = f.getpixel((col+(dpi/25),row-(dpi/60)))
                        p5 = f.getpixel((col+(dpi/25)+1,row-(dpi/60)))
                        if (
                            (p1[0]+p1[1]+p1[2]) > (dark_threshold*3) 
                            or (p2[0]+p2[1]+p2[2]) > (dark_threshold*3)
                            or (p3[0]+p3[1]+p3[2]) > (dark_threshold*3)
                            or (p4[0]+p4[1]+p4[2]) > (dark_threshold*3)
                            or (p5[0]+p5[1]+p5[2]) > (dark_threshold*3)
                                ):
                            z = Zone(col-dark_length+1,col,row)
                            #if z.start_x < (dpi/15):
                            #    print z
                            blob_list.append(z)
                        else:
                            pass
                    else:
                        z = Zone(col-dark_length+1,col,row)
                        #if z.start_x < (dpi/15):
                        #    print z
                        blob_list.append(z)
                        # dark areas will generate huge blob lists
                        # no reasonable ballot should have contests
                        # generating more than 100 blobs per row
                        if len(blob_list)>(100*max_age):
                            print "Blob list too long",len(blob_list)
                            return []
                pass
            else:
                pass
        lastp = p
    return [z for z in output_blobs if z.age > 0]

def find_aligned_blobs(output_blobs):
    # check for x1s, x2s, or y1s within some distance in multiple blobs
    for b1 in output_blobs:
        for b2 in output_blobs:
            pass


if __name__ == "__main__":
    if len(sys.argv)<5:
        print "Usage: python blobs.py filename dpi threshold min_width_divisor"
        sys.exit(-1)
    dpi = int(sys.argv[2])
    threshold_start = int(sys.argv[3])
    min_width_divisor = int(sys.argv[4])
    print "File %s dpi %d threshold_start %d min_width_divisor %d" % (sys.argv[1],
                                                                dpi,
                                                                threshold_start,
                                                                min_width_divisor)
    f = Image.open(sys.argv[1])
    # go through f line by line, 
    # recording start and end of every dark pixel zone
    #dark_threshold = 208
    #max_age = 5

    for tdelta in range(0,64,8):
        for mwddelta in range(4):
            output_blobs = big_blobs(f,
                                     dpi=dpi,
                                     dark_threshold=threshold_start+tdelta,
                                     min_width_divisor=min_width_divisor+mwddelta)
            print "Threshold %d min_width_divisor %d Blobs" % (
                threshold_start+tdelta,
                min_width_divisor+mwddelta
                )
            for b in output_blobs:
                if b.start_x>(dpi/10):
                    print b
            # find aligned blobs
            find_aligned_blobs(output_blobs)
