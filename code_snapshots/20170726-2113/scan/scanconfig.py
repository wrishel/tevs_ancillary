"""config.py offers two services: configuring the default logger and reading
the config file for the TEVS utilities."""
import ConfigParser
import logging
import const
import sys
import os
import errno

__all__ = ['logger', 'get']

def yesno(cfg, grp, itm):
    so = cfg.get(grp, itm)
    s = so.strip().lower()
    if s in "yes y true t on".split():
        return True
    if s in "no n false f off".split():
        return False
    raise ValueError("% is not a valid choice for %s in %s" % (so, grp, itm))

def logger(file):
    "configure the default logger to use file"
    level = logging.INFO
    if hasattr(const, 'debug'):
        try:
            level = const.debug
        except:
            level = logging.DEBUG

    logging.basicConfig(
        filename=file,
        format="%(asctime)s: %(levelname)s: %(module)s: %(message)s",
        level=level
    )

    logger = logging.getLogger('')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(
        logging.Formatter("%(message)s\n")
    )
    logger.addHandler(console)
    return logger

def get(cfg_file="tevs.cfg"):
    "get the tevs configuration file in ."
    config = ConfigParser.ConfigParser()
    config.read(cfg_file)

    path = lambda v: os.path.expanduser(config.get("Paths", v))
    const.root = path("root")
    try:
        const.incoming = path("incoming")
    except ConfigParser.NoOptionError:
        const.incoming = os.path.join(const.root, "unproc")

    # create any missing folders once you know the root
    try:
        if not os.path.exists(os.path.join(const.root, "logs" )):
            os.mkdir(os.path.join(const.root, "logs"))
        if not os.path.exists(os.path.join(const.root, "templates" )):
            os.mkdir(os.path.join(const.root, "templates"))
        if not os.path.exists(os.path.join(const.root, "template_images" )):
            os.mkdir(os.path.join(const.root, "template_images"))
        if not os.path.exists(os.path.join(const.root, "composite_images" )):
            os.mkdir(os.path.join(const.root, "composite_images"))
    except Exception as e:
        print "Could not find or create necessary subfolders in %s:  \n\
logs, templates, template_images, and composite_images." % (const.root,)
        sys.exit(0)
    # get log file name so log can be opened
    const.logfilename = os.path.join(const.root, "logs/tevsgui_log.txt" )
    #XXX only needed for scancontrol, view
    # then both log and print other config info for this run
    try:
        noc = config.get("Layout", "number_of_columns")
    except: 
        noc = -1

    bwi = config.get("Sizes", "ballot_width_inches")
    bhi = config.get("Sizes", "ballot_height_inches")
    try:
        ioi = config.get("Sizes", "imprint_offset_inches")
    except ConfigParser.NoOptionError:
        ioi = "2.0"
    try:
        debug = config.get("Mode", "debug")
    except ConfigParser.NoOptionError:
        const.debug = logging.INFO
    try:
        if debug == "True" or debug == "TRUE":
            const.debug = logging.DEBUG
        elif debug == "Warning" or debug == "WARNING":
            const.debug = logging.WARNING
        elif debug == "Error" or debug == "ERROR":
            const.debug = logging.ERROR
        elif debug == "Info" or debug == "INFO" or debug == "Off" or debug == "OFF" or debug == "False" or debug == "FALSE":
            const.debug = logging.INFO
    except:
        const.debug = logging.INFO

    tdpi = config.get("Scanner", "template_dpi")
    bdpi = config.get("Scanner", "ballot_dpi")

    const.ballot_width_inches = float(bwi)
    const.ballot_height_inches = float(bhi)
    const.imprint_offset_inches = float(ioi)
    const.ballot_dpi = int(bdpi)
    const.dpi = const.ballot_dpi 
    const.template_dpi = int(tdpi)

