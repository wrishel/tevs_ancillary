#!/usr/bin/env python
import gtk
import pdb


def responseToDialog(entry, dialog, response):
    dialog.response(response)


class BallotAcceptNotes(object):
    def getText(self,coords):
        wx,wy = self.window.get_position()
        dialog = gtk.MessageDialog(
            self.window,
            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
            gtk.MESSAGE_QUESTION,
            gtk.BUTTONS_OK,
            None)
        dialog.set_transient_for(self.window)
        dialog.set_markup('Enter brief note, then click OK:')
        # create multiline text input
        entry = gtk.TextView()
        entry.set_editable(True)
        textbuf = entry.get_buffer()
        
        #create the text input field
        #entry = gtk.Entry()
        #allow the user to press enter to do ok
        #entry.connect("activate", responseToDialog, dialog, gtk.RESPONSE_OK)
        #create a horizontal box to pack the entry and a label
        hbox = gtk.HBox()
        hbox.pack_start(gtk.Label("Note:"), False, 5, 5)
        hbox.pack_end(entry)
        dialog.vbox.pack_end(hbox, True, True, 0)
        dialog.move(wx+coords[0],wy+coords[1])
        dialog.show_all()
        dialog.move(wx+coords[0],wy+coords[1])
        dialog.run()
        text = textbuf.get_text(textbuf.get_start_iter(),textbuf.get_end_iter())
        #text = entry.get_text()
        dialog.destroy()
        # enter text into notes table, re-expose with note added to note list.
        return text

    def key_press_event(self,widget,event):
        keyval_name = gtk.gdk.keyval_name(event.keyval)
        #print "Keyval",keyval_name
        #print "State",event.state
        #print "Filename",widget.filename
        coords = widget.window.get_pointer()
        #print "Coords",coords
        try:
            xscalefactor = widget.xscalefactor
            yscalefactor = widget.yscalefactor
        except:
            xscalefactor = 1
            yscalefactor = 1
        if keyval_name=='n' and (event.state & gtk.gdk.CONTROL_MASK):
            x = int (coords[0] / xscalefactor)
            y = int (coords[1] / yscalefactor)
            bg_color = "yellow"
            note = self.getText(coords)
            if note is not None and len(note)>0:
                # convert the coordinates to inches 
                # need to have the ballot_id as well
                self.dbc.insert_note(widget.filename,widget.ballot_id,x,y,0,0,note,bg_color)

    def get_note(self,widget,event):
        #print "MI Activated"
        #print "Note x",self.note_x
        #print "Note y",self.note_y
        try:
            xscalefactor = self.da.xscalefactor
            yscalefactor = self.da.yscalefactor
        except:
            xscalefactor = 1
            yscalefactor = 1
        x = int (self.note_x / xscalefactor)
        y = int (self.note_y / yscalefactor)
        bg_color = "yellow"
        note = self.getText((self.note_x,self.note_y))
        if note is not None and len(note)>0:
            #print "Note text",note
                # convert the coordinates to inches 
            self.dbc.insert_note(self.da.filename,self.da.ballot_id,x,y,0,0,note,bg_color)
            if self.tevsgui is not None:
                if self.tevsgui.i1 == self.da:
                    self.tevsgui.update_image_and_data(
                        self.da.filename,window_number=0)
                else:
                    self.tevsgui.update_image_and_data(
                        self.da.filename,window_number=1)
            self.da.queue_draw()
        else:
            print "No note to insert into database."

    def present_popup(self,x,y,button,time):
            try:
                m = gtk.Menu()
                m.set_title("MyMenu")
                mi = gtk.MenuItem("--------")
                m.append(mi)
                mi.show()
                mi = gtk.MenuItem("Add note")
                mi.connect("activate",self.get_note,None)
                m.append(mi)
                mi.show()
                m.popup( None, None, None, button, time)
                
            except Exception as e: 
                print e,type(e)

    def on_da_button_press_event(self, widget, event):
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            self.note_x = x
            self.note_y = y
            time = event.time
            self.present_popup(x,y,event.button,time)

    def __init__(self,tevsgui,window,da,dbc=None):
        # window is the tevsgui main toplevel window
        self.tevsgui = tevsgui
        self.window = window
        self.da = da
        self.dbc = dbc
        self.note_x = 0
        self.note_y = 0
        self.da.connect("button_press_event",self.on_da_button_press_event)
        self.da.connect("key_press_event",self.key_press_event)
        self.da.set_flags(gtk.CAN_FOCUS)

        self.da.add_events(gtk.gdk.KEY_PRESS_MASK)


if __name__ == '__main__':

    # create a new window
    window = gtk.Window(gtk.WINDOW_TOPLEVEL)
    
    # Creates a new button with the label "Hello World".
    """self.button = gtk.Button("Hello World")
    self.button.connect("clicked", self.hello, None)
    self.button.connect(
    self.window.add(self.button)
    self.button.show()
    """# Creates a new drawarea 
    da = gtk.DrawingArea()
    da.set_size_request(200,200)
    window.add(da)
    da.show()
    window.show()
    ban = BallotAcceptNotes(None,window,da)
    gtk.main()
