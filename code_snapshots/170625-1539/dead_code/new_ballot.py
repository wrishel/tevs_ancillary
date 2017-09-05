#!/usr/bin/env python
# new_ballot merges hart_ballot and the generic ballot being developed;
# hart_ballot's build_layout makes calls to the routines from the old
# find_intensity_changes.
import Image
import ImageDraw
import ImageStat
import blobs
import sys
import pdb
import os
import os.path
import subprocess
import uuid
import re
import ocr
import BallotClass
import const
from adjust import rotator
from cropstats import cropstats
import Image, ImageStat
from demo_utils import *
from line_util import *
from diebold_util import *
from diebold_edges import find_dashes
from new_ballot_side import NewBallotSide

def adj(a):
    return int(round(float(const.dpi) * a))

def elim_halftone(x):
    if x>64:
        retval = 255
    else:
        retval = 0
    return retval


class NewBallot(BallotClass.Ballot):
    """Class representing Diebold duplex and single-sided ballots.

    The file name diebold_ballot.py and the class name DieboldBallot
    correspond to the brand entry in tevs.cfg (diebold.cfg), 
    the configuration file.
    """

    def __init__(self, image_filenames, extensions):
        #convert all our constants to locally correct values
        # many of these conversions will go to Ballot.py,
        # extenders will need to handle any new const values here, however
        # this is the size of the printed vote target's bounding box
        # add these margins to the vote target's bounding box 
        # when cropping and analyzing for votes
        self.min_contest_height = adj(const.minimum_contest_height_inches)
        self.vote_target_horiz_offset = adj(const.vote_target_horiz_offset_inches)
        self.writein_xoff = 0 #XXX
        self.writein_yoff = adj(-.1)
        self.allowed_corner_black = adj(const.allowed_corner_black_inches)
        self.back_upper_right_plus_x = 0
        self.back_upper_right_plus_y = 0
        self.left_landmarks = []
        self.right_landmarks = []
        self.vendor_landmarks = []
        super(NewBallot, self).__init__(image_filenames, extensions)
        def add_page(number, fname):
            nbs = NewBallotSide(
                ballot=self,
                dpi=const.dpi,
                image_filename=fname,
                number=number
            )
            self.side_list.append(nbs)
        if not isinstance(image_filenames, basestring):
            for i, fname in enumerate(image_filenames):
                add_page(i, fname)
        else: #just a filename
            add_page(0, image_filenames)


    def vendor_level_adjustment(self, page, image, x, y, w, h):
        """Given prelim xy offsets of target w margins, fine adjust target."""
        # this can make use of extended page landmarks
        # which should be complete or partial sets of left and right
        # timing marks; the vote op's y should be at the nearest quarter 
        # inch boundary corresponding to the lines running between left
        # and right dashes.

        # check strip at center to look for either filled or empty oval;
        # recenter vertically
        darkened = 245
        crop = page.image.crop((x,y,w,h))
        cropx = x
        cropy = y
        stripe = crop.crop(
            ((crop.size[0]/2),
             0,
             (crop.size[0]/2)+1,
             crop.size[1]-1)
            )
        before_oval = 0
        after_oval = 0
        oval = 0
        stripedata = list(stripe.getdata())
        for num,p in enumerate(stripedata):
            if p[0] > darkened:
                before_oval += 1
            else:
                try:
                    test_offset = before_oval+printed_oval_height
                    if ((stripedata[test_offset-2][0] < darkened) or 
                        (stripedata[test_offset-1][0] < darkened) or 
                        (stripedata[test_offset][0] < darkened) or
                        (stripedata[test_offset+1][0] < darkened) or
                        (stripedata[test_offset+2][0] < darkened)):
                        oval_start = num
                        oval_end = num + printed_oval_height
                        after_oval = (
                            stripe.size[1] 
                            - (oval_start+printed_oval_height))
                        break
                except IndexError:
                    break
        #print cropy,before_oval,oval,after_oval
        afterlessbefore = int(round((after_oval - before_oval)/2))
        if abs(afterlessbefore)>2:
            cropy -= afterlessbefore
            #print "Adjusted",cropy
            crop = page.image.crop((
                cropx - page.margin_width,
                cropy - page.margin_height,
                min(cropx + page.margin_width + page.target_width,
                    page.image.size[0]-1),
                min(cropy + page.margin_height + page.target_height,
                    page.image.size[1]-1)
                ))
        self.log.debug("Result after final adj: (%d,%d)" % (cropx,cropy))
        return cropx, cropy


    # Extenders do not need to supply even a stub flip
    # because flip in Ballot.py will print a stub message in the absence
    # of a subclass implementation
    #def flip(self, im):
    #    # not implemented for Demo
    #    print "Flip not implemented for Demo."
    #    return im

    def find_landmarks(self, page):
        """just dup find_front_landmarks"""
        return self.find_front_landmarks(page)

    def find_back_landmarks(self, page):
        """just dup find_front_landmarks"""
        try:
            retval = self.find_front_landmarks(page)
        except Ballot.BallotException as e:
            page.blank = True
            retval = [0,0,0]
        return retval

    def find_front_landmarks(self, page):
        """Diebold ballots have dashes across the top and down the sides.

        The dashes occupy the leftmost .2" of a .25" zone and 
        and the uppermost .05" of a .25" zone.

        The uppermost dashes begin approximately 0.5" from the top,
        and the top edge of the lowermost dashes 
        is approximately 0.5" from the bottom. 

        The lowermost edge dashes are level with a series of dashes
        along the bottom which represent the layout code.

        A thinline appears approximately 0.15" below the top of the
        uppermost dashes; this is the upper line of boxes surrounding
        the main material.  Unfortunately, the boxes may not form a
        single rectangle.

        There is text underneath the center part of the bottom dashes.

        The side dashes extend very nearly to the edges of the image;
        the better landmarks are their inboard edges, as opposed to 
        their outboard edges.

        Vote ovals are approximately 0.1" tall by 0.2" wide and are
        centered vertically on the centerlines of side dashes.

        Vote ovals may be printed in a color other than black.
        Marin: vote ovals are printed in red

        Column widths are not uniform: Marin 3 column may be 2.75", 2.75", 2.5"

        Allow for 1/4" vertical slippage by scanning for top and bottom dashes
        from 1/4" to 3/4" from the top and bottom.  Treat the top of the 
        first identified dash line as the upper y landmarks.

        Allow for 1/4" horizontal slippage by locating the last x at which
        a reliable .05" dark .2" white pattern appears for one inch beneath 
        the identified top dash row and treating that as the ulc landmark x;
        do the same scanning from the outside edge in to identify the urc 
        landmark y.

        Store the upper left x,y coordinates of EACH timing mark dash
        to allow greater accuracy in locating the vote ops.

        """
        # call routines in diebold_edges
        # and save resulting dash bboxes as self.vendor_landmarks
        
        left, right = find_dashes(page.image,const.dpi)
        self.vendor_landmarks = [left,right]
        # landmarks list 
        # built from inboard upper coordinates 
        # of the four dashes at ends of dash sequences,
        # counterclockwise from upper left corner
        landmarks = [(left[0][2],left[0][1]),
                     (right[0][0],right[0][1]),
                     (right[-1][0],right[-1][1]),
                     (left[-1][2],left[-1][1])
                     ]
        # we don't store here
        #self.landmarks = landmarks
        longdiff = landmarks[3][1] - landmarks[0][1]
        shortdiff = landmarks[3][0] - landmarks[0][0]
        r = float(shortdiff)/float(longdiff)
        # we depend on back landmarks being processed after front
        self.back_upper_right_plus_x = landmarks[1][0]
        self.back_upper_right_plus_y = landmarks[1][1]
        self.log.debug("Landmarks %s, rot %f, longdiff %d" % (landmarks,
                                                              r,
                                                              longdiff)
                       )
        page.landmarks = landmarks
        return r,landmarks[0][0],landmarks[0][1],longdiff

    

    def is_tinted_by(triplet,diff):
        """ return True if triplet tint  >=diff
        
        For this purpose, tint is defined as the maximum absolute value
        of the difference between any two members of the triplet;
        tint (126,128,130) is 4 and tint (128,128,128) is 0.

        Triplet may be a pixel or may be a mean from ImageStat.Stat.
        CAUTION: "Black" may have a non-zero tint
        """
        tint0_1 = abs(triplet[0] - triplet[1])
        tint1_2 = abs(triplet[1] - triplet[2])
        tint0_2 = abs(triplet[0] - triplet[2])
        tint = max(max(tint0_1,tint1_2), tint0_2)
        return tint >= diff
        
    def get_ulc_if_tinted_oval(self,image,x,y):
        """Return upper left corner of oval bbox if x,y on oval's bottom wall.

        Look back to find trailing oval offering tint at:

        left wall, up by half oval height and back by half oval width,
        with half oval width of checking;

        right wall, up by half oval height and forward by half oval width,
        with half oval width of checking;

        and top wall, up by oval height with half oval height of checking.
        """
        left_wall = -1
        for test_x in range(x-(oval_width/2),x+(oval_width/2)):
            p = getpixel((test_x,y))
            if is_tinted_by(p,10):
                left_wall = test_x
                break
        right_wall = -1
        for test_x in range(x+(oval_width/2),x+oval_width):
            p = getpixel((test_x,y))
            if is_tinted_by(p,10):
                right_wall = test_x
                break
        top_wall = -1
        for test_y in range(y - (3*oval_height/2),y-(oval_height/2),1):
            p = getpixel((x,test_y))
            if is_tinted_by(p,10):
                top_wall = test_y
                break
        if left_wall >= 0 and right_wall >= 0 and top_wall >=0:
            return (left_wall,top_wall)
        else:
            return ()
        
    def find_tinted_voteops(self, page):
        """NOT IN USE:Given deskewed image and starting x, return list of tinted voteops.

        The Humboldt Diebold images are so compressed that the tint is iffy.
        So an alternative is to use a darkness test followed by a check for
        darkness at the correct related pixels, COUPLED WITH A TEST FOR 
        NO SUBSTANTIAL DARKNESS IN TEST ZONES OUTBOARD .04" to .05" 
        FROM THE OVAL.


        Scan down deskewed image at starting x.

        When tinted pixel found, call is_bottom_wall_of_oval to determine
        existence of vote oval ending at coords.

        Group into sublists by using untinted dark pixels as breaks.

        When only one oval is found in a sublist, 
        check for additional oval at same y offset

        """
        retlist = []
        # start with one sublist
        retlist.append([])
        image = page.image
        for y in range(const.dpi,
                       im.size[1]-const.dpi,
                       1):
            p = image.getpixel((starting_x,y))
            # on tinted pix, check for and append oval to current sublist;
            # on darkened untinted pix, add new sublist
            if is_tinted_by(p,10):
                ulc_of_oval = get_ulc_if_tinted_oval(image,starting_x,y)
                if len(ulc_of_oval)>1:
                    # you could OCR now and store Choices instead of coords
                    retlist[-1].append(ulc_of_oval)
            elif p[0]< const.line_darkness_threshold and len(retlist[-1]>0):
                # you could OCR from here to the next oval encountered
                # and store Contest rather than sublist
                retlist.append([])
        
        return retlist
                
    def get_layout_code(self, page):
        """
        From PILB:
static inline PyObject*
diebolddashcode(Imaging im, int max4dark, int dpi, int starty)
{
  UINT8 *p;
  int x,y;
  int xcontig = 0;
  int ycontig = 0;
  int startx = 0;
  int foundx = 0;
  int foundy = 0;
  int startlastx = 0;
  int foundlastx = 0;
  int foundlasty = 0;
  int eighth = dpi/8;
  float distance = 0.;
  INT32 accum = 0;
  int n;
  // look for (x,y) of first dash at extreme left of image 
  // starting at starty and continuing upwards for one inch;
  // a dash will consist of at least 1/8" of dark pixels repeated for three rows
  foundx = 0;
  xcontig = 0;
  for( y = starty; y > (starty - dpi); y--){
    //printf("y=%d, max4dark %d, starty %d dpi %d\n",y,max4dark, starty, dpi);
    // if we failed to reach the necessary thickness of potential dash,
    // reset the starting point to zero for subsequent lines
    if (xcontig < eighth){
      printf("Setting startx back to zero at %d\n",y);
      startx = 0;
    }
    xcontig = 0;
    for (x = startx; x < startx + dpi; x++){
      p = (UINT8*) &im->image32[y][x];
      if (*p <= max4dark){
	xcontig++;
	if (xcontig > eighth){
	  foundx = x - xcontig;
	  foundx++;
	  foundy = y;
	  ycontig++;
	  printf("%d on line %d makes %d\n",xcontig,y,ycontig);
	  break;
	}
      }
      else {
	xcontig = 0;
      }
    }
    if (foundx>0){
      startx = foundx;
      //printf("ycontig now %d, startx set to %d\n",ycontig,startx);
    }
    if (ycontig == dpi/32){ 
      //printf("Ycontig is %d at line %d, foundx is %d\n",ycontig, y,foundx);
      break;
    }
    // found a dash ending at foundx+xcontig, foundy - ycontig
  }
        """
        dash_height_pixels = adj(0.06)
        dash_width_pixels = adj(0.18)
        dash_window_width_pixels = adj(0.25)
        # page.landmarks:
        # inboard upper edges of extreme dashes at UL, UR, LR, LL
        # page.landmarks[2] is upper inboard coord of bottom right dash
        # page.landmarks[3] is upper inboard coord of bottom left dash
        # length available to page.landmarks is horiz dist between l2 and l3
        length = page.landmarks[2][0] - page.landmarks[3][0]
        start_y = page.landmarks[3][1] + (dash_height_pixels/2)
        end_y = page.landmarks[2][1] + (dash_height_pixels/2)
        # length should exclude the unmarked contents of the left dash's window
        length -= adj(0.07)
        # first code dash begins after those contents
        fcd_start_x = page.landmarks[3][0] + adj(0.07)
        # code dash centers are half dash widths
        fcd_center_x = fcd_start_x + (dash_width_pixels/2)
        
        # if the ballot width is not 8.5", save someone some trouble
        num_coding_dashes = 8 * 4
        calced_dashes = int(round(float(4*length)/const.dpi))
        if num_coding_dashes != calced_dashes:
            self.log.error("NCD %d calced %d" % (num_coding_dashes,calced_dashes))
            print "NCD %d calced %d" % (num_coding_dashes,calced_dashes)
            print page.landmarks[2][0] - page.landmarks[3][0]
            print length, length * 4, (length * 4.)/const.dpi
            print page.landmarks
            pdb.set_trace()

        # check 3x3 spots at center of each dash location for dark/light, 
        # build up a binary pattern corresponding to presence of dashes
        # beware of rounding errors as moving from dash window to dash window
        accum = 0
        for n in range(32):
            this_dash_center_x = fcd_center_x + int(round(n*length/32.))
            dist_from_start = this_dash_center_x - fcd_start_x
            dist_from_end = length - dist_from_start
            this_dash_center_y = int(round(
                ( (dist_from_start * end_y) + (dist_from_end * start_y) )
                /length)
            )
            # check 9 pix square at coord for avg red
            crop = page.image.crop(
                (this_dash_center_x - 1,
                 this_dash_center_y - 1,
                 this_dash_center_x + 2,
                 this_dash_center_y + 2))
            stat = ImageStat.Stat(crop)
            dark = (stat.mean[0] < const.line_darkness_threshold)
            self.log.debug("Intensity at (%d,%d) = %f; dark = %s" % (
                this_dash_center_x,
                this_dash_center_y,
                stat.mean[0],
                stat.mean[0] < const.line_darkness_threshold))
                                                 
            if dark:
                accum += 1
            accum *= 2
            #self.log.debug( " Accum %x" % (accum,))
        print "Accum %x" % (accum,)
        return accum


    def build_front_layout(self, page):
        self.log.debug("Entering build front layout.")
        return self.build_layout(page)

    def build_back_layout(self, page):
        self.log.debug( "Entering build back layout.")
        return self.build_layout(page,back=True)

    def build_layout(self, page, back=False):
        """ Get layout and ocr information from Diebold ballot

        Assumes page.image has been deskewed.
        """
        app = GenerateTemplate(const.dpi,page.filename,200)
        return app.maincontestlist

# Support function for getting text
def tesseract_and_clean(x):
    text = ocr.tesseract(x)
    # strip initial space
    if len(text)>0 and text.startswith(" "):
        text = text[1:]
    # strip initial letter and space from start of longer text
    if len(text)>10 and text[1]==" ":
        text = text[2:]
    text = ocr.clean_ocr_text(text,keep_newlines=True)
    return text

def intensity(x):
    """return intensity assuming three color pixel x"""
    return int(round((x[0]+x[1]+x[2])/3.0))

def is_lighter_than(pix,threshold):
    """return whether intensity avg above threshold"""
    return (pix[0]>threshold and pix[1]>threshold and pix[2]>threshold)


class TargetAndText(object):
    def __init__(self,start_x,start_y,end_x,end_y):
        self.target_start_x = start_x
        self.target_start_y = start_y
        self.target_end_x = end_x
        self.target_end_x = end_x
        self.text = None

    def get_text_following_target(image):
        pass

class ContestBox(object):
    def __init__(self,start_x,start_y,end_x,end_y,text):
        self.start_x = start_x
        self.start_y = start_y
        self.end_x = end_x
        self.end_y = end_y
        self.text = text
        self.choices = []
    def choices_in_ballot_frame():
        pass
    def choices_in_contest_frame():
        pass

class PotentialBox(object):
    def __init__(self,left,right):
        quarter = 75
        # ensure lower xy precedes higher xy
        if left[0]>left[2]:
            left[0],left[2] = left[2],left[0]
        if left[1]>left[3]:
            left[1],left[3] = left[3],left[1]
        if right[0]>right[2]:
            right[0],right[2] = right[2],right[0]
        if right[1]>right[3]:
            right[1],right[3] = right[3],right[1]
        self.endpointsleft = left
        self.endpointsright = right
        # let's just get rid of completed, 
        # and always make the largest box 
        # (which will get deleted if it encloses others)
        self.completed = True 
        self.bbox = [min(self.endpointsleft[0],self.endpointsleft[2]),
                     min(self.endpointsleft[1],self.endpointsleft[3]),
                     max(self.endpointsright[0],self.endpointsright[2]),
                     max(self.endpointsright[3],self.endpointsright[1])]
        if abs(self.endpointsleft[3]-self.endpointsright[3]) < quarter:
            self.completed = True
        else:
            if self.endpointsleft[3] > self.bbox[3]:
                self.bbox[3] = self.endpointsleft[3]
            #print "Box %s may need split at y=%d or y = %d" % (
            #self.bbox,self.endpointsright[3],self.endpointsleft[3])
            

    def fully_encloses(self,other,threshold=10):
        if ( (self.bbox[0] <= (other.bbox[0]+threshold))
             and (self.bbox[1] <= (other.bbox[1]+threshold))
             and (self.bbox[2] >= (other.bbox[2]-threshold))
             and (self.bbox[3] >= (other.bbox[3]-threshold)) 
             and not (
                (self.bbox[0] == (other.bbox[0]))
             and (self.bbox[1] == (other.bbox[1]))
             and (self.bbox[2] == (other.bbox[2]))
             and (self.bbox[3] == (other.bbox[3]))
                )
             ):
            #print "%s ENCLOSES %s" % (self.bbox,other.bbox)
            return True
        else:
            #print "%s does not enclose %s" % (self.bbox,other.bbox)
            return False

    def __repr__(self):
        return "Potential box bbox %s complete %s" % (
            self.bbox,
            self.completed)


class Transition(object):
    def __init__(self,x, y, min_line_break_length):
        self.startx = x
        self.starty = y
        self.endx = x
        self.endy = y
        self.min_line_break_length = min_line_break_length

    def __repr__(self):
        return "Line from (%d,%d) to (%d,%d)" % (self.startx,
                                           self.starty,
                                           self.endx,
                                           self.endy)
    def endpoints(self):
        return ((self.startx,self.starty),(self.endx,self.endy))

    def isactive(self):
        return abs(self.endx-self.startx) < self.min_line_break_length


def find_white_in(im,start_x,end_x,dpi=300,threshold=208):
    """given an image, return bboxes of completely white areas"""
    #print "Examining image for white stripes"
    min_height = dpi/60
    data = list(im.getdata())
    light_lines = []
    zones = []
    light_length = 0
    in_light = True
    im_width, im_height = im.size
    for y in range(im_height):
        in_light = True
        light_length = 0
        for x in range(start_x,end_x):
            pix = data[(y*im_width)+x]
            if not is_lighter_than(pix,threshold):
                in_light = False
                break
        if in_light:
            light_lines.append(y)
    zone_start = -1
    for index in range(len(light_lines)):
        if zone_start == -1:
            zone_start = light_lines[index]
        elif light_lines[index] != ((light_lines[index-1])+1):
            zone_end = light_lines[index-1]
            zones.append((zone_start,zone_end))
            zone_start = light_lines[index]                   
    return [x for x in zones if (x[1]-x[0])>=min_height]

def offset_of_tlist_entry_with_x_y_slip_n(tlist,x,y,n=15):
    for offset,t in enumerate(tlist):
        if (t.endx > (x-n) 
            and t.endx < (x+n) 
            and t.endy > (y-n) 
            and t.endy < (y+n)):
            return offset
    return -1

def move_inactive_transitions(y, min_line_break_length,active,inactive):
    delete_from_active = []
    for t in active:
        if abs(y - t.endy) >= min_line_break_length:
            inactive.append(t)
            delete_from_active.append(t)
    for t in delete_from_active:
        active.remove(t)

def find_intensity_boundaries(image, 
                              skip_between_lines, 
                              min_extent, 
                              min_line_break_length,
                              required_intensity_drop=50, 
                              intensity_drop_span=2, 
                              search_forwards=True,
                              starting_x = 0,
                              max_width = None):
    """return list of intensity boundaries meeting or exceeding min_extent"""
    idrop = intensity_drop_span
    if max_width is None:
        max_width = image.size[0] - idrop
    else:
        pass
    active_tlist = []
    inactive_tlist = []
    if starting_x>0:
        xrange_start = starting_x + idrop
        xrange_end = min(starting_x + idrop + max_width,image.size[0]-1)
    else:
        xrange_start = 1+idrop
        xrange_end = max_width
    xrange_incr = 1
    if not search_forwards:
        xrange_start, xrange_end = xrange_end, xrange_start
        xrange_incr = -1

    for y in range(0, image.size[1], skip_between_lines):
        move_inactive_transitions(y, 
                                  min_line_break_length, 
                                  active_tlist, 
                                  inactive_tlist)

        xrange_end = min(xrange_end,image.size[0]-abs(idrop+1)) 
        for x in range(xrange_start, xrange_end, xrange_incr):
            for z in range(idrop):
                try:
                    pix1 = image.getpixel((x,y))
                    pix2 = image.getpixel((
                            x+((z+1)*xrange_incr),
                            y
                            ))
                except IndexError,e:
                    print x,y,image.size
                    print e
                    pdb.set_trace()
                if (intensity(pix1) >= 
                    (intensity(pix2) + required_intensity_drop)):
                    offset = offset_of_tlist_entry_with_x_y_slip_n(
                        active_tlist,
                        x,
                        y - skip_between_lines,
                        2)
                    if offset>-1:
                        active_tlist[offset].endx = x
                        active_tlist[offset].endy = y
                    else:
                        active_tlist.append(
                            Transition(x,y,min_line_break_length)
                            )
    active_good = [x for x in active_tlist if (x.endy - x.starty)>min_extent]
    inactive_good = [x for x in inactive_tlist 
                     if (x.endy - x.starty)>min_extent]
    return y,active_good,inactive_good

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

def merge_transition_list(tlist_to_merge):
    v_endpoints = []
    tlist_to_merge.sort(key = lambda x: x.startx)
    split_indices = [0]
    lastx = 0
    for (index,line) in enumerate(tlist_to_merge):
        if (line.startx - lastx)>50: 
            split_indices.append(index)
        lastx = line.startx
    for split_loc_index in range(len(split_indices)):
        try:
            end = split_indices[split_loc_index+1]
        except IndexError:
            end = -1
        sublist_to_merge = tlist_to_merge[split_indices[split_loc_index]:end]
        #print "Sublist_to_merge",sublist_to_merge
        # from the sublist, take the startx of the middle value
        # for every line in the zone
        if len(sublist_to_merge)>0:
            median_x = sublist_to_merge[len(sublist_to_merge)/2].startx
            endpoint_ys = [(t.starty,t.endy) for t in sublist_to_merge]
            endpoint_ys.sort()
            endpoint_ys2 = list(merge(endpoint_ys))
            endpoint_ys = endpoint_ys2
            new_endpoints = [[median_x,min(t[0],t[1]),median_x,max(t[0],t[1])] for t in endpoint_ys]
            v_endpoints.extend(new_endpoints)
            #print "Median x",median_x
            #print "New endpoints",new_endpoints
    #print "Tentative list",v_endpoints
    # for each x value, see if the endpoint of any line 
    # is within 1/10" of the start of the next; if so,
    # merge them.
    tmp_dict = {}
    tenth = 30
    for line in v_endpoints:
        if line[0] in tmp_dict:
            tmp_dict[line[0]].append(line)
        else:
            tmp_dict[line[0]]=[line]
    xkeys = tmp_dict.keys()
    xkeys.sort()
    final_endpoints = []
    for x in xkeys:
        lines = tmp_dict[x]
        lines.sort(key = lambda l: l[1])
        for index in range(1,len(lines)):
            if abs(lines[index][1] - lines[index-1][3]) < tenth:
                lines[index-1][3] = lines[index][3]
                lines[index][1] = -1
        # ensure each output set of end coordinates begins with low vals,
        # and ends with high vals
        final_endpoints.extend(
            [ [ min(x[0],x[2]),min(x[1],x[3]),max(x[0],x[2]),max(x[1],x[3]) ] 
              for x in lines if x[1] >= 0]
            )
    return final_endpoints

def confirm_continuing_dark_at(image,y,threshold=200):
    """starting at y, return True if line crosses image at/near y"""
    current_y = y
    miss_count = 0
    for x in range(image.size[0]-5):
        if current_y >=2:
            p0 = image.getpixel((x,current_y-2))
        else:
            p0 = (255,255,255)
        if current_y >=1:
            p1 = image.getpixel((x,current_y-1))
        else:
            p1 = (255,255,255)
        if current_y >=0:
            p2 = image.getpixel((x,current_y))
        else:
            p2 = (255,255,255)
        if current_y < (image.size[1]-2):
            p3 = image.getpixel((x,current_y+1))
        else:
            p3 = (255,255,255)

        if p1[0]<threshold or p2[0]<threshold:
            # line ok
            pass
        elif p0[0]<threshold:
            current_y = current_y - 1
        elif p3[0]<threshold:
            current_y = current_y + 1
        else:
            miss_count = miss_count + 1
            if miss_count > 15:
                return False
    return True


def find_contests(image,vboxlist,dpi):
    """find contests by looking for horizontal lines crossing column"""
    # note that we need alternative ways of finding a contest
    # change in font size would be one sign
    # substantial gaps between groups of vote targets would be another hint
    smallboxlist = []
    # if we find we are triggering continually,
    # we are in a gray scale area, 
    # and need to generate a high contrast crop if possible
    line_darkness_threshold, ldt = 200,200
    for index,vbox in enumerate(vboxlist):
        # walk the left edge, looking for solid black
        # immediately preceded and followed by no black
        bbox = []
        bbox.append(max(0,vbox.bbox[0]))
        bbox.append(max(0,vbox.bbox[1]))
        bbox.append(min(image.size[0]-1,vbox.bbox[2]))
        bbox.append(min(image.size[1]-1,vbox.bbox[3]))
        c = image.crop(bbox)
        #c.save("/tmp/pbox%d.jpg" % (index,))
        skip = 0
        lasty = 0
        darkcount_range = 15
        darkcount_threshold = 8
        lightcount_range = 15
        lightcount_threshold = 10
        for y in range(2,c.size[1]):
            if skip>0: 
                skip = skip-1
                continue
            darkcount = 0
            for n in range(1,darkcount_range):
                p1 = c.getpixel((n*dpi/60,y))
                p2 = c.getpixel((n*dpi/60,y-1))
                p3 = c.getpixel((n*dpi/60,y-2))
                if p1[0]<ldt or p2[0]<ldt or p3[0]<ldt: 
                    darkcount = darkcount + 1

            # A sequence of dark pixels along left edge suggest a horiz line
            # horiz line must be confirmed by following across and/or
            # finding white immed above. We also treat the very bottom
            # of the column box as a horizontal line, even if no line is found.c

            # When we confirm a horiz line, we skip next dpi/16.
            # Unfortunately, the numbers need to be tunable.
            if (darkcount > darkcount_threshold) or (y==(c.size[1]-1)):
                if ((y==(c.size[1]-1)) or confirm_continuing_dark_at(c,y) ):
                    #print index,vbox.bbox,"bbox y",y,"page y",y+vbox.bbox[1]
                    smallboxlist.append((vbox.bbox[0],lasty+vbox.bbox[1],
                                     vbox.bbox[2],y+vbox.bbox[1]))
                    skip = dpi/16
                    lasty = y
                    
    return smallboxlist



def get_tangent(image,dpi):
    print "Get tangent new_ballot"
    pdb.set_trace()
    # scan only the first two inches looking for vertical lines
    y, active_tlist,inactive_tlist = find_intensity_boundaries(
        image, 
        10, # wide for simple rotation check
        dpi*2, 
        25,
        max_width=dpi*2)
    tangents = []
    for line in inactive_tlist:
        tangents.append((line.endx-line.startx)/float(line.endy-line.starty))
    tangents.sort()
    #print "Tangents of lines > 2 dpi",tangents
    try:
        median_tangent = tangents[len(tangents)/2]
    except Exception, e:
        print e
        for line in inactive_tlist:
            tangents.append((line.endx-line.startx)/float(line.endy-line.starty))
        tangents.sort()
        #print "Tangents of all lines",tangents
        median_tangent = tangents[len(tangents)/2]
    return median_tangent

def boxes_from_lines(v_endpoints,dpi=300):
    quarter_inch = dpi/4
    pboxlist = []
    # if the outer endpoints are higher than the inner,
    # and the inner are a consistent height,
    # create a box spanning the image from the outer endpoint height
    # to the inner endpoint height, and set the remaining outer tops
    # to the inner height
    if abs(v_endpoints[0][1]-v_endpoints[-1][1]) < quarter_inch:
        if v_endpoints[1][1] > (v_endpoints[0][1]+(dpi/2)):
            pbox = PotentialBox(
                (v_endpoints[0][0],v_endpoints[0][1],
                 v_endpoints[0][0],v_endpoints[1][1]),
                (v_endpoints[-1][0],v_endpoints[0][1],
                 v_endpoints[-1][0],v_endpoints[1][1]))
            pboxlist.append(pbox)
            v_endpoints[0][1]=v_endpoints[1][1]
            v_endpoints[-1][1]=v_endpoints[1][1]
    for i1,l1 in enumerate(v_endpoints):
        for l2 in v_endpoints[i1+1:]:
            if abs(l1[1]-l2[1]) < quarter_inch:
                #tops are at same level; connect
                pbox = PotentialBox(l1,l2)
            else:
                # tops are at different level,
                # connect line with lower top to other line at lower top
                upper_top = min(l1[1],l2[1])
                lower_top = max(l1[1],l2[1])
                pbox = PotentialBox([l1[0],lower_top,l1[2],l1[3]],
                                    [l2[0],lower_top,l2[2],l2[3]]
                                    )
                #print pbox
                pboxlist.append(pbox)
                # and build a box from upper top to lower top
                pbox = PotentialBox([l1[0],upper_top,l1[2],lower_top],
                                    [l2[0],upper_top,l2[2],lower_top]
                                    )
            #print pbox
            pboxlist.append(pbox)
    return pboxlist

def find_contest_boxes(image, 
                       skip_between_lines, 
                       min_extent, 
                       min_line_break_length,
                       required_intensity_drop=50, 
                       search_forwards=True,
                       dpi=300):
    v_endpoints = []
    h_endpoints = []
    tenth = dpi/10

    try:
        median_tangent = get_tangent(image,dpi=dpi)
    except IndexError:
        print "Side may not have any line from which to calc tangent."
        median_tangent = 0
        pdb.set_trace()
        return [],image
    image = image.rotate(-median_tangent*360./6.28)
    #print "Rotated %f degrees." % (-median_tangent*360./6.28)
    #image.save("/tmp/rot.jpg")

    # pre-scan for long strips of black in center, 
    # then do detail check on those strips; allow only one check per 1/16"
    start_y = (1*image.size[1])/5
    end_y = (2*image.size[1])/5
    #start_y = (2*image.size[1])/5
    #end_y = (3*image.size[1])/5
    tlist_to_merge = []
    skip = 0
    for x in range(image.size[0]-1):
        if skip>0: 
            skip = skip -1
            continue
        strip_bbox = (x,start_y,x+1,end_y)
        strip = image.crop(strip_bbox)
        strip_stat = ImageStat.Stat(strip)
        if strip_stat.mean[0]<128:
            l2r = []
            y, active_tlist,inactive_tlist = find_intensity_boundaries(
                image,
                5, # narrow for line search
                dpi/2,
                25,
                starting_x = x - 10,
                max_width = 20
                )
            skip = (dpi/16)
            tlist_to_merge.extend(inactive_tlist)
            tlist_to_merge.extend(active_tlist)
            y, active_tlist,inactive_tlist = find_intensity_boundaries(
                image, 
                5, # narrow for line search
                dpi/2,
                25,
                starting_x = x-10,
                search_forwards=False,
                max_width = 20)

    # reject any lines within 1/6" of edge
    sixth = dpi/6
    #print tlist_to_merge
    #print len(tlist_to_merge)
    #pdb.set_trace()
    tlist_to_merge = [x for x in tlist_to_merge 
             if ((x.startx > sixth) and (x.startx < image.size[0]-sixth))]

    #print tlist_to_merge
    #print len(tlist_to_merge)
    #pdb.set_trace()
    #print "Merging %d line fragments." % (len(tlist_to_merge),)
    v_endpoints = merge_transition_list(tlist_to_merge)
    # lines must be at least dpi tall to count
    v_endpoints = [x for x in v_endpoints if x[1] < (x[3]-dpi)]
    

    # build columns and blocks from the vertical lines, analyze each for horiz
    pboxlist = boxes_from_lines(v_endpoints,dpi)
    vboxlist = []

    # remove any boxes less than an inch wide
    for pbox in pboxlist:
        if abs(pbox.bbox[2]-pbox.bbox[0]) >= dpi:
            vboxlist.append(pbox)
    pboxlist = vboxlist
    vboxlist = []

    # remove any boxes less than a sixth inch tall
    for pbox in pboxlist:
        if abs(pbox.bbox[3]-pbox.bbox[1]) >= (dpi/6):
            vboxlist.append(pbox)
    pboxlist = vboxlist
    vboxlist = []


    # remove any boxes that have a vline partly or fully spanning them, 
    # more than 1" from the vertical edges 
    for pbox in pboxlist:
        disqualify = False
        for l in v_endpoints:
            #if the line's x is away from the boxes vertical edges by an inch
            if ( l[0] > (pbox.bbox[0]+dpi) and l[0] < (pbox.bbox[2]-dpi)
                 # and either
                 # the line's top y is above (<) box bottom less dpi/4
                 and ( l[1] < (pbox.bbox[3] - (dpi/4))
                       # or the line's bot y is below (>) box top plus dpi
                       or l[3] > (pbox.bbox[1] + (dpi/4)) ) ):
                #remove from boxlist
                disqualify = True
                break
        if not disqualify:
            vboxlist.append(pbox)

    #print "Column boxes:"
    #for index,vbox in enumerate(vboxlist):
    #    print index,vbox

    smallboxlist = find_contests(image,vboxlist,dpi=dpi)
    # return boxes as editable lists, not non-editable tuples
    # and extend box bottom by 1/32"
    return [[x[0],x[1],x[2],x[3]+(dpi/32)] for x in smallboxlist],image

def find_tint(image,channel_darkness_threshold=128, tint_threshold=56):
    """return location of darkened pixels with tint"""
    counter = 0
    row = 0
    col = 0
    tinted_pix=[]
    for p in image.getdata():
        col = counter % image.size[0]
        row = counter/image.size[0]
        if (p[0]<channel_darkness_threshold
            or p[1]<channel_darkness_threshold 
            or p[2]<channel_darkness_threshold):
            if (abs(p[0]-p[1])>tint_threshold 
                or abs(p[0]-p[2])>tint_threshold 
                or abs(p[1]-p[2])>tint_threshold):
                tinted_pix.append((col,row))
        counter = counter + 1
    tinted_pix.sort()
    return tinted_pix

def guess_ballot_from_dashes(image,dpi=300):
    """find dashes along side and guess vendor from light/dark ratio"""
    # take center fifth to avoid being tripped up by hart barcode
    probable_vendor = "Unknown or Hart"
    for stripe_x in (int(.2*dpi),int(.3*dpi),int(.4*dpi)):
        #print "In from edge by ",stripe_x
        edge_image1 = image.crop((
            stripe_x,
            0,
            stripe_x+1,
            3*image.size[1]/5))
        edge_image2 = image.crop((
            image.size[0]-stripe_x-1,
            0,
            image.size[0]-stripe_x,
             3*image.size[1]/5))
        light_dark = []
        in_light = True
        zone_length = 0
        for edge in (edge_image1,edge_image2):
            for y in range(edge.size[1]-2):
                pix = edge.getpixel((0,y))
                if (pix[0]+pix[1]+pix[2])>(192*3):
                    light = True
                else:
                    light = False
                if in_light:
                    if light: zone_length = zone_length+1
                    else: 
                        light_dark.append(zone_length)
                        zone_length = 0
                        in_light = False
                else:
                    if not light: zone_length = zone_length+1
                    else: 
                        light_dark.append(zone_length)
                        zone_length = 0
                        in_light = True
            dashes = 0
            #print light_dark
            for index in range(len(light_dark)-3):
                if abs(light_dark[index]-light_dark[index+2])<light_dark[index]/4:
                    dashes = dashes + 1
                    if 0==(dashes % 6):
                        larger = max(light_dark[index],light_dark[index+1])
                        smaller = min(light_dark[index],light_dark[index+1])
                        combined = light_dark[index]+light_dark[index+1]
                        ratio = 0
                        try:
                            ratio = smaller/float(larger)
                        except:
                            pass
                        if abs(ratio - 1)<.1 and abs(combined-dpi/3)<5:
                            probable_vendor = "ESS"
                            return probable_vendor
                            break
                        if (ratio < .5 
                            and ratio  > .2 
                            and abs(combined - (dpi/4))<5):
                            probable_vendor = "Diebold"
                            return probable_vendor
                            break

    return probable_vendor

def find_xxy_of_contig_tinted_pixel_zone(tinted_pixels,
                                              required_contig = 8, 
                                         dpi = 300):
    """given set of tinted pixels, look for contig zones, ret first x,y"""
    # group into rows, 
    # require pixels to be clustered in required_contig contiguous rows 
    # in order for pixels to be used to determine minx, miny
    tp_dict = {}
    minx, miny = 100000,100000
    maxx = 0
    for tp in tinted_pixels:
        if tp[1] in tp_dict:
            tp_dict[tp[1]].append(tp)
        else:
            tp_dict[tp[1]]=[tp]
    tp_keys = tp_dict.keys()
    tp_keys.sort()
    last_key = 0
    contig_keys = 0
    tps_in_contig_rows = []
    tinted_rows = []
    miny = 100000
    for key in tp_keys:
        if (key - last_key) == 1:
            contig_keys = contig_keys + 1
        else:
            contig_keys = 0
        if contig_keys >= required_contig:
            #print "Tinted pixels in rows %d to %d" % (
            #    last_key-contig_keys,
            #    last_key
            #    )
            tinted_rows.append((last_key-contig_keys,last_key))
            for x in range(contig_keys-3):
                try:
                    tps_in_contig_row = tp_dict[last_key-x]
                except KeyError,e:
                    print e
                    print "Last key",last_key
                    print "Contig keys",contig_keys
                    print "Required contig",required_contig
                    print "x",x
                    print "last key - x",last_key - x
                    pdb.set_trace()
                    tps_in_contig_row = []
                tps_in_contig_row.sort()
                # use only rows with at least three tinted entries
                if len(tps_in_contig_row)>=3:
                    minx = min(minx,tps_in_contig_row[0][0])
                    maxx = max(maxx,tps_in_contig_row[-1][0])
                    if maxx<10:
                        print "Key",key,
                        print "Last key",last_key,
                        print "x",x,
                        print "Length of tp row",len(tps_in_contig_row),
                        print "First entry",tps_in_contig_row[0],
                        print "Last entry",tps_in_contig_row[-1]

            #print "...have min,max x of (%d,%d)" % (minx,maxx)
            miny = min(miny,(last_key - contig_keys))
        last_key = key
    # strip tinted_rows of all but the last (largest) item beginning at each y
    if len(tinted_rows)>0:
        tmp_dict = {}
        for tinted_row in tinted_rows:
            tmp_dict[tinted_row[0]]=tinted_row[1]
        keys = tmp_dict.keys()
        keys.sort()
        tinted_rows = []
        for key in keys:
            tinted_rows.append((key,tmp_dict[key]))
    return minx,maxx,miny,tinted_rows

def merge_artifacts(contestboxlist,dpi):
    contestboxlist.sort(key = lambda x: x[1])
    rev_vid_or_gray = [x for x in contestboxlist if abs(x[3]-x[1]) <= (dpi/8)]
    contestboxlist = [x for x in contestboxlist if abs(x[3]-x[1]) > (dpi/8)]

    merged_list = []
    for index in range(len(rev_vid_or_gray)-2):
        if index in merged_list: 
            continue
        for index2 in range(index+1,len(rev_vid_or_gray)-1):
            if index2 in merged_list: 
                continue
            if ( (rev_vid_or_gray[index2][1] 
                  - rev_vid_or_gray[index2-1][1]) <= (dpi/8) ):
                #print "Merge",rev_vid_or_gray[index],"with",rev_vid_or_gray[index2]
                rev_vid_or_gray[index][3] = max(rev_vid_or_gray[index2][3],
                                                rev_vid_or_gray[index][1]+1)
                merged_list.append(index2)
            else:
                break

    merged_rev_vid_or_gray = []
    for index in range(len(rev_vid_or_gray)-1):
        if not index in merged_list:
            merged_rev_vid_or_gray.append(rev_vid_or_gray[index])

    contestboxlist.extend(merged_rev_vid_or_gray)
    return contestboxlist

def trim_top_of_image(contest_bbox,main_image,contest_image,dpi,darkness_threshold):
    remove_count = 0
    for y in range(dpi/16):
        # get top of region line by line,
        # adding lines to removal range until all white
        remove_crop = contest_image.crop(
            (dpi/4,y,contest_image.size[0]-(dpi/4),y+1)
            )
        stat = ImageStat.Stat(remove_crop)
        mean = stat.mean
        if (mean[0]+mean[1]+mean[2]) < (darkness_threshold*3):
            remove_count = remove_count + 1

    contest_bbox[1] = contest_bbox[1]+remove_count
    contest_image = main_image.crop(contest_bbox)
    return contest_bbox,contest_image

def capture_text(image,surround_bbox,text_bbox,dpi=300):
    single_line_crop = image.crop(text_bbox)
    single_line_text = tesseract_and_clean(single_line_crop)
    #draw.text((surround_bbox[0]+text_bbox[0],
    #           surround_bbox[1]+text_bbox[1]+(dpi/10)),
    #          single_line_text,
    #          fill=(0,0,255))
    return single_line_text

def cleanup_bbox(contest_bbox,image):
    """ensure bbox works for image"""
    if contest_bbox[2]<=contest_bbox[0]:
        contest_bbox[2],contest_bbox[0] = contest_bbox[0],contest_bbox[2] 
    if contest_bbox[3]<=contest_bbox[1]:
        contest_bbox[3],contest_bbox[1] = contest_bbox[1],contest_bbox[3] 
    if contest_bbox[0]<0:
        contest_bbox[0] = 0
    if contest_bbox[1]<0:
        contest_bbox[1] = 0
    if contest_bbox[2]>=image.size[0]:
        contest_bbox[2] = image.size[0]-1
    if contest_bbox[3]>=image.size[1]:
        contest_bbox[3] = image.size[1]-1
    return contest_bbox

def get_targets_wide_bounded(contest_image,dpi):
    maxx = 0
    minx = contest_image.size[0]
    miny = contest_image.size[1]
    bloblist = blobs.big_blobs(contest_image,
                               dpi=dpi,
                               dark_threshold=192,
                               min_width_divisor = 6,
                               max_width_divisor = 2,
                               min_age_divisor = 16,
                               max_age_divisor = 7)
    #print "Length bloblist",len(bloblist)
    skipped = 0
    """
    for index,b in enumerate(bloblist):
        if b.end_x > (dpi/2):
            skipped = skipped + 1
            if skipped > (dpi/15):
                break
        else:
            maxx = max(b.end_x,maxx)
            minx = min(b.start_x,minx)
            miny = min(b.row-b.age,miny)
        if skipped > 0:
                print "SKIPPING Blob(s) ending more than 1/2 inch into box"
    """
    for index,b in enumerate(bloblist):
            maxx = max(b.end_x,maxx)
            minx = min(b.start_x,minx)
            miny = min(b.row-b.age,miny)

    return maxx,minx,miny,bloblist

def get_targets_tinted(contest_image,dpi):
    maxx = 0
    minx = contest_image.size[0]
    miny = contest_image.size[1]
    tintimage = contest_image.crop((0,
                                    0,
                                    contest_image.size[0]-(dpi/8),
                                    contest_image.size[1]-1))

    #tintimage.save("/tmp/tintimage.jpg")
    tinted_pixels = find_tint(tintimage)
    #pdb.set_trace()
    (minx,maxx,miny,tinted_rows) = find_xxy_of_contig_tinted_pixel_zone(
        tinted_pixels,
        required_contig = dpi/10
        )
        # for Diebold, ensure min_x is at least 1/16" from edge
    if minx < (dpi/16): minx = dpi/16
    print minx,maxx,miny,tinted_rows
    
    return maxx,minx,miny, tinted_rows



def process_box(contest_bbox,dpi,image,use_wide_bounded_test,use_tint_test):
    """ deal with one box"""
    contest_image = image.crop(contest_bbox)
    contest_bbox,contest_image = trim_top_of_image(contest_bbox,
                                                   image,
                                                   contest_image,
                                                   darkness_threshold=208,
                                                   dpi=dpi)
    try:
        if contest_bbox[3]<=contest_bbox[1]:
            contest_bbox[1],contest_bbox[3]=contest_bbox[3],contest_bbox[1]
    except SystemError,e:
        print e
        print contest_bbox
        

    maxx=0
    minx = contest_image.size[0]
    miny=contest_image.size[1]

    # find white zones between text lines
    white_lines = find_white_in(contest_image,
                                dpi/4,
                                contest_image.size[0]-(dpi/4),
                                dpi)

    # find targets by applying test appropriate to vendor type
    # BOUNDED
    if use_wide_bounded_test:
        maxx,minx,miny,bloblist = get_targets_wide_bounded(contest_image,dpi)
    if use_tint_test:
        #maxx,minx,miny,bloblist = get_targets_wide_bounded(contest_image,dpi)
        maxx,minx,miny,tinted_rows = get_targets_tinted(contest_image,dpi)
        #contest_image.save("/tmp/contest.jpg")
        #pdb.set_trace()
        bloblist = []
        print "Not yet searching beneath initial vote row."
        if (maxx - minx) < dpi:
            bloblist.append(blobs.Zone(minx,maxx,miny))
        else:
            bloblist.append(blobs.Zone(minx,minx+(dpi/4),miny))
            bloblist.append(blobs.Zone(maxx-(dpi/4),maxx,miny))
            
    # backup above the start of the first target by 1/8"
    vote_desc_x = maxx 
    vote_desc_y = miny - (dpi/8)

    # protect against impossible vote description offset
    # and if vote regions are not in left third of box, 
    # begin vote region at left so we pick up all vote text
    if(vote_desc_x > (contest_image.size[0]/3)):
        vote_desc_x = 0
    if(vote_desc_y > (contest_image.size[1]-10)):
        vote_desc_y = (contest_image.size[1]-10)
    if vote_desc_y < (1+(dpi/16)):
        vote_desc_y = 1+(dpi/16)

    # divide contest_box into vote and nonvote (header) parts
    nonvote_region = [0,
                      0, 
                      contest_image.size[0]-1,
                      vote_desc_y]
    vote_region = [vote_desc_x, 
                   vote_desc_y,
                   contest_image.size[0]-1, 
                   contest_image.size[1]-1]

    print "Bloblist",bloblist
    print "Vote desc",vote_desc_x,vote_desc_y

    white_lines_header = [x for x in white_lines if x[0]< vote_desc_y]
    white_lines_votes = [x for x in white_lines if x[1]>= vote_desc_y]
    print "White lines header",white_lines_header
    print "White lines votes",white_lines_votes

    # capture line by line text of nonvote region and create ContestBox
    contest_text = ""
    if len(white_lines_header)>1:
        for index in range(len(white_lines_header)-1):
            text_bbox = (0,
                         white_lines_header[index][1],
                         contest_image.size[0]-1,
                         white_lines_header[index+1][0])
            text = capture_text(contest_image,
                                         contest_bbox,
                                         text_bbox,dpi=dpi)
            contest_text = "%s\n%s" % (contest_text,text)

    contest_box = ContestBox(contest_bbox[0],
                             contest_bbox[1],
                             contest_bbox[2],
                             contest_bbox[3],
                             contest_text)
    this_contest = Ballot.Contest(
            contest_bbox[0],contest_bbox[1],
            contest_bbox[2],contest_bbox[3],
            0,
            contest_text,
            max_votes=2)


    # targets are in wide_zones or tinted zones or bloblist,
    # depending on the search that was run; text should be
    # associated with the nearest target
    #vote_text = tesseract_and_clean(vote_crop)
    #for choice in appropriate_zone:
    #    contest_box.choices.append(TargetAndText())
    all_text = ""
    linecount = 0

    for index in range(len(white_lines_votes)-1):
        text_bbox = (vote_desc_x,
                     white_lines_votes[index][1],
                     contest_image.size[0]-1,
                     white_lines_votes[index+1][0])
        if bloblist is not None:
            starting_y_for_maincontest = None
            for b in bloblist:
                start_row = b.row - b.age
                if ((abs(start_row-white_lines_votes[index][1])<(dpi/8)) 
                    and (b.start_x < (dpi/2))):
                    # minx and maxx are set to the same values 
                    # for every entry in contest
                    starting_y_for_maincontest = start_row+contest_bbox[1]
                    break
        elif tinted_rows is not None:
            for tr in tinted_rows:
                if (abs(tr[0]-white_lines_votes[index][1])<(dpi/8)):
                    # minx and maxx are set to the same values 
                    # for every entry in contest
                    starting_y_for_maincontest = tr[0]+contest_bbox[1]
                    break

        choice_text = capture_text(contest_image,
                              contest_bbox,
                              text_bbox,dpi=dpi)

        if starting_y_for_maincontest is not None:
            this_contest.choices.append(
                Ballot.Choice(
                    minx+contest_bbox[0],
                    starting_y_for_maincontest,
                    choice_text)
                )
            #print this_contest.description[:30],
            #print this_contest.choices[-1].x,
            #print this_contest.choices[-1].y,
            #print this_contest.choices[-1].description
    # if a region of interest 
    # extends past the last white zone's end,
    # capture from start of region of interest to end of contest crop
    if use_tint_test and len(tinted_rows)>0 and len(white_lines)>0:
        if tinted_rows[-1][1]>white_lines[-1][1]:
            text_bbox = (vote_desc_x,
                         tinted_rows[-1][0],
                         contest_image.size[0]-1,
                         contest_image.size[1]-1)
            capture_text(contest_image,
                                  contest_bbox,
                                  text_bbox,dpi=dpi)
    return this_contest

class GenerateTemplate(object):

    def print_contests(self):
        for contest in self.maincontestlist:
            print "CONTEST (%d,%d) to (%d,%d) %s" % (contest.x,contest.y,
                                             contest.x2,contest.y2,
                                             contest.description)
            for choice in contest.choices:
                print "  CHOICE %d,%d,%s" % (choice.x,choice.y,choice.description)

    def draw_contests(self,filename):
        """ draw bounding boxes and text into image saved to filename"""
        draw_image = Image.new(self.image.mode,
                                    self.image.size,
                                    (255,255,255))
        draw = ImageDraw.Draw(draw_image)
        for contest in self.maincontestlist:
            draw.rectangle((contest.x,contest.y,contest.x2,contest.y2),
                           outline=(0,0,255)
                           )
            draw.text((contest.x,contest.y),
                      contest.description,
                      fill = (0,0,0))
            for choice in contest.choices:
                draw.rectangle((choice.x,choice.y,choice.x+50,choice.y+50),
                           outline=(0,0,255)
                           )
                draw.text((choice.x+100,choice.y),
                          choice.description,
                          fill = (255,0,0))
        draw_image.save(filename)

    def __init__(self,dpi,filename,darkness_threshold=208):
        self.dpi = dpi
        self.filename = filename
        self.darkness_threshold = darkness_threshold
        self.use_tint_test = False
        self.use_wide_bounded_test = False
        self.bloblist = None
        self.tinted_rows = None
        self.image = Image.open(self.filename).convert("RGB")
        # first check for vendor
        self.probable_vendor = guess_ballot_from_dashes(self.image)
        print "Determined probable vendor", self.probable_vendor
        if self.probable_vendor.find("Diebold")>-1:
            # use tints to find vote ops
            #self.use_tint_test = True
            self.use_wide_bounded_test = True
        else:
            self.use_wide_bounded_test = True
        # split into boxes
        self.contestboxlist,self.image = find_contest_boxes(
            self.image,
            self.dpi/30,
            self.dpi/6,
            self.dpi,50,
            True,
            dpi=self.dpi)
        # Merge grey zone artifact boxes into larger boxes 
        # and append merged to our main boxlist.
        self.contestboxlist = merge_artifacts(self.contestboxlist,self.dpi)
        print "Have contest box list."

        self.maincontestlist = []
        for contest_bbox in self.contestboxlist:
            contest_bbox = cleanup_bbox(contest_bbox,self.image)
            this_contest = process_box(contest_bbox,
                                       self.dpi,
                                       self.image,
                                       self.use_wide_bounded_test,
                                       self.use_tint_test
                                       )
            self.maincontestlist.append(this_contest)



if __name__ == "__main__":
    """ main """
    if len(sys.argv)<3:
        print "usage: python new_ballot.py dpi file"
    dpi = int(sys.argv[1])
    filename = sys.argv[2]
    app = GenerateTemplate(dpi,filename,200)

    # for each contest box, trim up to 1/16" off top,
    # find contest header text, vote area, vote targets, and vote text
    #app.print_contests()
    app.draw_contests("/tmp/%dp_%s" % (dpi,os.path.basename(filename)))

    template = Ballot.Template(dpi,1,2,0,"17",app.maincontestlist)
    xml = Ballot.Template_to_XML(template)
    outfile = open("/tmp/t%d_%s.txt" % (dpi,os.path.basename(filename)),"w")
    outfile.write(xml)
    outfile.close()

    sys.exit(0)
