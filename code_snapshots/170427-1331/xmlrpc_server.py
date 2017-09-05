import os
import logging
import BallotClass
from BallotSide import BallotSide, LayoutCache
import BallotVOPtoDB as db
import config
import const
import sys
import util
import pdb

import SocketServer
from SimpleXMLRPCServer import SimpleXMLRPCServer,SimpleXMLRPCRequestHandler
from time import sleep

bv = None
bsv = None

class BallotServerException(Exception): pass

# Threaded mix-in
class AsyncXMLRPCServer(SocketServer.ThreadingMixIn,SimpleXMLRPCServer): pass
 
# Example class to be published
class TestObject:
    def talk(self, number):
        b = bv("/home/mitch/data/diebold/unproc/000/000001.jpg",None)
        try:
            # to test failure, raise an exception
            raise BallotServerException("You blew it because...")
            simplex_results = b.ProcessBallot(dbc)
        except Exception, e:
            return "FAIL e=%s" % (e,)
        #retstr = ""
        #for x in simplex_results:
        #    retstr += x.__repr__()
        return "OK"

if __name__ == "__main__": 
    config.get()
    bv = BallotClass.LoadBallotFactoryForVendorStyle(const.layout_brand)
    bsv = BallotClass.LoadBallotSideFactoryForVendorStyle(const.layout_brand)

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
    server = AsyncXMLRPCServer(('', 8000), SimpleXMLRPCRequestHandler)
 
    # Register example object instance
    server.register_instance(TestObject())
 
    # run!
    server.serve_forever()



