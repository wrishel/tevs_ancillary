# tevsgui_xmlrpc_scanning_requestor.py using xmlrpc
# part of TEVS
"""
The ScanServer must publish three functions
set_settings (we supply item string and value)
report (we supply item string)
scan (we supply filename format and starting number)
"""
import xmlrpclib
import threading
import gobject
import logging
import pdb

class ScanRequestorException(Exception):
    pass

class MyData(object):
    def __init__(self):
        self.retval = None

class ScanRequestor(object):
    def __init__(self,callback,suppress_increment=False):
        self.proceed = True
        self.last_request = -1
        self.last_processed = -1
        self.suppress_increment = suppress_increment
        try:
            self.xmlserver = xmlrpclib.ServerProxy('http://localhost:8001')
        except Exception, e:
            raise ScanRequestorException(e)
        self.call_scanner_id = None
        self.get_done_id = None
        self.thread = None
        self.threaddata = None
        self.last_status = "OK"
        self.callback = callback
        self.local_duplex = False
        self.logger = logging.getLogger('')
        try:
            print self.xmlserver.get_settings()
        except Exception, e:
            raise ScanRequestorException(e)
        
    def do_stop_scan(self):
        self.proceed = False

    def do_scan(self,this_number):
        # register call_scanner
        self.proceed = True
        self.last_request = this_number
        self.call_scanner_id = gobject.timeout_add(100,self.call_scanner, this_number)
        
    def report(self):
        retval = self.xmlserver.report()
        self.logger.info(retval)
        return retval

    def set_resolution(self,arg):
        self.logger.info("Setting resolution to %s int" % (arg,))
        print "set resolution"
        self.xmlserver.set_settings("resolution",int(arg))

    def set_save_location(self,arg):
        self.logger.info("Setting save location format string to %s %s" % (
                arg,type(arg)))
        self.xmlserver.set_settings("save_location",arg)

    def set_page_height(self,arg):
        self.logger.info("Setting page height to %s int" % (arg,))
        self.xmlserver.set_settings("page_height",int(arg))

    def set_page_width(self,arg):
        print "set page_width"
        self.logger.info("Setting page width to %s int" % (arg,))
        self.xmlserver.set_settings("page_width",int(arg))

    def set_duplex(self,arg):
        self.logger.info("Setting duplex to %s bool" % (arg,))
        self.local_duplex = bool(arg)
        self.xmlserver.set_settings("duplex",bool(arg))

    def set_endorser(self,arg):
        self.logger.info("Setting endorser to %s bool" % (arg,))
        self.xmlserver.set_settings("endorser",bool(arg))

    def set_endorser_val(self,arg):
        self.logger.info("Setting endorser_val to %s int" % (arg,))
        self.xmlserver.set_settings("endorser_val",int(arg))

    def set_endorser_y(self,arg):
        self.logger.info("Setting endorser_y to %s int" % (arg,))
        self.xmlserver.set_settings("endorser_y",int(arg))

    def set_endorser_string(self,arg):
        self.logger.info("Setting endorser_string to %s str" % (arg,))
        retval = self.xmlserver.set_settings("endorser_string",str(arg))

    def call_scanner(self,this_number):
        # allow only one active request thread in HelloWorld
        if self.thread is not None:
            print "Thread is not none, returning."
            return
        self.idle = gobject.idle_add(self.got_scan_return)
        self.logger.debug("call_scanner registering idle func got_scan_return")
        self.threaddata = MyData()
        self.thread = threading.Thread(
                target=myscan,
                args=(this_number,
                      this_number,
                      self.xmlserver,
                      self.threaddata))
        self.logger.debug("Call scanner registering myscan with this_number %s as arguments 0 and 1 and self.xmlserver %s and self.threaddata %s " % (
                this_number,self.xmlserver,self.threaddata))
        self.thread.start()

    def got_scan_return(self):
        if self.thread.isAlive(): return True
        # clear thread and threaddata fields as soon as XMLRPC completes; 
        # watch for update of scanner status 
        # by polling scanner for increment of last_processed status field
        self.logger.debug("In got_scan_return after thread death.")
        self.thread = None
        self.threaddata = None
        self.logger.debug("In got_scan_return registering get_done as timeout.")
        self.get_done_id = gobject.timeout_add(1000,self.get_done, self)
        return False

    def get_done(self,whatsthis):
        # will be called repeatedly until it returns false
        retval = True
        self.logger.debug("In got_done, retrieving last_processed from xmlserver dictionary.")
        x = self.xmlserver.get_settings()
        if type(x)==str:
            print x
            return False
        if type(x)==list:
            print x
            return False
        self.last_processed = int(x['last_processed'])
        status = x['status']
        self.logger.debug("self.last request %s self.last_processed %s status %s" % (self.last_request,self.last_processed,status)) 
        if status <> "OK":
            self.logger.debug("Calling registered callback.")
            self.callback(status,self.last_processed)
            self.logger.debug("setting retval false, will not register new scan.")
            retval = False
        if True:#self.last_processed >= int(self.last_request):
            retval = False
            if status == "OK":
                self.logger.debug("Calling registered callback, status OK.")
                self.callback("OK",self.last_processed)
                # set last_request only on actual request via do_scan
                if not self.suppress_increment:
                    if self.local_duplex:
                        self.last_request = self.last_processed + 2
                    else:
                        self.last_request = self.last_processed + 1
                    self.logger.debug("Incrementing 'last_request' to %d" % (
                            self.last_request))
                else:
                    self.logger.warning("Suppressing increment of last_processed.")
                if self.proceed:
                    self.call_scanner_id = gobject.timeout_add(
                        100,self.call_scanner, self.last_request)
                    # mjt 4/3/12 had been self.last_processed+1)
        else:
            self.logger.error("self.last_processed < self.last_request, why?")
            print "self.last_processed less than self.last_request, why?"
            return False
        return retval


def myscan(a,b,s,data):
    x =  s.scan(a,b)
    data.retval = x
    return x

def test_callback(status,number):
    print "Test Callback: status %s, number %d" % (status,number)
    if number > 45:
        print "Returned number > 45, exiting test."
        sys.exit(0)

if __name__ == "__main__":
    import sys
    import gtk
    import pygtk
    import pdb
    try:
        sr = ScanRequestor(test_callback)
    except ScanRequestorException as e:
        print "Problem creating scan requestor."
        print e
        sys.exit(0)

    print "MAIN TEST ROUTINE setting resolution, \nthen save loc, then duplex, endorser, endorser_val, endorser_string, endorser_y"
    sr.set_resolution(300)
    sr.set_save_location("saving to %03d/%06d")
    sr.set_duplex(True)
    sr.set_endorser(True)
    sr.set_endorser_val(4242)
    sr.set_endorser_string("Endorser")
    sr.set_endorser_y(420)
    print "MAIN TEST ROUTINE calling report"
    sr.report()
    print "MAIN TEST ROUTINE initiating scan with number 42"
    sr.do_scan(42)
    print "MAIN TEST ROUTINE calling gtk.main"
    gtk.main()
