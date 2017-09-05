"""
Former Ballot module is split into BallotClass (here),
BallotSide,
BallotIStats, 
BallotVoteData, 
BallotResultsToMosaic
all the "interesting" stuff is now in BallotTemplate, which is badly named
and should eventually be BallotSide.

The Ballot loads one or two images, confirming which of the two is a front, 
and names the collection.  

Routines for dealing with the images are all relocated to
BallotSide.py.

Also found in BallotSide are routines that may apply only to 
the front of a double-sided ballot: these are in FrontPage subclassed
off Page. 
"""
import os
import logging
from BallotSide import BallotSide, LayoutCache, prepopulate_cache, BallotSideException, LayoutIdException, LayoutInvalidException
import BallotVOPtoDB as db
import const
import sys
import util
import pdb
__all__ = [
    'BallotException', 
    'LoadBallotFactoryForVendorStyle', 
    'LoadBallotSideFactoryForVendorStyle', 
    'Ballot'
]

composite_counts_dict = {}

class BallotException(Exception):
    "Raised if analysis of a ballot image cannot continue"
    pass

def LoadBallotFactoryForVendorStyle(name):
    """LoadBallotVendorStyle  takes a string naming a kind of ballot
    layout approach and returns the appropriate subclass of Ballot 
    for processing ballots of that kind. 

    The returned value must be called with the same
    arguments as the Ballot class's __init__ as documented below.  
    
    If no such kind is supported, raises ValueError
    """
    name = name.lower().strip()
    try:
        module = __import__(
             name + "_ballot",
             globals(),
        )
    except ImportError as e:
        raise ValueError(str(e))
    name = name[0].upper() + name[1:] + "Ballot"
    return getattr(module, name)

def LoadBallotSideFactoryForVendorStyle(name):
    """LoadBallotVendorStyle  takes a string naming a kind of ballot
    layout approach and returns the appropriate subclass of Ballot 
    for processing ballots of that kind. 

    The returned value must be called with the same
    arguments as the Ballot class's __init__ as documented below.  
    
    If no such kind is supported, raises ValueError
    """
    name = name.lower().strip()
    try:
        module = __import__(
             name + "_ballot_side",
             globals(),
        )
    except ImportError as e:
        raise ValueError(str(e))
    name = name[0].upper() + name[1:] + "BallotSide"
    return getattr(module, name)

# Ballots can be created only after configuration has taken place
# and created various variables in the const module! See main below.
class Ballot(object):
    """A Ballot takes a set of images and an Extension object. The set of
    images can be described as either a string representing the filename of a
    single ballot image or an iterable of filenames representing the filenames
    of an ordered set of ballot images.

    When the ballot is created, it attempts to open all of the files given to
    it via PIL. 

    The Ballot class cannot be used directly. It must be used via a subclass
    that implements the required abstract methods (documented below). However,
    Ballot provides the interface for interacting with a subclass. To get the
    appropriate subclasses use LoadBallotVendorStyle 
    and LoadBallotSideVendorStyle and create Ballots and BallotSides 
    from thereturned factories.

    To use a Ballot, only call the methods that are AllCaps. To create a ballot
    subclass, override only the methods that are no_caps.

    Important data members are:
        * self.pages - a list of Page objects
        * self.extensions - the Extension object this object was
          instantiated with
        * self.results - a list of VoteData (empty until CapturePageInfo is
          called)
        * self.logger - a useful reference to the default logger, see the Python
          logging module.
    """
    def __init__(self, image_filenames, extensions):
        """ initialization for all ballot vendor styles 

        The side_list is populated in subclass __init__s.
        """
        self.side_list = []
        self.extensions = extensions
        self.results = []
        self.logger = logging.getLogger(__name__)

    def __repr__(self):
        retval = "Ballot"
        for side in self.side_list: 
            retval += "\n Side "
            retval += side.__repr__()
        retval += "\n Results "
        retval += str(self.results)
        return retval

    def ProcessBallot(self, the_db=None):
        """ everything that must happen to get from the images to results """
        self.OrderSides()
        try:
            self.side_list[0].GetLandmarks(landmarks_required=True)
            if len(self.side_list) == 2:
                self.side_list[1].GetLandmarks(landmarks_required=False)
        except BallotSideException as e:
            self.logger.warning("Ballot side exception %s" % e)
            # rather than raise an exception, try returning a result string
            # with a warning, allowing continuation
            return "%s" % (e,)
            #raise
        try:
            self.GetLayoutId()
        except LayoutIdException as e:
            self.logger.error("Error in GetLayoutId %s\n" % (e,))
        except Exception as e:
            self.logger.error("Error in GetLayoutId %s\n" % (e,))
        try:
            self.GetLayoutsFromCache()
        except Exception as e:
            self.logger.error("Error in GetLayoutsFromCache %s\n" % (e,))
            raise
        if const.save_composite_images:
            self.SaveComposites()
        results = None
        try:
            results = self.GetResults()
        except Exception as e:
            self.logger.error("Error in GetResults %s\n" % (e,))
            raise
        # the precinct and party are retrieved from the layout
        # into the BallotSide during BallotSideWalker/GetResults
        self.GetPrecinctId()
        self.GetPartyId()
        if the_db is not None:
            self.ResultsToDB(the_db)
            self.logger.debug("Saved to database.")
        return results

    def SaveComposites(self):
        """Ask each side to add itself to the appropriate composite image.

        """
        for sidenumber in range(len(self.side_list)):
            self.side_list[sidenumber].SaveComposite()

    def GetPrecinctId(self):
        """Get the human readable precinct information.

        This function is normally called only when a new layout code occurs
        and a template is built.
        """
        side_with_precinct_id = 0
        self.precinct_id = self.side_list[side_with_precinct_id].precinct
        return self.precinct_id

    def GetPartyId(self):
        """Get the human readable precinct information.

        This function is normally called only when a new layout code occurs
        and a template is built.
        """
        side_with_party_id = 0
        
        self.party_id = self.side_list[side_with_party_id].party
        return self.party_id

    def GetLayoutId(self):
        """Get a code for the layout, generally a bar or dash pattern

        This function calls its equivalent for the front side of the ballot.
        We are assuming here that landmarks must be available on the side
        of the ballot which carries the layout code, but we do not assume
        that landmarks will be available on the opposite side.  

        This allows for duplex ballots where the reverse side 
        is sometimes left blank.
        """
        side_with_layout_id = 0
        self.side_list[side_with_layout_id].landmarks = \
            self.side_list[side_with_layout_id].GetLandmarks()
        if self.side_list[side_with_layout_id].landmarks == []:
            raise BallotException, "Landmarks not found"
        lid = self.side_list[side_with_layout_id].GetLayoutId()
        self.layout_id = lid
        return lid

    def GetLayoutsFromCache(self):
        """Have each side retrieve its layout from the layout cache

        This function calls its equivalent for each side in side_list.
        Failure to retrieve a layout for the reverse is not necessarily
        fatal; it is possible to have duplex ballots where the reverse
        lacks a layout (is blank).
        """
        self.side_list[0].GetLayoutFromCacheOrBuild()

        if len( self.side_list ) > 1 :
            self.side_list[1].GetLayoutFromCacheOrBuild()

    def GetResults(self):
        self.results = []
        for side in self.side_list:
            self.results.extend(side.GetResults())
        return self.results

    def ResultsToDB(self,the_db):
        """ Put results into database."""
        self.logger.debug("ResultsToDB")
        the_db.insert_new(self)

    def OrderSides(self):
        """For two-sided ballots, ensure that the front is side_list[0]"""
        if len(self.side_list)==2:
            if self.side_list[0].IsFront():
                return
            elif self.side_list[1].IsFront():
                self.side_list = [self.side_list[1],self.side_list[0]]
                self.image_filenames = [self.image_filenames[1],
                                        self.image_filenames[0]
                                        ]
                return



    def merge_with_composites(self):
        """update composite images for this layout with this ballot's images"""
        try:
            oldimage = Image.open("%s/%s%d/%s.jpg" % (
                    util.root(),
                    "composite_images",os.getpid(),
                    tmpl.barcode))
        except:
            try:
                oldimage = Image.open("%s/%s%d/%s.jpg" % (
                        util.root(),
                        "template_images",os.getpid(),
                        tmpl.barcode))
            except:
                oldimage = None
                
        # else retrieve template image
        # derotate the new image as if you were building a template
        r2d = 180/3.14
        newimage = page.image.rotate(-r2d * page.rot, Image.BILINEAR)
        #page.image.save("/tmp/postrotate.jpg")
        if oldimage is None: oldimage = newimage
        # landmarks will change once image is derotated!
        try:
            self.FindLandmarks(pagenum)
        except BallotException:
            pass
        # translate the new image to align with composite image
        delta_x = tmpl.xoff - page.xoff 
        delta_y = tmpl.yoff - page.yoff

        newimage = newimage.offset(delta_x,delta_y)
        #newimage.save("/tmp/posttranslate.jpg")
        # apply darker operation, save result in first argument?
        oldimage.load()
        oldr,oldg,oldb = oldimage.split()
        newr,newg,newb = newimage.split()
            # count dark pixels in oldr excluding edges
        oldr_crop = oldr.crop((const.dpi/4,
                               const.dpi/4,
                               min(oldr.size[0],newr.size[0]) 
                               - (const.dpi/4),
                               min(oldr.size[1],newr.size[1]) 
                               - (const.dpi/4)))
        old_total_intensity = 0
        for p in oldr_crop.getdata():
            old_total_intensity += p
        newr = ImageChops.darker(oldr,newr)
        newg = ImageChops.darker(oldg,newg)
        newb = ImageChops.darker(oldb,newb)
        new_total_intensity = 0
            # count dark pixels in newr excluding edges
        newr_crop = newr.crop((const.dpi/4,
                               const.dpi/4,
                               min(newr.size[0],oldr.size[0]) 
                               - (const.dpi/4),
                               min(newr.size[1],oldr.size[1]) 
                               - (const.dpi/4)))
        new_total_intensity = 0
        for p in newr_crop.getdata():
            new_total_intensity += p
        self.logger.info("%s Old %d New %d Diff %d" % (
                os.path.basename(page.filename),
                old_total_intensity,
                new_total_intensity,
                old_total_intensity - new_total_intensity))
        newimage = Image.merge("RGB",(newr,newg,newb))
        try:
            composite_counts_dict[tmpl.barcode] += 1
            if 0==(composite_counts_dict[tmpl.barcode]%5):
                self.logger.info(
                    "Composite count for %s now %d (this run only)" % (
                                tmpl.barcode,
                                composite_counts_dict[tmpl.barcode]
                                ))
        except:
            composite_counts_dict[tmpl.barcode] = 1
        newimage.save("%s/%s%d/%s.jpg" % (
                util.root(),
                "composite_images",os.getpid(),
                tmpl.barcode))
                # save result as composite

def _ocr1(extensions, page, node):
    "this is the backing routine for Ballot.OCRDescriptions"
    crop = page.image.crop(node.bbox())
    if type(node) in (Jurisdiction, Contest, Choice):
        temp = extensions.ocr_engine(crop)
        temp = extensions.ocr_cleaner(temp)
        node.description = temp
    else:
        node.image = crop
    for child in node.children():
        _ocr1(extensions, page, child)


import config
if __name__ == "__main__":

    config.get()
    bv = LoadBallotFactoryForVendorStyle(const.layout_brand)
    bsv = LoadBallotSideFactoryForVendorStyle(const.layout_brand)

    # establish a connection to the database
    # connect to db and open cursor
    dbc = None
    if const.use_db:
        try:
            dbc = db.PostgresDB(database=const.dbname, user=const.dbuser)
        except db.DatabaseError:
            util.fatal("Could not connect to database!")
    else:
        dbc = db.NullDB()

    prepopulate_cache()
    # Create a ballot from one image file.  
    # This should create an instance for the style named as "brand" in tevs.cfg
    #b = bv("harttestfront.jpg",None)

    # WARNING -- The display program(s) 
    # will expect a numeric filename 
    # in the correct location specified by tevs.cfg
    # hart 
    filename1 = "/home/mitch/data/hart/unproc/000/000001.jpg" 
    filename2 = "/home/mitch/data/hart/unproc/000/000002.jpg" 
    filename3 = "/home/mitch/data/hart/unproc/000/000003.jpg" 
    filename4 = "/home/mitch/data/hart/unproc/000/000004.jpg" 
    # ess
    filename1 = "/home/mitch/essdata/unproc/000/000008.jpg"
    filename2 = "/home/mitch/essdata/unproc/000/000009.jpg"
    filename3 = "/home/mitch/essdata/unproc/000/000009.jpg"
    filename4 = "/home/mitch/essdata/unproc/000/000010.jpg"
    # diebold
    filename1 = "/home/mitch/tevs/tevs/diebold_data/unproc/000/000001.jpg" 
    filename2 = "/home/mitch/tevs/tevs/diebold_data/unproc/000/000001.jpg" 
    filename3 = "/home/mitch/tevs/tevs/diebold_data/unproc/000/000003.jpg" 
    filename4 = "/home/mitch/tevs/tevs/diebold_data/unproc/000/000004.jpg" 
    b = bv(filename1,None)
        
    simplex_results = b.ProcessBallot(dbc)
        
    #simplex_results = b2.ProcessBallot(dbc)
    #pdb.set_trace()
    # Create a ballot from two image files (or same one ref'd twice).
    """b2 = bv([filename1,filename2],None)
    duplex_results = b2.ProcessBallot(dbc)
    
    print "*********************************************************"
    print "S I M P L E X   R E S U L T S"
    print "*********************************************************"

    for result in simplex_results:
        print result
    print "*********************************************************"
    print "D U P L E X   R E S U L T S"
    print "*********************************************************"

    for result in duplex_results:
        print result
    """
    b = bv(filename3,None)
    simplex_results = b.ProcessBallot(dbc)
    b = bv(filename4,None)
    simplex_results = b.ProcessBallot(dbc)

    # At this point, there should be cached layouts
    #print "Layouts", LayoutCache, "should have two sides"
