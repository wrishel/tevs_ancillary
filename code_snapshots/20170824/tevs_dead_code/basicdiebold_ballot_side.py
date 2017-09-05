# basic_ballot_side.py
# Part of TEVS
# This file, with basic_ballot.py, demos the minimum functions
# to implement a new vendor ballot style.  It uses hart functions.

from BallotSide import BallotSide, Point, Landmarks, LandmarkException
#from BallotTemplate import BallotTemplate
from TemplateBuilder import TemplateBuilder, tenthfont
from line_util import *
from diebold_code import diebold_tm
from diebold_dashes import get_dash
from ocr import tesseract
import pdb
import xmlrpclib
# Note: WE HAVE DISABLED CHECK FOR HORIZONTAL

class BasicdieboldBallotSide(BallotSide):
    def __init__(self,ballot=None,dpi=None,image_filename=None,number=None):
        super(BasicdieboldBallotSide, self).__init__(
            ballot=ballot,
            dpi=dpi,
            image_filename = image_filename, 
            number = number)
        self.left_tm_list = None
        self.right_tm_list = None
        self.lrx, self.lry = 0,0
        self.llx, self.lly = 0,0

    def is_front(self):
        """ return True if this side's image represents a front """
        print "is_front now returning hard-coded true"
        return True

    def full_image_get_landmarks(self,landmarks_required=False):
        """ return list of landmark coordinates 

        By the time get_landmarks is called, BallotSide will have
        created and stored four cropped images in the instance,
        (u/l)(l/r)c_landmark_zone_image.  The job here is to 
        search these images for the suitable landmark and fill in
        the appropriate point.

        Landmarks will be adjusted by the BallotSide class
        to reflect the information generated here combined
        with the offsets of the landmark zone's bounding boxes;
        that adjustment should not be made here.
        """
        # we pass the four provided images to the diebold function below...
        # which must be changed to take four corner images and return
        # four coordinate pairs
        l,r = diebold_tm(self.image,self.dpi)
        self.left_tm_list = l
        self.right_tm_list = r
        ulx,uly = get_dash(self.image,self.dpi,left=True,top=True)
        urx,ury = get_dash(self.image,self.dpi,left=False,top=True)
        lrx,lry = get_dash(self.image,self.dpi,left=False,top=False)
        llx,lly = get_dash(self.image,self.dpi,left=True,top=False)
        self.llx = llx
        self.lly = lly
        self.lrx = lrx
        self.lry = lry
        lm = Landmarks(Point(ulx,uly),Point(urx,ury),
                       Point(lrx,lry),Point(llx,lly))
        """
        lm = Landmarks(Point(l[0][0],l[0][1]),
                       Point(r[0][0],r[0][1]),
                       Point(r[-1][0],r[-1][1]),
                       Point(l[-1][0],l[-1][1])
            )
        
        lm = self.find_landmarks(self.ulc_landmark_zone_image,
                                 self.urc_landmark_zone_image,
                                 self.lrc_landmark_zone_image,
                                 self.llc_landmark_zone_image)
        """
        # ...which returns us the corners within the four images,
        # which we, in turn, pass back to BallotSide.
        # BallotSide is responsible for putting our returned
        # coordinates in the appropriate coordinate frame
        return lm 

    def diebold_code(self):
        # interpolate the lower left,lower right landmarks
        width = self.lrx - self.llx
        delta_y = self.lry - self.lly
        code = 0
        for n in range(34):
            test_x = self.llx + ((width*n)/33) + self.dpi/16
            test_y = self.lly + ((delta_y*n)/33) + self.dpi/32
            p_int = 0
            try:
                if test_x < 0 or test_x > self.image.size[0]-1:
                    p_int = 0
                else:
                    p = self.image.getpixel((test_x,test_y))
                    try:
                        p_int = (p[0]+p[1]+p[2])/3
                    except IndexError, e:
                        p_int = p
            except Exception, e:
                print e,type(e)
            if p_int < 128:
                code += 1
            code = code << 1
        return code

    def get_layout_id(self):
        """ Analyze appropriate part of side and report a layout id code.

        Once landmarks have been determined, a vendor appropriate area
        is searched for information from which a layout id can be generated.
        The way in which this area is located is also vendor specific.
        """
        # we call the diebold function below...
        barcode = self.diebold_code()
        # and pass its returned string back up to BallotSide
        self.logger.info("Barcode as hex: %x as decimal: %d" % (barcode,barcode))
        printcode = barcode
        printstr = ""
        for p in range(34):
            if printcode % 2:
                printstr = "X%s" % (printstr,)
            else:
                printstr = "_%s" % (printstr,)
            printcode = printcode / 2
        self.logger.info("Barcode visually: %s" % (printstr,))
        return barcode


    def validate_layout_id(self,lid):
        """ return True if layout id is valid or believable """
        print "In validate layout id with lid %s, returning True" % (lid,)
        return True


    def check_for_target_in_region(self,region,threshold=232,minimum_tint=20):
        "Test to see if the region has a filled/unfilled vote target"
        # vote target requirement: line of darkish or tinted pixels 1/10" wide
        # allowing for allowed miss 
        # with similar line approximately 1/8" below
        intest = False
        if region[0] < (const.dpi/4): return None
        if region[2] > (self.image.size[0] - (const.dpi/4)): return None
        doublelines = []
        darklines = []
        pixtint = 0

        # we only need to scan the top half of the region, 
        # because if we haven't found a good line by then, 
        # we won't have room for a full target in the region
        for y in range(max(0,region[1]),region[3]+((region[3]-region[1])/2)):
            indark = False
            lendark = 0
            lengap = 0
            allowed_gap = 1
            # if we are getting a color image, test for tint here as well!!!
            # mjt 5/16/12
            for x in range(max(0,region[0]),min(self.image.size[0]-1,region[2])):
                try:
                    pix1 = self.image.getpixel((x,y))
                    pix1int = (pix1[0]+pix1[1]+pix1[2])/3
                    pix1tint = abs(pix1[0]-pix1[1])
                    pix1tint = max(abs(pix1[0]-pix1[2]),pix1tint)
                    pix1tint = max(abs(pix1[1]-pix1[2]),pix1tint)
                    pix2 = self.image.getpixel((x,y+1))
                    pix2int = (pix2[0]+pix2[1]+pix2[2])/3
                    pix2tint = abs(pix2[0]-pix2[1])
                    pix2tint = max(abs(pix2[0]-pix2[2]),pix2tint)
                    pix2tint = max(abs(pix2[1]-pix2[2]),pix2tint)
                    pixint = min(pix1int,pix2int)
                    pixtint = max(pix1tint,pix2tint)
                except IndexError as e:
                    print e,type(e)
                except TypeError as e:
                    print e,type(e)
                except:
                    pixint = min(pix1[0],pix2[0])
                # try using tint instead of darkness mjt 5/16/12 !!!
                #if pixint < threshold:
                if pixtint > minimum_tint:
                    if not indark:
                        indark = True
                        lendark = 1
                        lengap = 0
                    else:
                        lendark += 1
                        if lendark > (const.dpi/10):
                            darklines.append((x,y))
                            lendark = 0
                            indark = False
                            break
                if pixint >= threshold:
                    # too late to find a line?
                    if (x > (region[0]+((region[2]-region[0])/2)) 
                        and lendark == 0):
                        break
                    if indark:
                        lengap += 1
                        if lengap > allowed_gap:
                            indark = False
                            lendark = 0
        for n in range(len(darklines)):
            appended_n = False
            topline = darklines[n][1]
            for m in range(n+1,len(darklines)):
                if ( ((darklines[m][1] - topline) > const.dpi/9) and ((darklines[m][1] - topline) < const.dpi/8) ):
                    doublelines.append( darklines[n])
                    appended_n = True
            if appended_n:
                continue
        eliminate_duplicates_dict = {}
        for item in doublelines: eliminate_duplicates_dict[item] = 1
        doublelines = eliminate_duplicates_dict.keys()
        return doublelines

    def get_diebold_targets(self):
        "Use the diebold timing marks to get possible target locations."
        # the right timing marks are measured at their right end, we need
        # but we need to use their left end, which is 11/60 inch behind
        # divide the width into 32 zones
        self.logger.debug("Starting get_diebold_targets")
        target_list = []
        for item in zip(self.left_tm_list,self.right_tm_list):
            diffx = item[1][0] - int(const.dpi * 11/60.) - item[0][0]
            diffy = item[1][1] - item[0][1]
            stride_x = float(diffx)/33.
            interp_y = float(diffy)/33.
            for n in range(34): 
                x = item[0][0]+int(round(n*stride_x))
                y = item[1][1]+int(round(n*interp_y))
            # targets begin approximately 1/30" above timing mark 
            # are approximately 1/8" tall,
            # begin less than 1/30" before timing mark and
            # are approximately 1/5" wide
                region_to_check = (x - (const.dpi/30),
                                   y - (const.dpi/15),
                                   x + (const.dpi/5) + (const.dpi/30),
                                   y + (const.dpi/10) + (const.dpi/30))
                # does the region have two lines at least 1/10" long,
                # separated by approximately 1/8"
                target = self.check_for_target_in_region(region_to_check)
                # if you get a hit list, use the item with lowest y, 
                # but subtract for the 1/10" of dark found prior to hit
                # and the 1/20" of curve that precedes the dark
                #
                if target:
                    target_y = 9999
                    target_x = 9999
                    for t in target:
                        if t[1]<target_y: 
                            target_x = t[0]
                            target_y = t[1]

                    target_list.append(
                        (target_x - const.dpi/10 - const.dpi/20, 
                         target_y))
        return target_list

    def build_layout(self,side_number):
        """ build a layout, an array of region subclasses 

        The returned layout is stored in the instance and walked
        when the side's information is requested.  In walking
        the layout, BallotSide will call an adjustment routine
        on each coordinate in the layout to map the coordinate
        to its equivalent value in this image's coordinate frame.
        """
        self.logger.debug("In build layout, side %s" % (side_number,))
        diebold_targets = self.get_diebold_targets()
        self.logger.debug("Diebold targets %s" % (diebold_targets,))
        #print "Targets",diebold_targets
        # now, with targets, do same procedures as in regular TemplateBuilder:
        # determine enclosing box
        # determine targets sharing enclosing box
        # decide if box is likely valid
        # if box is valid, perform text extraction
        src_image = self.image.convert("L")
        # Note: WE HAVE DISABLED CHECK FOR HORIZONTAL
        tb = TemplateBuilder(src_image,
                             self.dpi,
                             self.image_filename,
                             ulc_x = self.landmarks.ulc.x,
                             ulc_y = self.landmarks.ulc.y,
                             urc_x = self.landmarks.urc.x,
                             urc_y = self.landmarks.urc.y,
                             llc_x = self.landmarks.llc.x,
                             llc_y = self.landmarks.llc.y,
                             lrc_x = self.landmarks.lrc.x,
                             lrc_y = self.landmarks.lrc.y,
                             layout_id = self.layout_id,
                             contest_gap_inches = 0.7,
                             min_target_width_inches = 0.13,
                             max_target_width_inches = 0.17,
                             target_width_inches = 0.2,
                             target_height_inches = 0.11,
                             check_for_horizontal = False,
                             min_target_set_height_inches = 0.25,
                             min_contest_height_inches = 0.6,
                             ignore_height_inches = 0.8,
                             ignore_width_inches = 0.4,
                             ignore_right_inches = 0.4,
                             diebold = True,
                             diebold_targets = diebold_targets)
        layout = tb.__repr__()                       
        return layout, tb.out_image
    # *************************************************
    # Sample routines from hart_ballot
    # *************************************************
    

    def good_barcode(self,barcode):
        """ Indicate whether a barcode conforms to our requirements."""
        if barcode=="NOGOOD":
            return False
        # if any additional requirements for valid layout id are available,
        # add them in this test
        return True

    def get_precinct_id(self):
        """ Return precinct id from class cache, or OCR it. """

        def adj(f): return int(f*self.dpi)
        apzhoi = self.landmarks.ulc.x
        apzhoi += adj(const.precinct_zone_horiz_offset_inches)
        apzvoi = self.landmarks.ulc.y
        apzvoi += adj(const.precinct_zone_vert_offset_inches)
        croplist = (
            int(apzhoi),
            int(apzvoi),
            int(apzhoi) + adj(const.precinct_zone_width_inches),
            int(apzvoi) + adj(const.precinct_zone_height_inches)
             )
        pimage = self.image.crop(croplist)
        precinct = tesseract(pimage)
        BallotSide.precinct_cache[self.layout_id] = precinct
        return precinct

    def get_party_id(self):
        """ Return party id from class cache, or OCR it. """

        def adj(f): return int(f*self.dpi)
        apzhoi = self.landmarks.ulc.x
        apzhoi += adj(const.party_zone_horiz_offset_inches)
        apzvoi = self.landmarks.ulc.y
        apzvoi += adj(const.party_zone_vert_offset_inches)
        croplist = (
            int(apzhoi),
            int(apzvoi),
            int(apzhoi) + adj(const.precinct_zone_width_inches),
            int(apzvoi) + adj(const.precinct_zone_height_inches)
             )
        pimage = self.image.crop(croplist)
        party = tesseract(pimage)
        BallotSide.party_cache[self.layout_id] = party
        return party

