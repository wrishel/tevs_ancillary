# replacing tevsgui_processing_requestor.py using xmlrpc
# part of TEVS

"""
xmlrpc_client.py demonstrates how we can launch an XMLRPC call 
from within a thread, allowing our GUI to continue, then retrieve
the call results once it has completed.
"""

import xmlrpclib
import threading
import gobject
import socket
import logging
import pdb
class ProcessBallotsException(Exception):
    pass

class MyData(object):
    retval = None

class ProcessBallotsRequestor(object):
    """ launch a thread to process a ballot, register a callback to get data"""
    def __init__(self,cb_func,number_widget):
        self.proceed = False
        self.logger = logging.getLogger(__name__)
        try:
            self.xmlserver = xmlrpclib.ServerProxy('http://localhost:8000')
            self.logger.info("Connected to processing service.")
        except socket.error, e:
            self.logger.error("Socket error connecting to processing service.")
            self.logger.error(e)
            raise ProcessBallotsException(e)
        self.cb_func = cb_func
        self.idle = None
        self.thread = None
        self.lastdata = None
        self.number = None
        self.number_widget = number_widget
        

    def process(self,number=None):

        if not self.proceed:
            return False
        if number is not None:
            self.number = number
        if self.thread is not None:
            print "(Thread already in progress. Returning.)"
            return
        """print ""Starting thread to get text.  
The thread will call a function in xmlrpc_server.py.  
This could be a request for the next ballot's results or,
more likely, a request for the success or failure of the ballot's 
processing cycle, with any errors reported."""
        self.threaddata = MyData()
        self.threaddata.retval = None
        self.thread = threading.Thread(target=self.sendcommand,args=(self.number,self.threaddata))
        self.thread.start()
        self.idle = gobject.idle_add(self.got_return)
        #print "Now returning control to GUI, having stored got_return as our idle id %s" % (self.idle)
        #print "In got_return, we check to see whether the thread has finished."
        return False

    def got_return(self):
        if not self.thread.isAlive():
            #print "Thread has returned",self.threaddata.retval
            gobject.source_remove(self.idle)
            self.idle = None
            self.thread = None
            #print "And we've reset the thread and idle id to None."
            # It is the callback's responsibility to handle
            # anything associated with successful processing
            # or failed processing (updating the tracking file, moving the
            # processed files, etc...)
            self.cb_func(self)
            return False
        return True

    def sendcommand(self,number,data):
        #print "sending command process_ballot",number
        self.threaddata.retval = self.xmlserver.process_ballot(number)
        
if __name__ == "__main__":
    pass
