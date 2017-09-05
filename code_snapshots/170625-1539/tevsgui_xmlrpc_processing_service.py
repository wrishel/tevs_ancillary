# tevsgui_xml_processing_service.py
import datetime
import os
import gc
import logging
import BallotClass
from BallotSide import BallotSide, LayoutCache, prepopulate_cache, BallotSideException
import BallotVOPtoDB as db
import config
import const
import socket
import sys
import util
import SocketServer
from SimpleXMLRPCServer import SimpleXMLRPCServer,SimpleXMLRPCRequestHandler
from time import sleep
import tevsgui_get_args
bv = None
bsv = None

# Threaded mix-in
class AsyncXMLRPCServer(SocketServer.ThreadingMixIn,SimpleXMLRPCServer): pass
 
# Example class to be published
class ProcessBallots(object):
    def __init__(self,root,bv,bsv,dbc):
        self.root = root
        self.bv = bv
        self.bsv = bsv
        self.dbc = dbc

    def test_process(self,starting_at, how_many):
        return "Test starting at %d how many %d" % (starting_at, how_many)

    def test_talk(self,number):
        return "Test talk with number %d" % (number,)

    def process_ballot(self,number):
        #sleep(0.2)
        if (number%50)==0: 
            print "Collecting garbage."
            gc.collect()
        image_filename = os.path.join(const.root,"unproc/%03d/%06d.jpg" % (number/1000,number))
        logging.info("About to process %s" % (image_filename,))
        #b = bv("/home/mitch/data/hart/unproc/000/000001.jpg",None)
        try:
            # to test failure, raise an exception
            #raise BallotServerException("You blew it because...")
            b = self.bv(image_filename,None)
            simplex_results = b.ProcessBallot(self.dbc)
        except BallotSideException as e:
            logging.error("%s FAILED to process number %d." % (e,number,))
            # The return on a failure MUST consist of the literal "FAIL," 
            # followed by the error message to be displayed at the GUI
            return "FAIL, %s" % (e,)
        except Exception as e:
            logging.error("FAILED to process number %d." % (number,))
            # The return on a failure MUST consist of the literal "FAIL," 
            # followed by the error message to be displayed at the GUI
            return "FAIL, %s" % (e,)
        logging.info("Processed number %d ok." % (number,))
        return number
 
def run_server():
    cfg_file = tevsgui_get_args.get_args()
    config.get(cfg_file)
    logfile = os.path.join(const.root,"logs/processing_log.txt")
    bv = BallotClass.LoadBallotFactoryForVendorStyle(const.layout_brand)
    bsv = BallotClass.LoadBallotSideFactoryForVendorStyle(const.layout_brand)

    logging.basicConfig(filename=logfile,
                        format = '%(asctime)s %(levelname)s %(module)s %(message)s',
                        level=logging.INFO)
    logging.info("Processing server starting.")

    prepopulate_cache()

    # establish a connection to the database
    # connect to db and open cursor
    dbc = None
    if const.use_db:
        try:
            dbc = db.PostgresDB(database=const.dbname, user=const.dbuser)
        except db.DatabaseError:
            util.fatal("Could not connect to database!")
    else:
        dbc = db.NullDB()


    # Instantiate and bind to localhost:8000
    try:
        server = AsyncXMLRPCServer(('', 8000), SimpleXMLRPCRequestHandler)
    except socket.error as e:
        print "A service is already running on address 8000."
        sys.exit()
    # Register example object instance
    server.register_instance(ProcessBallots(const.root,bv,bsv,dbc))
    print "Ballot processing / scraping service now ready on address 8000."
    print "Using %s as root directory." % (const.root,)
    # run!
    server.serve_forever()

if __name__ == "__main__": 
    run_server()


