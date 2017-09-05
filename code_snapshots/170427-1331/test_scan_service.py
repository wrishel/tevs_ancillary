# test_scan_service.py is part of TEVS
# TEVS, Trachtenberg Election Verification System
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

import config
import const
import tevsgui_get_args
from tevsgui_xmlrpc_scanning_requestor import ScanRequestor, ScanRequestorException

class gui(object):
    """Click to start scanner, click to stop scanner"""
    
    def scan_requestor_callback(self,arg2,arg3):
        "Called when scan_requestor has completed saving a scan."
        print "Scan requestor callback %s %s, setting counter to %s " % (
            arg2, arg3, arg3)
        self.logger.info( 
            "Scan requestor callback %s %s,setting counter to %s" % (
                arg2, arg3, arg3) )
        
    def exit_test(self,widget,data):
        print "Exit button clicked"
        gtk.main_quit()

    def delete_event(self,widget,data):
        print "Delete event received"
        gtk.main_quit()

    def res_150(self,widget,counter):
        print "Setting scan_requestor resolution to 150"
        self.logger.info("Setting scan_requestor resolution to 150.")
        self.scan_requestor.set_resolution(150)

    def res_300(self,widget,counter):
        print "Setting scan_requestor resolution to 300"
        self.logger.info("Setting scan_requestor resolution to 300.")
        self.scan_requestor.set_resolution(300)

    def imprint_on(self,widget,counter):
        print "Setting scan_requestor imprint on"
        self.logger.info("Setting scan_requestor imprint on.")
        self.scan_requestor.set_endorser(True)

    def imprint_value(self,widget,counter):
        print "Setting scan_requestor imprint value"
        self.logger.info("Setting scan_requestor imprint value to .")
        self.scan_requestor.set_endorser_val(876)

    def stop_scan(self,widget,counter):
        "Called to prevent a NEW scanning operation when one completes."
        print "Setting scan_requestor.proceed to False."
        self.logger.info("Setting scan_requestor.proceed to false.")
        self.scan_requestor.proceed = False

    def do_scan(self,widget,counter):
        "Called to start a continuing series of scanning operations."
        print "Calling scan_requestor.do_scan with %d" % (int(self.counter),)
        self.logger.info(
            "Calling scan_requestor.do_scan with %d" % (int(self.counter),))
        self.scan_requestor.do_scan(self.counter)
        # get the new counter value back in scan_requestor's callback arg3
        #self.counter += 1

    def __init__(self,logger):
        "Assemble and present the test GUI"
        self.logger = logger

        try:
            self.scan_requestor = ScanRequestor(self.scan_requestor_callback)
            self.logger.info("Connected to Scan Service.")
        except ScanRequestorException, sre:
            self.logger.info("Not connected to Scan Service.")
            self.logger.info(sre)

        self.counter = 1

        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.connect("delete_event",self.delete_event)

        self.hbox = gtk.HBox()
        self.button1 = gtk.Button("Do scan")
        self.button1.connect("clicked",self.do_scan,self.counter)
        self.button2 = gtk.Button("Stop scan")
        self.button2.connect("clicked",self.stop_scan,self.counter)
        self.button3 = gtk.Button("Exit test")
        self.button3.connect("clicked",self.exit_test,None)
        self.button4 = gtk.Button("Res150")
        self.button4.connect("clicked",self.res_150,None)
        self.button5 = gtk.Button("Res300")
        self.button5.connect("clicked",self.res_300,None)
        self.button6 = gtk.Button("Imprint On")
        self.button6.connect("clicked",self.imprint_on,None)
        self.button7 = gtk.Button("Imprint Value")
        self.button7.connect("clicked",self.imprint_value,None)
        self.window.add(self.hbox)
        self.hbox.pack_start(self.button1)
        self.hbox.pack_start(self.button2)
        self.hbox.pack_start(self.button3)
        self.hbox.pack_start(self.button4)
        self.hbox.pack_start(self.button5)
        self.hbox.pack_start(self.button6)
        self.hbox.pack_start(self.button7)
        self.hbox.show()
        self.button1.show()
        self.button2.show()
        self.button3.show()
        self.button4.show()
        self.button5.show()
        self.button6.show()
        self.button7.show()
        self.window.show()

if __name__ == "__main__":
    gobject.threads_init()
    cfg_file = tevsgui_get_args.get_args()
    config.get(cfg_file)
    logger = config.logger(const.logfilename)

    myGui = gui(logger)

    gtk.main()
