# tevsgui_xml_scanning_server.py

import SocketServer
from SimpleXMLRPCServer import SimpleXMLRPCServer,SimpleXMLRPCRequestHandler
from time import sleep

# Threaded mix-in
class AsyncXMLRPCServer(SocketServer.ThreadingMixIn,SimpleXMLRPCServer): pass

import threading
import thread
import sane
import _sane
import pdb
import logging
import sys
import socket
import tevsgui_get_args
"""
In this example, we are providing a response to the XMLRPC request after 
two seconds, but in addition to sending our response, we start up an
additional thread which will only print after an additional five seconds.

The print is not communicated back to our client, but it does take place.

This is equivalent to immediately acknowledging a request 
to scan or process a ballot, but spawning the scanprocess in 
another function.

On a subsequent request, we can return our current state (still scanning,
up to this number).
"""


# Example class to be published
class ScanService(object):
    def __init__(self):
        self.imgs = []
        self.settings = {}
        sane.init()
        try:
            for device in sane.get_devices():
                if device[3] == 'scanner':
                    self.scanner_device = sane.get_devices()[0][0]
            self.scanner = sane.open(self.scanner_device)
        except:
            self.settings['status'] = "NO SCANNER"
            print self.settings['status']
            self.scanner = None
            return None
        self.settings['dpi'] = 100
        self.settings['scanner'] = self.scanner_device
        self.settings['page_height'] = int(25.4 * 11.0) 
        self.settings['br_y'] = int(25.4 * 11.0) 
        self.settings['page_width'] = int(25.4 * 8.5) 
        self.settings['br_x'] = int(25.4 * 8.5) 
        self.settings['duplex'] = True
        self.settings['imprinter'] = False
        self.settings['note'] = "No note."
        self.settings['status'] = "OK"
        self.settings['last'] = 0
        self.settings['last_processed'] = -1
        self.settings['status'] = "OK"
        self.scanner.resolution = self.settings['dpi']
        self.scanner.mode = 'Color'
        if self.settings['duplex']:
            self.scanner.source = 'ADF Duplex'
        else:
            self.scanner.source = 'ADF Front'
        logging.info( "Scanner is %s resolution %s mode %s source %s" % (self.scanner_device,self.scanner.resolution,self.scanner.mode,self.scanner.source))
        print "Scanner is %s resolution %s mode %s source %s" % (
            self.scanner_device,
            self.scanner.resolution,
            self.scanner.mode,
            self.scanner.source)
        return None

    def get_settings(self):
        return self.settings

    def get_settings_splitbytype(self):
        retval_active_nonset = ["ACTIVE NOT SETTABLE"]
        retval_active = ["ACTIVE"]
        retval_inactive = ["NOT ACTIVE"]
        if self.scanner is None:
            return "No scanner"
        keys = self.scanner.opt.keys()
        for k in keys:
            if self.scanner.opt[k].is_active():
                if self.scanner.opt[k].is_settable():
                    retval_active.append(k)
                else:
                    retval_active_nonset.append(k)
            else:
                retval_inactive.append(k)
        return (retval_active,retval_active_nonset,retval_inactive)

    def set_settings(self, x, y) :
        try:
            self.settings[x]=y
        except:
            print "Could not set",x,"to",y
            return False
        try:
            if x == "resolution":
                self.scanner.resolution = int(y)
                print self.scanner.resolution
            if x == "duplex":
                if y:
                    self.scanner.source = 'ADF Duplex'
                    print self.scanner.source
                else:
                    self.scanner.source = 'ADF Front'
                    print self.scanner.source
            if x == "endorser":
                if y:
                    self.scanner.endorser = True
                    print self.scanner.endorser
                else:
                    self.scanner.endorser = False
                    print self.scanner.endorser
            if x == "page_height" :
                self.scanner.page_height = int(.254*y)
                print self.scanner.opt['page_height']
                self.scanner.br_y = int(.254*y)
                print self.scanner.opt['br_y']
            if x == "page_width" :
                self.scanner.page_width = int(.254*y)
                print self.scanner.opt['page_width']
                self.scanner.br_x = int(.254*y)
                print self.scanner.opt['br_x']
            #if x == "endorser_y" and self.scanner.endorser:
            #    self.scanner.endorser_y = int(y)
            #    print self.scanner.opt['endorser_y']
            if x == "endorser_val" and self.scanner.endorser:
                print "x",x,"y",y
                self.scanner.endorser_val = int(y)
                print self.scanner.opt['endorser_val']
            elif x == "endorser_val" and not self.scanner.endorser:
                print "NOT setting x",x,"y",y
                #self.scanner.endorser_val = int(y)
                print self.scanner.opt['endorser_val']
            if x == "endorser_string" and self.scanner.endorser:
                print "x",x,"y",y
                self.scanner.endorser_string = str(y)
                print self.scanner.opt['endorser_string']
            elif x == "endorser_string" and not self.scanner.endorser:
                print "NOT setting x",x,"y",y
                print self.scanner.opt['endorser_string']
            else: 
                return False
        except:
            return False
        return True

    def report(self):
        sleep(0.1)
        return self.settings

    def scan(self, x, y) :
        # do without threading
        try:
            logging.info("Setting counter to %s" % (x,))
            start = int(x)
            counter = int(x)
            errcounter = 0
            failnum = None
            self.settings['status']="OK"
            self.imgs = []
            while (counter < (start+1) and errcounter < 1):
                try:
                    if self.settings['endorser']:
                        self.scanner.endorser_val = int(x)
                    self.scanner.start()
                    if self.settings['duplex']:
                        self.imgs.append(self.scanner.snap(no_cancel=True))
                        self.scanner.start()
                    self.imgs.append(self.scanner.snap())

                except Exception, e2:
                    print "Non-SANE exception",e2
                except _sane.error, e2:
                    errstr = "SCANNER ISSUE %s" % (e2,)
                    print errstr
                    self.settings['status'] = errstr
                    self.imgs = []

                    # added but untested 5/29/12 mjt !!!
                    self.scanner.cancel()

                    break
                for image in self.imgs:
                    try:
                        location = self.settings['save_location'] % (
                                counter/1000,
                                counter)#%1000)
                        logging.info( "Saving %s" % (location,))
                        image.save(location)
                        counter += 1
                    except Exception, e:
                        print e
                self.imgs = []
                self.settings['status'] = "OK"
                self.settings['last_processed']=x
        except Exception, e:
            print e
        finally:
            pass
        return self.settings
 
 
if __name__ == "__main__": 
    # Instantiate and bind to localhost:8001
    import sys
    import os
    import config
    import const
    cfg = tevsgui_get_args.get_args()
    config.get(cfg)
    try:
        server = AsyncXMLRPCServer(('', 8001), SimpleXMLRPCRequestHandler)
    except socket.error as e:
        print "A service is already running on address 8001."
        sys.exit()
    logging.basicConfig(filename=os.path.join(const.root,"logs/scanning_log.txt"),
                        format = '%(asctime)s %(levelname)s %(module)s %(message)s',
                        level=logging.DEBUG)
    logging.info("Scan server starting.")
    # Register example object instance
    server.register_instance(ScanService())
    print "Using %s as root directory." % (const.root,)

    server.serve_forever()
 

