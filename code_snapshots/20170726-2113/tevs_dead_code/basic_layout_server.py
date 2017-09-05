import xmlrpclib
from SimpleXMLRPCServer import SimpleXMLRPCServer

def get_layout(name,landmarks):
    return "FROMPROXY %s %s" % (name,landmarks)

server = SimpleXMLRPCServer(("localhost",8000))
print "listening on port 8000..."
server.register_function(get_layout,"get_layout")
server.serve_forever()
