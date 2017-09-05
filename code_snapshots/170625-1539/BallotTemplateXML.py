# BallotTemplate.py
# part of TEVS

import const

from xml.dom import minidom, Node
from xml.parsers.expat import ExpatError
import pdb
from BallotRegions import Point, Box, Region, Landmarks, Layout
from BallotSide import Jurisdiction, Contest, Choice, VOP, WriteIn
def TemplateFromXML(xml): 
    """Takes an XML string generated from Template_to_XML and returns a
    Template"""
    doc = minidom.parseString(xml)
    return doc

# can be page?
BlankTemplate = TemplateFromXML("""<?xml version="1.0"?>
<BallotSide></BallotSide>""")

def ParseSubtree(node):
    # deal with attributes of node, create Node object
    if node.nodeType != Node.ELEMENT_NODE:
        return
    print "Node",node
    if node.hasAttributes():
        attributes = node.attributes
        for x in range(attributes.length):
            n = attributes.item(x)
            print " Attr %s=%s;"% (n.name, n.value),
        print
    for n in node.childNodes:
        ParseSubtree(n)
    return node
    # call ParseSubtree on every child node, returns list of Node objects
    # add list of node objects to list member of Node
    # return Node

if __name__ == "__main__":
    my_xml = """<?xml version="1.0"?>
<BallotSide ulc_x='1' ulc_y='2'>
<Box x='1' y='2' x2='3' y2='4' text='First'>
  <Box x='10' y='20' x2='30' y2='40' text='First Child of First'>
  </Box>
  <Box x='11' y='21' x2='31' y2='41' text='Second Child of First'>
  </Box>
</Box>
<Box x='2' y='3' x2='4' y2='5' text='Second'></Box>
</BallotSide>
"""
    doc = minidom.parseString(my_xml)

    bs = doc.getElementsByTagName("BallotSide")
    tree = ParseSubtree(bs[0])
    pdb.set_trace()

    my_xml1 = """<?xml version="1.0"?>
<BallotSide frompage='/home/mitch/sagdata/unproc/004/004001.jpg' barcode='0A0B3A8B0B0B5B1B9B' y2y='3906' dpi='300' party='No party id.' precinct='I Precinct 817' rot='-0.000256016385049' lx='346' ly='196'>
	<Contest text='/Amendment 60 CONSTITUTIONAL/Shall there be an amendment to the/Colorado constit' prop='0' x2='1038' y='248' x='347' y2='2560' max_votes='5'>
		<oval y='2394' x='389' x2='-1' y2='-1' text='YES SI' />
		<oval y='2492' x='389' x2='-1' y2='-1' text='NO NO' />
	</Contest>
</BallotSide>
"""
    t = TemplateFromXML(my_xml)
    pdb.set_trace()
