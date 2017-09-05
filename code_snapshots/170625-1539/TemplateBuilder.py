# template_builder.py (TemplateBuilder)
# Part of TEVS, copyright 2012
# Author: Mitch Trachtenberg mjtrac@gmail.com
# Licensed under the GNU General Public License v. 2

# WARNING: HANDLING OF HORIZONTAL TARGET SETS DISABLED
# search on DISABLE to find commented line

"""TemplateBuilder generates a template of contests and
vote targets from a PIL image and a dpi value.

This version accepts a diebold flag and behaves differently for diebold.
Only diebold checks for both top and bottom of targets.

Note that diebold could further restrict targets to lines
beginning and ending within quarter inch regions bounded by horiz marks
and spanning specific 1/16" regions defined by vertical timing marks

Diebold checked with horizontal only, .11 to .14 target width range.  
Others checked with vertical only.

OCR degrades beneath 300 dpi.

The actual target width and actual target height may be passed in,
but should be updated (if necessary) based on the actual targets found.

"""

import Image, ImageDraw, ImageStat, ImageFont
import pdb
import sys
import logging
import os.path
from ocr import tesseract, clean_ocr_text
from darkstripes import darkstripes
from target_and_text import target_and_text_from_images,text_code
from DTD import DTD
"""
TemplateBuilder, supported by classes Target and TargetSet,
and files darkstripes.py, target_and_text.py, and ocr.py, 
parses a ballot into labelled vote targets in contests.

The template is written as XML and visualized overlaid upon
the starting image in files stored in /tmp.  This is done in 
the __main__ program, but should be made a method of the
TemplateBuilder class.

The strategy is to start by searching for darkened line segments
of a size that makes them possible components of target ovals or
rectangles.  The list of candidates is then winnowed by looking
for vertically or horizontally aligned candidates spaced such that
they might be part of a set.  

A bounding box is constructed around each such set, and 
another bounding box is built by searching outwards until
solid lines are encountered.  Sets sharing a common expanded
bounding box are merged.  Small or short expanded bounding
boxes are eliminated.

The expanded bounding boxes that remain are split horizontally
into the part above the target set bounding box and the rest.
The part above is treated as containing a contest name; the
rest is split again, vertically, to the side of the target
set opposite the nearest wall of the expanded bounding box.

This lower part is divided, using code in target_and_text.py,
into individual vote targets and their associated text.

On a 300 dpi Saguache template, each actual target 
gets picked up.  Works pretty well at 200dpi.

This is time consuming, and the parsing can be made much
faster if more ballot constraints are available, but this
should work with a minimum set of constraints:

(1) the first n pixels of each scan line can be ignored
(2) targets are wider than individual letters
(3) targets will be aligned in groups of at least two,
    and separated vertically by a minimum of 1/3" (more?)
(4) contests are boxed by solid lines
(5) (where lines are missing, it may be possible to treat
    large areas of white space inside black space as column
    and row boundary lines, but this is NYI.)

(Still might OCR each region that is not in an expanded bbox, 
for the ballot side record.  Also, make initial target hunt pluggable.)


"""
fontpath = "/usr/share/fonts/truetype/freefont/FreeSerif.ttf"
tenthfont = ImageFont.truetype(fontpath,30)

def print_ts_of_tb(self):
	for index,ts in enumerate(self.target_sets):
		print index,ts

def column_lt_threshold(data, start, stride, num, threshold):
    retval = False
    move_down_by = 0
    for counter in range(start,start + (stride*num),stride):
        if data[counter] < threshold:
            retval = True
            break
	move_down_by += 1
    return retval, move_down_by

def column_gt_threshold(data, start, stride, num, threshold):
    retval = False
    for counter in range(start,start + (stride*num),stride):
        if data[counter] > threshold:
            retval = True
            break
    for counter in range(start,start + (-stride*num),-stride):
        if data[counter] > threshold:
            retval = True
            break
    return retval


def tess_and_clean(im):
    text = tesseract(im)
    cleaned_text = clean_ocr_text(text)
    return cleaned_text

def get_x_offset_of_targets(im,threshold = 232,min_dark=4):
    """return x val where darkening of image starts """
    start_x = 0
    trim = 5
    found = False
    #im.save("/tmp/targets.jpg")
    #print "Saved targets image about to be used for finding target left edge."
    for x in range(trim,im.size[0]-trim):
        dark_count = 0
        column = im.crop((x,trim,x+1,im.size[1]-trim))
        for p in column.getdata():
            val = 0
            try:
                val = p[0]
            except:
                val = p
            if val < threshold:
                dark_count += 1
                if dark_count > min_dark:
                    start_x = x
                    found = True
                    break
        if found: break
    return start_x

def split_at_white_horiz_line(im,threshold=232):
	"""Return list of starting y offsets of all white stripes in image."""
	looking_for_white = True
	found_white = False
	whites = []
	for y in range(im.size[1]):
		line_white = True
		for x in range(im.size[0]):
			if im.getpixel((x,y)) < threshold:
				# not this line
				line_white = False
				break
		if line_white and looking_for_white:
			# this is a white line, append it to the list
			found_white = True
		elif (not line_white) and looking_for_white and found_white:
			if y>0:
				looking_for_white = False
				found_white = False
				whites.append(y-1)
		elif (not line_white) and (not looking_for_white):
			# this is a black line, so let's 
			# resume our hunt for white
			looking_for_white = True
			continue
	return whites

class Line(object):
    def __init__(self, image, dpi, x1, y1, x2, y2,text=""):
        self.image = image
        self.dpi = dpi
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.w = self.x2 - self.x1 
        self.h = self.y2 - self.y1 
        self.text = text

    def __repr__(self):
        return "(%d %d %d %d) %s" % (self.x1,self.y1,self.x2,self.y2,self.text)

class Target(object):
    """Holds the coordinates of a mark together with assoc information."""
    def __init__(self,x,y,x2,y2=0):
        self.x = x
        self.y = y
        self.x2 = x2
        self.y2 = y2
        self.text = ""
        
    def get_text(self):
        self.text = "Not yet"

    def __repr__(self):
        return "Target x %d y %d x2 %d y2 %d text %s" % (self.x,
                                                        self.y,
                                                        self.x2,
                                                        self.y2,
                                                        self.text)

class TargetSet(object):
    """Holds a set of potentially logically grouped vote targets."""
    generic_darkened_threshold = 232
    def append(self,new_target):
        self.marks.append(new_target)
        if new_target.x < self.bbox[0]:
            self.bbox[0] = new_target.x
        if new_target.y < self.bbox[1]:
            self.bbox[1] = new_target.y
        if new_target.x2 > self.bbox[2]:
            self.bbox[2] = new_target.x2
        if new_target.y2 > self.bbox[3]:
            self.bbox[3] = new_target.y2
            
    def __init__(self,initial_target, image, orientation = "V",dpi=300):
        self.im = image
        self.marks = [initial_target]
        self.orientation = orientation
        self.targets_left_of_text = True
        self.bbox = [initial_target.x,
                     initial_target.y,
                     initial_target.x2,
                     initial_target.y2]
        self.dpi = dpi
        # populated during processing

        # the region around the vote targets that includes text
        self.expanded_bbox = None
        self.expanded_bbox_image = None
        self.left_line = None
        self.right_line = None
        self.top_line = None
        self.bottom_line = None

        # the part of the expanded region 
        # with text not associated with any target
        self.zone_above_targets = None

        # the original target zone (is this just bbox again?)
        self.zone_of_targets_only = None

        # the part of the expanded region with per-target text
        self.zone_with_targets_text = None

        self.contest_text = None
        self.target_text = None

        # the horizontal offset into the expanded bbox
        # dividing targets from target-affiliated text
        self.gap_after_targets = None

    def find_left_line(self,min_line_height=0):
        """Search to left of bbox for solid line"""
        return self.find_vertical_line(
            direction=-1,
            min_line_height=min_line_height)

    def find_right_line(self,min_line_height=0):
        """Search to left of bbox for solid line"""
        return self.find_vertical_line(
            direction=1,
            min_line_height=min_line_height)
        
    def find_vertical_line(self,direction=-1,min_line_height=0):
        if min_line_height == 0:min_line_height=self.dpi
        if self.bbox[3]<=self.bbox[1]:
            return 0# raise "Box not tall enough to check"
        if self.bbox[2]<=self.bbox[0]:
            return 0# raise "Box not wide enough to check"
        if direction == -1:
            range_start = self.bbox[0]
            range_end = 10
            range_inc = -1
        else:
            range_start = self.bbox[0]
            range_end = self.im.size[0]-2
            range_inc = 1
        # check for a vertical dark strip to side of the bbox
        # with avg intensity below threshold value
        vline = 0
        for x in range(range_start,range_end,range_inc):
            testcrop = self.im.crop(
                (x,
                 self.bbox[1],
                 x+1,
		 self.bbox[1]+min_line_height
		 )
		)
	    if self.is_this_mostly_dark(
                testcrop,
                threshold=self.generic_darkened_threshold):
                if self.is_this_97pct_dark_pix(
                    testcrop,
                    threshold=self.generic_darkened_threshold):
                    vline = x
                    break
        return vline

    def find_top_line(self,min_line_width=0,search_leftwards=False):
        """Search above bbox for solid line"""
        return self.find_horizontal_line(
            direction=-1,
            min_line_width=min_line_width,
            search_leftwards=search_leftwards)

    def find_bottom_line(self,min_line_width=0,search_leftwards=False):
        """Search to left of bbox for solid line"""
        return self.find_horizontal_line(
            direction=1,
            min_line_width=min_line_width,
            search_leftwards = search_leftwards)
        
    def find_horizontal_line(self,direction=-1,min_line_width=0, search_leftwards=False):
        if min_line_width == 0:min_line_width=self.dpi
        if search_leftwards: 
            min_line_width = -min_line_width
        if self.bbox[3]<=self.bbox[1]:
            return 0# raise "Box not tall enough to check"
        if self.bbox[2]<=self.bbox[0]:
            return 0# raise "Box not wide enough to check"
        if direction == -1:
            range_start = self.bbox[1]
            range_end = 0
            range_inc = -1
        else:
            range_start = self.bbox[3]
            range_end = self.im.size[1]-2
            range_inc = 1
        # check for a horizontal dark strip above or below the bbox
        # with avg intensity below threshold value
        vline = 0
        for y in range(range_start,range_end,range_inc):
            # we insist the line be dark for min_line_width /past target/;
            # this may fail if target is at right edge of box
            testcrop = self.im.crop(
                (min(self.bbox[0],self.bbox[0]+min_line_width),
                 y,
                 max(self.bbox[0],self.bbox[0]+min_line_width),
                 y+1
                 )
                )
            if self.is_this_mostly_dark(
                testcrop,
                threshold=self.generic_darkened_threshold):
                if self.is_this_97pct_dark_pix(
                    testcrop,
                    threshold=self.generic_darkened_threshold):
                    vline = y
                    break
        return vline

    def find_complete_targets(self, image, darkness_threshold=232):
        """return targets and coords from image line by line"""
        return self.find_line_breaks(image,do_ocr=False)
        
    def find_line_breaks(self, image, darkness_threshold=232, do_ocr=True):
        """return text and coords from image line by line"""
        gaps = []
        lines = []
        dpi = self.dpi
        for y in range(3,image.size[1]-4):
            zone0 = image.crop((1,y-3,image.size[0]-1,y-2))
            zone1 = image.crop((1,y,image.size[0]-1,y+1))
            stat0 = ImageStat.Stat(zone0)
            stat1 = ImageStat.Stat(zone1)
            min0 = stat0.extrema[0][0]
            min1 = stat1.extrema[0][0]
            last_gap = 0
            data0 = zone0.getdata()
            data0_darkcount = 0
            for d in data0:
                try:
                    if d[0]<darkness_threshold:
                        data0_darkcount += 1
                        if data0_darkcount > 1: break
                except:
                    if d<darkness_threshold:
                        data0_darkcount += 1
                        if data0_darkcount > 1: break

            data1 = zone1.getdata()
            data1_darkcount = 0
            for d in data1:
                try:
                    if d[0]<darkness_threshold:
                        data1_darkcount += 1
                        if data1_darkcount > 1: break
                except:
                    if d<darkness_threshold:
                        data1_darkcount += 1
                        if data1_darkcount > 1: break

            if ( data1_darkcount == 0 and data0_darkcount > 1 ): 
                gaps.append(y)

        last_gap = 0
        for gap in gaps:
            #print last_gap,"to",gap
            # no text if less than 1/16" tall, probably write-in underline
            if (gap-last_gap) < (dpi/16):
                last_gap = gap
                continue
            line_image =  image.crop((0,max(0,last_gap),image.size[0],gap+1))
            lines.append(Line(
                    line_image,
                    dpi,
                    0,last_gap,image.size[0],gap+1))
            text = tess_and_clean(line_image)
            if text is not None: 
                lines[-1].text = text.strip("\n")
            last_gap = gap
        return lines

    def is_this_mostly_dark(self,image,threshold=128):
        try:
            m = self.channel_zero_mean(image,threshold)
        except ZeroDivisionError,e:
            print e
            pdb.set_trace()
        if m < threshold:
            return True
        else:
            return False

    def is_this_97pct_dark_pix(self,image,threshold=216):
        darkcount = 0
        fullcount = 0
        for d in image.getdata():
            fullcount += 1
            try:
                if d[0]<threshold:
                    darkcount += 1
            except:
                if d<threshold:
                    darkcount += 1
        if fullcount == 0:
            print "About to divide by zero, why?"
            pdb.set_trace()
        if float(darkcount)/float(fullcount) >= .97:
            return True
        else:
            return False

    def channel_zero_mean(self,image,threshold=232):
        istat = ImageStat.Stat(image)
        return istat.mean[0]

    def find_gap_after_targets(self):
        """Search the bbox for first fully white stripe"""
        retval = 0
        # start in by dpi/10 from bounding box to avoid white
        # at very start of bounding box
	indent_by = 0#dpi/10
	if self.bbox[2]>self.bbox[0]:
		indent_by = (self.bbox[2] - self.bbox[0])/2
        for x in range(self.bbox[0] + indent_by,self.expanded_bbox[2]):
		# search only top half of bbox, to allow write-in lines
		# to allow write-in lines to cross over vertical dividing
		# column on Hart ballots.
		halfway = (self.bbox[1]+self.bbox[3])/2
		test_image = self.im.crop((x,self.bbox[1] ,x+1,halfway))
		all_white = True
		for ypix in test_image.getdata():
			try:
				is_dark = (((ypix[0]+ypix[1]+ypix[2])/3) 
					   < self.generic_darkened_threshold)
			except TypeError:
				is_dark = (ypix 
					   < self.generic_darkened_threshold)
			if is_dark:
				all_white = False
				break
		if all_white:
			retval = x
			break
        return x

    def find_gap_before_targets(self):
        """Search the bbox for first fully white stripe"""
        retval = 0
        for x in range(self.bbox[0],self.expanded_bbox[0],-1):
            test_image = self.im.crop((x,self.bbox[1] ,x+1,self.bbox[3]))
            all_white = True
            for ypix in test_image.getdata():
                try:
                    is_dark = ypix[0] < self.generic_darkened_threshold
                except TypeError:
                    is_dark = ypix < self.generic_darkened_threshold
                if is_dark:
                    all_white = False
                    break
            if all_white:
                retval = x
                break
        return x

    def __repr__(self):
        return "--%sTS w/ %d marks bbox %s ebb %s\n%s\n%s\n" % (
            self.orientation,
	    len(self.marks), 
            self.bbox, 
            self.expanded_bbox, 
            self.right_line, 
            self.marks)

class TemplateBuilder(object):
    """A class that builds XML representation of ballot image."""
    generic_darkened_threshold = 232
    def __init__(self,
                 im,
                 dpi,
                 filename = "no name provided",
                 threshold = 0,
		 # the layout_id, precinct, and x and y args are passed through
		 # to the output template XML, but not used otherwise
		 layout_id = "no layout id provided",
		 precinct = "no precinct provided",
                 ulc_x = 0,
                 ulc_y = 0,
		 urc_x = 0,
		 urc_y = 0,
		 lrc_x = 0,
		 lrc_y = 0,
		 llc_x = 0,
		 llc_y = 0,

                 ignore_width_inches = 0.85,
                 ignore_right_inches = 0.85,
                 ignore_height_inches = 1.5,
                 contest_gap_inches = .5,
                 max_merge_distance_inches = 0.17,
                 min_target_width_inches = 0.1,
                 max_target_width_inches = 0.6,
		 target_width_inches = 0.34,
		 target_height_inches = 0.17,
                 min_contest_width_inches = 1.5,
                 min_contest_height_inches = 1.0,
		 min_target_set_height_inches = 0.25,
                 check_for_vertical = True,
                 check_for_horizontal = False,
		 output_directory = "/tmp",
		 #max_target_separation_inches=1.0,
		 diebold = False,
		 diebold_targets = []
                 ):
        self.g = []
        self.im = im
        self.dpi = dpi
	self.filename = filename 
	self.layout_id = layout_id 
	self.precinct = precinct 
        self.out_image = Image.new("L",self.im.size,255)
        self.draw = ImageDraw.Draw(self.out_image)
	self.output_directory = output_directory
	self.as_xml = None
	self.logger = logging.getLogger(__name__)
	self.diebold = diebold
	self.diebold_targets = diebold_targets
        if threshold == 0:
            self.threshold = self.generic_darkened_threshold
        else:
            self.threshold = threshold

        self.ulc_x = ulc_x
        self.ulc_y = ulc_y
        self.urc_x = urc_x
        self.urc_y = urc_y
        self.llc_x = llc_x
        self.llc_y = llc_y
        self.lrc_x = lrc_x
        self.lrc_y = lrc_y

        self.ignore_width = int(ignore_width_inches * dpi)
        self.ignore_right = int(ignore_right_inches * dpi)
        self.ignore_height = int(ignore_height_inches * dpi)
        self.contest_gap = int(contest_gap_inches * dpi)
        self.max_merge_distance = int(max_merge_distance_inches * dpi)
        # minimum and maximum target sizes are specified
        # as fraction of full page image width
        self.min_target_width = int(min_target_width_inches * dpi)
        self.max_target_width = int(max_target_width_inches * dpi)
	self.target_width_inches = float(target_width_inches)
	self.target_height_inches = float(target_height_inches)
	self.target_height = int(target_height_inches * dpi)#for diebold only;
	# (update target_height with calculation during template build)
	self.target_width = int(target_width_inches * dpi) # calculate during template build
        self.min_contest_width = int(min_contest_width_inches * dpi)
        self.min_contest_height = int(min_contest_height_inches * dpi)
        self.min_target_set_height = int(min_target_set_height_inches * dpi)
        
        self.check_for_horizontal = check_for_horizontal
        
        self.targets = []
        self.horiz_target_sets = []
        self.target_sets = []

        self.logger.debug("Landmark offset (%d,%d)." % (
            self.ulc_x,
            self.ulc_y))
        self.logger.debug("Searching for dark lines of length %d to %d" % (
            self.min_target_width,
            self.max_target_width))
        self.logger.debug("Scanning %s (%d dpi image, size %s) for possible vote targets." % (
            self.filename,
            self.dpi,
            self.im.size))

	pdb.set_trace()
        if diebold:
		pass
	else:
		self.g = self.find_candidate_line_segments(diebold=diebold)
        # self.g now has all candidate glyphs; 
	self.logger.debug("Candidate glyphs follow:")
	self.logger.debug(self.g)
        self.logger.debug("Finding potential targets vertically aligned")
        self.find_potential_targets_vert_aligned()
	#print "TARGETS",self.targets
	#print "TARGET_SETS",self.target_sets
	#print "DIEBOLD TARGETS",self.diebold_targets
	#pdb.set_trace()

        min_separation = int(self.dpi*1.1)
        max_separation = int(self.dpi*1.3)
        below = self.dpi
        above = self.dpi
        # group horiz aligned targets if desired
        if self.check_for_horizontal: # 
            self.logger.debug("Grouping horizontally aligned targets into sets.")
            if not diebold:
		    self.find_potential_target_sets_horiz_aligned(
			    min_separation,max_separation,below,above)
	    else:
		    self.find_diebold_target_sets_horiz_aligned(
			    min_separation,max_separation,below,above)
		    #print "HORIZ_TARGET_SETS",self.horiz_target_sets
		    self.logger.debug("DIEBOLD TARGETS %s" % (self.diebold_targets,))

	#print "Putting horiz target sets into log"
        #for index,ts in enumerate(self.horiz_target_sets):
        #    try:
        #        self.logger.debug("%s %s %s" % (index,ts.bbox,ts.expanded_bbox))
        #    except Exception as e:
        #        self.logger.error(e)
        #self.logger.debug("END HORIZ TARGET SETS")

	#print "Trying to group vertically aligned"
        # group the vertically aligned targets
        self.logger.debug("Grouping vertically aligned targets into sets.")
	if diebold:
		self.group_diebold_targets_into_target_sets_vert_aligned()
	else:
		self.group_targets_into_target_sets_vert_aligned()
		self.logger.debug("Merging vertically aligned target sets.")
		if not diebold:
			self.merge_vertical_target_sets()

        # eliminate dups from vertical where possible
        #print "Expand target sets without boundary lines
        # (Worry about implementing after with boundary works)
        #self.expand_target_set_bboxes_wo_lines()

        # generate expanded bboxes to support 
        # further elim of embeds and dups
        self.logger.debug("Expanding bounding boxes to enclosing lines.")
        self.generate_expanded_target_set_bboxes()
	self.eliminate_horizontal_target_sets_not_at_bottom()
        # and further elim embeds and dups
        self.logger.debug("Merging v and h target sets.")
	self.merge_v_and_h_target_sets_post_expansion()
        
        self.logger.debug(
		"Eliminating low area target sets (area below %s squared)" % (
			self.dpi,))
        self.eliminate_target_sets_with_low_area(min_area=(self.dpi*self.dpi))

        for index,ts in enumerate(self.target_sets):
            try:
                self.logger.debug("%s %s %s" % (index,ts.bbox,ts.expanded_bbox))
            except Exception as e:
                self.logger.error(e)
        self.logger.debug("END ALL TARGET SETS")
        self.logger.info("Processing text in %d target sets." % (len(self.target_sets),))

        self.process_all_target_sets_text()

	for ts in self.target_sets:
		try:
			ts.contest_text = ts.contest_text.strip()
		except:
			pass
	template_text = "\n".join(self.template_text_array)
	self.logger.info( "Writing xml template.")
	try:
		f = open("%s/%s.xml" % (self.output_directory,
				  os.path.basename(self.filename),),"w")
		f.write(DTD)

		f.write("""
<BallotSide 
 layout-id='%s' 
 src='%s'
 units='%s' 
 precinct='%s'
 target-height='%04.4f'
 target-width='%04.4f' 
>

<Landmarks ulc-x='%04.4f' ulc-y = '%04.4f'
urc-x='%04.4f' urc-y = '%04.4f'
lrc-x='%04.4f' lrc-y = '%04.4f'
llc-x='%04.4f' llc-y = '%04.4f' >
</Landmarks>

""" % (self.layout_id,
       self.filename,
       "inches",
       self.precinct,
       float(self.target_height)/self.dpi,
       float(self.target_width)/self.dpi,
       float(self.ulc_x)/self.dpi,
       float(self.ulc_y)/self.dpi,
       float(self.urc_x)/self.dpi,
       float(self.urc_y)/self.dpi,
       float(self.lrc_x)/self.dpi,
       float(self.lrc_y)/self.dpi,
       float(self.llc_x)/self.dpi,
       float(self.llc_y)/self.dpi
       ))
	        f.write(template_text)
	        f.write("\n</BallotSide>")
		f.close()
	except Exception as e:
		self.logger.error(e)
	try:
		f = open("%s/%s.xml" % (self.output_directory,
					os.path.basename(self.filename),),"r")
		self.as_xml = f.read()
	except Exception as e :
		self.logger.error("Could not read back template file.")
		self.logger.error(e)
		self.xml = None
	finally:
		f.close()
	self.logger.info( "Writing visual template.")
	self.write_visual_template()


    def draw_vote_boxes_and_text(self,ts):
        """ draw vote information into visual template image """
	dpi = self.dpi
	# we have to add in the ts box upper left corner
	add_x = ts.expanded_bbox[0]
	add_y = ts.expanded_bbox[1]
        for box in ts.template_boxes_array:
            text = box[-1]
            try:
                x1 = box[0]+add_x
		y1 = box[1]+add_y
		x2 = box[2]+add_x
		y2 = box[3]+add_y
                self.draw.rectangle(
			(x1,y1,x2,y2),
			fill=128,
			outline='black')
		textsize = tenthfont.getsize(text)
		text_height = textsize[1]
		width_avail = (ts.expanded_bbox[2]
			       -ts.expanded_bbox[0])/2
		lines_needed = int(textsize[0]/width_avail)
		len_text = len(text)
		if lines_needed <= 1:
                    self.draw.text(
			    (x1+(dpi/30),y1),
			    text,
			    fill='black',
			    font=tenthfont)
		else:
                    end_off = 0
                    for linenum in range(min(lines_needed,3)):
                        try:
                            start_off = end_off
			    text_width = 0
			    end_off = start_off+1
                            while ((text_width < width_avail) 
				   and (end_off < len_text)):
				    
				    text_width = tenthfont.getsize(
					    text[start_off:end_off])[0]
				    end_off += 1
			    if end_off > (len_text-1):
                                end_off = (len_text-1)
			    subtract_x = 0
			    if not ts.targets_left_of_text:
				    subtract_x = tenthfont.getsize(
					    text[start_off:end_off])[0]
			    drawtext_x = box[2] + (dpi/30) - subtract_x 
			    drawtext_y = box[1] 
			    drawtext_y += (int((2/3.)*text_height)*linenum)
			    #print "start_off %d end_off %d text %s,width %d,width avail %d" % (start_off,end_off,text[start_off:end_off],text_width,width_avail)
			    self.draw.text( 
				    (drawtext_x,drawtext_y),
				    text[start_off:end_off],
				    fill='black',
				    font=tenthfont)
			except Exception, pe:
				self.logger.error(pe)

	    except Exception, e:
                    self.logger.error(e)

    def write_visual_template(self):
        """overlay template over original"""	    
        fontpath = "/usr/share/fonts/truetype/freefont/FreeSerif.ttf"
	try:
		tenthfont = ImageFont.truetype(fontpath,int(self.dpi/10))
	except Exception, e:
		tenthfont = ImageFont.load_default()
	# draw contest layer
	for index,ts in enumerate(self.target_sets):
	    self.logger.info("Contest %s %s %s" %(index,
						  ts.bbox,
						  ts.expanded_bbox))
	    self.draw.rectangle(ts.bbox,fill=200,outline=0)
	    try:
		indent_rectangle = int(self.dpi/30)
		self.draw.rectangle(
		    [ts.expanded_bbox[0]+indent_rectangle,
		     ts.expanded_bbox[1]+indent_rectangle,
		     ts.expanded_bbox[2]-indent_rectangle,
		     ts.expanded_bbox[3]-indent_rectangle],
		    fill = 224,
		    outline=0
		    )
		if ts.contest_text is not None:
		    textheight = (2/3.)*tenthfont.getsize(
			    ts.contest_text)[1]
		    width_avail = (ts.expanded_bbox[2]-ts.expanded_bbox[0])/2
		    for index,segment in enumerate(ts.contest_text.split("/")):
			    self.draw.text(
			    (ts.expanded_bbox[0]+20,
					    ts.expanded_bbox[1]+20
					    +(textheight*index)
					    ),
			    segment,
			    fill='black',
			    font=tenthfont
			    )
	    except Exception as e1:
		self.logger.error(e1)
		pass
	    # draw vote layer
	    self.draw_vote_boxes_and_text(ts)
	blended = Image.blend(self.out_image,self.im,.2)
	blended.save("%s/b_%s" % (self.output_directory,
				  os.path.basename(self.filename),))


    def find_candidate_arrows_NYI(self,separation = 0.2):
        """find paired darkened line segments in acceptable width range

	We look for lines that could be components of arrows with either
	of the following appearances (filled or unfilled):

	<---  ---<
	<--------<
	
	The first and second segments, if separated, must each be at least
	n pixels; the total length must not exceed m pixels.
	"""
	print "find_candidate_arrows_NYI"


    def find_candidate_line_segments(self,diebold=False):
        """find darkened line segments in acceptable width range

	restricting to double line segments spaced by .12" if diebold
	"""
        width = self.im.size[0]
        height = self.im.size[1]
        dpi = self.dpi

	target_height = self.target_height

        min_width = self.min_target_width
        max_width = self.max_target_width
        data = self.im.getdata()
        # start 10 scan lines down and end 10 scan lines from end
        skip = int((dpi/30)*width)
        linenumber = 0
        g = []
        contig = 0
	move_down_by = 0
	print "Starting search"
        for counter in range(skip, len(data) - skip - (self.target_height * width)):
            new_line = False
            passed_width = counter % width
            if (passed_width) == 0:
                # clear any line-related counters
                new_line = True
                contig = 0
                linenumber += 1
                if (linenumber % 500)==0: 
                    self.logger.info("Scanned %d lines, got %d candidate line segments." % (
                        linenumber, 
                        len(g)
                        ))
		    print "Searching for vote targets... line %d of %d" % (
			    linenumber,
			    height)
	    if counter < (self.ignore_height * width):
		    continue
            if passed_width < self.ignore_width:
		    continue
            if passed_width > (width - self.ignore_width):
		    continue
            coltop_is_dark, move_top_down_by = column_lt_threshold(
                data,
                counter + (move_down_by*width),
                width,
                int(dpi/60),# changed from dpi/60 928am 2/26
                threshold=self.generic_darkened_threshold)
	    # only diebold checks for double line segment;
	    # for others, we accept single lines and so don't test
	    # for a second dark zone at a fixed offset beneath first
	    if not diebold:
		    colbot_is_dark = True
		    move_bot_down_by = 0
	    else:
		    colbot_is_dark, move_bot_down_by = column_lt_threshold(
			    data,
			    counter + (move_down_by*width) + (self.target_height*width),
			    width,
			    int(dpi/60),# changed from dpi/60 928am 2/26
			    threshold=self.generic_darkened_threshold)
	    if move_down_by > int(dpi/60):
		    move_down_by = int(dpi/60)
            if coltop_is_dark and colbot_is_dark:
                contig = contig + 1
	    # three conditions to satisfy to add line to candidate set:
	    # dark pixel, 
	    # light pixel nearby, and
	    # if diebold, dark pixel below
            elif contig > min_width and contig < max_width:
                # only accept as a candidate if there is a light pixel
                # within 1/50" directly above or below
                if column_gt_threshold(
                    data,
                    counter-width,
                    -width,
                    int(dpi/50),
                    threshold=self.generic_darkened_threshold):
			g.append(((counter%width),
				  (counter/width),
				  contig))
			# diebold checks for double line segment
			if self.diebold:
				g.append(((counter%width),
					  (counter/width)+target_height,
					  contig))
			contig = 0
			move_down_by = 0
            else:
                contig = 0
		move_down_by = 0

            if len(g)>5000:break
        return g

    def find_diebold_target_sets_horiz_aligned(self,
                                             min_separation,
                                             max_separation,
                                             below,
                                             above):
	    # using the diebold targets, build target sets 
	    # using same rules as in find_potential..."
	    yoffset_dictionary = {}
	    for target in self.diebold_targets:
		    #print target
		    yoffset_div10 = target[1]/10
		    if yoffset_div10 not in yoffset_dictionary:
			    yoffset_dictionary[yoffset_div10] = []
		    yoffset_dictionary[yoffset_div10].append(
			    # 50 will come out once we
			    # no longer need to mimic old method
			    (target[0]+50,
			     target[1],
			     50))

	    keys = yoffset_dictionary.keys()
	    keys.sort()
            # we use a dictionary to prevent dups
	    self.horiz_pairs = {}
	    for k in keys:
		# for multiple glyphs sharing a y offset,
		# check to see if their x values represent
		# a sensible spacing, where sensible is
		# initially defined as more than 1/10 but less than 1/3
		# of the full image width
		if len(yoffset_dictionary[k]) <= 1 :continue
		glyphs = yoffset_dictionary[k]
		for g1 in glyphs:
			x1 = g1[0]
			y1 = g1[1]
			for g2 in glyphs:
				matched = False
				x2 = g2[0]
				y2 = g2[1]
				if (
					((x2 - x1) > min_separation) 
					and ((x2 - x1) < max_separation) ):
					if not ((x1/10,k,x2/10,k) in self.horiz_pairs):
						self.horiz_pairs[(x1/10,k,x2/10,k)]=True
						t1 = Target(x1,y1,x1+1,y1+1)
						t2 = Target(x2,y2,x2+1,y2+1)
						ts = TargetSet(t1,self.im,orientation="H",dpi=self.dpi)
						ts.append(t2)
						self.horiz_target_sets.append(ts)
						# we only handle horizontal layouts of two
						matched = True
						break
			if matched: 
				continue
	    keys = self.horiz_pairs.keys()
	    keys.sort(key = lambda a: (a[1]*1000)+a[0])
	    self.logger.debug("Length of horiz_pairs %d" % (len(keys)))
	    self.logger.debug("Length of horiz_target_sets %d" % (
			    len(self.horiz_target_sets)))
		    
    def find_potential_target_sets_horiz_aligned(self,
                                             min_separation,
                                             max_separation,
                                             below,
                                             above):
        """rescan glyphs looking for horizontal alignments

        Likely targets may also come as horizontally aligned
        glyphs in addition to vertically aligned, so check
        for targets with close y value and x value with
        likely horizontal separation (between 1/3 and 1/10
        of image width.
        """
        # do up a dictionary of how many glyphs begin at each 
        # begin at each horizontal offset / 10.
        yoffset_dictionary = {}
        for g in self.g:
            if g[1] < below: continue
            if (self.im.size[0]- g[1]) < above: continue
            yoffset_div10 = g[1]/10
            if yoffset_div10 in yoffset_dictionary:
                yoffset_dictionary[yoffset_div10].append((g[0],g[1],g[2]))
            else:
                yoffset_dictionary[yoffset_div10] = []
        keys = yoffset_dictionary.keys()
        keys.sort()
        # we use a dictionary to prevent dups
        self.horiz_pairs = {}
        for k in keys:
            # for multiple glyphs sharing a y offset,
            # check to see if their x values represent
            # a sensible spacing, where sensible is
            # initially defined as more than 1/10 but less than 1/3
            # of the full image width
            if len(yoffset_dictionary[k]) > 1 :
                glyphs = yoffset_dictionary[k]
                for g1 in glyphs:
                    x1 = g1[0]
		    y1 = g1[1]
                    for g2 in glyphs:
                        matched = False
                        x2 = g2[0]
			y2 = g2[1]
                        if (
                            ((x2 - x1) > min_separation) 
                            and ((x2 - x1) < max_separation) ):
                            if not ((x1/10,k,x2/10,k) in self.horiz_pairs):
                                self.horiz_pairs[(x1/10,k,x2/10,k)]=True
                                t1 = Target(x1,y1,x1+1,y1+1)
                                t2 = Target(x2,y2,x2+1,y2+1)
                                ts = TargetSet(t1,self.im,orientation="H",dpi=self.dpi)
                                ts.append(t2)
                                self.horiz_target_sets.append(ts)
                                # we only handle horizontal layouts of two
                                matched = True
                                break
                    if matched: 
                        continue
        keys = self.horiz_pairs.keys()
        keys.sort(key = lambda a: (a[1]*1000)+a[0])
        self.logger.debug("Length of horiz_pairs %d" % (len(keys)))
        self.logger.debug("Length of horiz_target_sets %d" % (
		len(self.horiz_target_sets)))

    def find_potential_targets_vert_aligned(self):
        """sort out likely targets from candidate line segments and store in self.targets

        Assume likely targets will come in batches of more than four
        candidate scan line segments (glyphs) having x values in the
        same or adjacent ranges of 10 
        """
        # do up a dictionary of how many glyphs begin at each 
        # begin at each horizontal offset / 10.
        xoffset_dictionary = {}
	last_y = 0
	if self.diebold:
		#print "Diebold, finding targets forming vertical target sets."
		search_array = self.diebold_targets
        else:
		search_array = self.g
	#print "Dividing into columns of 10 pixels"
        for x in search_array:
            xoffset_div10 = x[0]/10
	    #if hart:
	    # hart targets are 1/6" tall
	    # test for 1/6" difference from last; if found, append both
	    # not impl.
            if xoffset_div10 not in xoffset_dictionary:
                xoffset_dictionary[xoffset_div10] = []
	    try:
		    xoffset_dictionary[xoffset_div10].append((x[1],x[2])) 
	    except:
		    xoffset_dictionary[xoffset_div10].append((x[1],40)) # remove 40!!!
		    
	#print "Done loading xoffset_dictionary"
        keys = xoffset_dictionary.keys()
        keys.sort()
        glyph_serial = 0
	if self.diebold:
		minimum_hits = 2
	else:
		minimum_hits = 4
        for k in keys:
            # extend the entry in xoffset dictionary 
            # with the entries
            # under the key value (x_offset/10) plus 1
            # to catch situations where the entries
            # cross a 10 pixel boundary
            try:
                extend_by = len(xoffset_dictionary[k+1])
            except:
                extend_by = 0

            if (extend_by+len(xoffset_dictionary[k])) >= minimum_hits:
                # find the mean contig length and report if at least
                # half of the values have less than 20% variation from 
                # the mean
                contig_sum = 0
                mylist = xoffset_dictionary[k]
                try:
                    mylist.extend(xoffset_dictionary[k+1])
                except:
                    pass
                collapsed = []
                # sort based on y offsets, collapse contig zones to one entry
                mylist.sort(key=lambda a: a[0])
                last_y = 0
                for item in mylist:
                    if abs(item[0]-last_y)>1:
                        collapsed.append(item)
                    last_y = item[0]
                collapsed.sort(key=lambda a: a[1])
                median = collapsed[len(collapsed)/2][1]
                close_to_median = 0
                for item in collapsed:
                    if item[1] >= (median *.67) and item[1] <= (median * 1.5):
                        close_to_median += 1
                if close_to_median >= len(collapsed)/2:
                    last_y = 0
                    collapsed.sort(key=lambda a: a[0])
		    print k,"Mylist",mylist
		    print "K %d Collapsed, sorted %s" % (k,collapsed)
                    for item in collapsed:
                        self.targets.append((k*10,item[0],item[1]))
                        glyph_serial += 1
			# simulate the upper and lower lines of the target
                        if self.diebold: 
				#print "Appending target"
				self.targets.append(
					(k*10,
					 item[0]+(self.dpi/10),
					 item[1])
					)
				glyph_serial += 1


    def add_target_set(self,new_list):
	    self.target_sets.append(
		    TargetSet(
			    Target(new_list[0][0],
				   new_list[0][1],
				   new_list[0][0]+self.dpi/4,
				   new_list[0][1]+self.dpi/8),
			    self.im,
			    self.dpi
			    )
		    )
	    for item in new_list[1:]:
		    self.target_sets[-1].marks.append(
			    Target(item[0],
				   item[1],
				   item[0]+self.dpi/4,
				   item[1]+self.dpi/8)
			    )

    def group_diebold_targets_into_target_sets_vert_aligned(self):
	    grouping_by_x = {}
	    for item in self.diebold_targets:
		    appended = False
		    for key in grouping_by_x.keys():
			    if abs(key-item[0])<15:
				    grouping_by_x[key].append(item)
				    appended = True
				    break
		    if not appended:
			    grouping_by_x[item[0]] = [item]
	    x_keys = grouping_by_x.keys()
	    x_keys.sort()
	    for key in x_keys:
		    grouping_by_x[key].sort(key=lambda x: x[1])
		    #print key, grouping_by_x[key]
		    # go through each set of keys, 
		    # and form a target set from elements in a list
		    # that are within dpi of other elements;
		    # breaking every time there is a gap of >dpi
		    #print key
		    current_list = grouping_by_x[key]
		    new_list = []
		    for item_offset in range(len(current_list)-1):
			    ydiff = abs(current_list[item_offset+1][1]
				     -current_list[item_offset][1])
			    # if the next item is close to this one,
			    # create a new list with the next item and this
			    if ydiff < self.dpi:
				    # but only append the current item if it's
				    # not already the last item in the new list
				    if (len(new_list)==0 
					or new_list[-1][1]!=current_list[item_offset][1]):
					    new_list.append(current_list[item_offset])
				    new_list.append(current_list[item_offset+1])
			    # otherwise, build a target set and reset the list
			    # is in the new list
			    elif len(new_list)>0:
				    self.add_target_set(new_list)
				    new_list = []
		    if len(new_list)>0:
			    self.add_target_set(new_list)
			    new_list = []

    def group_targets_into_target_sets_vert_aligned(self):
        """Given a target candidate list of (x,y,width) triplets, group them."""
        # Subdivide into groups by x
        grouping_by_x = {}
        for item in self.targets:
            if item[0] in grouping_by_x:
                grouping_by_x[item[0]].append(item)
            else:
                grouping_by_x[item[0]] = [item]
        x_keys = grouping_by_x.keys()
        x_keys.sort()
        # for each group by x, sort by y and determine gaps
        last_x = 0
        for x in x_keys:
            group = [(0,0,0)]
            group.extend(grouping_by_x[x])
            group.sort(key=lambda a:a[1])
            gaps = []
            last_break_bottom = 0
            for index in range(len(group)):
                try:
                    gap_to_next = group[index+1][1]-group[index][1]
                except IndexError:
                    gap_to_next = 10000
                gaps.append(gap_to_next)
                if gap_to_next > self.contest_gap:
                    self.target_sets.append(
                        TargetSet(
                            Target(x,
                                   group[last_break_bottom][1],
                                   x+group[last_break_bottom][2],
                                   group[index][1]),
                            image=self.im,
                            dpi = self.dpi
                            )
                        )
                    self.target_sets[-1].marks.extend(
                        # create a new target with x and the two y vals
                        # for each element in the list's zone
                        map(lambda a: Target(a[0],a[1],a[0]+a[2],y2=0),
                            group[last_break_bottom:index])
                        )
                    last_break_bottom = index+1
            last_x = x


    def merge_vertical_target_sets(self):
        """Remove inappropriate bboxes, merge the remainder."""

        # first remove the boxes with zero y offsets
        self.logger.debug("Orig target sets %s" % (self.target_sets,))
        merged_list = []
        self.target_sets = filter(lambda a: a.bbox[1]>0,
                                          self.target_sets)

        # then see about merging boxes with near x's and y's
        # go through list looking for near matches; when found,
        # append bounding box enclosing both near matches to merged_list; 
        # for unmatched, just append the original
        ignore_list = []
        for index1,b1 in enumerate(self.target_sets):
            if index1 in ignore_list: continue
            found_match = False
            for index2,b2 in enumerate(self.target_sets):
                if index2 in ignore_list: continue
                if index2 <= index1: continue
                # we may have added index1 to the list in this loop
                if index1 in ignore_list: continue
                if ( (abs(b1.bbox[0]-b2.bbox[0]) < self.max_merge_distance)
                     and (abs(b1.bbox[1]-b2.bbox[1]) < self.max_merge_distance)
                     ):
                    merged_list.append(
                        TargetSet(
                            Target(min(b1.bbox[0],b2.bbox[0]),
                                   min(b1.bbox[1],b2.bbox[1]),
                                   max(b1.bbox[2],b2.bbox[2]),
                                   max(b1.bbox[3],b2.bbox[3])
                                   ),
                            image=self.im,
                            dpi = self.dpi
                            )
                        )
                    merged_list[-1].marks.extend(b1.marks)
                    merged_list[-1].marks.extend(b2.marks)
                    found_match = True
                    ignore_list.append(index1)
                    ignore_list.append(index2)
                    break
            if (not found_match) and (not index1 in ignore_list):
                merged_list.append(b1)
            ignore_list.append(index1)
        self.logger.debug("Merged targ bboxes %s" % (merged_list,))
        # remove short boxes
        newlist = []
        for index,ts in enumerate(merged_list):
            # vertically aligned contest targets 
            # must span min_target_set_height vertically
            if abs(ts.bbox[3]-ts.bbox[1]) >= self.min_target_set_height:
                ts.expanded_bbox = ts.bbox
                newlist.append(ts)
	    else: self.logger.info( "Removed short target set %s" % (ts,))
        self.target_sets = newlist


    def eliminate_horizontal_target_sets_not_at_bottom(self):
	    self.horiz_target_sets = filter(
				    lambda a: a.bbox[1] > (a.expanded_bbox[3] - (self.dpi/2)),
					    self.horiz_target_sets)
	    for index,ts in enumerate(self.horiz_target_sets):
		    bottom_y = ts.expanded_bbox[3]

    def merge_v_and_h_target_sets_post_expansion(self):
        # remove target sets if their expanded bbox is within
        # the expanded bbox of another box
        newlist = []
	# DISABLE HANDLING OF HORIZONTAL TARGET SETS
        #self.target_sets.extend(self.horiz_target_sets)
        for index1,ts1 in enumerate(self.target_sets):
            matched = False
            if ts1.expanded_bbox is None:
                continue
            ebb1 = list(ts1.expanded_bbox)
            for index2,ts2 in enumerate(self.target_sets):
                if index2 <= index1:
                    continue
                if ts2.expanded_bbox is None:
                    continue
                ebb2 = list(ts2.expanded_bbox)
                if ( (ebb1[0]>=ebb2[0]
                      and (ebb1[1] >= ebb2[1])
                      and (ebb1[2] <= ebb2[2])
                      and (ebb1[3] <= ebb2[3])) ):
                    matched = True
                    # because of match, merge bboxes of ts1 and ts2
                    ts1.bbox = [min(ts1.bbox[0],ts2.bbox[0]),
                                min(ts1.bbox[1],ts2.bbox[1]),
                                max(ts1.bbox[2],ts2.bbox[2]),
                                max(ts1.bbox[3],ts2.bbox[3])]
                    ts2.bbox = [min(ts1.bbox[0],ts2.bbox[0]),
                                min(ts1.bbox[1],ts2.bbox[1]),
                                max(ts1.bbox[2],ts2.bbox[2]),
                                max(ts1.bbox[3],ts2.bbox[3])]
                    break
            for ts2 in newlist:
                if ts2.expanded_bbox is None:
                    continue
                ebb2 = list(ts2.expanded_bbox)
                if ( (ebb1[0]>=ebb2[0]
                      and (ebb1[1] >= ebb2[1])
                      and (ebb1[2] <= ebb2[2])
                      and (ebb1[3] <= ebb2[3])) ):
                    matched = True
                    # because of match, merge bboxes of ts1 and ts2
                    ts1.bbox = [min(ts1.bbox[0],ts2.bbox[0]),
                                min(ts1.bbox[1],ts2.bbox[1]),
                                max(ts1.bbox[2],ts2.bbox[2]),
                                max(ts1.bbox[3],ts2.bbox[3])]
                    ts2.bbox = [min(ts1.bbox[0],ts2.bbox[0]),
                                min(ts1.bbox[1],ts2.bbox[1]),
                                max(ts1.bbox[2],ts2.bbox[2]),
                                max(ts1.bbox[3],ts2.bbox[3])]
                    break
            if not matched:
                newlist.append(ts1)
        self.logger.debug("Target sets post merge and removal \
of embedded or dup expanded bboxes %s" % (newlist,))
        self.target_sets = newlist

    def generate_expanded_target_set_bboxes(self):
        """identify enclosing contest bounding box for each set of targets

        Initial method is to search outwards for enclosing lines; however,
        if enclosing lines are not found, we should consider using a midpoint
        between bounding boxes in the same vertical column... probably
        by dividing at points about 1/4" below the last point in a bbox. 
        """
        
        outcounter = 0
        # NB we will need to check for and toss duplicates, and toss small.
        for ts in self.horiz_target_sets:
            # Warning: the dpi/6 in the searches for vertical lines will work
            # with diebold targets at a height of .12, but may trigger early
            # on taller targets or text from other vendors.
            try:
                ts.left_line = ts.find_left_line(min_line_height=ts.dpi/6)
                ts.right_line = ts.find_right_line(min_line_height=ts.dpi/6)
                ts.top_line = ts.find_top_line(min_line_width=ts.dpi)
                ts.bottom_line = ts.find_bottom_line(min_line_width=ts.dpi/2)
            except Exception, e:
                self.logger.debug(e)
	    # NB if ts.top_line is too close to existing bbox top y,
	    # we probably need to use material between our bbox and
	    # the prior bbox or top of column -- not yet implemented
            ts.expanded_bbox = (ts.left_line,
                                ts.top_line,
                                ts.right_line,
                                ts.bottom_line)

            self.logger.debug( "Horiz ts %s %s %s" % (outcounter, 
						      ts.bbox,
						      ts.expanded_bbox))
            outcounter += 1
        for ts in self.target_sets:
            try:
                ts.left_line = ts.find_left_line(min_line_height=ts.dpi/3)
                ts.right_line = ts.find_right_line(min_line_height=ts.dpi/3)
            except Exception as e:
                self.logger.error(e)
            ts.targets_left_of_text = ( 
                (ts.bbox[0] - ts.left_line) 
                < (ts.right_line - ts.bbox[0])
                   )
            try:
                # if 
                targets_at_right = not ts.targets_left_of_text
                ts.top_line = ts.find_top_line(
                    min_line_width=ts.dpi,
                    search_leftwards=targets_at_right)
                ts.bottom_line = ts.find_bottom_line(
                    min_line_width=ts.dpi/2,
                    search_leftwards=targets_at_right)
            except Exception as e:
                self.logger.debug(e)

	    if (ts.top_line + (ts.dpi/5)) > ts.bbox[1]:
		    if ts.top_line > ts.dpi:
			    ts.top_line -= (2*ts.dpi/3)
            if (ts.left_line is None 
                or ts.right_line is None 
                or ts.top_line is None 
                or ts.bottom_line is None):
                self.logger.info("Skipping where could not find left/top/right/bottom")
                self.logger.info("%s %s %s %s %s" % (
			ts.bbox,
			ts.left_line,ts.top_line,ts.right_line,ts.bottom_line))
                continue

            if (ts.left_line >= (ts.right_line - (self.min_contest_width)) ):
                self.logger.debug("Width below min: %s %s %s %s %s %s" % (
			self.min_contest_width,
			ts.bbox,
			ts.left_line,ts.top_line,ts.right_line,ts.bottom_line))
                continue

            if (ts.top_line >= (ts.bottom_line - (self.min_contest_height)) ):
                self.logger.debug("Height below min: %s %s %s %s" % (
			self.min_contest_height,
			ts.bbox,
			ts.top_line,ts.bottom_line))
                continue

            
            ts.expanded_bbox = (ts.left_line,
                                ts.top_line,
                                ts.right_line,
                                ts.bottom_line)
            
            outcounter += 1

    def eliminate_target_sets_with_low_area(self,min_area=0):
        if min_area == 0:
            min_area = self.dpi*self.dpi
        self.target_sets = filter(
            lambda ts: ((ts.expanded_bbox[2]-ts.expanded_bbox[0]) 
                        * (ts.expanded_bbox[3]-ts.expanded_bbox[1]) ) >= min_area, self.target_sets
            )

    def process_all_target_sets_text(self):
        outcounter = 0
        self.template_text_array = []
        self.template_boxes_array = []
        
        for ts in self.target_sets:
            try:
                self.template_text_array.append(
                    self.process_ts_for_text(ts,outcounter)
                    )
                self.template_boxes_array.append(
                    ts.template_boxes_array
                    )
            except Exception as e:
                self.logger.error("Failed to save /tmp/ebb %d %s" % ( 
			outcounter,
			e))
            outcounter += 1
        return self.template_text_array

    def process_horizontal_target_set(self,ts,include_pixels_above_targets):
        targetlines = []
        trim = 2
        ts.zone_with_targets_text = ts.im.crop(
            (ts.bbox[0]+trim,
             ts.bbox[1]-include_pixels_above_targets, 
             ts.expanded_bbox[2]-trim,
             ts.expanded_bbox[3])
        )
        ts.marks.sort(key=lambda a: a.x)
        for offset in range(len(ts.marks)):
            lower_x = ts.marks[offset].x
	    # advance off of target mark until no black,
	    # dummied for now as + .1 inch
	    text_lower_x = lower_x + int(self.dpi*.1)
            text_higher_x = text_lower_x + 1
	    # backup from target mark until no black,
	    # dummied for now as - .17 inch
	    mark_lower_x = lower_x - int(self.dpi * .17)
            try:
                ts.marks[offset+1]
                text_higher_x = ts.marks[offset+1].x
		# backup from target mark until no black,
		# dummied for now as - 0.2 inch
		text_higher_x -= int(self.dpi*.2)
            except:
                text_higher_x = int(ts.expanded_bbox[2])
            if ( (text_higher_x - text_lower_x) 
                 > ((ts.bbox[2]-ts.bbox[0])/4) ):
		tscrop = ts.im.crop(
			(text_lower_x,
                                ts.bbox[1]-include_pixels_above_targets,
                                text_higher_x,
                                ts.expanded_bbox[3])
			)
                tstext = tess_and_clean(tscrop)
		# add 1/60" trim, because we trigger when lines 1/60 below us match
		x1 = mark_lower_x - ts.expanded_bbox[0]
		y1 = ts.bbox[1] - ts.expanded_bbox[1]
		x2 = x1 + int(.25 * self.dpi)
		y2 = y1 + self.target_height + int(self.dpi/60)
		tsline = Line(tscrop,ts.dpi,x1,y1,x2,y2,text=tstext)
                #tsline = Line(tscrop,
                #              ts.dpi,
                #              mark_lower_x, #x1
		#	       # target width dummied as .3 inch
                #              ts.bbox[1], #y1
                #              mark_lower_x + int(.25 * self.dpi),#x2
                #              ts.bbox[1]+int(self.dpi/60)+self.target_height,#y2
                #              text=tstext)
                targetlines.append(tsline)
        return targetlines

    def process_vertical_target_set(self,ts,trim):
        """process vertically aligned target sets"""
        include_pixels_above_targets = (self.dpi/10)
        ts.gap_after_targets = ts.find_gap_after_targets()
        if ts.targets_left_of_text:
            text_croplist = (ts.gap_after_targets,
                             ts.bbox[1]-include_pixels_above_targets, 
                             ts.expanded_bbox[2]-trim,
                             ts.expanded_bbox[3])
	    target_croplist = (ts.expanded_bbox[0],
                               ts.bbox[1]-include_pixels_above_targets,
                               ts.gap_after_targets,
                               ts.expanded_bbox[3])
            ts.zone_with_targets_text = ts.im.crop(
                text_croplist
                )
            ts.zone_of_targets_only = ts.im.crop(
                target_croplist
                )
        else:
            ts.gap_before_targets = ts.find_gap_before_targets()
            ts.bbox[0] = ts.gap_before_targets
            text_croplist = (
                ts.expanded_bbox[0]+trim,
                ts.bbox[1]-include_pixels_above_targets, 
                ts.bbox[0]-trim,
                ts.expanded_bbox[3]-trim
                )
            must_exceed_trim_in_targets_and_text = 3
            target_croplist = (
                ts.gap_before_targets-must_exceed_trim_in_targets_and_text,
                ts.bbox[1]-include_pixels_above_targets,
                ts.gap_after_targets+must_exceed_trim_in_targets_and_text,
                ts.expanded_bbox[3]
                )
            ts.zone_with_targets_text = ts.im.crop(
                text_croplist
                )
            ts.zone_of_targets_only = ts.im.crop(target_croplist)
        target_zone_y_start = (ts.zone_above_targets.size[1] 
                               - include_pixels_above_targets)
        if ts.targets_left_of_text:
            target_zone_x_end = ts.zone_of_targets_only.size[0]
            target_zone_x_start = get_x_offset_of_targets(
                ts.zone_of_targets_only,threshold=192)
	    if target_zone_x_start == 0:
		    self.logger.error("Target zone starting at zero x offset, highly unlikely!")
        else:
            target_zone_x_start = ts.bbox[0] - ts.expanded_bbox[0]
            target_zone_x_end = target_zone_x_start + ts.zone_of_targets_only.size[0]
        self.logger.debug("Vertical target set text %s targets %s" % (
			text_croplist,
			target_croplist))
        return target_zone_x_start, target_zone_y_start, target_zone_x_end

    def process_ts_for_text(self,ts,outcounter):
        """Associate a target set's targets with text lines."""
        self.logger.debug("Processing text in ts %d" % (outcounter,))
        ts.template_text_array = [] 
        ts.template_boxes_array = []
        trim = (self.dpi/150)
        #ts.expanded_bbox_image = ts.im.crop(ts.expanded_bbox) 
        #ts.expanded_bbox_image.save("/tmp/ebb%d.jpg" % (outcounter,))
        ts.zone_above_targets = ts.im.crop(
            (ts.expanded_bbox[0]+trim,
             ts.expanded_bbox[1]+trim,
             ts.expanded_bbox[2]-trim,
             ts.bbox[1]-trim)
        )
        ts.contest_text = tess_and_clean(ts.zone_above_targets)
	#
	# split the zone into lines separated by white space
	split_ys = split_at_white_horiz_line(ts.zone_above_targets)
	# 
	# then, for each line, get and append a text code
	contest_text_code = ""
	lastsplit = 0
	for split in split_ys:
		if split > (lastsplit+1):
			if split < (ts.zone_above_targets.size[1] - 1):
				split = split + 1
			line = ts.zone_above_targets.crop(
				(0,
				 lastsplit,
				 ts.zone_above_targets.size[0],
				 split)
				)
			this_code = text_code(line)
			
			if len(this_code)>1:
				contest_text_code = "%s %s" % (
					contest_text_code,
					this_code
					)
			lastsplit = split
	# and assemble into a single text code
        h_include_pixels_above_targets = int(self.dpi/20)
        targetlines = []
        keys = []
        if ts.orientation == "H":
            targetlines = self.process_horizontal_target_set(ts,h_include_pixels_above_targets)
	    for targetline in targetlines:
		    self.logger.debug("target set %s" % (ts,))
		    self.logger.debug("target line x1 %d y1 %d x2 %d y2 %d" %
				      (targetline.x1,targetline.y1,
				       targetline.x2,targetline.y2))
		    ts.template_boxes_array.append(
                (
                    targetline.x1, 
                    targetline.y1,
		    targetline.x2,
		    targetline.y2,
                    targetline.text)
                )

        else:
            (target_zone_x_start,
             target_zone_y_start,
             target_zone_x_end) = self.process_vertical_target_set(ts,trim)
            tt,tc = target_and_text_from_images(
		    ts.zone_of_targets_only,
		    ts.zone_with_targets_text,
		    debug=False
		    )
            keys = tt.keys()
            keys.sort()

	box_x1 = float(ts.expanded_bbox[0])/self.dpi
	box_y1 = float(ts.expanded_bbox[1])/self.dpi
	box_x2 = float(ts.expanded_bbox[2])/self.dpi
	box_y2 = float(ts.expanded_bbox[3])/self.dpi

        ts.template_text_array.append(
            "<Box x1='%02.4f' y1='%02.4f' x2='%02.4f' y2='%02.4f' \n text='%s'\n  text-code='%s'\n  >" % (
			box_x1, box_y1, box_x2, box_y2,
			ts.contest_text[0:80].strip(),
			contest_text_code[0:80].strip()))
        for k in keys:
            # ALL VOTES ARE REPORTED RELATIVE TO THE ENCLOSING CONTEST BOX
            #eliminate keys that are less than 1/16" tall 
            #(typically write-in line segments invading target column)
            if abs(k[1]-k[0]) <= (self.dpi/16):
		    continue


            textlines = "\n   ".join(map(lambda a: a[2],tt[k]))
	    textcodelines = ""
	    # investigate why we have single codes nested in lists,
	    # clean up !!!
	    for textcodeline in tc[k]:
		    textcodelines = "%s %s" % (textcodelines,textcodeline[0])

            ts.template_boxes_array.append(
                (
                    target_zone_x_start,# + ts.expanded_bbox[0], 
                    k[0]  + target_zone_y_start,# + ts.expanded_bbox[1],
                    target_zone_x_end,# + ts.expanded_bbox[0], 
                    k[1] + target_zone_y_start,#,+ ts.expanded_bbox[1] 
                    textlines)
                )

	    vote_x1 = float(target_zone_x_start)/self.dpi
	    vote_y1 = float(k[0]+target_zone_y_start)/self.dpi
	    vote_x2 = vote_x1 + self.target_width_inches#float(target_zone_x_end + ts.expanded_bbox[0])/self.dpi
	    vote_y2 = vote_y1 + self.target_height_inches#float(k[1] + target_zone_y_start)/self.dpi

            ts.template_text_array.append(
                "  <Vote orient='%s' x1='%02.4f' y1='%02.4f' x2='%02.4f' y2='%02.4f' \n   text='%s' text-code='%s'>\n  </Vote>" % (
			    ts.orientation,
			    vote_x1, 
			    vote_y1,
			    vote_x2,
			    vote_y2,
			    textlines.strip(),
			    textcodelines.strip()))
                    
        for targetline in targetlines: 
            vote_x1 = float(targetline.x1)/self.dpi
	    vote_y1 = float(targetline.y1)/self.dpi
	    vote_x2 = float(targetline.x2)/self.dpi
	    vote_y2 = float(targetline.y2)/self.dpi
            ts.template_text_array.append(
                "  <Vote orient='%s' x1='%02.4f' y1='%02.4f' x2='%02.4f' y2='%02.4f'\n   text='%s' />" 
                    % (ts.orientation,
		       vote_x1,
		       vote_y1,
		       vote_x2,
		       vote_y2,
                       targetline.text.replace("\n","   \n")))
        ts.template_text_array.append("</Box>")
        return "\n".join(ts.template_text_array)

    def expand_target_set_bboxes_wo_lines(self):
        """identify enclosing contest bounding box for each set of targets

        If enclosing lines are not found, we divide target sets sharing
        a vertical column by dividing an expanded bbox at points about 
        1/4" below the last point in a target set bbox. 
        """
        """
        # Then, get widths of remaining target sets
        widths = []
        for index,ts in enumerate(self.target_sets):
            widths.append(ts.bbox[2]-ts.bbox[0])
            print index,ts.bbox,"Width",widths[-1]
        widths.sort()
        total_width = reduce(lambda a,b: a+b, widths)
        avg_width = total_width / len(self.target_sets)
        med_width = widths[len(widths)/2]
        print "Avg width",avg_width,"Med width",med_width

        # and remove those which are narrower than median and average
        newlist = []
        for index,ts in enumerate(self.target_sets):
            if abs(ts.bbox[2]-ts.bbox[0]) >= min(avg_width,med_width):
                #!!!
                ts.extended_bbox = ts.bbox
                #!!! Need to generate extended bbox's properly
                newlist.append(ts)
        print "Ts count pre removal of narrow",len(self.target_sets)
        print "Post removal of narrow",len(newlist)
        self.target_sets = newlist
        To generate the expanded bboxes, try the following:

        For sanity, no set should overlap another; if it does, see if they are dups.
        
        Bottoms should generally be 1/4 or 1/2" below last vote target of prior set in row;
        if no prior set in row, use remaining height of row.

        Tops should generally be the bottom of the prior set in row.  
        If no prior set in row, use 1" to 2" of material above, or look for line breaks
        and use first set of lines.

        Left and right can be determined as follows.  

        Compare distance of leftmost target set from 0 to distance of rightmost target set
        from im.size[0] (width of image).  If leftmost target set is closer to wall than
        rightmost, assume target sets are to left of textual descriptions, and set left
        to the left edge of the target set (perhaps minus a target width).  Otherwise,
        do the same with right and the right edge of the target set.

        If targets at left (see prev paragraph), right for column n is left of column n+1.
        If targets at right (see prev paragraph), left for column n is right of column n-1
        """


    def __repr__(self):
	    if self.as_xml is not None:
		    return self.as_xml
	    else:
		    return "Sorry."

if __name__ == "__main__":
    usage = "Usage: python glyph_hunter.py filename dpi landmarkx landmarky min_target_width_inches max_target_width_inches" 
    if len(sys.argv) < 7:
        print usage 
	sys.exit(0)
    logging.basicConfig(filename='template_builder.log',
                    format = '%(asctime)s %(levelname)s %(module)s %(message)s',
                    level=logging.DEBUG)
    filename = sys.argv[1]
    src_image = Image.open(filename).convert("L")
    try:
        dpi = int(sys.argv[2])
        ulc_x = float(int(sys.argv[3]))/dpi
        ulc_y = float(int(sys.argv[4]))/dpi
	urc_x,urc_y,lrc_x,lrc_y,llc_x,llc_y = 0.,0.,0.,0.,0.,0.
    except Exception, e:
        print e
        print usage
    try:
	    min_target_width_inches = float(sys.argv[5])
	    max_target_width_inches = float(sys.argv[6])
	    print "Min target width %f max target width %f" % (
		    int(min_target_width_inches*dpi),
		    int(max_target_width_inches*dpi))
    except:
	    pass
    t_image = Image.new("L",src_image.size,255)
    draw = ImageDraw.Draw(t_image)

    fontpath = "/usr/share/fonts/truetype/freefont/FreeSerif.ttf"
    tenthfont = ImageFont.truetype(fontpath,int(dpi/10))
    twentiethfont = ImageFont.truetype(fontpath,int(dpi/15))

    # In searching for vote targets, we ignore the first 20th 
    # of the width of the page, which may contain barcode
    # In building contests, we skip boxes if they are shorter than 1/20 
    # of the page height or narrower than 1/8 of the page width
    # These numbers may need tuning for Diebold.

    check_for_horizontal = True
    diebold = True
    # this should take landmarks as well so that it can subtract
    # the landmarks values from the reported offsets, then convert
    # values to inches
    # or we need a function that modifies the template values
    tb = TemplateBuilder(src_image,
                         dpi,
                         filename = filename,
                         ulc_x = ulc_x,
                         ulc_y = ulc_y,
                         urc_x = urc_x,
                         urc_y = urc_y,
                         lrc_x = lrc_x,
                         lrc_y = lrc_y,
                         llc_x = llc_x,
                         llc_y = llc_y,
                         min_target_width_inches =  min_target_width_inches, 
                         max_target_width_inches = max_target_width_inches,
			 check_for_horizontal = False,#check_for_horizontal,
			 min_target_set_height_inches = 0.25,
			 min_contest_height_inches = 0.9,
			 ignore_height_inches = 0.6,
			 target_height_inches = 0.17,
			 target_width_inches = 0.34,
                         ignore_width_inches = 0.5,
			 ignore_right_inches = 0.5,
			 #max_target_separation_inches = 0.7,
			 diebold = False)#diebold)

    # find darkened scan lines of targetish length
    print "End of program"
