"""
TemplateToDB.py

Provides a set of database tables for template records, and the ability to
convert between the tabular information and an XML/EML template.

LoadTemplate loads an XML template into an in-memory XML tree,
TemplateToDB creates the equivalent records.
PaintTemplate generates a jpeg file showing the template visually.

AddBox inserts a new box into the template.
EditBox updates an existing box's information.
AddVote inserts a new vote into the template.
EditVote inserts an existing vote's information
VisuallyEdit template presents the template in a window and allows 

The table formats are as follows:


"""
create_templates_table = """create table templates(
  template_id serial PRIMARY KEY,
  precinct varchar(128),
  units varchar(128),
  target_height smallint,
  target_width smallint,
  src varchar(128),
  ulc_x smallint,
  ulc_y smallint,
  urc_x smallint,
  urc_y smallint,
  lrc_x smallint,
  lrc_y smallint,
  llc_x smallint,
  llc_y smallint
  );
"""

create_template_boxes_table = """create table template_boxes (
  template_box_id serial PRIMARY KEY,
  template_id int REFERENCES templates (template_id),
  x1 smallint,
  y1 smallint,
  x2 smallint,
  y2 smallint,
  max_votes smallint,
  text_code varchar(256),
  text varchar(256),
  text_image bytea default NULL
  );
"""

create_template_votes_table = """template_votes:
  template_vote_id serial PRIMARY KEY,
  template_box_id REFERENCES template_boxes (template_box_id),
  template_id REFERENCES templates (template_id),
  x1,
  y1,
  text_code,
  text,
  text_image default NULL
  );
"""
try:
    import psycopg2 as DB
    DatabaseError = DB.DatabaseError
except ImportError:
    DatabaseError = Exception
    pass

import pdb
import logging
# store parsed version of layout in cache, so import minidom
from xml.dom import minidom, Node
from xml.parsers.expat import ExpatError

class TemplateDBException(Exception):
    pass

class TemplateDB(object):
    def query_no_returned_values(self, q, *a):
        "returns a list of all results of q parameterized with a"
        cur = self.conn.cursor()
        try:
            cur.execute(q, *a)
            self.conn.commit()
        except DatabaseError, e:
            print e
            pdb.set_trace()
        return 

    def query(self, q, *a):
        "returns a list of all results of q parameterized with a"
        cur = self.conn.cursor()
        cur.execute(q, *a)
        r = list(cur)
        cur.close()
        return r

    def insert_template(self):
        r = self.query("insert into templates (layout, precinct, units, target_height, target_width, src) values ( %(layout)s, %(precinct)s, %(units)s,%(target_height)s,%(target_wdth)s,src varchar %(image_filename)s)" % self)
        print r
        self.current_template = r[0][0]
        pdb.set_trace()

    def update_template_landmarks(self):
        r = self.query("update templates set ulc_x = $(ulc_x), ulc_y = $(ulc_y),ulc_x = $(ulc_x), ulc_y = $(ulc_y),ulc_x = $(ulc_x), ulc_y = $(ulc_y),ulc_x = $(ulc_x), ulc_y = $(ulc_y) where template_id = %(current_template)" % self)

    def insert_template_box(self):
        r = self.query("insert into template_boxes () values ();")
        print r
        self.current_box = r[0][0]

    def insert_template_vote(self):
        r = self.query("insert into template_votes () values ();")
        print r
        self.current_vote = r[0][0]

    def __init__(self, database, user,xmlstring=None):
        self.logger = logging.getLogger(__name__)
        self.current_template = None
        self.document = None
        try:
            self.conn = DB.connect(database=database, user=user)
            self.logger.info("Connected to database %s as user %s" % (database,user))
        except Exception, e:
            # try to connect to user's default database
            try:
                self.conn = DB.connect(database=user, user=user)
            except Exception, e:
                self.logger.error("Could not connect to database %s specified in tevs.cfg,\nor connect to default database %s for user %s \nin order to create and initialize new database %s" % (database,user,user,database)) 
                self.logger.error("Do you have permission to create new databases?")
                self.logger.error(e)
            # try to create new database, close, and reconnect to new database
            try:
                self.query_no_returned_values(create_templates_table)
                self.query_no_returned_values(create_template_boxes_table)
                self.query_no_returned_values(create_template_votes_table)
            except Exception as e:
                self.logger.error("Could not initialize database %s\nwith template tables." % (database,))
                self.logger.error(e)

        self.results = []
        self.landmarks = landmarks
        self.image = image
        self.image_filename = image_filename
        self.enclosing_label = enclosing_label
        self.jurisdiction = None
        self.contest = None
        self.max_votes = 1
        self.choice = None
        self.transformer = None
        self.current_x = 0
        self.current_y = 0
        self.units = ''
        self.target_height = ''
        self.target_width = ''
        self.target_hotspot_offset_x = 0
        self.target_hotspot_offset_y = 0
        self.side = None
        self.layout_id = None

    def LoadTemplate(self,xmlstring):
        """Load template into memory"""
        self.document = minidom.parseString(xmlstring)
        # we need to confirm that childNodes[1] is indeed a BallotSide
        try:
            x=self.document.childNodes[1]
            if x.nodeType != Node.ELEMENT_NODE:
                raise TemplateDBException("Child node 1 not element.")
            if x.nodeName != "BallotSide":
                raise TemplateDBException("Child node 1 not BallotSide element.")
        except AttributeError:
            self.logger.debug("Document has no child node 1.")
            raise TemplateDBException("Document has no child node 0.")
        
        
    def TemplateToDB(self):
        self.process_recursive(self.document.childNodes[1],0,0)

    def process_recursive(self,node,x,y):

        """Recursive walk through XML rooted at node.

        The process_recursive function walks an XML tree 
        generating VOPAnalyze instances for each Vote node of the tree.
        """

        if node.nodeType != Node.ELEMENT_NODE:
            return

        if node.nodeName == 'BallotSide':
            # deal with a BallotSide by creating a database record in templates
            units = node.getAttribute('units')
            if units == '':
                self.units = 'pixels'
            elif units == 'pixels' or units == 'inches':
                self.units = units
            else:
                raise WalkerException(
                    "Ballot side specified unknown unit %s" % (units,))
            self.side = node.getAttribute('side')
            self.layout_id = node.getAttribute('layout-id')

            # LAYOUT
            l = node.getAttribute('layout')
            if l=='':
                self.layout = "NO LAYOUT"
            else:
                self.layout = l

            # PRECINCT
            p = node.getAttribute('precinct')
            if p=='':
                self.precinct = "NO PRECINCT"
            else:
                self.precinct = p

            # If the layout includes attributes 
            # related to the target size, use them.  
            # For missing attributes, use values from the config file.

            # TARGET HEIGHT
            th = node.getAttribute('target-height')
            if th=='':
                self.target_height = target_height
            else:
                self.target_height = float(th)

            # TARGET WIDTH
            tw = node.getAttribute('target-width')
            if tw=='':
                self.target_width = target_width
            else:
                self.target_width = float(tw)

            # TARGET HOTSPOT OFFSET X 
            # (a target may begin visually before the area to be analyzed,
            # for example, it may consist of two printed arrow halves,
            # with the area to analyze centered between the two printed halves.)
            thox = node.getAttribute('target-hotspot-offset-x')
            if thox=='':
                self.target_hotspot_offset_x = target_hotspot_offset_x
            else:
                self.target_hotspot_offset_x = float(thox)

            # TARGET HOTSPOT OFFSET Y 
            thoy = node.getAttribute('target-hotspot-offset-y')
            if thoy=='':
                self.target_hotspot_offset_y = target_hotspot_offset_y
            else:
                self.target_hotspot_offset_y = float(thoy)
            self.insert_template()
        elif node.nodeName == 'Landmarks':
            # deal with the landmarks by updating the database record
            # of the previous template, created just before
            try:
                self.ulc_x = float(node.getAttribute('ulc-x'))
                self.ulc_y = float(node.getAttribute('ulc-y'))
                self.urc_x = float(node.getAttribute('urc-x'))
                self.urc_y = float(node.getAttribute('urc-y'))
                self.llc_x = float(node.getAttribute('llc-x'))
                self.llc_y = float(node.getAttribute('llc-y'))
                self.lrc_x = float(node.getAttribute('lrc-x'))
                self.lrc_y = float(node.getAttribute('lrc-y'))
                self.update_template_landmarks()
            except ValueError:
                raise WalkerException(
                    "Missing required attrib in Landmarks node of XML.")
            

        elif node.nodeName == 'Box':
            # Deal with a box by creating a record 
            # in the database template_boxes table
            try:
                x = x + float(node.getAttribute('x1'))
                y = y + float(node.getAttribute('y1'))
            except ValueError:
                raise WalkerException(
                    "Missing required attrib in Box node of XML.")

            text = node.getAttribute('text')
            if text.upper().startswith('CONTEST:'):
                self.contest = text[8:]
            elif text.upper().startswith('JURISDICTION:'):
                self.jurisdiction = text[13:]
            else: self.contest = text

        elif node.nodeName == 'Vote':
            # Deal with a vote by creating a record in the database
            # template_votes table
            attrib_x = None
            attrib_y = None
            attrib_name = None
            try:
                attrib_x = float(node.getAttribute('x1'))
                attrib_y = float(node.getAttribute('y1'))
                attrib_name = node.getAttribute('text')
            except ValueError:
                raise WalkerException(
                    "Missing required attrib in Landmarks node of XML.")

        else:
            self.logger.info("Unhandled element %s" % (node.nodeName,))

        for n in node.childNodes:
            self.process_recursive(n,x,y)

        return node
