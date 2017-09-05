from BallotSide import BallotSide, Point, Landmarks, LandmarkException

class NewBallotSide(BallotSide):
    def __init__(self,ballot=None,dpi=None,image_filename=None,number=None):
        super(NewBallotSide, self).__init__(
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
        print "returning list of landmark coordinates"
        print self.ulc_landmark_zone_image
        print self.urc_landmark_zone_image
        print self.lrc_landmark_zone_image
        print self.llc_landmark_zone_image
        #if landmarks_required:
        #    raise LandmarkException("failed on ulc, landmarks were required")
        lm = Landmarks(Point(1,2),Point(3,4),Point(5,6),Point(7,8))

        return lm 

    def get_layout_id(self):
        """ Analyze appropriate part of side and report a layout id code.

        Once landmarks have been determined, a vendor appropriate area
        is searched for information from which a layout id can be generated.
        The way in which this area is located is also vendor specific.
        """
        print "In get layout id"
        return "5"

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
        return []
