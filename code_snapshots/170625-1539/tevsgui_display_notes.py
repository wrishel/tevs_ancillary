import const
import pdb
import os.path

text_size="medium"



class DBNote(object):
    def __init__(self):
        self.x,self.y,self.w,self.h = 0,0,0,0
        self.note = ""
        self.color = ""
        self.bg_color = "yellow"
        self.ballot_id = 0

class BallotNotes(object):
    def __init__(self,imagenumber,dbc=None):
        if const.use_db:
            # query the database for the notes matching file number
            self.notelist = []
            dbfileroot = const.root+"/unproc"
            dbfilename = "%s/%03d/%06d.jpg" % (
                dbfileroot,imagenumber/1000,imagenumber)
            results = dbc.query("select x,y,w,h,bg_color,note from notes where filename like '%s'" % (dbfilename,) )
            #results = None
            #n1 = DBNote()
            #n1.x = 2.
            #n1.y = 3.
            #n1.w = 1.
            #n1.h = 1.
            #n1.note = "Hello,\nnote."
            #n1.ballot_id = 199
            #self.notelist = results#[n1]
            if results is not None and len(results)>0:
                for fields in results:
                    n = DBNote()
                    n.x = int(float(fields[0]))
                    n.y = int(float(fields[1]))
                    n.w = int(float(fields[2]))
                    n.h = int(float(fields[3]))
                    n.note = fields[5]
                    n.bg_color = fields[4]
                    self.notelist.append(n)    

    def paint(self,main_app,drawarea,orig_width,orig_height,imagedpi):
        """Paint note"""
        gc = main_app.gc
        red = main_app.red
        green = main_app.green
        blue = main_app.blue
        purple = main_app.purple
        drawable = drawarea.window
        w,h = drawable.get_size()
        xscalefactor = float(w)/orig_width
        yscalefactor = float(h)/orig_height
        drawarea.xscalefactor = xscalefactor
        drawarea.yscalefactor = yscalefactor
        for n in self.notelist:
            # for the moment, since we are not taking scaling into account when storing, we set scalefactors to 1 here
            scaledx = int(n.x * xscalefactor)
            scaledy = int(n.y * yscalefactor)
            scaledw = int(n.w * xscalefactor)
            scaledh = int(n.h * yscalefactor)
            cmap = drawable.get_colormap()
            markup = drawarea.create_pango_layout("a")
            markup.set_markup(
                """<span size="%s" foreground="%s" background="%s">%s</span>""" % (
                    text_size,"black",n.bg_color,n.note
                    )
                )
            # draw markup at lower right of vote oval, offset by 5 pix 
            drawable.draw_layout(gc,
                               scaledx,
                               scaledy,
                               markup)


