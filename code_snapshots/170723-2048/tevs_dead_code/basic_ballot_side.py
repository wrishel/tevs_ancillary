# basic_ballot_side.py
# Part of TEVS
# This file, with basic_ballot.py, demos the minimum functions
# to implement a new vendor ballot style.  It uses hart functions.

from Ballot import BallotException
from BallotSide import BallotSide, Point, Landmarks, LandmarkException
from BallotTemplate import BallotTemplate
from line_util import *
from hart_barcode import hart_barcode
from ocr import tesseract
import pdb
import xmlrpclib

class BasicBallotSide(BallotSide):
    def __init__(self,ballot=None,dpi=None,image_filename=None,number=None):
        super(BasicBallotSide, self).__init__(
            ballot=ballot,
            dpi=dpi,
            image_filename = image_filename, 
            number = number)
        
    def is_front(self):
        """ return True if this side's image represents a front """
        print "is_front now returning hard-coded true"
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
        return retval 


    def validate_layout_id(self,lid):
        """ return True if layout id is valid or believable """
        print "In validate layout id with lid %s, returning True" % (lid,)
        return True


    def build_layout(self,side_number):
        """ build a layout, an array of region subclasses 

        The returned layout is stored in the instance and walked
        when the side's information is requested.  In walking
        the layout, BallotSide will call an adjustment routine
        on each coordinate in the layout to map the coordinate
        to its equivalent value in this image's coordinate frame.
        """
        print "In build layout for side %d" % (self.side_number,)
        print "Building of layouts is implemented by another program,"
        print "which may be called here by exec or xmlrpc"
        print self.image_filename
        print self.landmarks
        # python BallotTemplate.py dpi image_filename 
        # can be set up as xmlrpc or just called
        # xmlrpc will send xml to stdout, so let's incorporate that as our
        # way of generating layouts; need to ensure it meets the LayoutSpec.txt
        # we can simplify its job by passing it landmarks, layout_id,
        # brand, and target sizes;
        # we need to rename it to something like GenericBuildLayout.py
        #proxy = xmlrpclib.ServerProxy("http://localhost:8000/",allow_none=True)
        #layout = proxy.get_layout(self.image_filename,self.landmarks)
        layout = BallotTemplate(self.dpi,
                            self.image_filename,
                            landmarks = self.landmarks,
                            layout_id = self.layout_id,
                            precinct = 'yabba',
                            vendor = 'hart')
        return layout.__repr__()

    # *************************************************
    # Sample routines from hart_ballot
    # *************************************************
    
    def find_landmarks(self,uli,uri,lri,lli):
        """ retrieve landmarks for Hart images

        Landmarks for the Hart Ballot will be the ulc, urc, lrc, llc 
        (x,y) pairs marking the four corners of the main surrounding box."""

        TOP=True
        BOT=False
        LEFT=True
        RIGHT=False
        lm = []

        hline = scan_strips_for_horiz_line_y(
            uli, 
            const.dpi, 
            uli.size[0] - const.dpi/2,#starting_x 
            const.dpi/4, #starting_y
            const.dpi/2, #height_to_scan
            TOP)
        x,y = follow_hline_to_corner(
            uli, 
            const.dpi, 
            uli.size[0], #starting_x
            hline, #starting_y
            LEFT)
        lm.append(Point(x,y))

        hline = scan_strips_for_horiz_line_y(
            uri, 
            const.dpi, 
            const.dpi/2, #starting_x
            const.dpi/4, #starting_y 
            const.dpi/2, #height to search
            TOP)
        x,y = follow_hline_to_corner(
            uri, 
            const.dpi, 
            const.dpi/2, #startx
            hline, #hline
            RIGHT)
        lm.append(Point(x,y))
                  
        hline=scan_strips_for_horiz_line_y(
            lri, 
            const.dpi, 
            const.dpi/2, 
            const.dpi/4, 
            const.dpi/2, 
            BOT)
        x,y = follow_hline_to_corner(
            lri, 
            const.dpi, 
            const.dpi/2,
            hline, 
            RIGHT)
        lm.append( Point(x,y) )
        hline=scan_strips_for_horiz_line_y(
            lli, 
            const.dpi,
            uli.size[0]-const.dpi/2, 
            const.dpi/4, 
            const.dpi/2, 
            BOT)
        x,y = follow_hline_to_corner(
            lli, 
            const.dpi, 
            uli.size[0]-const.dpi/2,
            hline, LEFT)
        lm.append(Point(x,y))
            
        landmarks = Landmarks(lm[0],lm[1],lm[2],lm[3])
        return landmarks

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

    def get_layout_code(self):
        """ Determine the layout code(s) from the ulc barcode(s) """
        # barcode zones to search are from 1/3" to 1/6" to left of ulc
        # and from 1/8" above ulc down to 2 5/8" below ulc.
        def adj(f): return f*self.dpi

        qtr_inch, sixth_inch, eighth_inch = adj(.22), adj(.1667), adj(.125)
        third_inch = adj(0.33)
        point2inch = adj(0.2)
        point02inch = adj(0.02)
        # don't pass negative x,y into getbarcode
        if self.landmarks.ulc.x < point2inch:
            raise BallotException("bad xref %s" % (self.landmarks.ulc,))
        if self.landmarks.ulc.y < eighth_inch:
            raise BallotException("bad yref %s" % (self.landmarks.ulc,))
        # pass image, x,y,w,h

        if self.landmarks.ulc.x >= third_inch:
            startx = max(0,self.landmarks.ulc.x-third_inch)
            widthx = sixth_inch
        elif self.landmarks.ulc.x >= point2inch:
            startx = max(0,self.landmarks.ulc.x-point2inch)
            widthx = 2
        try:
            barcode = hart_barcode(
                self.image,
                startx,
                self.landmarks.ulc.y - eighth_inch,
                widthx,
                eighth_inch + int(round((7.*const.dpi)/3.)) # bar code 2 1/3"
                )
        except BarcodeException as e:
            self.log.info("%s %s" % (page.filename,e))
            barcode = "NOGOOD"
        if not self.good_barcode(barcode):
            # try getting bar code from ocr of region beneath
            self.log.debug("Barcode no good, trying to get barcode via OCR")
            zone = self.image.crop((
                    max(0,self.landmarks.ulc.x - adj(.35)),
                    self.landmarks.ulc.y + adj(2.5),
                    max(1,self.landmarks.ulc.x - adj(.1)),
                    self.landmarks.ulc.y + adj(4.3)
                    ))
            zone = zone.rotate(-90) #make it left to right
            barcode = self.extensions.ocr_engine(zone)

            #remove OCR errors specific to text guranteed numeric
            for bad, good in (("\n", ""),  (" ", ""),  ("O", "0"), ("o", "0"),
                              ("l",  "1"), ("I", "1"), ("B", "8"), ("Z", "2"),
                              ("]",  "1"), ("[", "1"), (".", ""),  (",", ""),
                              ("/","1")):
                barcode = barcode.replace(bad, good)

            if not good_barcode(barcode):
                raise BallotException("bad bar code %s" % (barcode,))

        return barcode

