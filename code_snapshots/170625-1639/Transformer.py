import math
import pdb
from BallotRegions import Point
from wjr_debugging import source_line
class TransformerException(Exception):
    pass

class Transformer(object):
    """ caches needed transformation info 
    Given:
    1. the upper left coordinates of template and ballot,
    2. upper right or lower left coord of template and ballot,
    Transformer will cache the needed rotation, xlat, scaling info
    needed to convert the template's coordinates to the coordinate
    system of the ballot which provided landmarks.
    Methods to call after initialization are:
    t.transform_in_place(region)
    new_region = t.return_transformed(region)
    """

    def __init__(self, src_ulc, target_ulc,
                 src_urc=None, target_urc=None,
                 src_llc=None, target_llc=None):
        self.src_ulc = src_ulc
        self.target_ulc = target_ulc
        self.src_urc = src_urc
        self.target_urc = target_urc
        self.src_llc = src_llc
        self.target_llc = target_llc
        if src_ulc is None or target_ulc is None:
            raise TransformerException("Must have upper left landmark.")
        if ( (src_urc is None and src_llc is None) or 
             (target_urc is None and target_llc is None) ):
            raise TransformerException("Must have second landmark.")

        # determine scale factor needed to convert template coords to ballot
        self.scale = self.calc_needed_scaling()
        self.scale_x = self.calc_needed_scaling_x()
        self.scale_y = self.calc_needed_scaling_y()
        #print "Scales hypot*.995=%f  x=%f  y=%f" % (self.scale,self.scale_x,self.scale_y)
        # determine translation needed to convert template coords to ballot
        self.delta_x, self.delta_y = self.calc_needed_translation()
        # determine angle of rot needed to convert template coords to ballot
        self.ra_radians = self.calc_needed_rotation_angle()
        self.ra_sin = math.sin(self.ra_radians)
        self.ra_cos = math.cos(self.ra_radians)


    def calc_needed_rotation_angle(self):
        """ 
        determine rotation needed

        given the template (src) and ballot (target) landmarks,
        determine the rotation of each from the horizontal
        and return the angle by which template coordinates must be
        rotated to map to locations in the ballot's coordinate system.
        """
        target_angle = 0
        vtarget_angle = 0
        if self.src_urc is not None:
            longdiff = self.src_urc.x - self.src_ulc.x
            shortdiff = self.src_urc.y - self.src_ulc.y
        else:
            shortdiff = self.src_llc.x - self.src_ulc.x
            longdiff = self.src_llc.y - self.src_ulc.y
            # working vertically, flip angle from horizontal
            shortdiff = -shortdiff
        # short/long is tangent of src
        src_angle = math.atan(float(-shortdiff)/longdiff)
        if self.target_urc is not None:
            longdiff = self.target_urc.x - self.target_ulc.x
            shortdiff = self.target_urc.y - self.target_ulc.y
            # short/long is tangent of target
            target_angle = math.atan(float(-shortdiff)/longdiff)
        if self.target_llc is not None:
            vshortdiff = self.target_llc.x - self.target_ulc.x
            vlongdiff = self.target_llc.y - self.target_ulc.y
            # working vertically, flip angle from horizontal
            vshortdiff = -vshortdiff  # WJR 4/28/17
            vtarget_angle = math.atan(float(-vshortdiff)/vlongdiff)
        # use reverse rotation due to flipped y coord system
        #  empirical; reduce angle of rotation to .02 of report; deg2rad?
        #print "TARGET_ANGLE, VTARGET_ANGLE",target_angle, vtarget_angle
        #pdb.set_trace()
        #if abs(target_angle-vtarget_angle)>.016:
        #    db.set_trace()
        avg_target_angle = (vtarget_angle+target_angle)/2.
        print source_line(), "Tformer rotation ta:%d, vta:%d, avg:%d, src:%d" % \
            (target_angle, vtarget_angle, avg_target_angle, src_angle)
        return (src_angle - avg_target_angle)
        #return 0.02*(src_angle - target_angle)

    def calc_needed_scaling(self):
        """ 
        return ratio of distance between two landmarks for template v ballot
        """
        if self.src_urc is not None:
            src_diff1 = self.src_urc.x - self.src_ulc.x
            target_diff1 = self.target_urc.x - self.target_ulc.x
            src_diff2 = self.src_urc.y - self.src_ulc.y
            target_diff2 = self.target_urc.y - self.target_ulc.y
        else:
            src_diff1 = self.src_llc.x - self.src_ulc.x
            target_diff1 = self.target_llc.x - self.target_ulc.x
            src_diff2 = self.src_llc.y - self.src_ulc.y
            target_diff2 = self.target_llc.y - self.target_ulc.y
        src_hypot = math.sqrt(src_diff1*src_diff1 + src_diff2*src_diff2)
        target_hypot = math.sqrt(target_diff1*target_diff1 + 
                                   target_diff2*target_diff2 )
        #retval  = int(round(float(target_diff1)/src_diff1))
        #return retval
        return target_hypot/src_hypot

    def calc_needed_scaling_x(self):
        """ 
        return ratio of distance between two landmarks for template v ballot
        """
        if self.src_urc is not None:
            src_diff1 = self.src_urc.x - self.src_ulc.x
            target_diff1 = self.target_urc.x - self.target_ulc.x
        else:
            src_diff1 = self.src_rlc.x - self.src_llc.x
            target_diff1 = self.target_rlc.x - self.target_llc.x
        return float(target_diff1)/src_diff1

    def calc_needed_scaling_y(self):
        """ 
        return ratio of distance between two landmarks for template v ballot
        """
        if self.src_urc is not None:
            src_diff1 = self.src_llc.y - self.src_ulc.y
            target_diff1 = self.target_llc.y - self.target_ulc.y
        else:
            src_diff1 = self.src_lrc.y - self.src_urc.y
            target_diff1 = self.target_lrc.y - self.target_urc.y
        try:
            retval = float(target_diff1)/src_diff1
        except ZeroDivisionError:
            print "Divide by zero"
            pdb.set_trace()

        return float(target_diff1)/src_diff1

    def calc_needed_translation(self):
        """move my coords into system of target"""
        #print self.scale_x,self.scale_y
        delta_x = self.target_ulc.x - (self.src_ulc.x*self.scale_x)
        delta_y = self.target_ulc.y - (self.src_ulc.y*self.scale_y)
        return int(round(delta_x)),int(round(delta_y))

    def transform_in_place(self,region):
        """ region may have two coordinate pairs """
        region.x,region.y = self.transform_coord(region.x,region.y)

    def return_transformed(self,region):
        x,y = self.transform_coord(region.x,region.y)
        return Point(x,y)
                      

    def transform_coord(self,st_x,st_y):
        """ return coordinates suitable for use with template coordinates """
        if st_x is None:
            return st_x,st_y
        # reversibly shift such that landmark's x,y at origin
        x = st_x - self.src_ulc.x
        y = st_y - self.src_ulc.y
        # rotate about origin
        x,y = self.rotate(x,y)
        # restore x,y's prior shift, completing rotation
        x = x + self.src_ulc.x
        y = y + self.src_ulc.y
        # scale x,y, adjust based on shift from template
        x = x*self.scale_x + self.delta_x
        y = y*self.scale_y + self.delta_y
        return int(round(x)),int(round(y))    

    def rotate(self,in_x,in_y):
        x = in_x*self.ra_cos - in_y*self.ra_sin
        y = in_x*self.ra_sin + in_y*self.ra_cos
        #print in_x*self.ra_cos, "-", in_y*self.ra_sin
        #print in_x*self.ra_sin, "+", in_y*self.ra_cos
        return x,y

    def __repr__(self):
        return "Transformer scale by (%1.3f,%1.3f) xlat by (%d,%d), rot by %1.3f radians" % (self.scale_x,self.scale_y,self.delta_x,self.delta_y,self.ra_radians) 



