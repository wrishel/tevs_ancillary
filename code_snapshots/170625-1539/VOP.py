#VOP.py
# part of TEVS

import const
import Image
import ImageStat
import util
import os
import os.path
import coord_adjust
import pdb
global vote_threshold, count_threshold
#vote_threshold = const.vote_intensity_threshold
#count_threshold = const.dark_pixel_threshold
"""
The crop bbox passed in does not include any added margins;
margins are specified as additional arguments.
"""

class VOPException(Exception):
    pass

class VOPAnalyze(object):

    def central_region(self):
        hspan = self.x2 - self.x1
        vspan = self.y2 - self.y1
        cropbox = (self.x1 + int(round(2.*hspan/5.)),
                       self.y1 + int(round(2.*vspan/5.)),
                       self.x2 - int(round(2.*hspan/5.)),
                       self.y2 - int(round(2.*vspan/5.)))
        return self.image.crop(cropbox)

    def __init__(self,
                 x1,y1,
                 x2,y2,
                 v_margin=1,
                 h_margin=1,
                 side="Noside",
                 layout_id = "Nolayoutid",
                 image=None,
                 image_filename="Nofilename",
                 jurisdiction="Nojurisdiction",
                 contest="Nocontest",
                 choice="Nochoice",
                 max_votes=1,
                 logger=None):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        logger.info("VOP at %d %d %d %d" % (self.x1,self.y1,self.x2,self.y2))
        self.crop_bbox = (x1-h_margin,
                          y1-v_margin,
                          x2+h_margin,
                          y2+v_margin)

        # test crop_bbox for reasonableness, and recenter if necessary
        # report recentered coordinates as adjusted_x and y.
        self.image = image
        self.image_filename = image_filename
        self.side = side
        self.layout_id = layout_id
        self.jurisdiction = jurisdiction
        self.contest = contest
        self.choice = choice
        self.histogram = None
        self.red_mean = None
        self.red_lowest = None
        self.red_low = None
        self.red_high = None
        self.red_highest = None
        self.green_mean = None
        self.green_lowest = None
        self.green_low = None
        self.green_high = None
        self.green_highest = None
        self.blue_mean = None
        self.blue_lowest = None
        self.blue_low = None
        self.blue_high = None
        self.blue_highest = None
        self.voted = None
        self.ambiguous = None
        self.max_votes = max_votes
        self.logger = logger
        # overvoted flag is set by BallotSideWalker 
        # when it has finished checking all votes for a box
        self.overvoted = False
        # vote test sets self.voted and self.ambiguous
        # returns 0 on success but 1 if updating self coordinates
        self.crop=image.crop(self.crop_bbox)
        self.stat = ImageStat.Stat(self.crop)
        # fills in r/g/b mean values
        self.mean()
        # make a copy of self.mean, and throw out the adjustment
        # if this copy is darker than the new copy
        (orig_red_mean,orig_green_mean,orig_blue_mean) = self.stat.mean
        # !!!new mjt 11/12/13
        ret_coord = coord_adjust.coord_adjust(self.crop,h_margin,v_margin,x2-x1,y2-y1)
        
        if ret_coord is not None:
            #print ret_coord, "applies to old crop now saved."
            #self.crop.save("/tmp/saved.jpg")
            # the returned coordinate is the ULC in a crop box w/  margins
            self.x1 = x1+ret_coord[0]-h_margin
            self.y1 = y1+ret_coord[1]-v_margin
            self.x2 = x2+ret_coord[0]-h_margin
            self.y2 = y2+ret_coord[1]-v_margin
            logger.info("VOP adj to %d %d %d %d" % (self.x1,self.y1,self.x2,self.y2))
            #print "VOP adj to %d %d %d %d" % (self.x1,self.y1,self.x2,self.y2)
            self.crop_bbox = (self.x1-h_margin,
                              self.y1-v_margin,
                              self.x2+h_margin,
                              self.y2+v_margin)
            self.crop=image.crop(self.crop_bbox)
            #self.crop.save("/tmp/saved_adj.jpg")
            #pdb.set_trace()
        self.stat = ImageStat.Stat(self.crop)
        # fills in r/g/b mean values
        self.mean()
        # fills in r/g/b lowest/low/high/highest values
        # undo move if it turns out this red_mean is lighter than orig_red_mean
        if orig_red_mean < self.red_mean:
            self.x1 = x1
            self.y1 = y1
            self.x2 = x2
            self.y2 = y2
            self.crop_bbox = (x1-h_margin,
                              y1-v_margin,
                              x2+h_margin,
                              y2+v_margin)

            self.crop=image.crop(self.crop_bbox)
            self.stat = ImageStat.Stat(self.crop)
            # fills in r/g/b mean values
            self.mean()
            logger.info("VOP unadj back to %d %d %d %d" % (self.x1,self.y1,self.x2,self.y2))
        self.hist4()
        
        self.vote_test()
        # save image around write-in
        if (self.choice.find("Write")>=0) and (self.voted or self.ambiguous):
            #print "self.choice",self.choice
            #print "self.voted",self.voted
            #print "self.ambiguous",self.ambiguous
            # we should save the image with the writein to our writeins folder
            # using the contest text's first few chars,

            # first, generate a subimage using the upper left 
            # of self.crop_bbox and extending for the contest width and
            # for 1".
            # !!!TODO
            # image_to_save = self.image.crop((self.crop_bbox[0],
            # self.crop_bbox[1],
            # self.crop_bbox[2]+(the column's width),
            # self.crop_bbox[3]+dpi))
            outcropbox = None
            try:
                wizhop = const.writein_zone_horiz_offset_inches*const.dpi
                #self.logger.info("Wizhop %s" % (wizhop,))
                wizvop = const.writein_zone_vert_offset_inches*const.dpi
                #self.logger.info("Wizvop %s" % (wizvop,))
                wizwidth = const.writein_zone_width_inches*const.dpi
                #self.logger.info("Wizwidth %s" % (wizwidth,))                
                wizheight = const.writein_zone_height_inches*const.dpi
                #self.logger.info("Wizheight %s" % (wizheight,))                
                outfile = os.path.join(util.root("writeins"),
                                 self.contest[:4]+
                                 os.path.basename(image_filename))
                outcropbox = (int(self.crop_bbox[0]+wizhop),
                                 int(self.crop_bbox[1]+wizvop),
                                 int(self.crop_bbox[0]+wizhop+wizwidth),
                                 int(self.crop_bbox[1]+wizvop+wizheight))
                self.image.crop(outcropbox).save(outfile)
                self.logger.info("Wrote writein image %s" % (outfile,))
            except Exception as e:
                self.logger.warning("Could not save writein image %s %s %s" % (outfile,outcropbox,e))
                
        

    # This routine is replaced for the Hart only version
    # with the coord_adjust routine in coord_adjust.py,
    # which searches for a box's corner and adjusts crop accordingly.
    def coord_adjust(self):
        """ adjust coordinates when target area is too light

        Try moving up, down, left and right by 1.5x the margin size
        in order to get a darker image; whenever you get a darker image,
        adjust the coordinates in the direction of the darker image, 
        and return 1 to indicate adjustment has been made.
        No adjustment, return 0.
        """
        retval = 0
        c = (self.red_lowest + self.red_low + self.red_high 
             + self.blue_lowest + self.blue_low + self.blue_high
             + self.green_lowest + self.green_low + self.green_high)/3
        tentative_move = int(round(const.margin_height_inches * 1.5 * const.dpi))
        higher_bbox = (
            self.crop_bbox[0],
            self.crop_bbox[1] - tentative_move,
            self.crop_bbox[2],
            self.crop_bbox[3] - tentative_move)
        crop_higher=self.image.crop(higher_bbox)
        stat_higher = ImageStat.Stat(crop_higher)
        try:
            red_mean_higher = stat_higher.mean[0]
        except:
            red_mean_higher = stat_higher.mean
        if red_mean_higher < self.red_mean:
            self.y1= self.y1 - tentative_move
            self.crop_bbox = (
                self.crop_bbox[0],
                self.crop_bbox[1] - tentative_move,
                self.crop_bbox[2],
                self.crop_bbox[3] - tentative_move)
            self.logger.warning( self.crop_bbox )
            retval = 1
        else:
            lower_bbox = (
                self.crop_bbox[0],
                self.crop_bbox[1] + tentative_move,
                self.crop_bbox[2],
                self.crop_bbox[3] + tentative_move)
            crop_lower=self.image.crop(lower_bbox)
            stat_lower = ImageStat.Stat(crop_lower)
            try:
                red_mean_lower = stat_lower.mean[0]
            except:
                red_mean_lower = stat_lower.mean
            if red_mean_lower < self.red_mean:
                self.y1 = self.y1 + tentative_move
                self.logger.warning("%s changed to " % (self.crop_bbox,))
                self.crop_bbox = (
                    self.crop_bbox[0],
                    self.crop_bbox[1] + tentative_move,
                    self.crop_bbox[2],
                    self.crop_bbox[3] + tentative_move)
                self.logger.warning( self.crop_bbox )
                retval = 1
        if retval > 0:
            return retval
        # adjust x only when y adjustment was not sufficient 
        #print "Adjusting x; beware of tighter tolerance"
        tentative_move = int(round(const.margin_width_inches*const.dpi/2))
        righter_bbox = (
            self.crop_bbox[0] + tentative_move,
            self.crop_bbox[1],
            self.crop_bbox[2] + tentative_move,
            self.crop_bbox[3])
        crop_righter=self.image.crop(righter_bbox)
        stat_righter = ImageStat.Stat(crop_righter)
        try:
            red_mean_righter = stat_righter.mean[0]
        except:
            red_mean_righter = stat_righter.mean
        if red_mean_righter < self.red_mean:
            self.x1= self.x1 + tentative_move
            self.logger.warning("%s changed to " % (self.crop_bbox,))
            self.crop_bbox = (
                self.crop_bbox[0] + tentative_move,
                self.crop_bbox[1],
                self.crop_bbox[2] + tentative_move,
                self.crop_bbox[3])
            self.logger.warning( self.crop_bbox )
            retval = 1
        else:
            lefter_bbox = (
                self.crop_bbox[0] - tentative_move,
                self.crop_bbox[1],
                self.crop_bbox[2] - tentative_move,
                self.crop_bbox[3])
            crop_lefter=self.image.crop(lefter_bbox)
            stat_lefter = ImageStat.Stat(crop_lefter)
            try:
                red_mean_lefter = stat_lefter.mean[0]
            except:
                red_mean_lefter = stat_lefter.mean
            if red_mean_lefter < self.red_mean:
                self.x1 = self.x1 - tentative_move
                self.logger.warning("%s changed to " % (self.crop_bbox,))
                self.crop_bbox = (
                    self.crop_bbox[0] - tentative_move,
                    self.crop_bbox[1],
                    self.crop_bbox[2] - tentative_move,
                    self.crop_bbox[3])
                #print self.crop_bbox
                retval = 1
        return retval

    def vote_test(self):
        #global vote_threshold, count_threshold
        # return value of 0 means OK, otherwise recrop and retest
        retval = 0
        passed_mean = False
        passed_count = False
        self.voted = False
        self.ambiguous = False
        # check for off-center if light, adjust y by margin if shift darkens
        tentative_move = 0
        m = (self.red_mean + self.blue_mean + self.green_mean)/3.
        if m < const.vote_intensity_threshold:
            passed_mean = True
        c = (self.red_lowest + self.red_low 
             + self.blue_lowest + self.blue_low 
             + self.green_lowest + self.green_low )/3
        #c_red = self.red_lowest+self.red_low
        if c > const.dark_pixel_threshold:
            passed_count = True

        #print m, const.vote_intensity_threshold, passed_mean, 
        #print c, const.dark_pixel_threshold, passed_count
        if passed_mean or passed_count: 
            self.voted = True
            if passed_mean != passed_count:
                self.ambiguous = True
        if not self.voted and not self.ambiguous:
             # Check for speck if not voted and not ambig
            central_histo = self.hist4(self.central_region())
            if central_histo[0] > 0 or central_histo[1] > 0:
                self.logger.info("Found speck in red channel of unvoted, unambig box.")        
                self.ambiguous = True
                self.voted = True

    def db_insert_string(self):
        pass

    def db_retrieval_string(self):
        pass


    def __repr__(self):
        return """VOP at %(crop_bbox)s
 REPRESENTING %(image_filename)s, type %(layout_id)s %(side)s, %(jurisdiction)s, %(contest)s, %(choice)s.
 RED m=%(red_mean)03.1f lowest=%(red_lowest)d  low=%(red_low)d high=%(red_high)d highest=%(red_highest)d
 GREEN m=%(green_mean)03.1f lowest=%(green_lowest)d low=%(green_low)d high=%(green_high)d highest=%(green_highest)d 
 BLUE m=%(blue_mean)03.1f lowest=%(blue_lowest)d low=%(blue_low)d high=%(blue_high)d highest=%(blue_highest)d 
""" % self.__dict__
    def mean(self):
        try:
            (self.red_mean,self.green_mean,self.blue_mean) = self.stat.mean
        except:
            self.red_mean = self.stat.mean
        return self.stat.mean

    def hist4(self,region=None):
        self.histogram = []
        # histogram has 256 boxes per channel, r/g/b or mono
        if region is None:
            h = self.crop.histogram()
        else:
            h = region.histogram()
        accum = 0
        # we want a 4 box per channel histogram, so divide 256 into zones of 64,
        # getting rrrrggggbbbb or mmmm
        for x in range(len(h)):
            accum += h[x]
            if (x%64==63):
                self.histogram.append(accum)
                accum = 0
        if region is None:
            (self.red_lowest,self.red_low,
             self.red_high,self.red_highest) = self.histogram[0:4]
            try:
                (self.green_lowest,self.green_low,
                 self.green_high,self.green_highest) = self.histogram[4:8]
                (self.blue_lowest,self.blue_low,
                 self.blue_high,self.blue_highest) = self.histogram[8:12]
            except:
                pass
        return self.histogram
