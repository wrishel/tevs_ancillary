#! /usr/bin/env python
# NEXT: What's wrong with the transition from process_overvote to vote_count

# This is the entry for TEVS, the Trachtenberg Election Verification System.
# In addition to this GUI process, there are scanning and ballot processing
# processes, and a reporting shell script.  The GUI component hierarchy is
# in tevsgui.glade.
# TEVS is copyright 2010, 2011, 2012 Mitch Trachtenberg
# Released under the terms of the GNU Public License version 2
# More information at http://www.tevsystems.com 
# and http://www.mitchtrachtenberg.com
# If you are an election integrity activist, please do not hesitate
# to get in touch with me at mjtrac@gmail.com.


import sys
try:  
    import pygtk  
    pygtk.require("2.0")  
except:  
    pass  
try:  
    import gtk  
except:  
    print("GTK Not Available")
    sys.exit(1)
import gobject
try:
    import vte
except:
    print("VTE Not Available")
    #sys.exit(2)

import time
import const
import config
import BallotVOPtoDB as db
from BallotAcceptNotes import BallotAcceptNotes
import exceptions
import getopt
import gobject
import glib
import glob
import Image
import logging
import os
import pdb
import pickle
import util
import sane
import subprocess
import warnings

import tevsgui_get_args
# handles auto advance when viewing processed ballots
from tevsgui_auto_advance import AutoAdvance

# each "requestor" sets up and communicates with a subprocess or xmlrpc server 
# to handle tasks that would otherwise freeze the GUI
from tevsgui_db_query_requestor import QueryRequestor

# communicate with processing service on 8000
# service command: python tevsgui_xmlrpc_processing_service.py
from tevsgui_xmlrpc_processing_requestor import ProcessBallotsRequestor, ProcessBallotsException

# communicate with scanning service on 8001
# service command: python tevsgui_xmlrpc_scanning_service.py
from tevsgui_xmlrpc_scanning_requestor import ScanRequestor, ScanRequestorException

from  tevsgui_display_votes import BallotVotes
from tevsgui_display_notes import BallotNotes 
import tevsgui_status
import tevsgui_print
import tevsgui_postprocess_db

# the db query requestor sets up programs 
# which store potentially lengthy 
# response data in python "pickle" files
# for reading by the main program
# when the main program is called back

ambig_pickle_file = "/tmp/ambig.pickle"
typecode_pickle_file = "/tmp/typecode.pickle"

global_remaining_fails = 200

class control_notebook_pages(object):
    Config = 0
    Scan = 1
    Process = 2
    Display = 3


def get_text(prompt,labelprompt="Name:"):
    """Utility function to prompt user for text and return text."""
    dialog = gtk.MessageDialog(
        None,
        gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
        gtk.MESSAGE_QUESTION,
        gtk.BUTTONS_OK_CANCEL,
        None)
    dialog.set_markup(prompt)
    dialog.set_default_response(gtk.RESPONSE_OK)
    entry = gtk.Entry()
    entry.set_property("activates-default",True)
    #create a horizontal box to pack the entry and a label
    hbox = gtk.HBox()
    hbox.pack_start(gtk.Label(labelprompt), False, 5, 5)
    hbox.pack_end(entry)
    dialog.vbox.pack_end(hbox, True, True, 0)
    dialog.show_all()
    response = dialog.run()
    if response == gtk.RESPONSE_OK:
        text = entry.get_text()
    else: 
        text = ""
    dialog.destroy()
    return text


# db setup for direct connections
def initialize_database():
    dbc = None
    try:
        dbc = db.PostgresDB(const.dbname, const.dbuser)
    except db.DatabaseError:
        util.fatal("Could not connect to database")
    return dbc

def on_delete_event(widget, event):
    return True

class tevsGui:
    """tevsGui is the user interface application for TEVS

    In addition to displaying ballots overlaid with any vote data 'banked'
    in the SQL database, tevsGui provides access to several service
    programs.  Ballot scanning and ballot processing are handled in 
    tevsgui_xmlrpc_scanner/processing_service.py; tevsGui communicates
    with those programs by calling functions in 
    tevsgui_xmlrpc_scanner/processing_requestor.py.

    tevsGui 

    """
    # graphics setup
    gc = None
    cmap = None
    paginated_pages = 0
    page_breaks = []
    lines_per_page = 20
    printfile = None
    printfilename = "/tmp/printfile.txt"
    green, red, blue, purple, cyan = None,None,None,None,None
    postprocess_instance = None


    def initialize_gc(self,window):
        tevsGui.cmap = window.get_colormap()
        tevsGui.green= tevsGui.cmap.alloc_color("green")
        tevsGui.red= tevsGui.cmap.alloc_color("red")
        tevsGui.blue= tevsGui.cmap.alloc_color("blue")
        tevsGui.purple= tevsGui.cmap.alloc_color("purple")
        tevsGui.cyan= tevsGui.cmap.alloc_color("cyan")
        self.gc = window.new_gc(foreground=tevsGui.green)
        self.gc.set_line_attributes(2,gtk.gdk.LINE_SOLID,
                                    gtk.gdk.CAP_BUTT,
                                    gtk.gdk.JOIN_BEVEL)

    # GUI initial state
    # is configured from tevs.cfg height, width, and resolution info
    # set configuration to locked, set lock toggle on
    # start with pretty pix in left and right windows
    

    def expose_cb(self,drawarea,exposure,image_side):
        """draw image according to scale settings"""
        if drawarea.window is None: 
            return
        if self.gc is None:
            self.initialize_gc(drawarea.window)
        w,h = drawarea.window.get_size()
        if image_side == 0:
            orig_width,orig_height = self.leftimage.size
            imagedpi = int(round(orig_width/const.ballot_width_inches))
            image = self.leftimage.resize((w,h)).convert("RGB")
            bv = self.leftbv
            try:
                bn = self.leftbn
            except:
                bn = None
        else:
            orig_width,orig_height = self.rightimage.size
            imagedpi = int(round(orig_width/const.ballot_width_inches))
            image = self.rightimage.resize((w,h)).convert("RGB")
            bv = self.rightbv
            try:
                bn = self.rightbn
            except:
                bn = None

        drawarea.window.draw_rgb_image(
            self.gc, 
            0, 0, 
            w, h, 
            gtk.gdk.RGB_DITHER_NONE, 
            image.tostring(), 
            w*3
            )
        if bn is not None:
            bn.paint(self,
                 drawarea,
                 orig_width,
                 orig_height,
                 imagedpi)
                 
        if bv is None:
            return
        bv.paint(self,
                 drawarea,
                 orig_width,
                 orig_height,
                 imagedpi,
                 overlay_votes=self.overlay_votes.get_active(),
                 overlay_choices=self.overlay_choices.get_active() ,
                 overlay_contests = self.overlay_contests.get_active(),
                 overlay_stats = self.overlay_stats.get_active())


    def configure_cb(self,drawarea,event,image_side):
        self.logger.debug("Configure DrawingArea %s %s" % (drawarea,image_side))
        # from pygtk tutorial
        if drawarea.window is None: 
            return
        x,y,width,height = drawarea.get_allocation()
        #print x, y, width, height
        self.leftpixmap = gtk.gdk.Pixmap(drawarea.window,
                                         width,height)

	# call expose callback to clean up
	self.expose_cb(drawarea,event,image_side)


    # adjustments
    def on_imprintOffsetAdjustment_changed(self,adj,data):
        self.builder.get_object(
            "imprintOffsetScale").set_value(adj.get_value())
        try:
            self.scan_requestor.set_endorser_y(int(adj.get_value())) 
            self.status.update(
                "Imprint offset now %d" % (int(adj.get_value())))
        except AttributeError,e:
            self.status.update("Problem updating scanner.")
        except:
            pass

    def on_widthAdjustment_changed(self,adj,data):
        self.builder.get_object("widthScale").set_value(adj.get_value())
        try:
            self.scan_requestor.set_page_width(int(adj.get_value())) 
            self.status.update(
                "Width adjustment now %d" % (int(adj.get_value())))
        except AttributeError,e:
            self.status.update("Problem updating scanner.")

    def on_heightAdjustment_changed(self,adj,data):
        self.builder.get_object("heightScale").set_value(adj.get_value())
        try:
            self.scan_requestor.set_page_height(int(adj.get_value())) 
            self.status.update(
                "Height adjustment now %d" % (int(adj.get_value())))
        except AttributeError,e:
            self.status.update("Problem updating scanner.")

    def on_zoomAdjustment_changed(self,adj,data):
        self.builder.get_object("zoomScale").set_value(adj.get_value())
        #print data
        v = adj.get_value()
        v = float(v/10)
        self.status.update("Zoom now %d" % (int(adj.get_value())))
        self.zoom_value = v
        (w,h) = self.leftimage.size
        self.i1.set_size_request(int(w*v),int(h*v))
        self.i1.width = int(w*v)
        self.i1.height = int(h*v)
        try:
            (w,h) = self.rightimage.size
            self.i2.set_size_request(int(w*v),int(h*v))
            self.i2.width = int(w*v)
            self.i2.height = int(h*v)
        except:
            pass


    # toggles
    def on_autoAdvance_toggled(self, button, data):
        self.aa.toggled(self,button,data)


    def on_doubleSided_toggled(self, button, data):
        if not button.get_active(): return
        #print "double sided toggled"
        try:
            self.scan_requestor.set_duplex(True) 
            self.status.update("Scanning both sides.")
        except AttributeError,e:
            self.status.update("Problem updating scanner.")
        except:
            pass


    def on_singleSided_toggled(self, button, data):
        if not button.get_active(): return
        #print "single sided toggled"
        try:
            self.scan_requestor.set_duplex(False) 
            self.status.update("Scanning fronts only.")
        except AttributeError,e:
            self.status.update("Problem updating scanner.")
        except:
            pass

    def on_lowRes150_toggled(self, button, data):
        if not button.get_active(): return
        print "150 dpi"
        try:
            self.scan_requestor.set_resolution(150) 
            self.status.update("Scan resolution 150 dots per inch.")
        except AttributeError,e:
            self.status.update("Problem updating scanner.")
        except:
            pass

    def on_hiRes300_toggled(self, button, data):
        if not button.get_active(): return
        print "300 dpi"
        try:
            self.scan_requestor.set_resolution(300)
            self.status.update("Scan resolution 300 dots per inch.")
        except AttributeError,e:
            self.status.update("Problem updating scanner.")
        except:
            pass

    def on_imprintOff_toggled(self, button, data):
        if not button.get_active(): return
        print "Scanner numbering off"
        try:
            self.scan_requestor.set_endorser(False) 
            self.status_update("Scanner numbering off.")
        except AttributeError,e:
            self.status.update("Problem updating scanner.")
        except:
            pass

    def on_imprintOn_toggled(self, button, data):
        if not button.get_active(): return
        print "Scanner numbering on"
        try:
            self.scan_requestor.set_endorser(True) 
            self.status_update("Scanner numbering on.")
        except AttributeError,e:
            self.status.update("Problem updating scanner.")
        except:
            pass

    def on_overlayVotes_toggled(self, button, data):
        self.expose_cb(self.i1,None,0)
        self.expose_cb(self.i2,None,1)

    def on_overlayStats_toggled(self, button, data):
        self.expose_cb(self.i1,None,0)
        self.expose_cb(self.i2,None,1)

    def on_overlayContests_toggled(self, button, data):
        self.expose_cb(self.i1,None,0)
        self.expose_cb(self.i2,None,1)

    def on_overlayChoices_toggled(self, button, data):
        self.expose_cb(self.i1,None,0)
        self.expose_cb(self.i2,None,1)

    def on_configurationLock_toggled(self, button, data):
        sb = self.builder.get_object("statusbar1")
        sb.set_has_resize_grip(True)
        basic_cid = sb.get_context_id("Basic")
        sb.push(basic_cid,"Configuration lock toggled %s." % (
                str(button.get_active()),))
        self.builder.get_object("configurationFrame").set_sensitive(
            button.get_active()
            )

    # clicked
    def on_symlinkDialog_okButton_clicked(self, button, data):
        print "Symlink dialog ok button clicked."
        print self
        #wildcard = self.builder.get_object(
        #"symlinkDialog_wildcardEntry").get_text()


# ***********************************************************************
# VOTE EXTRACTION
# ***********************************************************************

    def extractNow_cbfunc(self,req):
        """Called back from tevsgui_xmlrpc_processing_requestor 
        when the processing server has responded.

        This callback should repeat the ballot request for subsequent ballots
        when the requestor indicates a successful return from the server, and
        should cause the failure to be presented to the user  
        when the requestor indicates a failed return from the server.

        It is also responsible for updating the tracking file nexttoprocess.txt
        and for moving the processed file, if required.

        When the processing service encounters an error, it must return 
        "FAIL," followed by the error message.

        """
        #print "Self",self
        #print "Requestor",req
        #print "Requestor threaddata return value",req.threaddata.retval
        global global_remaining_fails;
        failed = False
        if req.threaddata.retval is not None:
            if (type(req.threaddata.retval)==str 
                and req.threaddata.retval.startswith("FAIL,")):
                self.status.update("%s" % (req.threaddata.retval.split(",")[1:]))
                self.logger.error("Failed to process %s" % (str(req.threaddata.retval)))
                self.logger.error("%s" % (req.threaddata.retval.split(",")[1:]))
                failed = True
            else:
                self.status.update("Processed %s" % str(req.threaddata.retval))

        n = int(req.number)
        # form filename as expected by update_image_and_data
        unprocessed_filename = "%s/unproc/%03d/%06d.jpg" % (const.root,
                                                          n/1000,
                                                          n)
        processed_filename = "%s/proc/%03d/%06d.jpg" % (const.root,
                                                        n/1000,
                                                        n)
        # set up for next
        increment = const.num_pages
        nextnum = int(req.number) + increment
        self.next_to_extract.set_text(str(nextnum))
        util.writeto(os.path.join(const.root,"nexttoprocess.txt"),nextnum)

        req.number += increment

        # If success, move the processed file from unproc to proc,
        # display it, and request the next; otherwise, decrement the
        # allowed_fail_count and if still above 0, continue
        if not failed:
            try:
                os.renames(unprocessed_filename,processed_filename)
                self.logger.info("Processed %d" % (n,))
            except Exception as e:
                self.logger.warning(e)
            
            # if the processing control panel page is displayed, 
            # show results of processing in the drawing area(s)
            if (self.control_notebook.get_current_page() 
                == control_notebook_pages.Process):
                self.update_image_and_data(processed_filename,0)

            gobject.idle_add(req.process)
        else:
            self.logger.error("Failed to process %d" % (n,))
            self.logger.error("global_remaining_fails = %d" % (global_remaining_fails - 1));
            global_remaining_fails = global_remaining_fails - 1
            if global_remaining_fails > 0:
                gobject.idle_add(req.process)

    def on_extractNowXMLRPC_clicked(self, button, data):
        """Initiate ballot processing.

        The ballot process is an external xmlrpc server program 
        which responds to xmlrpc calls issued by the requestor client
        that is created here.  The callback is called every time
        a call completes, and must contain information indicating
        the success or failure of the task the external server has
        attempted.  Successes may continue, with the callback issuing
        another process call.  Failures should end the processing loop.

        We only plan on creating one requestor, but there is nothing
        clearly prohibiting the creation of multiple requestors making
        calls to a single server.
        """
        
        try:
            self.process_ballots_requestor = ProcessBallotsRequestor(
                self.extractNow_cbfunc,self.next_to_extract)
            self.process_ballots_requestor.proceed = True
            self.logger.info("Process ballot requestor created.")
        except ProcessBallotsException, e:
            self.logger.error("Process ballot requestor was not created.")
            self.logger.error(e)
            return
        try:
            ntp = util.readfrom(util.root("nexttoprocess.txt"),1)
            ntp = int(ntp)
            self.process_ballots_requestor.number = ntp
        except Exception as e:
            print e, type(e)
            pdb.set_trace()

        gobject.idle_add(self.process_ballots_requestor.process)


    def on_lastExtractedAllowUpdate_clicked(self, button, data):
        text = get_text("Next number to process:",labelprompt="Number")
        if len(text)>0:
            next_number = int(text)
            self.next_to_extract.set_text(text)
            self.last_processed_number = next_number - 1
            util.writeto(util.root("nexttoprocess.txt"),next_number)
            self.status.update("Next number now %d" % (next_number,))

    def on_extractEnd_clicked(self, button, data):
        self.process_ballots_requestor.proceed = False
        pass

    def on_extractAsArrive_toggled(self, button, data):
        print "Extract as arrive toggled."
        print "Inactive, set it to keep attempting to start up the processing\n\
every few seconds until successful."
        self.status.update("Sorry, not yet implemented.")
        self.extract_continually = button.get_active()
        if self.extract_continually:
            pass
        else:
            pass



# ***********************************************************************
# SCANNING
# ***********************************************************************

    def on_searchForScanner_clicked(self, button, data):
        print "Search for scanner clicked."
        print self
        self.showScannerString()
        print button
        print data

    def scanner_setup(self):
        (duplex,
         height_in_100th,width_in_100th,
         resolution,
         height_in_mm,width_in_mm,
         endorser) = self.get_scan_settings()

        try:
            self.scan_requestor
        except AttributeError, e:
            self.status.update("No scan requestor is available.")
            return
        self.scan_requestor.set_resolution(resolution) 
        self.scan_requestor.set_duplex(duplex) 
        self.scan_requestor.set_endorser(endorser) 
        # endorser imprint initially centered vertically
        # horizontal shift generally mechanical at scanner
        #self.scan_requestor.set_endorser_y(height_in_100th/2) 
        # end with %05ud
        self.scan_requestor.set_endorser_string("%05ud") 
        # number replacing %05ud
        self.scan_requestor.set_endorser_val(self.batch_start_number) 
        if self.scanner is None:
            self.scanner = "ready"

    def on_testScan_clicked(self, button, data):
        self.scanner_setup()
        try:
            self.batch_start_number = self.builder.get_object("nextScanNumber").get_text()
            if self.batch_start_number == "":
                self.batch_start_number = "0"
            else:
                self.batch_start_number = int(self.builder.get_object("nextScanNumber").get_text())
            self.scan_requestor.set_save_location("/tmp/test%03d%03d.jpg")
            self.scan_requestor.do_scan(0)
        except AttributeError, e:
            self.status.update("No scan requestor is available.")
        print "Test scan written to /tmp/test..."

    def on_scanStart_clicked(self, button, data):
        try:
            self.scan_requestor.set_save_location(const.unprocformatstring)
            self.batch_start_number = self.builder.get_object("nextScanNumber").get_text()
            if self.batch_start_number == "":
                self.batch_start_number = "0"
            else:
                self.batch_start_number = int(
                    self.builder.get_object("nextScanNumber").get_text())
            logger.info("Scanning from %d Note:%s\n" % (
                    self.batch_start_number,
                    self.builder.get_object("nextScanNoteEntry").get_text())
                        )
        except Exception, e:
            print e
        # keep setup below assignment to self.batch_start_number
        self.scanner_setup()
        try:
            self.scan_requestor.do_scan(self.batch_start_number)
        except AttributeError, e:
            self.status.update("No scan requestor is available.")

    def on_scanRequestStop_clicked(self, button, data):
        print "Scan request stop clicked."
        #self.scanner.stop()
        # Need to send xmlrpc call 
        # to be processed by scan service immediately,
        # jumping any queue. How?  Perhaps the multiple scan loop 
        # at the service will have a break variable that can be set?
        try:
            self.scan_requestor
        except AttributeError, e:
            self.status.update("No scan requestor is available.")
            return
        self.scan_requestor.do_stop_scan()
        self.scanner = None

    def get_scan_settings(self):
        duplex = self.builder.get_object("doubleSided").get_active()

        height_in_100th = int(
            self.builder.get_object("heightScale").get_value())
        height_in_mm = int(.254 * height_in_100th)
        width_in_100th = int(
            self.builder.get_object("widthScale").get_value())
        width_in_mm = int(.254 * width_in_100th)

        r150 = self.builder.get_object("lowRes150").get_active()
        r300 = self.builder.get_object("hiRes300").get_active()
        if r150:
            resolution = 150
        elif r300:
            resolution = 300
        endorser = self.builder.get_object("imprintOn").get_active()
        return (duplex,
                height_in_100th,
                width_in_100th,
                resolution,
                height_in_mm,
                width_in_mm,
                endorser)
        
    def update_image_and_data(self,new_file,window_number=0):
        #print "Display file changed to ",new_file,"in",window_number
        if window_number==0:
            imageobj = self.leftimage
            self.image_number_entry.set_text(new_file[-10:-4]) 
            companion_filename_number = int(new_file[-10:-4])+1
            companion_filename = const.unprocformatstring % (
            companion_filename_number/1000,
            companion_filename_number)
            self.i1.filename = new_file
            self.i2.filename = companion_filename
        else:
            imageobj = self.rightimage
        try:
            imageobj = Image.open(new_file)
        except Exception, e:
            try:
                imageobj = Image.open(new_file.replace("unproc","proc"))
            except Exception,e2:
                print e2
        image_number = int(new_file[-10:-4])
  
        if window_number == 0:
            self.cmap = self.i1.window.get_colormap()
            # trieving the votes locates the ballot id, so lets store it
            self.leftbv = BallotVotes(image_number,self.dbc)
            self.left_ballot_id = self.leftbv.ballot_id
            self.i1.ballot_id = self.leftbv.ballot_id
            # and we can (but haven't) changed BallotNotes to use it directly
            self.leftbn = BallotNotes(image_number,self.dbc)
            self.leftimage = imageobj
            self.expose_cb(self.i1,None,0)
            try:
                self.image_number_entry.set_text(new_file[-10:-4]) 
                self.rightimage = Image.open(companion_filename)
            except Exception, e:
                try:
                    self.rightimage = Image.open(
                        companion_filename.replace("unproc","proc"))
                except Exception,e2:
                    print e2
            image_number = int(companion_filename[-10:-4])
            self.rightbv = BallotVotes(image_number,self.dbc)
            self.right_ballot_id = self.rightbv.ballot_id
            self.i2.ballot_id = self.rightbv.ballot_id
            self.expose_cb(self.i2,None,1)
        else:
            self.rightbv = BallotVotes(image_number,self.dbc)
            self.right_ballot_id = self.rightbv.ballot_id
            self.rightbn = BallotNotes(image_number,self.dbc)
            self.i2.ballot_id = self.rightbv.ballot_id
            self.rightimage = imageobj
            self.expose_cb(self.i2,None,1)
        
    def imageList_selection_changed(self,tvselection,data):
        
        tm,ti = tvselection.get_selected()
        try:
            selected_filename = tm.get_value(ti,0)
            if selected_filename is not None:
                self.update_image_and_data(selected_filename,0)
        except Exception as e:
            print e
  

    def do_print(self,button,data):
        # data is list_store
        p = tevsgui_print.PrintTotals(data,self.window)
        
    def do_hide(self,button,window):
        window.hide()
        

#*************************************************************************
# DATABASE FILTER QUERIES:
# Ambig only checkbox triggers database request, 
# updating table when request calls back.
#*************************************************************************

    def ambig_data_ready_cb(self,line,data):
        #print "Ambig data ready in /tmp/ambig.pickle"
        tv = self.builder.get_object("imageListTreeView")
        tm = self.builder.get_object("imageListTreeModel")
        tvsel = tv.get_selection()
        # initialize at first use
        if not self.imageListInitted:
            tvsel.connect("changed",self.imageList_selection_changed,0)

            cr0 = gtk.CellRendererText()
            tvc0 = gtk.TreeViewColumn("Matches")
            tv.append_column(tvc0)
            tvc0.pack_start(cr0,True)
            tvc0.set_attributes(cr0,text=0)
            self.imageListInitted = True # do not reinit
        tm.clear()
        try:
            picklefile = open(ambig_pickle_file,"rb")
            retval = pickle.load(picklefile)
            picklefile.close()
            os.unlink(ambig_pickle_file)
        except IOError:
            retval =None
        if retval is not None:
            for record in retval:
                tm.append(record)
        else:
            self.status.update("No available match file.")


    def multiple_data_ready_cb(self, line, data):
        queries = data[0]
        qindex = data[1]+1
        self.status.update("Overvote step %d of %d" % (qindex+1,len(queries)))
        if qindex < len(queries)-1:
            qr = QueryRequestor(
                stdout_cb =self.multiple_data_ready_cb,
                user = const.dbuser,
                database = const.dbname,
                query = queries[qindex],
                retfile = ambig_pickle_file,
                stdout_cb_data = (queries,qindex))
            
    def multiple_q(self,button,data):
        queries = [
"drop table if exists overvotes cascade;",
"drop table if exists overvote_ids cascade;",
"drop table if exists overvote_values cascade;",
"drop table if exists overvote_diffs cascade;",
"""select count(*) as votes, contest_text_standardized_id, filename 
    into overvotes 
    from voteops 
    where was_voted 
    group by contest_text_standardized_id, filename;
""",
"""
select v.voteop_id 
       into overvote_ids 
       from overvotes o 
       join voteops v 
       on o.contest_text_standardized_id = v.contest_text_standardized_id 
       join ocr_variants ocr on v.contest_text_standardized_id = ocr.id
       and o.filename = v.filename 
       where o.votes > ocr.max_votes_in_contest;
""",
"""
select v.voteop_id, 
       substring(v.filename,28,15) as filename ,
       substring(v.contest_text,1,30) as contest,
       substring(v.choice_text,1,30) as choice, 
       v.red_darkest_pixels as darkest, 
       v.red_mean_intensity as intensity 
       into overvote_values 
       from overvote_ids o join voteops v 
       on o.voteop_id = v.voteop_id where was_voted;
""",
"""
select a.*, b.voteop_id as b_voteop_id, 
       (a.intensity - b.intensity) as intensity_a_less_intensity_b 
       into overvote_diffs 
       from overvote_values a join overvote_values b 
       on a.contest = b.contest and a.filename=b.filename and a.choice != b.choice; 
""",
"""
update voteops 
       set was_voted = False, overvoted=False, suspicious=True 
       where voteop_id in 
       (select b_voteop_id 
       	       from overvote_diffs 
	       where intensity_a_less_intensity_b < -30);

""",
"""
update voteops 
       set was_voted = False, overvoted=False,
       suspicious = True
       where voteop_id in 
       (select voteop_id 
       	       from overvote_diffs 
	       where intensity_a_less_intensity_b > 30);

""",
"""
update voteops 
       set was_voted = True, 
       suspicious = True,
       overvoted = True,
       where voteop_id in 
       (select voteop_id 
       	       from overvote_diffs 
	       where (intensity_a_less_intensity_b <= 30) 
               and (intensity_a_less_intensity_b >= -30)
);

"""]
        qr = QueryRequestor(
            stdout_cb =self.multiple_data_ready_cb,
            user = const.dbuser,
            database = const.dbname,
            query = queries[0],
            retfile = ambig_pickle_file,
            stdout_cb_data = (queries,0))
        self.status.update("Overvote step %d of %d" % (1,len(queries)))

    def on_ambigOnly_toggled(self, button, data):
        #self.multiple_q(button,data)
        #return
        query_string = """
select distinct filename 
from voteops v join ballots b on v.ballot_id = b.ballot_id 
where (suspicious or overvoted) order by filename
"""
        #print "Ambig only toggled."
        toggled_on = button.get_active()
        if toggled_on :
            qr = QueryRequestor(
                stdout_cb = self.ambig_data_ready_cb,
                user = const.dbuser,
                database = const.dbname,
                query = query_string,
                retfile = ambig_pickle_file)
            self.status.update("Locating ambiguous ballots.")
        else:
            tm = self.builder.get_object("imageListTreeModel")
            print tm.clear()
            self.status.update("Ready.")


#*************************************************************************
# Typecode entry (enter key) triggers database request, 
# updating table when request calls back.
#*************************************************************************

    def typecode_data_ready_cb(self,line,data):
        tv = self.builder.get_object("imageListTreeView")
        tm = self.builder.get_object("imageListTreeModel")
        tvsel = tv.get_selection()
        # initialize at first use
        if not self.imageListInitted:
            tvsel.connect("changed",self.imageList_selection_changed,0)
            cr0 = gtk.CellRendererText()
            tvc0 = gtk.TreeViewColumn("Matches")
            tv.append_column(tvc0)
            tvc0.pack_start(cr0,True)
            tvc0.set_attributes(cr0,text=0)
            self.imageListInitted = True # do not reinit
        tm.clear()
        try:
            picklefile = open(typecode_pickle_file,"rb")
            retval = pickle.load(picklefile)
            picklefile.close()
            os.unlink(typecode_pickle_file)
        except IOError:
            retval=None
            
        if retval is not None:
            for record in retval:
                tm.append(record)
            self.status.update("Ready")
        else:
            self.status.update("No available match file.")

    def on_typeCodeEntry_activate(self, button, data):
        #print "On type code entry activated"
        type_code = button.get_text()
        #print button, "text is", type_code
        typecode_query = """
select distinct filename from voteops v join ballots b on v.ballot_id = b.ballot_id where precinct like '%s%%' or code_string like '%s%%' order by filename;""" %  (type_code,type_code)        
        tv = self.builder.get_object("imageListTreeView")
        tm = self.builder.get_object("imageListTreeModel")
                
        tm.clear()
        self.status.update("Locating ballots having type code %s" % (
                type_code,))
        qr = QueryRequestor(
            stdout_cb = self.typecode_data_ready_cb,
            user = const.dbuser,
            database = const.dbname,
            query = typecode_query,
            retfile = typecode_pickle_file)

    def on_sqlEntry_activate(self, button, data):
        """Get a filelist matching an sql condition from the user. """
        # !!!! Protect against injection, if needed
        sql_where_clause = button.get_text()
        sql_where_clause = sql_where_clause.replace(";","")
        sql_query = """
select distinct filename 
from voteops v join ballots b on v.ballot_id = b.ballot_id 
where 
%s
order by filename
""" %  (sql_where_clause,)        
        tm = self.builder.get_object("imageListTreeModel")
        tm.clear()
        self.status.update("Locating ballots where condition %s holds" % (
                sql_where_clause,))
        # Note uses same callback as typecode (as could ambig)
        qr = QueryRequestor(
            stdout_cb = self.typecode_data_ready_cb,
            user = const.dbuser,
            database = const.dbname,
            query = sql_query,
            retfile = typecode_pickle_file)

#*************************************************************************
# Votecount button triggers two database requests, 
# updating GUI table when request calls back.
#*************************************************************************
#*************************************************************************

    def on_showVoteCounts_clicked(self, button, data):
        #print "tevsgui Show vote counts clicked, "
        #print "calling routine in tevsgui_postprocess_db."
        self.postprocess_instance.on_showVoteCounts_clicked(button,data)

    def on_printVoteCounts_clicked(self, button, data):
        self.postprocess_instance.on_printVoteCounts_clicked(button,data)

    def on_buildVariantsTable_clicked(self, button, data):
        self.postprocess_instance.on_buildVariantsTable_clicked(button,data)

    def on_writingToDVD_clicked(self, button, data):
        print "Writing to DVD clicked."
        print "Send the growisofs command to the vte terminal"
        self.vte.feed_child("growisofs -dry-run -Z /dev/dvdrw1 /tmp/fordvd*\n")

    def on_generateSigningKey_clicked(self, button, data):
        print "Generate signing key clicked"
        print "Send gpg --gen-key to the vte terminal"
        self.vte.feed_child("gpg --gen-key\n")

    def on_createDatabaseDump_clicked(self, button, data):
        print "Create database backup clicked"
        try:
            print "Root",const.root
        except:
            pass
        try: 
            print "Dbname",const.dbname
        except:
            pass
        try:
            print "Database",const.database
        except:
            pass
        self.vte.feed_child("pg_dump --create --file %s.sql %s\n" % (
                (os.path.join(const.root, const.dbname), 
                 const.dbname
                 )
                )
                            )

    def on_buildArchive_clicked(self, button, data):
        print "Create archive clicked"
        self.vte.feed_child("tar cvzf /tmp/fordvd.tgz %s\n" % (const.root,))

    def on_signingFiles_clicked(self, button, data):
        print "Signing files clicked"
        print "Send gpg --sign to the vte terminal"
        self.vte.feed_child("gpg --detach-sign /tmp/fordvd.tgz\n")

    def on_cewCloseButton_clicked(self,button,data):
        self.window1.hide()
        self.dialogCEW.hide()

    def on_saveToDVD_clicked(self, button, data):
        #if self.window1 is None:
        if True:
            self.window1 = gtk.Window()
            self.window1.connect("delete-event",on_delete_event)
            self.window1.set_title("TEVS Linux Command Window")
            self.vte = vte.Terminal()
            self.window1.add(self.vte)
            self.vte.fork_command()
            self.dialogCEW = self.builder.get_object("dialogCommandEntryWindow")
            self.dialogCEW.set_title("TEVS Linux Command Assistant")
            self.add_vte_here = self.builder.get_object("add_vte_here")
            
        self.window1.show_all()
        self.dialogCEW.show_all()
        self.window1.present()
        self.dialogCEW.present()
        #self.vte.feed_child("man growisofs\n")

#*************************************************************************
# IMAGE NAVIGATION
#*************************************************************************

    def on_quitbutton_clicked(self, button, data):
        """Go to the current image."""
        gtk.main_quit()

    def on_gotoImage_clicked(self, button, data):
        """Go to the current image."""
        self.on_imageNumberEntry_activate(self.image_number_entry,data)


    def on_nextImage_clicked(self, button, data):
        """Go to the next image, in context if restricted."""
        num_text=self.image_number_entry.get_text()
        num = int(num_text)+const.num_pages
        self.image_number_entry.set_text("%d" % (num,))
        self.on_imageNumberEntry_activate(self.image_number_entry,data)

    def on_prevImage_clicked(self, button, data):
        """Go to the prev image, in context if restricted."""
        num_text=self.image_number_entry.get_text()
        num = int(num_text)-const.num_pages
        num = max(0,num)
        self.image_number_entry.set_text("%d" % (num,))
        self.on_imageNumberEntry_activate(self.image_number_entry,data)

    def on_imageNumberEntry_activate(self, button, data):
        """Go to the image referenced in the entry widget."""
        num_text = button.get_text()
        num = None
        try:
            num = int(num_text)
            num = abs(num)
        except Exception as e:
            self.status.update("Enter a valid number and press Enter.")
        if num is not None:
            num = max(0,num)
        else:
            return
        filename = const.unprocformatstring % (num/1000,num)
        self.update_image_and_data(filename,0)

    def on_nextScanNumber_activate(self, button, data):
        print "On next scan number activated"
        print button, "text is", button.get_text()
        print data
        
    def on_nextScanNoteEntry_activate(self, button, data):
        print "On next scan number activated"
        print button, "text is", button.get_text()
        print data
        
    def on_rootFolder_current_folder_changed(self, button):
        current_folder = button.get_current_folder()
        #print "Current folder",current_folder
        if const.root != current_folder:
            md = gtk.MessageDialog(
                message_format="""For now,
you must manually update root
in tevs.cfg config file.""")
            md.run()
            md.destroy()

#    def on_symlinkFromDirectoryChooser_current_folder_changed(self, button):
#
#        if self.symlinkFromDirectoryChooser_not_yet_called:
#            self.symlinkFromDirectoryChooser_not_yet_called = False
#            #print "On symlinkFromDirectory current folder changed."
#            #print "Returning, because first time"
#            return
#
#        chosen_folder = button.get_current_folder()
#        #print "Current folder",chosen_folder
#        dialog = self.builder.get_object("symlinkFromDialog")
#        root_folder = self.builder.get_object("rootFolder").get_current_folder()
#        response_id = dialog.run()
#            
#        if response_id == 1:
#            try:
#                wildcard = self.builder.get_object(
#                    "symlinkDialog_wildcardEntry").get_text()
#                print "Create symlinks to %s/%s files in %s/unproc tree." % (
#                    chosen_folder,wildcard,root_folder)
#                pathlist = glob.glob("%s/%s" % (chosen_folder,wildcard))
#                index = 0
#                for p in pathlist:
#                    try:
#                        if not os.path.exists(
#                            "%s/unproc/%03d" % (
#                                root_folder,index/1000)
#                            ):
#                            os.makedirs("%s/unproc/%03d" % (
#                                    root_folder,
#                                    index/1000)
#                                        )
#                        if not os.path.exists(
#                            "%s/unproc/%03d/%06d%s" % (
#                                root_folder,
#                                index/1000,
#                                index,
#                                p[p.rindex("."):]
#                                )):
#                            os.symlink(
#                                p,
#                                "%s/unproc/%03d/%06d%s" % (root_folder,
#                                                           index/1000,
#                                                           index,
#                                                           p[p.rindex("."):])
#                                )
#                        index += 1
#                    except ValueError, e:
#                        print e
#            except Exception, e:
#                print e
#            # create symlinks"
#            dialog.hide()

    def on_autoAdvance_seconds_value_changed(self,button,data):
        print "On auto advance seconds value changed."
        print "Value now %d" %(button.get_value_as_int(),)
        print data
        self.aa.seconds_value_changed(self,button,data)

    def showScannerString( self ):
        #process_output = subprocess.Popen(["/usr/bin/scanimage",
        #                                   "--list-devices"],
        #                                  stdout=subprocess.PIPE
        #                                  ).communicate()[0]
        #message = process_output.replace("is a","\nis a")
        #
        #if message.find("No scanner")>-1:
        #    message = """NO SCANNER FOUND.
        #Check cabling and power
        #if you'd like to scan."""
        report = self.scan_requestor.report()
        
        self.builder.get_object("scannerIDLabel").set_text(report['scanner'])

    def scan_requestor_callback(self, status, last_processed):
        self.status.update("%s Last scanned: %s" % (status,last_processed))
        nextnum = last_processed+1
        self.builder.get_object("nextScanNumber").set_text(
            str(nextnum))
        # update nexttoscan file
        util.writeto(os.path.join(const.root,"nexttoscan.txt"),str(nextnum))

        # !!! Need to prevent update of nextScanNumber when under test.
        
    def __init__( self, dbc, logger ):
        # data base connection is handed in on creation
        self.dbc = dbc
        self.logger = logger
        self.scanner = None
        try:
            self.scan_requestor = ScanRequestor(self.scan_requestor_callback)
            self.logger.info("Connected to Scan Service.")
        except ScanRequestorException, sre:
            self.logger.info("Not connected to Scan Service.")
            self.logger.info(sre)
        self.process_ballots_requestor = None
        self.batch_start_number = 0
        self.batch_count_number = 0
        # user interface is in external file tevsgui.glade
        self.builder = gtk.Builder()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
		runpath = os.path.split(__file__)[0]
		gladefile = os.path.join(runpath,"tevsgui.glade")  
                self.builder.add_from_file(gladefile)
            except Exception as e:
                print e, type(e)
                pdb.set_trace()

        self.window = self.builder.get_object ("windowMain")
        self.window.set_title("TEVS November 2013")
        self.symlinkFromDirectoryChooser_not_yet_called = True
        # placeholders for uncreated windows
        self.dialogCEW = None
        self.window1 = None
        self.vte = None

        # set imageList initted True when you first create an image list
        # in response to user request for sublist of images
        self.imageListInitted = False

        self.zoom_value = .30 #slider set to 3.0, value is slider/10

        self.postprocess_instance = tevsgui_postprocess_db.PostProcessDB(
            tevs=self,
            dbc=dbc)
        
        if self.window:
            self.window.connect("destroy", gtk.main_quit)

        self.overlay_votes = self.builder.get_object("overlayVotes")
        self.overlay_stats = self.builder.get_object("overlayStats")
        self.overlay_choices = self.builder.get_object("overlayChoices")
        self.overlay_contests = self.builder.get_object("overlayContests")



        # the root folder widget has as its current_folder value
        # the root folder from the tevs.cfg configuration file,
        # which points to the top of the tree containing unprocessed
        # and processed ballots and results.
        self.root_folder = self.builder.get_object("rootFolder")
        self.root_folder.set_current_folder(util.root())

        # create subfolders of the root, if needed:
        try:
            rootfiles = os.listdir(const.root)
        except:
            try:
                os.makedirs(const.root)
                self.logger.info("Created folder %s" % (const.root,))
            except Exception as e:
                print e
                pdb.set_trace()
        for folder in ("unproc",
                       "proc",
                       "templates",
                       "template_images",
                       "composite_images",
                       "logs",
                       "writeins"):
            if folder not in rootfiles:
                os.makedirs(os.path.join(const.root,folder))
                self.logger.info("Created folder %s" % (
                        os.path.join(const.root,folder),)
                            )


        # last_scanned_number is set to the FIRST (sic) image 
        # of the LAST scanned sheet, as is last_processed_number
        self.last_scanned_number = None
        self.last_processed_number = None

        # the widget displaying "ready to process" should be public
        self.next_to_extract = self.builder.get_object("nextToExtractEntry")
        # the image_number_entry object shows 
        # the number of the image to DISPLAY on exposure or activity
        self.image_number_entry = self.builder.get_object("imageNumberEntry")

        # the next_scan_number_entry object shows
        # the number that will be used for the next image SCANNED
        self.next_scan_number_entry = self.builder.get_object("nextScanNumber")
        # retrieve its initial value from the file nexttoscan.txt in root
        nextscanfile = "%s/nexttoscan.txt" % (util.root(),)
        try:
            nsf = open(nextscanfile,"r")
            nsf_text = nsf.readline().strip()
            nsf.close()
            self.next_scan_number_entry.set_text(nsf_text)
        except:
            self.logger.warning(
                "No next scan number file at %s" % (nextscanfile,))
            try:
                os.mknod(os.path.join(const.root,"nexttoscan.txt"))
                util.writeto(os.path.join(const.root,"nexttoscan.txt"),"0\n")
                self.logger.warning("Created %s with value 0" % (nextscanfile,))
                self.next_scan_number_entry.set_text("0")
            except Exception, e:
                print e

        nexttoprocessfile = os.path.join(const.root,"nexttoprocess.txt")
        try:
            ntp = open(nexttoprocessfile,"r")
            ntp_text = ntp.readline().strip()
            ntp.close()
            self.next_to_extract.set_text(ntp_text)
        except:
            ntp_text = '0'
            os.mknod(nexttoprocessfile)
            util.writeto(os.path.join(nexttoprocessfile), ("%s\n" % ntp_text))
            self.logger.warning(
                "Created %s with value %s" % ((nexttoprocessfile, ntp_text)))

        # If the symlink source folder is changed from the root folder,
        # we create, in the root folder unproc tree, one numbered link 
        # for every image file in the alternate symlink source folder.
        # This allows for easy import of externally built files
        # if they are named sequentially.
        self.symlink_source_folder = self.builder.get_object(
            "symlinkFromDirectoryChooser")
        self.symlink_source_folder.set_current_folder(util.root())
        # This always triggers when widgets are created; disabled for now.
        #self.symlink_source_folder.connect("current_folder_changed",
        #     self.on_symlinkFromDirectoryChooser_current_folder_changed)

        self.rootFolder = self.builder.get_object(
            "rootFolder")
        self.rootFolder.connect("current_folder_changed",
             self.on_rootFolder_current_folder_changed)

        # when toggled on, we have a separate subprocess running
        # which extracts votes from scans
        self.extract_continually = False

        # status is presented to the user via self.status.update("News")
        sb = self.builder.get_object("statusbar1")
        self.status = tevsgui_status.Status(sb)

        # try connecting to a scanner with scanimage;
        # show what scanimage returns 
        try:
            self.showScannerString()
        except Exception as e:
            print e

        # configuration area should always start insensitive
        self.builder.get_object("configurationFrame").set_sensitive(False)

        # we will display different things in the windows based on
        # which page the control notebook is displaying.
        # page numbers are 0 (config), 1 (scan), 2 (process), 3 (display)
        self.control_notebook = self.builder.get_object("notebook1")

        # sw1, sw2 are the two scrolled windows containing drawing areas
        self.sw1 = self.builder.get_object("scrolledwindow1")
        self.sw2 = self.builder.get_object("scrolledwindow2")
        # i1, i2 are the drawing areas
        self.i1,self.i2 = None,None
        # i1window, i2window are the low level drawables in the drawing areas
        self.i1window, self.i2window = None,None
        # leftimage and rightimage are PIL images 
        # containing the files currently requested for display
        self.leftimage, self.rightimage = None, None
        # leftbv and rightbv are the BallotVotes lists 
        # associated with the files currently requested for display
        self.leftbv = None
        self.rightbv = None

        screen_width = gtk.gdk.screen_width()
        screen_height = gtk.gdk.screen_height()

        # left drawing area created within scrolledwindow1
        self.i1gc = None
        self.i1 = gtk.DrawingArea()
        self.i1initimage = gtk.Image()
        self.i1initimage.set_from_file("/home/tevs/Desktop/tevslogo.png")
        self.n1 = BallotAcceptNotes(self,self.window,self.i1,self.dbc)
        # force fixed size for demo
        self.sw1.set_size_request(400,100)
        self.sw1.add_with_viewport(self.i1)
        self.i1window = self.i1.window

        # right scrolled drawing area created within scrolledwindow2
        self.i2gc = None
        self.i2 = gtk.DrawingArea()
        self.n2 = BallotAcceptNotes(self,self.window,self.i2,self.dbc)
	#self.sw2.set_size_request(screen_width/6,screen_height/2)
        self.sw2.add_with_viewport(self.i2)
        self.i2window = self.i2.window

        # have the drawing areas request as many pixels 
        # as there are in their images, but we don't have images yet
        #self.i1.set_size_request(int(0.3*screen_width/6),int(0.3*screen_height/2))
        self.i1.width = int(0.3*screen_width/6)
        self.i1.height = int(0.3*screen_height/6)
        #self.i1.set_size_request(1000,1500)
        #self.i2.set_size_request(1000,1500)
        self.i1.show()
        self.i2.show()

        try:
            self.leftimage = Image.open("/tmp/left.jpg")
            self.rightimage = Image.open("/tmp/right.jpg")
        except:
            self.leftimage = Image.new("RGB",(500,700),(255,0,0))
            self.rightimage = Image.new("RGB",(501,701),(0,0,255))
        self.i1.connect("expose_event",self.expose_cb,0)
        self.i1.connect("configure-event",self.configure_cb, 0)
        self.i2.connect("expose_event",self.expose_cb,1)
        self.i2.connect("configure-event",self.configure_cb, 1)

        self.i1.add_events(gtk.gdk.EXPOSURE_MASK
                            | gtk.gdk.LEAVE_NOTIFY_MASK
                            | gtk.gdk.BUTTON_PRESS_MASK
                            | gtk.gdk.POINTER_MOTION_MASK
                            | gtk.gdk.POINTER_MOTION_HINT_MASK
                           | gtk.gdk.KEY_PRESS_MASK)
        self.i2.add_events(gtk.gdk.EXPOSURE_MASK
                            | gtk.gdk.LEAVE_NOTIFY_MASK
                            | gtk.gdk.BUTTON_PRESS_MASK
                            | gtk.gdk.POINTER_MOTION_MASK
                            | gtk.gdk.POINTER_MOTION_HINT_MASK
                           | gtk.gdk.KEY_PRESS_MASK)

        # set toggles to initial values spec'd in config file:
        self.builder.get_object("doubleSided").set_active(const.num_pages==2)
        self.builder.get_object("singleSided").set_active(const.num_pages==1)
        self.builder.get_object("lowRes150").set_active(const.dpi==150.)
        self.builder.get_object("hiRes300").set_active(const.dpi==300.)

        # set sliders to initial values spec'd in config file
        for text,val in (("widthAdjustment",const.ballot_width_inches*100),
                     ("heightAdjustment",const.ballot_height_inches*100),
                     ("imprintOffsetAdjustment",const.imprint_offset_inches*100.),
                     ("zoomAdjustment",3.)
                         ):

            scale = self.builder.get_object(text.replace("Adjustment","Scale"))
            adj = self.builder.get_object(text)
            adj.set_value(val)
            scale.set_value(val)

        # set up for auto-pressing the "nextImage" button
        self.nextImage = self.builder.get_object("nextImage")
        self.aa = AutoAdvance(self.nextImage)


        # MAY NEED A WAY TO MAKE SURE 
        # EVERYTHING ABOVE HAS COMPLETED
        # PRIOR TO REGISTERING CALLBACKS
        # We keep landing, bizarrely, in on_symlinkFromDirectoryChooser_set_file
        # Standard way of setting up callbacks, didn't work for us
        #dic = {
        #    "on_buttonQuit_clicked" : self.quit,
        #    "on_buttonAdd_clicked" : self.add,
        #    "on_buttonAdd_activate" : self.add,
        #    "on_windowMain_destroy" : self.quit,
        #    }
        #self.builder.connect_signals( dic )

        connex = ( 
            ("widthAdjustment",            #object name to GtkBuilder XML
             "on_widthAdjustment_changed", #signal in builder, not used
             "value-changed",              # signal
             self.on_widthAdjustment_changed), #callback in program
            ("heightAdjustment",
             "on_heightAdjustment_changed", 
             "value-changed", 
             self.on_heightAdjustment_changed),
            ("zoomAdjustment",
             "on_zoomAdjustment_changed", 
             "value-changed", 
             self.on_zoomAdjustment_changed),
            ("imprintOffsetAdjustment",
             "on_imprintOffsetAdjustment_changed", 
             "value-changed", 
             self.on_imprintOffsetAdjustment_changed),
            ("autoAdvance",
             "NI",
             "toggled",
             self.on_autoAdvance_toggled),
            ("autoAdvanceSeconds",
             "NI",
             "value-changed",
             self.on_autoAdvance_seconds_value_changed),
            ("overlayVotes",
             "NI",
             "toggled",
             self.on_overlayVotes_toggled),
            ("overlayStats",
             "NI",
             "toggled",
             self.on_overlayStats_toggled),
            ("overlayContests",
             "NI",
             "toggled",
             self.on_overlayContests_toggled),
            ("overlayChoices",
             "NI",
             "toggled",
             self.on_overlayChoices_toggled),
            ("ambigOnly",
             "NI",
             "toggled",
             self.on_ambigOnly_toggled),
            ("extractAsArrive",
             "NI",
             "toggled",
             self.on_extractAsArrive_toggled),
            ("configurationLock",
             "NI",
             "toggled",
             self.on_configurationLock_toggled),
            ("doubleSided",
             "NI",
             "toggled",
             self.on_doubleSided_toggled),
            ("singleSided",
             "NI",
             "toggled",
             self.on_singleSided_toggled),
            ("lowRes150",
             "NI",
             "toggled",
             self.on_lowRes150_toggled),
            ("hiRes300",
             "NI",
             "toggled",
             self.on_hiRes300_toggled),
            ("imprintOn",
             "NI",
             "toggled",
             self.on_imprintOn_toggled),
            ("imprintOff",
             "NI",
             "toggled",
             self.on_imprintOff_toggled),
            ("searchForScanner",
             "NI",
             "clicked",
             self.on_searchForScanner_clicked),
            ("symlinkDialog_okButton",
             "NI",
             "clicked",
             self.on_symlinkDialog_okButton_clicked),
            ("scanStart",
             "NI",
             "clicked",
             self.on_scanStart_clicked),
            ("scanRequestStop",
             "NI",
             "clicked",
             self.on_scanRequestStop_clicked),
            ("testScan",
             "NI",
             "clicked",
             self.on_testScan_clicked),
            ("extractNow",
             "NI",
             "clicked",
             self.on_extractNowXMLRPC_clicked),
            ("lastExtractedAllowUpdate",
             "NI",
             "clicked",
             self.on_lastExtractedAllowUpdate_clicked),
            ("extractEnd",
             "NI",
             "clicked",
             self.on_extractEnd_clicked),
            ("buildVariantsTable",
             "NI",
             "clicked",
             self.on_buildVariantsTable_clicked),
            ("showVoteCounts",
             "NI",
             "clicked",
             self.on_showVoteCounts_clicked),
            ("cewSaveToDVD",
             "NI",
             "clicked",
             self.on_saveToDVD_clicked),
            ("cewCloseButton",
             "NI",
             "clicked",
             self.on_cewCloseButton_clicked),
            ("cewGenerateSigningKey",
             "NI",
             "clicked",
             self.on_generateSigningKey_clicked),
            ("cewCreateDatabaseDump",
             "NI",
             "clicked",
             self.on_createDatabaseDump_clicked),
            ("cewBuildArchive",
             "NI",
             "clicked",
             self.on_buildArchive_clicked),
            ("cewSigningFiles",
             "NI",
             "clicked",
             self.on_signingFiles_clicked),
            ("cewWritingToDVD",
             "NI",
             "clicked",
             self.on_writingToDVD_clicked),
            ("gotoImage",
             "NI",
             "clicked",
             self.on_gotoImage_clicked),
            ("quitbutton",
             "NI",
             "activate",
             self.on_quitbutton_clicked),
            ("prevImage",
             "NI",
             "clicked",
             self.on_prevImage_clicked),
            ("nextImage",
             "NI",
             "clicked",
             self.on_nextImage_clicked),
            ("imageNumberEntry",
             "NI",
             "activate",
             self.on_imageNumberEntry_activate),
            ("typeCodeEntry",
             "NI",
             "activate",
             self.on_typeCodeEntry_activate),
            ("sqlEntry",
             "NI",
             "activate",
             self.on_sqlEntry_activate),
            ("nextScanNumber",
             "NI",
             "activate",
             self.on_nextScanNumber_activate),
            ("nextScanNoteEntry",
             "NI",
             "activate",
             self.on_nextScanNoteEntry_activate),
        )
        for x in connex:
            try:
                self.builder.get_object(x[0]).connect(x[2],x[3],None)
            except Exception, e:
                print x
                print e
                #pdb.set_trace()
        self.status.update("Ready")
        copyright = gtk.MessageDialog(
            flags=gtk.DIALOG_MODAL,type=gtk.MESSAGE_INFO,
            buttons=gtk.BUTTONS_OK,
            message_format = """TEVS is not finished.  

TEVS is free, open source software for vote counting, licensed 
under the terms of the GNU GPL, version 2.0 as found at 
http://www.gnu.org/licenses/gpl-2.0.html

TEVS is Copyright 2009-2013 Mitch Trachtenberg

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

Click OK to continue, accepting the terms and accept these terms.

Questions? Email the author at mjtrac@gmail.com
""")
        copyright.run()
        copyright.destroy()
  
    def quit(self, widget):
        sys.exit(0)
        

def run_tevs():
    # enable use of threads in tevsgui_xmlrpc_processing_requestor.py
    gobject.threads_init()
    # read configuration from tevs.cfg and set constants for this run
    cfg_file = tevsgui_get_args.get_args()
    if not os.path.isabs(cfg_file):
        cfg_file = os.path.join(os.path.expanduser("~"),cfg_file)
    config.get(cfg_file)
    logger = config.logger(const.logfilename)

    proc = util.root("proc")
    results = util.root("results")
    const.procformatstring = proc + "/%03d/%06d" + const.filename_extension
    const.unprocformatstring = const.incoming + "/%03d/%06d" + const.filename_extension
    const.resultsformatstring = results + "/%03d/%06d" + ".txt"
    # set up db connection and pass to gui
    dbc = None
    if const.use_db:
        dbc = initialize_database()
    gui = tevsGui(dbc,logger)
    gui.window.show()
    gtk.main()


if __name__ == "__main__":
    run_tevs()


