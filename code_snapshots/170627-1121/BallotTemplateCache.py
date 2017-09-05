import util
import os
import logging
import sys
import pdb

# This may need a redo.  Individual ballot sheets may have unique id
# information on only one side (only one page).  So pages must be
# cached using the ballot sheet identification together with a side integer,
# not just based on the identification of the page. 
# May as well add functionality to enable template save to database as well.

class TemplateCache(object):
    """A TemplateCache stores Templates by their barcode PLUS BALLOT INFO
    and loads and saves
    them in a directory location. When instantiated, it loads all templates
    into ram for quick access. It does not automatically save templates, but
    provides methods for saving them. It uses Template_to_XML/Template_from_XML
    for the serialization and deserialization of the template. For storing and
    retrieving templates from the cache it behaves as a standard dictionary.
    """
    def __init__(self, location):
        self.cache = {}
        self.location = location
        util.mkdirp(location)
        self.log = logging.getLogger('')
        #attempt to prepopulate cache
        try:
            for file in os.listdir(location):
                # Mitch 1/11/2011 really want != .xml
                if os.path.splitext(file)[1] == ".jpg":
                    continue
                rfile = os.path.join(location, file)
                data = util.readfrom(rfile, "<") #default to text that will not parse
                try:
                    tmpl = BallotTemplate.Template_from_XML(data)
                except ExpatError:
                    if data != "<":
                        self.log.exception("Could not parse " + file)
                    continue
                fname = os.path.basename(file)
                self.cache[fname] = tmpl
        except OSError:
            self.log.info("No templates found")

    def __call__(self, id):
        return self.__getitem__(id)

    def __getitem__(self, id):
        id = str(id)
        if id == "blank":
            return BlankTemplate
        try:
            return self.cache[id]
        except KeyError:
            self.log.info("No template found for %s", id)
            return None

    def __setitem__(self, id, template):
        id = str(id)
        if id == "blank":
            return
        self.cache[id] = template
        self.log.info("Template %s created", id)
        # always save template upon creation
        self.save(id)

    def save(self, id):
        id = str(id)
        "write the template id to disk at self.location"
        fname = os.path.join(self.location, id)
        if not os.path.exists(fname):
            template = self.cache[id]
            if template is None:
                return
            xml = BallotTemplate.Template_to_XML(template)
            util.writeto(fname, xml)
            if template.image is not None:
                try:
                    im = _fixup(
                        template.image, 
                        template.rot, 
                        template.xoff,
                        template.yoff
                    )
                    im.save(fname + ".jpg")
                except IOError:
                    util.fatal("could not save image of template")
            self.log.info("new template %s saved", fname)

    def save_all(self):
        "save all templates that are not already saved"
        for id in self.cache.iterkeys():
            self.save(id)

class NullTemplateCache(object):
    "A Template Cache that is a no-op for all methods"
    def __init__(self, loc):
        pass
    def __call__(self, id):
        pass
    def __getitem__(self, id):
        if id == "blank":
            return BlankTemplate
    def __setitem__(self, id, t):
        pass
    def save(self):
        pass

NullCache = NullTemplateCache("") #used as the default

if __name__ == "__main__":
    try:
        tc = TemplateCache("/tmp/templatecache")
    except Exception, e:
        print e
    print "Past creation of template cache."
    try:
        sys.exit(0)
    except Exception, e:
        print e
