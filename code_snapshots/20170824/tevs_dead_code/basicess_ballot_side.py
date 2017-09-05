# basic_ballot_side.py
# Part of TEVS
# This file, with basic_ballot.py, demos the minimum functions
# to implement a new vendor ballot style.  It uses hart functions.

from BallotSide import BallotSide
from BallotRegions import Point, Landmarks
from TemplateBuilder import TemplateBuilder, tenthfont
#from BallotTemplate import BallotTemplate
from line_util import *
from ess_code import ess_code, find_front_landmarks
from ocr import tesseract
import os
import pdb
import ImageChops
import xmlrpclib

class BasicessBallotSide(BallotSide):
    def __init__(self,ballot=None,dpi=None,image_filename=None,number=None):
        super(BasicessBallotSide, self).__init__(
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
        # we pass the four provided images to the ess function below...
        # which must be changed to take four corner images and return
        # four coordinate pairs
        lm = find_front_landmarks(self.image)

        """
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

    def get_layout_id(self):
        """ Analyze appropriate part of side and report a layout id code.

        Once landmarks have been determined, a vendor appropriate area
        is searched for information from which a layout id can be generated.
        The way in which this area is located is also vendor specific.
        """
        # we call the ess function below...
        barcode, tm = ess_code(self.image,self.landmarks.ulc.x,self.landmarks.ulc.y)
        # and pass its returned string back up to BallotSide
        return barcode


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

        src_image = self.image.convert("L")
        #Image.open(self.image_filename).convert("L")

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
                                 min_target_width_inches = 0.16,
                                 max_target_width_inches = 0.19,
                                 target_width_inches = 0.25,
                                 target_height_inches = 0.17,
                                 check_for_horizontal = False,
                                 min_target_set_height_inches = 0.25,
                                 min_contest_height_inches = 0.6,
                                 ignore_height_inches = 0.8,
                                 ignore_width_inches = 0.9,
                                 ignore_right_inches = 0.5,
                                 diebold = False)
        layout = tb.__repr__()                       
        return layout, tb.out_image


        #layout = BallotTemplate(self.dpi,
        #                    self.image_filename,
        #                    landmarks = self.landmarks,
        #                    layout_id = self.layout_id,
        #                    precinct = 'yabba',
        #                    vendor = 'ess')
        # the alternative would be to use 
        # an ESS specific layout development routine
        # as found in ess_ballot and ess1_ballot (old files)
        #return layout.__repr__()

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

