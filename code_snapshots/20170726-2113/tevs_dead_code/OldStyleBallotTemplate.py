# BallotTemplate.py
# part of TEVS

import const
from xml.dom import minidom
from xml.parsers.expat import ExpatError
import pdb

class Point(object):
    def __init__(self,x,y):
        self.x, self.y = x, y

class Region(object):
    def __init__(self, x, y, x2, y2):
        self.x, self.y, self.x2, self.y2 = x, y, x2, y2
        self.description = None #there will be one of these two but not both
        self.image = None

    def __repr__(self):
        return "Region x: %(x)s y: %(y)s x2: %(x2)s y2: %(y2)s \nRegion description: %(description)s\nRegion image: %(image)s" % self.__dict__

    def coords(self):
        return self.x, self.y

    def bbox(self):
        return self.x, self.y, self.x2, self.y2

    def children(self):
        return []


#A choice has and must have one and only one VOP--VOP is an essentially useless
#class but it is way easier to think about it this way instead of having one
#object with two bounding boxes
class Choice(Region):
    """An item in a layout hierarchy representing an individual vote
    opportunities text, as a bounding box, and, if it has been OCRed, by a
    string, self.description.
    
    After creation, self.VOP should be set to an instance of VOP. If it is
    WriteIn, self.description should remain None.
    """ 
    def __init__(self, x, y, x2=-1, y2=-1, description=None): 
        super(Choice, self).__init__(x, y, x2, y2) 
        self.VOP = None
        self.description = description #XXX change to None

    def children(self):
        """returns self.VOP or []"""
        return self.VOP or []

class VOP(Region):
    """The bounding box of a VOP. If this is the VOP of a write in, set
    self.WriteIn to a WriteIn object for the write in's bounding box.
    """
    def __init__(self, x, y, x2, y2):
        super(VOP, self).__init__(x, y, x2, y2)
        self.WriteIn = WriteIn

    def children(self):
        """return self.WriteIn or []"""
        return self.WriteIn or []

class WriteIn(Region):
    """The bounding box for a WriteIn, not including the VOP of the WriteIn. It
    is the child of its VOP, so in:
        
         Contest:
         
            [ ] Choice a

            [ ] Choice b
         
            [ ] Write in

            `____________`
    

    WriteIn will be the child of the VOP to the left of the Choice "Write in" """
    def __init__(self, x, y, x2, y2):
        super(VOP, self).__init__(x, y, x2, y2)

class Jurisdiction(Region):
    """The top level item in a layout hierarchy. Its children are a list of
    Contest's. A ballot may have zero or more Jurisdictions. If there are no
    Jurisdictions, all of the top level elements in the template must be
    Contest's, and the children of a Jurisdiction must be Contest's. An example
    of a Jurisdiction is a ballot containing contests for both a state and
    county election: In this case, the template should have a state
    Jurisdiction, containing all of the Contest's for the state election; and a
    county Jurisdiction, containing all of the Contest's for the county
    election. The bounding box of a Jurisdiction should only enclose the text
    of the description, such as the word 'State'."""
    def __init__(self, x, y, x2, y2):
        super(Jurisdiction, self).__init__(x, y, x2, y2)
        self.contests = []

    def append(self, contest):
        self.contests.append(contest)

    def children(self):
        return self.contests

class Contest(Region):
    """Either the top level item in a layout hierarchy or the child of a
    Jurisdiction. A Contest is the bounding box of the text describing a single
    vote. It's children are the Choice's available in that contest. For
    example:

         Vote for one:

             [ ] Billy

             [ ] Jane

    The contest would be the bounding box around the text "Vote for one:" and
    its children would be the Choices for Billy and Jane.
    """
    def __init__(self, x, y, x2, y2, prop, description, max_votes=2): #XXX axe prop/description
        super(Contest, self).__init__(x, y, x2, y2)
        self.prop = prop #XXX del
        self.w = x2 #XXX del
        self.h = y2 #XXX del
        self.description = description #XXX change to None
        self.choices = []
        self.max_votes = max_votes

    def append(self, choice):
        self.choices.append(choice)

    def children(self):
        return self.choices

class _scannedPage(object):
    """Superclass of ballot Page.
    
    Note: y2y, when nonzero, is pixel spacing between top and bottom landmark,
    used for more precise/reliable scaling than asserted dpi.
    """
    def __init__(self, dpi, xoff, yoff, rot, image, y2y=0):
        self.dpi = int(dpi)
        self.xoff, self.yoff, self.y2y = int(xoff), int(yoff), int(y2y)
        self.rot = float(rot)
        self.image = image

def _fixup(im, rot, xoff, yoff):
    return im.rotate(180*rot/math.pi)

class Page(_scannedPage):
    """A ballot page represented by an image and a Template. It is created by
    Ballot.__init__ for each ballot image. Important properties:
    
       * self.ballot - to allow the page access to its host ballot's info
       * self.filename - the name of the file of the ballot page's initial image
       * self.image - the PIL image created from self.filename
       * self.dpi - an integer specifying the DPI of the image
       * self.template - The Template created by Ballot.BuildLayout or None
       * self.barcode - The barcode associated with self.template
       * self.blank - a special sentinel indicator for pages intentionally left
          blank
       * self.number - the page number
       * self.xoff - the x offset of the ulc landmark within the ballot image
       * self.yoff - the y offset of the uld landmark within the ballot image
       * self.rot - the rotation of the ballot within the ballot image, radians
       * self.y2y - the (misnamed) distance between two standard landmarks,
                    for scaling between real page and template coordinates
    Note that self.rot is in radians, which is used by python's math library,
    but that the rotate method in PIL uses degrees.
    """
    def __init__(self, ballot=None,
                 dpi=0, 
                 xoff=0, 
                 yoff=0, 
                 rot=0.0, 
                 filename=None, 
                 image=None, 
                 template=None, 
                 number=0, 
                 y2y=0):
        super(Page, self).__init__(dpi, xoff, yoff, rot, image, y2y)
        self.ballot = ballot
        self.filename = filename
        self.template = template
        self.number = number
        self.blank = False
        self.barcode = ""
        self.landmarks = []
        # the standard size and margin of vote targets, converted to pixels
        adj = lambda a: int(round(float(const.dpi) * a))
        try:
            self.target_width = adj(const.target_width_inches)
            self.target_height = adj(const.target_height_inches)
            self.margin_width = adj(const.margin_width_inches)
            self.margin_height = adj(const.margin_height_inches)
            self.writein_zone_width = adj(const.writein_zone_width_inches)
            self.writein_zone_height = adj(const.writein_zone_height_inches)
            self.writein_zone_horiz_offset = adj(const.writein_zone_horiz_offset_inches)
            self.writein_zone_vert_offset = adj(const.writein_zone_vert_offset_inches)
        except AttributeError as e:
            self.margin_width = 0
            self.margin_height = 0
            self.target_width = 30
            self.target_height = 30
            raise AttributeError(e + " and is required in the tevs.cfg file.")
            print e

    def as_template(self, 
                    barcode, 
                    contests, 
                    precinct=None, 
                    party=None, 
                    frompage=None):
        """Convert this page into a Template
        and store that objects as its own template. This is handled by
        Ballot.BuildLayout

        Mitch 1/10/2011 not clear why he bothered splitting out a new class;
        it ought to be ok to use any page as a template for any other page,
        and add whatever functionality is needed in the template to Page
"""
        t = Template(self.dpi, self.xoff, self.yoff, self.rot, barcode, contests, self.image, self.y2y, precinct, party, frompage=self.filename) #XXX update
        self.template = t
        return t

    def fixup(self):
        """Undo the xoff, yoff, and rot of self.image. This is not necessary
        but useful for saving "pretty versions" of ballot images, as template
        cache does for the images that templates are created from."""
        self.image = _fixup(self.image)
        self.rot, self.xoff, self.yoff = 0.0, 0, 0
        return self.image

    def __iter__(self):
        if self.template is None:#XXX should be jurisdictions
            raise StopIteration()
        return iter(self.template)

    def __repr__(self):
        return str(self.__dict__)

class Template(_scannedPage):
    """A ballot page that has been fully mapped and is used as a
    template for similiar pages. A template MAY have an associated
    image but it is not guaranteed.
    
    A Template is very similiar to a Page but it contains the layout
    information of every Page with the same barcode. As an iterator, it yields
    all the top level elements stored in the template in the order they were
    discovered."""
    def __init__(self, dpi, xoff, yoff, rot, barcode, contests, image=None,y2y=0, precinct=None, party=None, frompage=None):
        if image is not None:
            if const.save_template_images:
                image.save("%s/%s%d/%s.jpg" % (
                        util.root(),
                        "template_images",os.getpid(),
                        barcode))

        # don't save images in templates (causes high memory usage)
        super(Template, self).__init__(dpi, xoff, yoff, rot, None, y2y)
        self.barcode = barcode
        self.precinct = precinct
        self.party = party
        self.contests = contests #TODO should be jurisdictions
        self.frompage = frompage

    def append(self, contest):
        "add a new contest to the template"
        self.contests.append(contest)

    def __iter__(self):
        if self.contests is None: #XXX both should be jurisdictions
            raise StopIteration()
        return iter(self.contests)

    def __repr__(self):
        return str(self.__dict__)

def Template_to_XML(template): #XXX needs to be updated for jurisdictions
    """Takes a template object and returns a serialization in XML format

    Mitch 1/11/2011 will this work with regular page; check for iteration
"""
    acc = ['<?xml version="1.0"?>\n<BallotSide']
    def attrs(**kw):
        for name, value in kw.iteritems(): #TODO change ' < > et al to &ent;
            name, value = str(name), str(value)
            acc.extend((" ", name, "='", value, "'"))
    ins = acc.append

    attrs(
        dpi=template.dpi,
        barcode=template.barcode,
        lx=template.xoff,
        ly=template.yoff,
        rot=template.rot,
        y2y=template.y2y,
        precinct=template.precinct,
        party=template.party,
        frompage=template.frompage
    )
    ins(">\n")

    #TODO add jurisdictions loop
    for contest in template.contests: #XXX should be jurisdiction
        ins("\t<Contest")
        attrs(
            prop=contest.prop,#XXX del
            text=contest.description,
            x=contest.x,
            y=contest.y,
            x2=contest.x2,
            y2=contest.y2,
            max_votes = contest.max_votes
        )
        ins(">\n")

        for choice in contest.choices:
            ins("\t\t<oval")
            attrs(
                x=choice.x,
                y=choice.y,
                x2=choice.x2,
                y2=choice.y2,
                text=choice.description
            )
            ins(" />\n")
            #TODO add loop for vops that checks for writeins

        ins("\t</Contest>\n")
    ins("</BallotSide>\n")
    return "".join(acc)

def Template_from_XML(xml): #XXX needs to be updated for jurisdictions
    """Takes an XML string generated from Template_to_XML and returns a
    Template"""
    doc = minidom.parseString(xml)

    tag = lambda root, name: root.getElementsByTagName(name)
    def attrs(root, *attrs):
        get = root.getAttribute
        for attr in attrs:
            if type(attr) is tuple:
                try:
                    t, a = attr
                    yield t(get(a))
                except ValueError, e:
                    yield 0
            else:
                yield get(attr)

    side = tag(doc, "BallotSide")[0]
    dpi, barcode, xoff, yoff, rot, y2y = attrs(
        side,
        (int, "dpi"), 
        "barcode", 
        (int, "lx"), 
        (int, "ly"), 
        (float, "rot"), 
        (int, "y2y")
    )
    contests = []

    for contest in tag(side, "Contest"):

        """cur = Contest(*attrs(
            contest,
            (int, "x"), 
            (int, "y"), 
            (int, "x2"), 
            (int, "y2"),
            (int, "max_votes"),
            "prop", 
            "text"
        ))"""
        #self, x, y, x2, y2, prop, description, max_votes=2): #XXX axe prop/description
        cur = Contest(*attrs(
            contest,
            (int, "x"), 
            (int, "y"), 
            (int, "x2"), 
            (int, "y2"),
            "prop", 
            "text",
            (int, "max_votes"),
        ))

        for choice in tag(contest, "oval"):
            cur.append(Choice(*attrs(
                 choice,
                 (int, "x"), 
                 (int, "y"), 
                 #(int, "x2"), (int, "y2"), #STAGE choice
                 "text"
            )))

        contests.append(cur)
    # can be Page?
    return Template(dpi, xoff, yoff, rot, barcode, contests, y2y=y2y)

# can be page?
BlankTemplate = Template(0, 0, 0, 0.0, "blank", [])


if __name__ == "__main__":
    r = Region(1,2,3,4)
    print r
    pdb.set_trace()
    tc = TemplateCache("/tmp/templatecache")
    print tc
    pdb.set_trace()
