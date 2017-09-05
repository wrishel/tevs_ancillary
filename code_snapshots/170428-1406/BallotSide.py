"""
BallotSide.py
 part of TEVS

as of 1/16/12, should be able to work if a side is created with an 
appropriate layout instance. build_layout will not yet function.
layout may be created directly from an xml template, though the
to and from template functions will need tweaking.

Update required for SaveComposite: we need to have access to the template's
landmarks and our image's rotation in order to translate and rotate our
image prior to compositing, if we want near exact alignment.

The reason we might want near-exact alignment is so that we can do 
a count of added dark pixels with each ballot, in order to identify
ballots that have extraneous marks.

We also need to darken all pixels within some distance of an existing
dark pixel when we generate the initial composite image, so that marks
due only to slight remaining misalignments are not counted.  This can
be done by repeatedly running ImageChops.darken on slightly shifted
versions of the original, a fairly brain-dead approach.  Alternatively,
we could do a single walk through the original, generating a single new
version with a dark pixel whenever a dark pixel is within a certain
distance above, below, left or right in the original.  With either approach,
it might be a good idea to reduce resolution on all merged images to 100 or
150 dpi (or 1000 x 1000*aspect-ratio) if necessary for speed.

We also need to walk the template in order to mask out the targets,
so that filling in targets doesn't contribute to the new dark pixel
count.
"""

import const# the image must be opened to determine its size 
# for passing crop regions
# to the subclass to find landmarks
import Image, ImageChops
from BallotRegions import Point, Landmarks
from BallotSideWalker import XMLWalker, sample_document, sample_xml
from BallotSideExtensions import Extensions
from Transformer import Transformer
# store parsed version of layout in cache, so import minidom
from xml.dom import minidom, Node
from xml.parsers.expat import ExpatError
import math
import os
import os.path
import logging
import util
import pdb

def TO_DPI(a):
    return int(const.dpi * a)

class TransformerException(Exception):
    pass

class _scannedPage(object):
    """Superclass of BallotSide.
    
    Note: y2y, when nonzero, is pixel spacing between top and bottom landmark,
    used for more precise/reliable scaling than asserted dpi.
    """
    def __init__(self, dpi, xoff, yoff, rot, image, y2y=0):
        self.dpi = int(dpi)
        self.xoff, self.yoff, self.y2y = int(xoff), int(yoff), int(y2y)
        self.rot = float(rot)
        self.image = image
        self.extensions = Extensions

def _fixup(im, rot, xoff, yoff):
    return im.rotate(180*rot/math.pi)

class BallotSideException(Exception):
    "Raised if analysis of a ballot image cannot continue"
    pass

class LandmarkException(Exception):
    "Raised if landmarks cannot be located"

class LayoutIdException(Exception):
    "Raised if layout id cannot be located"

class LayoutInvalidException(Exception):
    "Raised if layout cannot be properly generated or saved."

def LoadBallotSideVendorStyle(name):
    """LoadBallotSideType  takes string describing the name of a kind of ballot
    layout, returns the appropriate subclass of BallotSide for processing ballot
    images of that kind. The returned value must be called with the same
    arguments as the Ballot class's __init__ as documented below.  
    
    If no such kind is supported, raises ValueError
    """
    name = name.lower().strip()
    try:
        module = __import__(
             name + "_ballotside",
             globals(),
        )
    except ImportError as e:
        raise ValueError(str(e))
    name = name[0].upper() + name[1:] + "BallotSide"
    return getattr(module, name)

LayoutCache = {
            ('testlayoutid',0):sample_document,
            ('testlayoutid',1):sample_document

}

def prepopulate_cache():
    """Preload all template files from specified location."""
    logger = logging.getLogger(__name__)
    errors = False
    for filename in os.listdir(util.root("templates")):
        logger.info("Preloading %s" % (filename,))
        basename = os.path.basename(filename)
        try:
            fullpath = util.root("templates/%s" % (filename,))
            f = open(fullpath,"r")
            try:
                layout = minidom.parseString(f.read())
            except Exception as e:
                logger.error(e)
                logger.error("No layout built for %s" % (fullpath,))
            lid,side_number = basename.split("_")
            side_number = int(side_number[0])
            LayoutCache[lid,side_number]=layout
        except OSError as e:
            logger.error( "OSError %s"%(e,))
        except ValueError as e:
            logger.error("Failed to retrieve %s" % (fullpath,))
            logger.error( """Is it a non-template file in the templates directory?
All files in the template directory should have names ending _0.xml or _1.xml.""")
            logger.error(e)
            errors = True
        except ExpatError as e:
            logger.error("Expat error %s" % (e,))
            errors = True
        except Exception as e:
            logger.error( "Exception %s %s" % (type(e),e))
            errors = True
        finally:
            f.close()
    if errors: 
        logger.error("Errors prepopulating layout cache.")

class BallotSide(_scannedPage):
    """A ballot side represented by an image and a Template. It is created by
    Ballot.__init__ for each ballot image. Important properties:
    
       * self.ballot - to allow the side access to its host ballot's info
       * self.image_filename - filename of the ballot side's initial image
       * self.image - the PIL image created from self.image_filename
       * self.dpi - an integer specifying the dots per inch of the image
       * self.blank - True if this is a blank (blank backs are legal)
       * self.side_number - 0 for a front, 1 for a back
       * self.landmarks - a structure with info about four corner landmarks
       * self.xoff - the x offset of the ulc landmark within the ballot image
       * self.yoff - the y offset of the uld landmark within the ballot image
       * self.rot - the rotation of the ballot within the ballot image, radians
       * self.y2y - the (misnamed) distance between two standard landmarks,
                    for scaling between real side and template coordinates
    Note that self.rot is in radians, which is used by python's math library,
    but that the rotate method in PIL uses degrees.
    """
    precinct_cache = {}
    party_cache = {}


    def __repr__(self):
        """Print representation of ballot side."""
        retval = ""
        try:
            typestring = str(type(self))
            retval = " side_number=%(side_number)s \
dpi=%(dpi)s image_filename='%(image_filename)s'" % self.__dict__
        except Exception, e:
            self.logger.error(e)
        return typestring + retval

    def __init__(self, ballot=None,
                 dpi=0, 
                 xoff=0, 
                 yoff=0, 
                 rot=0.0, 
                 filename=None, 
                 image_filename=None,
                 template=None, 
                 number=0, 
                 y2y=0):

        def iopen(fname):
            try:
                return Image.open(fname).convert("RGB")
            except BallotSideException:
                raise
            except KeyboardInterrupt:
                raise
            except IOError:
                raise BallotSideException("Could not open %s" % (fname,))

        self.logger = logging.getLogger(__name__)
        self.blank = False
        self.image = None
        self.image_filename = None
        self.ballot = ballot
        self.template = template
        self.side_number = number
        self.dpi = 0
        self.layout_id = None
        self.xml_walker = None
        self.precinct = None
        self.party = None
        # keep track of some maximums over all voteops on the side;
        # these can be used to report other values as deviations
        # from the max, rather than as absolute values
        self.max_red_intensity = 0
        self.max_red_lowest = 0
        self.max_red_low = 0
        self.max_red_high = 0

        if image_filename is None:
            self.blank = True
            return
        self.image = iopen(image_filename)
        self.image_filename = image_filename
        self.image_was_flipped = False
        self.image_needs_flipping = False
        super(BallotSide, self).__init__(dpi, xoff, yoff, rot, self.image, y2y)

        self.barcode = ""
        self.landmarks = None
        self.ulc_landmark_zone_image = None
        self.urc_landmark_zone_image = None
        self.lrc_landmark_zone_image = None
        self.llc_landmark_zone_image = None
        # the standard size and margin of vote targets, converted to pixels
        adj = lambda a: int(round(float(const.dpi) * a))
        try:
            self.target_width = adj(const.target_width_inches)
            self.target_height = adj(const.target_height_inches)
            self.margin_width = adj(const.margin_width_inches)
            self.margin_height = adj(const.margin_height_inches)
            self.writein_zone_width = adj(const.writein_zone_width_inches)
            self.writein_zone_height = adj(const.writein_zone_height_inches)
            self.writein_zone_horiz_offset = \
                adj(const.writein_zone_horiz_offset_inches)
            self.writein_zone_vert_offset = \
                adj(const.writein_zone_vert_offset_inches)
        except AttributeError as e:
            self.margin_width = 0
            self.margin_height = 0
            self.target_width = 30
            self.target_height = 30
            self.logger.error(e)
            raise AttributeError(e + " and is required in the tevs.cfg file.")

    def SaveComposite(self):
        """ retrieve the composite image and mix it with current image,
        taking darkest pixel from each; save result as new composite.
        """
        # determine filename from layout id and side
        filename = "composite_images/%s_%d.jpg" % (self.layout_id,
                                                   self.side_number)
        composite_filename = os.path.join(const.root,filename)

        # ensure single channel
        this_image = self.image.convert("L")

        # retrieve existing composite image if available
        try:
            old_image = Image.open(composite_filename).convert("L")
        except:
            old_image = this_image

        min_width = min(old_image.size[0],this_image.size[0])
        min_height = min(old_image.size[1],this_image.size[1])
        old_image = old_image.crop((0,0,min_width,min_height))
        this_image = this_image.crop((0,0,min_width,min_height))

        # optionally, derotate and translate this image to bring into alignment
        # NYI not yet implemented

        # mix with single channel version of current image
        new_image = ImageChops.darker(old_image,this_image)
        # save result to composite image's filename
        new_image.save(composite_filename)



    def GetPrecinctId(self):
        """ If cached, return precinct; else farm job to subclass """
        pid = None
        if self.layout_id in BallotSide.precinct_cache:
            return BallotSide.precinct_cache[self.layout_id]
        try:
            pid = self.get_precinct_id()
        except AttributeError:
            pid = "Pct Id NYI"
        except Exception as e:
            self.logger.error(e)
        return pid

    def GetPartyId(self):
        """ If cached, return party; else farm job to subclass """
        pid = None
        if self.layout_id in BallotSide.party_cache:
            return BallotSide.party_cache[self.layout_id]
        try:
            pid = self.get_party_id()
        except AttributeError:
            pid = "Pty Id NYI"
        except Exception as e:
            self.logger.error(e)
        return pid


    def GetLayoutId(self):
        """ job of finding layout is farmed to subclass 

        Note that subclasses for vendors that do not provide a unique 
        layout id on both sides of a ballot style should fill  
        the layout_id field for the back side by copying 
        an already determined front side layout_id.
        """
        try:
            self.get_layout_id
        except AttributeError:
            self.logger.info("get_layout_id not implemented in subclass")
            return []
 
        try:
            lid = self.get_layout_id()
        except LayoutIdException:
            raise 

        # subclasses may implement validation routines if they wish
        # validation routines may go in and adjust the landmark_id
        # attribute of the instance if they can get a new valid id
        # using a slower or harder mechanism
        try:
            valid = self.validate_layout_id(lid)
        except AttributeError:
            valid = True

        if not valid:
            raise BallotSideException("Layout id %s is not valid.")

        self.layout_id = lid
        return lid

    def SetupLandmarkZoneImages(self):
        """create four subimages for landmark detection"""
        self.ulc_landmark_zone_image = self.image.crop((
                TO_DPI(const.ulc_zone_x1),
                TO_DPI(const.ulc_zone_y1),
                TO_DPI(const.ulc_zone_x2),
                TO_DPI(const.ulc_zone_y2)
                ))
        self.urc_landmark_zone_image = self.image.crop((
                self.image.size[0] + (TO_DPI(const.urc_zone_x1)),
                TO_DPI(const.urc_zone_y1),
                self.image.size[0] + TO_DPI(const.urc_zone_x2),
                TO_DPI(const.urc_zone_y2)
                ))
        self.lrc_landmark_zone_image = self.image.crop((
                self.image.size[0] + TO_DPI(const.lrc_zone_x1),
                self.image.size[1] + TO_DPI(const.lrc_zone_y1),
                self.image.size[0] + TO_DPI(const.lrc_zone_x2),
                self.image.size[1] + TO_DPI(const.lrc_zone_y2)
                ))
        self.llc_landmark_zone_image = self.image.crop((
                TO_DPI(const.llc_zone_x1),
                self.image.size[1] + TO_DPI(const.llc_zone_y1),
                TO_DPI(const.llc_zone_x2),
                self.image.size[1] + TO_DPI(const.llc_zone_y2)
                ))

    def LandmarkPointsToFullImageCoordinates(self,landmarks):
        landmarks = Landmarks(landmarks[0],
                              landmarks[1],
                              landmarks[2],
                              landmarks[3])
        #landmarks = Landmarks(Point(landmarks[0][0],landmarks[0][1]),
        #                      Point(landmarks[1][0],landmarks[1][1]),
        #                      Point(landmarks[2][0],landmarks[2][1]),
        #                      Point(landmarks[3][0],landmarks[3][1]))

        landmarks.ulc = Point(landmarks.ulc.x + TO_DPI(const.ulc_zone_x1),
                              landmarks.ulc.y + TO_DPI(const.ulc_zone_y1))
        landmarks.urc = Point(landmarks.urc.x + 
                              (self.image.size[0] + TO_DPI(const.urc_zone_x1)),
                              landmarks.urc.y + TO_DPI(const.urc_zone_y1))
        landmarks.lrc = Point(landmarks.lrc.x + 
                              (self.image.size[0] + TO_DPI(const.lrc_zone_x1)),
                              landmarks.lrc.y + 
                              (self.image.size[1] + TO_DPI(const.lrc_zone_y1)))
        landmarks.llc = Point(landmarks.llc.x + TO_DPI(const.llc_zone_x1),
                              landmarks.llc.y + 
                              (self.image.size[1] + TO_DPI(const.llc_zone_y1)))
        return landmarks

    def GetLandmarks(self,landmarks_required=False):
        """ job of finding landmarks is farmed to subclass 

        Landmark zone regions are created as images and loaded into the side 
        here, based on the landmark regions as specified in the config file
        via const; the subclass is asked to examine the images and report the
        offsets of the landmarks in each image; then, at this level, we 
        add in the offsets of the passed images, and set the instance's
        landmarks attribute.

        Subclasses should set image_needs_flipping on the instance if they
        discover the image is an upside down ballot; if they wish, they may
        flip the image (but not the file), set image_was_flipped True, 
        and leave image_needs_flipping set False.
        """
        landmarks = None
        full_image_landmarks_implemented = False
	"""
        try:
            landmarks = self.full_image_get_landmarks
            full_image_landmarks_implemented = True
        except AttributeError:
            self.logger.info("full_image_get_landmarks not implemented in subclass")
	"""
        if full_image_landmarks_implemented:
            landmarks = self.full_image_get_landmarks(
                landmarks_required = landmarks_required)
            if self.image_needs_flipping:
                self.image = self.image.rotate(180.)
                self.logger.info("FLIPPED")
                landmarks = self.full_image_get_landmarks(
                    landmarks_required = landmarks_required)
        else:
            try:
                self.get_landmarks
            except AttributeError:
                self.logger.error("get_landmarks not implemented in subclass")
                raise BallotSideException(
                    "get_landmarks not implemented in subclass")
            self.SetupLandmarkZoneImages()
            try:
                # subclass is called once the cropped zone images 
                # have been created
                landmarks = self.get_landmarks(
                    landmarks_required = landmarks_required)

                if self.image_needs_flipping:
                    self.image = self.image.rotate(180.)
                    self.logger.info("IMAGE FLIPPED, FILE IMAGE UPSIDE DOWN")
                    self.image_needs_flipping = False
                    self.image_was_flipped = True
                    self.SetupLandmarkZoneImages()
                    landmarks = self.get_landmarks(
                        landmarks_required = landmarks_required)
            except LandmarkException, e:
                raise BallotSideException(
                    "subclass' get_landmarks failed %s" % (e,))

        if landmarks is None:
            self.landmarks = None
            return landmarks

        # if landmarks are not returned as a Landmark instance, but as
        # an array of coordinate pairs, the values are still in subimage 
        # coordinates and must be converted to full image coordinates
        
        try:
            landmarks.ulc
        except:
            landmarks = self.LandmarkPointsToFullImageCoordinates(landmarks)
        self.logger.debug("Landmarks %s" % (landmarks,))
        self.landmarks = landmarks
        return landmarks

    def IsFront(self):
        """ job of finding if this side is front is farmed to subclass """
        try:
            self.is_front
        except AttributeError:
            self.logger.error("is_front not implemented in subclass")
            return False
        return self.is_front()

    def GetLayoutFromCacheOrBuild(self):
        """ return a cached layout for the code and side

        If the layout does not initially exist in the cache, 
        we'll call to the subclass' build_layout function, 
        which will fill the cache with a layout.  The layout
        is initially None; the returned layout from the subclass 
        will be [] if the side is blank.
        """
        try:
            # Some vendor styles may have unique layout id's only on the front
            if self.layout_id is None:
                self.layout_id = self.ballot.side_list[0].layout_id

            self.layout = LayoutCache[(str(self.layout_id),self.side_number)]
        except KeyError:
            print "Could not find (%s,%s)" % (str(self.layout_id),self.side_number)
            try:
                self.derotate_landmarks_and_image(do_image=True)
                self.layout, self.layout_image = self.build_layout(self.side_number)
            except AttributeError as e:
                self.logger.error("no build_layout %s" % (e,))
                raise BallotSideException("build_layout not implemented in subclass.")
            self.logger.debug("Layout is %s" % (self.layout,))
            self.SaveLayoutThenParseAndStore()
        return self.layout
    
    
    def derotate_landmarks_and_image(self,do_image=True,filter=Image.BICUBIC):
        """Return new landmark pts calculated by rotating tangent about center.

        If do_image is true, rotate self.image as well.
        This is appropriate if it is to be passed to a template building 
        routine or program.
        """

        center = Point(self.image.size[0]/2,self.image.size[1]/2)
        pt_array = []
        delta_x = self.landmarks.urc.x - self.landmarks.ulc.x
        delta_y = self.landmarks.urc.y - self.landmarks.ulc.y
        tangent = float(delta_y)/float(delta_x)
        for pt in (self.landmarks.ulc,
                   self.landmarks.urc,
                   self.landmarks.lrc,
                   self.landmarks.llc):

            #rotate relative to center
            pt.x -= center.x
            pt.y -= center.y
            ra_sin = math.sin(-tangent)#*math.pi/180.)
            ra_cos = math.cos(-tangent)#*math.pi/180.)
            #print "SIN %2.1f COS %2.1f" % (ra_sin,ra_cos)
            #print "pt3.x= %2.1f minus %2.1f" % (pt2.x*ra_cos, pt2.y*ra_sin)
            #print "pt3.y=%2.1f plus %2.1f" % (pt2.x*ra_sin,pt2.y*ra_cos)
            adj_pt = Point(pt.x*ra_cos - pt.y*ra_sin,
                           pt.x*ra_sin + pt.y*(ra_cos))
            # restore original center offset
            adj_pt.x += center.x
            adj_pt.y += center.y
            adj_pt.x = int(adj_pt.x)
            adj_pt.y = int(adj_pt.y)
            pt_array.append(adj_pt)

        self.landmarks = Landmarks(pt_array[0],pt_array[1],pt_array[2],pt_array[3])    
        if do_image:
            # PIL wants tangent in degrees not radians
            self.image = self.image.rotate(tangent*180./math.pi,filter)
        return self.landmarks 


    def SaveLayoutThenParseAndStore(self):
        """save the layout to a file, parse it, store it in LayoutCache dict"""
        filename = "templates/%s_%d.xml" % (self.layout_id,self.side_number)
        filename = os.path.join(const.root,filename)
        try:
            f = open(filename,"w")
            f.write(self.layout)
            self.logger.info("Template %s saved." % (filename,))
        except TypeError as e:
            raise BallotSideException("Layout could not be written.")
        except OSError as e:
            self.logger.error(e)
        finally:
            f.close()

        filename = "composite_images/%s_%d.jpg" % (self.layout_id,self.side_number)
        filename = os.path.join(const.root,filename)
        try:
            self.image.save(filename)
        except IOError as e:
            self.logger.error(e)
            raise

        filename = "template_images/%s_%d.jpg" % (self.layout_id,self.side_number)
        filename = os.path.join(const.root,filename)
        #try:
        #    blended = Image.blend(self.image.convert("L"),self.layout_image,.8)
        #    blended.save(filename)
        #except IOError as e:
        #    self.logger.error(e)
        #    raise
        try:
            self.layout = minidom.parseString(self.layout)
            LayoutCache[(str(self.layout_id),self.side_number)] = self.layout
        except:
            self.layout = None
        return self.layout

    def GetResults(self):
        """ return an array of VoteData results 

        Walking the side's layout and adjusting each coordinate
        for this ballot's landmarks as compared with the landmarks
        stored with the layout, determine the location of each
        voteop and gather the needed information into VoteData,
        return the array.
        """
        # generate a transformer using the landmark information
        # from the template and the ballot side.
        #transformer = Transformer(src_ulc=Point(0,0),
        #                          target_ulc=self.landmarks.ulc,
        #                          src_urc=Point(1000,0),
        #                          target_urc=self.landmarks.urc,
        #                          src_llc=Point(0,2000),
        #                          target_llc=self.landmarks.llc)
        # xml
                                                
        # self layout must meet criteria for root box of layout
        self.logger.debug("Getting results.")
        if self.layout is None: return []
        self.xml_walker = XMLWalker(
            document=self.layout,
            landmarks=self.landmarks,
            image=self.image,
            image_filename=self.image_filename,
            enclosing_label=self.image_filename)
        self.precinct = self.xml_walker.precinct
        self.party = self.xml_walker.party
        # This debug line causes problems for the logging module.
        #self.logger.debug(self.xml_walker.results)

        # INSERT FUNCTION CALCULATING 
        # HOW MUCH DARKER THAN MAX INTENSITY
        # EACH VOTE OP IS AND REPORT THAT 
        # ALONG WITH OTHER RESULTS
        self.max_red_intensity = 0
        self.max_red_lowest = 0
        self.max_red_low = 0
        self.max_red_high = 0
        for result in self.xml_walker.results:
            self.max_red_intensity = max(self.max_red_intensity,
                                         result.red_mean)
            self.max_red_lowest = max(self.max_red_lowest,result.red_lowest)
            self.max_red_low = max(self.max_red_low,result.red_low)
            self.max_red_high = max(self.max_red_high,result.red_high)
        return self.xml_walker.results


# ***********************************************************************
# Page/Template to XML
# ***********************************************************************

def Template_to_XML(template): #XXX needs to be updated for jurisdictions
    """Takes object and returns a serialization in XML format

    Mitch 1/11/2011 will this work with regular page; check for iteration
"""
    acc = ['<?xml version="1.0"?>\n<BallotSide']
    def attrs(**kw):
        for name, value in kw.iteritems(): #TODO change ' < > et al to &ent;
            name, value = str(name), str(value)
            acc.extend((" ", name, "='", value, "'"))
    ins = acc.append

    attrs(
        dpi=template.dpi,
        barcode=template.barcode,
        lx=template.xoff,
        ly=template.yoff,
        rot=template.rot,
        y2y=template.y2y,
        precinct=template.precinct,
        party=template.party,
        frompage=template.frompage
    )
    ins(">\n")

    #TODO add jurisdictions loop
    for contest in template.contests: #XXX should be jurisdiction
        ins("\t<Contest")
        attrs(
            prop=contest.prop,#XXX del
            text=contest.description,
            x=contest.x,
            y=contest.y,
            x2=contest.x2,
            y2=contest.y2,
            max_votes = contest.max_votes
        )
        ins(">\n")

        for choice in contest.choices:
            ins("\t\t<oval")
            attrs(
                x=choice.x,
                y=choice.y,
                x2=choice.x2,
                y2=choice.y2,
                text=choice.description
            )
            ins(" />\n")
            #TODO add loop for vops that checks for writeins

        ins("\t</Contest>\n")
    ins("</BallotSide>\n")
    return "".join(acc)


# can be page?
#global BlankTemplate 

# config required prior to test
import config
if __name__ == "__main__":
    global BlankTemplate
    config.get()
    # BallotSide cannot be created until config has been called
    BlankTemplate = BallotSide()
    bs = BallotSide(ballot=None,
                 dpi=0, 
                 xoff=0, 
                 yoff=0, 
                 rot=0.0, 
                 filename=None, 
                 image_filename=None, 
                 template=None, 
                 number=0, 
                 y2y=0)

    #t = Transformer(Point(0,0),Point(2,2),Point(50,0),Point(102,2))
    #print t.return_transformed(Point(50,40))
    xmlwalker = XMLWalker(
        # when no document is provided,
        # XMLWalker uses a sample layout in BallotSideWalker.py
        # which corresponds to testlayout.jpg
                 document=None,
                 # image testlayoutrot.jpg is testlayout.jpg
                 # rotated by 3 degrees, Martha box 348,942
                 landmarks = Landmarks(Point(150,150),
                                       Point(2400,272),
                                       Point(2244,3272),
                                       Point(-20,3150) ),
                 # gimp orig, Martha box 387,933
                                      # Point(2400,150),
                                      # Point(2400,3150),
                                      # Point(150,3150)),
                 image=Image.open("testlayoutrot.jpg").convert("RGB"),
                 enclosing_label="testlayoutrot.jpg",
                 image_filename="testlayoutrot.jpg"
                 )
    print "*********************************************************"
    print "R E S U L T S"
    print "*********************************************************"
    for result in xmlwalker.results:
        print result

