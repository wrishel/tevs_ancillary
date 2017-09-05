# Need to change code to buffer results until end of each box,
# so that we can flag overvotes as we go if our templates properly
# show a max-votes value. Search on box_results.
"""
BallotSideWalker.py
 part of TEVS
 implements XMLWalker, a recursive walk through an XML layout tree
 see LayoutSpec.txt for elements and attributes to be handled here
"""
from xml.dom import minidom, Node
from xml.parsers.expat import ExpatError
from Transformer import Transformer
from BallotRegions import Point
from VOP import VOPAnalyze
from DTD import DTD
import logging
import pdb
import const
from recentering import recenter, RecenteringException
from wjr_debugging import source_line, dumpdict

target_height = 0
target_width = 0
target_hotspot_offset_x = 0
target_hotspot_offset_y = 0
global sample_xml, sample_document

sample_xml = """<?xml version="1.0"?>
%s
<BallotSide 
 layout-id='id1' 
 units='inches' 
 precinct='passed_in_value'
 target-height='0.15'
 target-width='0.25' 
 target-hotspot-offset-x='0'
 target-hotspot-offset-y='0'
>
<Landmarks 
ulc-x='0.593' ulc-y = '0.733'
urc-x='7.893' urc-y = '0.723'
lrc-x='7.893' lrc-y = '13.257'
llc-x='0.583' llc-y = '13.253' >
</Landmarks>
<Landmarks ulc-x = '0.5' ulc-y = '0.5' 
           urc-x = '8.0' urc-y = '0.5'  
           lrc-x = '8.0' lrc-y = '10.5' 
           llc-x = '0.5' llc-y='10.5'></Landmarks>

<Box x1='1.0' y1='1.0' x2='3.' y2='4' text='JURISDICTION:J1'>
  <Box x1='0.1' y1='0.1' x2='3.' y2='4.0' text='CONTEST:J1C1 '>
   <Vote x1='0.2' y1='2.' text='Martha'></Vote>
   <Vote x1='0.2' y1='2.25' text='Jane'></Vote>
  </Box>
  <Box x1='0.1' y1='3.1' x2='3' y2='7' text='CONTEST:J1C2'>
   <Vote x1='0.2' y1='2.' text='Hubert'></Vote>
   <Vote x1='0.2' y1='2.25' text='George'></Vote>
  </Box>
</Box>
<Box x1='2' y1='3' x2='4' y2='5' text='JURISDICTION:J2'>
  <Box x1='10' y1='20' x2='30' y2='40' text='CONTEST:J2C1 '>
  </Box>
  <Box x1='11' y1='21' x2='31' y2='41' text='CONTEST:J2C2'>
  </Box>
</Box>
</BallotSide>
""" % (DTD,)
sample_document = minidom.parseString(sample_xml)


class WalkerException(Exception):
    pass

class XMLWalker(object):
    """ A class enabling recursive walk of an XML tree representing layout;
    
    An XMLWalker instance will walk a layout tree keeping track
    of the current Jurisdiction and Contest, and keeping track 
    of the x and y offset of the current nested box.  

    In addition to the layout tree (the document member), the XMLWalker
    requires the current ballot side's landmarks and its image so that it
    can convert layout coordinates to coordinates in the current ballot
    side's coordinate system and then analyze the locations in the current
    ballot side's image.
    
    Additional data is provided for passing to each VOPAnalyze, so that
    each VOPAnalyze can uniquely identify each vote op with its filename,
    side, jurisdiction, and contest.

    When it encounters Vote nodes in the XML tree, it first transforms 
    the coordinates specified in the tree to coordinates appropriate for
    the existing ballot (as determined through that ballot's landmarks).

    It then creates a VOPAnalyze instance for the vote, which analyzes
    the appropriate area on the XMLWalker's image argument, and stores
    data suitable for reporting.  An array of VOPAnalyze instances is
    stored in the XMLWalker's results member, typically for passage
    back to a ballot side and then to a ballot.
    """

    def line_offset(self,data,min_line_thickness=4):
        """Return offset into data list where a line might have begun"""
        in_black = False
        line_at = -1
        black_start = -1
        black_end = -1
        black_contig = 0
        for counter, pix in enumerate(data):
            try:
                pval = pix[0]
            except:
                pval = pix
            if pval<128:
                black_contig = black_contig + 1
                if black_contig >= min_line_thickness and line_at < 0:
                    line_at = counter
                    black_start = counter + 1 - black_contig
                    break
            else:
                black_contig = 0
        return black_start


    
    def box_follows_hstart(self,image,black_start,threshold):
        """Return true if box may exist to right of black_start."""
        dark_count = 0
        test_vline = image.crop((black_start + 2,0,black_start+3,image.size[1]-1))
        test_data = vline.getdata()
        for datum in test_data:
            try:
                datum = datum[0]
            except:
                pass
            if datum < 128:
                dark_count += 1
                if dark_count > threshold: return True
        return False
    def box_follows_hstart(self,image,black_start,threshold):
        """Return true if box may exist to right of black_start."""
        dark_count = 0
        test_hline = image.crop((0,black_start + 2,image.size[0]-1,black_start + 3))
        test_data = hline.getdata()
        for datum in test_data:
            try:
                datum = datum[0]
            except:
                pass
            if datum < 128:
                dark_count += 1
                if dark_count > threshold: return True
        return False



    def __init__(self,
                 document=None,
                 landmarks=None,
                 image=None,
                 image_filename='missing',
                 enclosing_label=None,
                 ballot_class_vop_fine_adjust=None):

        """Create instance and walk tree, generating results."""

        global sample_xml
        self.logger = logging.getLogger(__name__)
        self.document = document
        if document is None:
            self.document = minidom.parseString(sample_xml)
        self.results = []
        # we will change code to buffer results until the end of each box
        self.box_results = []
        self.landmarks = landmarks
        self.image = image
        self.image_filename = image_filename
        self.enclosing_label = enclosing_label
        self.precinct = "NOTINTEMPLATE"
        self.party = "NOTINTEMPLATE"
        self.jurisdiction = None
        self.contest = None
        self.max_votes = 1
        self.current_votes = 0
        self.current_box_node = None
        self.choice = None
        self.transformer = None
        self.current_x = 0
        self.current_y = 0
        self.units = ''
        self.target_height = ''
        self.target_width = ''
        self.target_hotspot_offset_x = 0
        self.target_hotspot_offset_y = 0
        self.side = None
        self.layout_id = None
        self.mwp = int(round(const.margin_width_inches * const.dpi))
        self.mhp = int(round(const.margin_height_inches * const.dpi))
        self.twp = int(round(const.target_width_inches * const.dpi))
        self.thp = int(round(const.target_height_inches * const.dpi))
        self.hlt = int(round(const.dpi/32))
        self.vlt = int(round(const.dpi/32))

        if ballot_class_vop_fine_adjust is None:
            self.ballot_class_vop_fine_adjust = recenter
        if self.document is None:
            raise WalkerException("Document is required.")
        if self.image is None:
            raise WalkerException("Image is required.")
        if self.landmarks is None:
            raise WalkerException("Landmarks instance is required.")
        # we need to confirm that childNodes[1] is indeed a BallotSide
        try:
            x=self.document.childNodes[1]
            if x.nodeType != Node.ELEMENT_NODE:
                raise WalkerException("Child node 1 not element.")
            if x.nodeName != "BallotSide":
                raise WalkerException("Child node 1 not BallotSide element.")
        except AttributeError:
            self.logger.debug("Document has no child node 1.")
            raise WalkerException("Document has no child node 0.")

        self.process_recursive(self.document.childNodes[1],0,0)

    def process_recursive(self,node,x,y):

        """Recursive walk through XML rooted at node.

        The process_recursive function walks an XML tree 
        generating VOPAnalyze instances for each Vote node of the tree.
        """

        if node.nodeType != Node.ELEMENT_NODE:
            return
        print source_line(), "node name: ", node.nodeName
        print source_line(), dumpdict(node.attributes)
        #pdb.set_trace()
        if node.nodeName == 'BallotSide':
            units = node.getAttribute('units')
            if units == '':
                self.units = 'pixels'
            elif units == 'pixels' or units == 'inches':
                self.units = units
            else:
                raise WalkerException(
                    "Ballot side specified unknown unit %s" % (units,))
            self.side = node.getAttribute('side')
            self.layout_id = node.getAttribute('layout-id')

            # If the layout includes attributes 
            # related to the target size, use them.  
            # For missing attributes, use values from the config file.

            # TARGET HEIGHT
            th = node.getAttribute('target-height')
            if th=='':
                self.target_height = target_height
            else:
                self.target_height = float(th)

            # TARGET WIDTH
            tw = node.getAttribute('target-width')
            if tw=='':
                self.target_width = target_width
            else:
                self.target_width = float(tw)

            # PRECINCT
            precinct = node.getAttribute('precinct')
            if precinct=='':
                self.precinct = "NOTINTEMPLATE"
            else:
                self.precinct = precinct

            # PARTY
            party = node.getAttribute('party')
            if party=='':
                self.party = "NOTINTEMPLATE"
            else:
                self.party = party

            # TARGET HOTSPOT OFFSET X 
            # (a target may begin visually before the area to be analyzed,
            # for example, it may consist of two printed arrow halves,
            # with the area to analyze centered between the two printed halves.)
            thox = node.getAttribute('target-hotspot-offset-x')
            if thox=='':
                self.target_hotspot_offset_x = target_hotspot_offset_x
            else:
                self.target_hotspot_offset_x = float(thox)

            # TARGET HOTSPOT OFFSET Y 
            thoy = node.getAttribute('target-hotspot-offset-y')
            if thoy=='':
                self.target_hotspot_offset_y = target_hotspot_offset_y
            else:
                self.target_hotspot_offset_y = float(thoy)
            print source_line(), "target height: %s, width: %s" % (self.target_height, self.target_width)

        elif node.nodeName == 'Landmarks':
            # Set landmarks from node, building transformer 
            try:
                ulc_x = float(node.getAttribute('ulc-x'))
                ulc_y = float(node.getAttribute('ulc-y'))
                urc_x = float(node.getAttribute('urc-x'))
                urc_y = float(node.getAttribute('urc-y'))
                llc_x = float(node.getAttribute('llc-x'))
                llc_y = float(node.getAttribute('llc-y'))
                lrc_x = float(node.getAttribute('lrc-x'))
                lrc_y = float(node.getAttribute('lrc-y'))
            except ValueError:
                raise WalkerException(
                    "Missing required attrib in Landmarks node of XML.")
            
            print source_line(), "Layout",ulc_x,ulc_y,urc_x,urc_y
            print source_line(), "Image",self.landmarks.ulc,self.landmarks.urc
            self.transformer = Transformer(Point(ulc_x,ulc_y),#layout
                                           self.landmarks.ulc,#ballot
                                           Point(urc_x,urc_y),#layout
                                           self.landmarks.urc,#ballot
                                           Point(llc_x,llc_y),#layout
                                           self.landmarks.llc #ballot
                                           )
            print source_line(), "Transformer", self.transformer
        elif node.nodeName == 'Box':
            #Deal with a box by: 
            #(1) changing our accumulated starting x and y positions;
            #(2) outputting appropriate data, if any, for the box 
            #(3) setting juris, contest, etc... depending on the box's 
            #    text attribute"""
            print source_line(), "old x,y =(%d, %d)" % (x, y)
            try:
                x = (x + float(node.getAttribute('x1')))
                y = (y + float(node.getAttribute('y1')))
            except ValueError:
                raise WalkerException(
                    "Missing required attrib in Box node of XML.")

            text = node.getAttribute('text')
            print source_line(), "new x,y =(%d, %d)" % (x, y)
            if text.upper().startswith('CONTEST:'):
                self.contest = text[8:]
            elif text.upper().startswith('JURISDICTION:'):
                self.jurisdiction = text[13:]
            else: self.contest = text
            try:
                self.max_votes = node.getAttribute('max-votes')
            except:
                self.max_votes = 1
                pass
            try:
                #print self.max_votes
                self.max_votes = int(self.max_votes)
                if (self.max_votes == 0):
                    self.max_votes=1
                    print "Max votes was zero, set to 1."
                #print self.max_votes
            except:
                raise WalkerException("Failed to convert or receive max-votes attribute as integer.")
                self.max_votes = 1
            self.current_votes = 0
            # save the box node, so we can go to all its votes
            # if we turn out to have an overvote
            self.current_box_node = node
        elif node.nodeName == 'Vote':
            # Deal with a vote by adding its coordinates to the existing
            # surrounding box coordinates and transforming the result 
            # to get actual coordinates to pass to an analysis object.
            # That object should probably hold the accumulating results,
            # not the BSW.
            attrib_x = None
            attrib_y = None
            attrib_name = None
            #max_votes = 1;
            try:
                attrib_x = float(node.getAttribute('x1'))
                attrib_y = float(node.getAttribute('y1'))
                attrib_name = node.getAttribute('text')
            except ValueError:
                raise WalkerException(
                    "Missing required attrib in Vote node of XML.")
                
            v_x,v_y = self.transformer.transform_coord(
                (attrib_x + x),
                (attrib_y + y))
            v_x2,v_y2 = self.transformer.transform_coord(
                (attrib_x + x + self.target_width),
                (attrib_y + y + self.target_height))
            #v_x = int(round(.998*v_x))
            v_y = int(round(v_y))
            v_y2 = int(round(v_y2))
            print source_line(), "(v_x=%d, vy=%d), (v_x2=%d, v_y2=%d)" % \
                                 (v_x, v_y, v_x2, v_y2)

            if abs(v_y2 - v_y) > 100: 
                self.logger.error("Unreasonable values: %s %s %s %s" % (
                        v_x,v_y
,v_x2,v_y2))
                raise WalkerException("Unreasonable transformed values.")
            # Note that the material below is bypassed with an "if False"!!!
            # A class-specific fine adjustment routine to adjust the crop
            # the crop coordinates for vote areas may be passed in
            # as an initialization argument to the walker.  Otherwise,
            # it uses a version suited for Hart target boxes.
            # This can be generalized to a pre-vote-statistics call,
            # a post-vote-statistics call, and similar optional calls
            # for pre and post contest boxes and pre and post the entire image.
            if False:
                try:
                    #before_filename = "/tmp/before/BEFORE_%d_%d.jpg" % (
                    #    int(round(v_x)),int(round(v_y)))
                    #after_filename = "/tmp/after/AFTER_%d_%d.jpg" % (
                    #    int(round(v_x)),int(round(v_y)))
                    #self.image.crop((int(round(v_x)),
                    #                 int(round(v_y)),
                    #                 int(round(v_x2)),
                    #                 int(round(v_y2))
                    #                 )).save(before_filename)
                    self.logger.info(
                        "Recentering calculated crop %d %d %d %d." % (
                            int(round(v_x)),
                            int(round(v_y)),
                            int(round(v_x2)),
                            int(round(v_y2)),
                            ))
                    v_x,v_y,v_x2,v_y2 = self.ballot_class_vop_fine_adjust(
                        self.logger,
                        self.image,
                        int(round(v_x)),
                        int(round(v_y)),
                        int(round(v_x2)),
                        int(round(v_y2)),
                        #x,y margin in pixels, stored in BSW
                        self.mwp,self.mhp,
                        #horiz and vert line thickness,stored in BSW, 
                        # currently hardcoded to 1/32" as pixels
                        self.hlt,self.vlt,
                        # target width and height in pixels,stored in BSW 
                        self.twp,self.thp
                        )
                    self.logger.info(
                        "Recentered crop %d %d %d %d." % (
                            int(round(v_x)),
                            int(round(v_y)),
                            int(round(v_x2)),
                            int(round(v_y2)),
                            ))
                    #self.image.crop((int(round(v_x)),
                    #                 int(round(v_y)),
                    #                 int(round(v_x2)),
                    #                 int(round(v_y2))
                    #                 )).save(after_filename)
                except RecenteringException as e:
                    self.logger.warning("Recentering failed, target crop unchanged.")
                    self.logger.warning(e)
                except Exception as e:
                    self.logger.warning( "Adjustment routine failed, ballot_class_vop_fine_adjust")
                    #pdb.set_trace()
                    self.logger.warning(e)

            # Provide margins to add to the bounding box 
            # as arguments to VOPAnalyze;
            # the coordinates should continue to reflect 
            # the exact boundaries of the vote op.
            mwp = int(round(const.margin_width_inches*const.dpi))
            mhp = int(round(const.margin_height_inches*const.dpi))
            
            vop = VOPAnalyze(int(round(v_x)),
                             int(round(v_y)),
                             int(round(v_x2)),
                             int(round(v_y2)),
                             v_margin = mhp, 
                             h_margin = mwp, 
                             image=self.image,
                             image_filename=self.image_filename,
                             side=self.side,
                             layout_id= self.layout_id,
                             jurisdiction=self.jurisdiction,
                             contest=self.contest,
                             choice=attrib_name,
                             max_votes=self.max_votes,
                             logger = self.logger)
            print source_line(), vop
            # if the vop was_voted, increment self.current_votes
            # if self.current_votes exceeds self.max_votes
            # for the moment, set the ambig flag on this vote op
            # it would be nice if we could walk back up to the box level
            # and flag every vote in the box as ambiguous or overvoted.

            if vop.voted:
                self.current_votes = self.current_votes + 1
                if self.current_votes > self.max_votes:
                    vop.ambiguous = True
                    # do something to flag every vote in self.current_box_node;
                    # meaning we have to buffer the vops 
                    # until each box is completed
            # We need to buffer all vops for a box, 
            # then flush them to the main
            # results only when we return from recursion. 
            #print "Appending to box_results"
            #print vop
            self.box_results.append(vop)
            #print "Box results now"
            #print self.box_results
            #self.results.append(vop)
        else:
            self.logger.info("Unhandled element %s" % (node.nodeName,))

        for n in node.childNodes:
            self.process_recursive(n,x,y)
            # set vote nodes overvoted if we have too many votes in box,
            # clear the was_voted flag, set ambiguous flag, 
            # then flush pending box results to the main results, 
        if self.box_results and node.nodeName == 'Box':
                #print "Self current votes %d > self.max_votes %d" % (self.current_votes,self.max_votes)
                #pdb.set_trace()
            # Don't call it an overvote if you encounter a situation
            # where an overvote would be caused by a slight mark in comparison
            # with one or more heavier marks
            lowest_intensity = 255
            highest_intensity = 0
            intensity_range = 0
            if self.current_votes > self.max_votes:
                for vop in self.box_results:
                    # determine the darkest and lightest vop
                    if vop.red_mean < lowest_intensity:
                        lowest_intensity = vop.red_mean
                    if vop.red_mean > highest_intensity:
                        highest_intensity = vop.red_mean
                intensity_range = highest_intensity - lowest_intensity
		# commenting out next two for loops as failing, mjt 11/15/2015
                #for vop in self.box_results:
                #    if vop.red_mean > (lowest_intensity + (.9*intensity_range)):
                #        vop.voted = False
                #        vop.ambiguous = False
                #        vop.overvoted = False
                #        self.current_votes = self.current_votes - 1
                # now, are any of the valid votes still ambiguous
                #for vop in self.box_results:
                #    if vop.voted and (vop.red_mean < (lowest_intensity + (.5*intensity_range))):
                #        vop.ambiguous = False
                #        vop.overvoted = False

            for vop in self.box_results:
                if self.current_votes > self.max_votes:
                    if vop.voted:
                        vop.overvoted = True
                        vop.ambiguous = True
                    vop.voted = False
                #print "Copying from box_results to results"
                #print vop
                self.results.append(vop)
            #print "Clearing box_results"
            #print self.box_results
            self.box_results = []
        return node

