import gtk
import pygtk
import tevsgui

class Drawing(object):

    def __init__(self,d1=None,d2=None):
        """initialize with one or two drawing area widgets"""
        self.d1 = d1
        self.d2 = d2
        
    def draw():
        print "Draw",which

        if drawarea.window is None: 
            return

        w,h = drawarea.window.get_size()

        if self.gc is None:
            self.initialize_gc(drawarea.window)

        try:
            if image_side == 0:
                orig_width,orig_height = self.leftimage.size
                imagedpi = int(round(orig_width/const.ballot_width_inches))
                image = self.leftimage.resize(
                    (w,h)).convert("RGB")
                imagestr = image.tostring()
                bv = self.leftbv
            else:
                orig_width,orig_height = self.rightimage.size
                imagedpi = int(round(orig_width/const.ballot_width_inches))
                image = self.rightimage.resize(
                    (w,h)).convert("RGB")
                imagestr = image.tostring()
                bv = self.rightbv
            imagewidth, imageheight = image.size

            xscalefactor = float(w)/orig_width
            yscalefactor = float(h)/orig_height
            #print "W,H,IW,IH,XS,YS,DPI"
            #print w,h
            #print orig_width, orig_height
            #print xscalefactor,yscalefactor,imagedpi
            drawarea.window.draw_rgb_image(
                self.gc, 
                0, 0, 
                w, h, 
                gtk.gdk.RGB_DITHER_NONE, 
                imagestr, 
                w*3
                )

            if bv is not None:
                bv.paint(self,
                         drawarea,
                         xscalefactor,
                         yscalefactor,
                         imagedpi,
                         overlay_votes=self.overlay_votes.get_active(),
                         overlay_choices=self.overlay_choices.get_active() ,
                         overlay_contests = self.overlay_contests.get_active())
        except Exception, e:
            print e
        #drawarea.window.draw_line(self.gc, 0, 0, w, h);
        #drawarea.window.draw_line(self.gc, 0, 0, w, int(h*.9))
        #drawarea.window.draw_line(self.gc, w, 0, 0, h);
        #drawarea.window.draw_line(self.gc, w, 0, 0, int(h*.9))
