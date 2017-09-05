# basic_ballot_side.py
# Part of TEVS
# This file, with basic_ballot.py, demos the minimum functions
# to implement a new vendor ballot style.  It uses hart functions.

from BallotClass import BallotException
from BallotSide import BallotSide, Point, Landmarks, LandmarkException, LayoutIdException, LayoutInvalidException
from line_util import *
from hart_barcode import hart_barcode, BarcodeException
from subprocess import call
from ocr import tesseract
import xmlrpclib
from TemplateBuilder import TemplateBuilder, tenthfont
import const
import os
import gc
#from BallotTemplate import BallotTemplate

def read_xml_file_from_tmp(layout_id):
    try:
        f = open("/tmp/%s.xml" % (layout_id),"r")
        contents = f.read()
        f.close()
    except Exception as e:
        contents = e
        print e
    gc.collect()
    return contents 

def HartBuildTemplate(src_image,
                      dpi,
                      image_filename,
                      ulc_x, ulc_y,
                      urc_x, urc_y,
                      llc_x, llc_y,
                      lrc_x, lrc_y,
                      layout_id,
                      min_target_width_inches,
                      max_target_width_inches,
                      target_width_inches,
                      target_height_inches):
    # call external C/Leptonica program, passing information to it 
    print "/home/tevs/leptonica-1.68/prog/ballot %s %d %s %d %d %d %d %d %d %d %d" % (
            image_filename,
            dpi, 
            layout_id,
            ulc_x,ulc_y,
            urc_x,urc_y,
            llc_x,llc_y,
            lrc_x,lrc_y
            )
              
    try:
        call(
            ["/home/tevs/leptonica-1.68/prog/ballot",
             image_filename,
             str(dpi), 
             layout_id,
             str(ulc_x),str(ulc_y),
             str(urc_x),str(urc_y),
             str(llc_x),str(llc_y),
             str(lrc_x),str(lrc_y)]
            )
    except Exception as e:
        print e
        #pdb.set_trace()
        
class BasichartBallotSide(BallotSide):
    def __init__(self,ballot=None,dpi=None,image_filename=None,number=None):
        super(BasichartBallotSide, self).__init__(
            ballot=ballot,
            dpi=dpi,
            image_filename = image_filename, 
            number = number)
        
    def is_front(self):
        """ return True if this side's image represents a front """
        self.logger.debug("is_front now returning hard-coded true")
        return True

    def get_landmarks(self,landmarks_required=False):
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
        # we pass the four provided images to the hart function below...
        lm = self.find_landmarks(self.ulc_landmark_zone_image,
                                 self.urc_landmark_zone_image,
                                 self.lrc_landmark_zone_image,
                                 self.llc_landmark_zone_image)
        # ...which returns us the corners within the four images,
        # which we, in turn, pass back to BallotSide.
        # BallotSide is responsible for putting our returned
        # coordinates in the appropriate coordinate frame

        return lm 

    def get_layout_id(self):
        """ Analyze appropriate part of side and report a layout id code.

        Once landmarks have been determined, a vendor appropriate area
        is searched for information from which a layout id can be generated.
        The way in which this area is located is also vendor specific.
        """
        # we call the hart function below...
        retval = self.get_layout_code()
        # and pass its returned string back up to BallotSide
        print retval
        return retval 


    def validate_layout_id(self,lid):
        """ return True if layout id is valid or believable """
        self.logger.debug("In validate layout id with lid %s, returning True" % (lid,))
        return True


    def build_layout(self,side_number):
        """ build a layout, an array of region subclasses 

        The returned layout is stored in the instance and walked
        when the side's information is requested.  In walking
        the layout, BallotSide will call an adjustment routine
        on each coordinate in the layout to map the coordinate
        to its equivalent value in this image's coordinate frame.
        """
        self.logger.debug( "In build layout for side %d" % (self.side_number,))
        """
        layout = BallotTemplate(self.dpi,
                                self.image_filename,
                                landmarks = self.landmarks,
                                layout_id = self.layout_id,
                                precinct = 'yabba',
                                vendor = 'hart',
                                flip=self.image_was_flipped)

        """
        src_image = Image.open(self.image_filename).convert("L")
        # run the Leptonica c program ballot, 
        # passing required arguments and waiting for completion 
        # upon successful completion, read that programs output  
        # from "/tmp/template.xml" 
        HartBuildTemplate(src_image,
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
                          min_target_width_inches = 0.28,
                          max_target_width_inches = 0.35,
                          target_width_inches = 0.34,
                          target_height_inches = 0.17)
        layout = read_xml_file_from_tmp(self.layout_id)
        #tb = TemplateBuilder(src_image,
        #                         self.dpi,
        #                         self.image_filename,
        #                         ulc_x = self.landmarks.ulc.x,
        #                         ulc_y = self.landmarks.ulc.y,
        #                         urc_x = self.landmarks.urc.x,
        #                         urc_y = self.landmarks.urc.y,
        #                         llc_x = self.landmarks.llc.x,
        #                         llc_y = self.landmarks.llc.y,
        #                         lrc_x = self.landmarks.lrc.x,
        #                         lrc_y = self.landmarks.lrc.y,
        #                         layout_id = self.layout_id,
        #                         min_target_width_inches = 0.28,
        #                         max_target_width_inches = 0.35,
        #                         target_width_inches = 0.34,
        #                         target_height_inches = 0.17,
        #                         check_for_horizontal = False,
        #                         min_target_set_height_inches = 0.25,
        #                         min_contest_height_inches = 0.9,
        #                         ignore_height_inches = 0.6,
        #                         ignore_width_inches = 0.5,
        #                         ignore_right_inches = 0.5,
        #                         diebold = False)
        #layout = tb.__repr__()                       
        return layout, None

    # *************************************************
    # Sample routines from hart_ballot
    # *************************************************
    
    def find_landmarks(self,uli,uri,lri,lli):
        """ retrieve landmarks for Hart images

        Landmarks for the Hart Ballot will be the ulc, urc, lrc, llc 
        (x,y) pairs marking the four corners of the main surrounding box.

        In this and other landmark search routines, we are responsible
        for determining if the ballot is upside down.  If the ballot
        is upside down, we can flip self.image, set self.image_was_flipped,
        and determine the landmarks based on the flipped image.

        Or, we can set self.image_needs_flipping, in which case 
        the superclass logic is responsible for flipping the image
        and reinvoking find_landmarks with new sub-images.

        The detection of upside down ballots should be done when
        landmarks are needed; this is the earliest point at which
        we have a chance of discovering the problem.
        """

        TOP=True
        BOT=False
        LEFT=True
        RIGHT=False
        lm = []
        try:
            hline = scan_strips_for_horiz_line_y(
                uli, 
                const.dpi, 
                int(uli.size[0] - const.dpi/2),#starting_x 
                const.dpi/4, #starting_y
                3*const.dpi/4, #height_to_scan
                TOP)
        except LineUtilException:
            raise LandmarkException("Bad landmark upper left, scan_strips ")
        x,y = follow_hline_to_corner(
            uli, 
            const.dpi, 
            int(uli.size[0]), #starting_x
            hline, #starting_y
            LEFT)
        if (x==0 and y==0):raise LandmarkException("Bad landmark upper left")
        lm.append(Point(x,y))

        hline = scan_strips_for_horiz_line_y(
            uri, 
            const.dpi, 
            const.dpi/2, #starting_x
            const.dpi/4, #starting_y 
            3*const.dpi/4, #height to search
            TOP)
        x,y = follow_hline_to_corner(
            uri, 
            const.dpi, 
            const.dpi/2, #startx
            hline, #hline
            RIGHT)
        if (x==0 and y==0):raise LandmarkException("Bad landmark")
        lm.append(Point(x,y))
                  
        # Given tentative top landmarks, we can check for barcode positions
        # by doing quick intensity checks where they belong relative to
        # normally-oriented landmarks; if they indicate we are upside-down,
        # we have to flip self.image, set the self.image_was_flipped flag,
        # and recalc the landmarks to return them for the flipped image.
        
        # A rightside up ballot will have no barcode 0.25" to the right of the 
        # second landmark; an upside down ballot will have barcode at that
        # location.
        darkpixcount = 0
        for test_y in range(y,y+const.dpi/4):
            if uri.getpixel((x+const.dpi/4,test_y))[0] < 128:
                darkpixcount += 1
        if darkpixcount > 5:
            self.image_needs_flipping = True
            return None

        hline=scan_strips_for_horiz_line_y(
            lri, 
            const.dpi, 
            const.dpi/2, 
            const.dpi/4, 
            7*const.dpi/8, # mjt 7/1/12 was just missing on some 
            BOT)
        x,y = follow_hline_to_corner(
            lri, 
            const.dpi, 
            const.dpi/2,
            hline, 
            RIGHT)
        if (x==0 and y==0):raise LandmarkException("Bad landmark")
        lm.append( Point(x,y) )
        hline=scan_strips_for_horiz_line_y(
            lli, 
            const.dpi,
            int(uli.size[0]-const.dpi/2), 
            const.dpi/4, 
            7*const.dpi/8, # mjt 7/1/12 was just missing on some 
            BOT)
        x,y = follow_hline_to_corner(
            lli, 
            const.dpi, 
            int(uli.size[0]-const.dpi/2),
            hline, LEFT)
        if (x==0 and y==0):raise LandmarkException("Bad landmark")
        lm.append(Point(x,y))
            
        
        # dont generate landmarks, return this array
        return lm
        #landmarks = Landmarks(lm[0],lm[1],lm[2],lm[3])
        #return landmarks

    def good_barcode(self,barcode):
        """ Indicate whether a barcode conforms to our requirements."""
        if barcode=="NOGOOD":
            return False
        #pdb.set_trace()
        if not barcode.startswith("100"):
            return False
        # if any additional requirements for valid layout id are available,
        # add them in this test, this test should be bundled into a separately
        # modifiable file !!!
        if not (int(barcode[4:7])<140):
            self.logger.debug("Precinct number %s not less than 140.\n" % (
                    barcode[4:6],))
            return False
        if not (barcode[8]=='1' or barcode[8]=='2'):
            self.logger.debug("Ninth digit in %s is not 1 or 2." % (barcode,))
            return False
        if (len(barcode)<>14):
            self.logger.debug("%s is not 14 chars." % (barcode))
            return False
        return True

    def get_precinct_id(self):
        """ Return precinct id from class cache, or OCR it. """
        """this must be changed to use the precinct 
        as defined in the template, which will have been retrieved
        by the time this is called."""
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

    def get_layout_code(self):
        """ Determine the layout code(s) from the ulc barcode(s) """
        # barcode zones to search are from 1/3" to 1/6" to left of ulc
        # and from 1/8" above ulc down to 2 5/8" below ulc.
        def adj(f): return f*self.dpi

        sixteenth_inch, eighth_inch = adj(.0625), adj(.125)
        point3inch = adj(0.3) 
        point2inch = adj(0.2)
        point02inch = adj(0.02)
        # don't pass negative x,y into getbarcode
        if self.landmarks.ulc.x < point2inch:
            raise LayoutIdException("bad landmark x %s" % (self.landmarks.ulc,))
        if self.landmarks.ulc.y < eighth_inch:
            raise LayoutIdException("bad landmark y %s" % (self.landmarks.ulc,))
        # pass image, x,y,w,h
        if self.landmarks.ulc.x >= point3inch:
            startx = max(0,self.landmarks.ulc.x-point3inch)
            widthx = eighth_inch
        elif self.landmarks.ulc.x >= point2inch:
            startx = max(0,self.landmarks.ulc.x-point2inch)
            widthx = sixteenth_inch
        zone = self.image.crop((
                int(max(0,self.landmarks.ulc.x - adj(.35))),
                int(self.landmarks.ulc.y + adj(2.5)),
                int(max(1,self.landmarks.ulc.x - adj(.1))),
                int(self.landmarks.ulc.y + adj(4.3))
                ))
        zone = zone.rotate(-90) #make it left to right
        barcode = tesseract(zone)
        #remove OCR errors specific to text guranteed numeric
        for bad, good in (("\n", ""),  (" ", ""),  ("O", "0"), ("o", "0"),
                          ("l",  "1"), ("I", "1"), ("B", "8"), ("Z", "2"),
                          ("]",  "1"), ("[", "1"), (".", ""),  (",", ""),
                          ("/","1")):
            barcode = barcode.replace(bad, good)

        barcode = barcode.strip("_")
        barcode = barcode.strip("-")
        barcode = barcode.strip(" ")
        barcode = barcode.strip("\n")
        if barcode[4]=="b": 
            barcode = barcode.replace("b","0")
        if not self.good_barcode(barcode):
            # try getting bar code from ocr of region beneath
            self.logger.debug("Barcode digit OCR no good, trying to get barcode via hart_barcode")
            try:
                barcode_height = int(round((7.*const.dpi)/3.))
                barcode = hart_barcode( #x,y,w,h
                    self.image,
                    startx, #x
                    self.landmarks.ulc.y - eighth_inch, #y
                    widthx, #w
                    eighth_inch + barcode_height + eighth_inch #h 
                    )
            except BarcodeException as e:
                self.logger.error("%s %s" % (page.filename,e))
                raise LayoutIdException("bad bar code %s" % (barcode,))
                barcode = "NOGOOD"

        return barcode

