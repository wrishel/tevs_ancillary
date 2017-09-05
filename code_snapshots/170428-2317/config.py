"""config.py offers two services: configuring the default logger and reading
the config file for the TEVS utilities."""
import ConfigParser
import logging
import const
import sys
import os
import errno
import pdb
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
    twi = config.get("Sizes", "target_width_inches")
    thi = config.get("Sizes", "target_height_inches")
    mwi = config.get("Sizes", "margin_width_inches")
    mhi = config.get("Sizes", "margin_height_inches")
    vthoi = config.get("Sizes", "vote_target_horiz_offset_inches")
    cthoi = config.get("Sizes", "candidate_text_horiz_offset_inches")
    cwi = config.get("Sizes", "candidate_text_width_inches")
    chi = config.get("Sizes", "candidate_text_height_inches")
    wizhoi = config.get("Sizes", "writein_zone_horiz_offset_inches")
    wizvoi = config.get("Sizes", "writein_zone_vert_offset_inches")
    wizwi = config.get("Sizes", "writein_zone_width_inches")
    wizhi = config.get("Sizes", "writein_zone_height_inches")

    pizhoi = config.get("Sizes", "precinct_zone_horiz_offset_inches")
    pizvoi = config.get("Sizes", "precinct_zone_vert_offset_inches")
    pizwi = config.get("Sizes", "precinct_zone_width_inches")
    pizhi = config.get("Sizes", "precinct_zone_height_inches")

    paizhoi = config.get("Sizes", "party_zone_horiz_offset_inches")
    paizvoi = config.get("Sizes", "party_zone_vert_offset_inches")
    paizwi = config.get("Sizes", "party_zone_width_inches")
    paizhi = config.get("Sizes", "party_zone_height_inches")

    mchi = config.get("Sizes", "minimum_contest_height_inches")
    acbi = config.get("Sizes", "allowed_corner_black_inches")
    allowed_tangent = config.get("Sizes", "allowed_tangent")
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

    try:
        hsxoi = config.get("Sizes", "hotspot_x_offset_inches")
        const.hotspot_x_offset_inches = float(hsxoi)
    except ConfigParser.NoOptionError:
        const.hotspot_x_offset_inches = 0.0
    try:
        hsyoi = config.get("Sizes", "hotspot_y_offset_inches")
        const.hotspot_y_offset_inches = float(hsyoi)
    except ConfigParser.NoOptionError:
        const.hotspot_y_offset_inches = 0.0
    try:
        linedarkthresh = config.get("Intensities","line_darkness_threshold")
        const.line_darkness_threshold = int(linedarkthresh)
    except ConfigParser.NoOptionError:
        const.line_darkness_threshold = 128

    try:
        linelightthresh = config.get("Intensities","line_exit_threshold")
        const.line_exit_threshold = int(linelightthresh)
    except ConfigParser.NoOptionError:
        const.line_exit_threshold = 128

    vit = config.get("Votes", "vote_intensity_threshold")
    dpt = config.get("Votes", "dark_pixel_threshold")
    pit = config.get("Votes", "problem_intensity_threshold")

    tdpi = config.get("Scanner", "template_dpi")
    bdpi = config.get("Scanner", "ballot_dpi")


    const.ballot_width_inches = float(bwi)
    const.ballot_height_inches = float(bhi)
    const.imprint_offset_inches = float(ioi)
    const.target_width_inches = float(twi)
    const.target_height_inches = float(thi)
    const.margin_width_inches = float(mwi)
    const.margin_height_inches = float(mhi)
    const.candidate_text_horiz_offset_inches = float(cthoi)
    const.vote_target_horiz_offset_inches = float(vthoi)
    const.candidate_text_width_inches = float(cwi)
    const.candidate_text_height_inches = float(chi)
    const.writein_zone_horiz_offset_inches = float(wizhoi)
    const.writein_zone_vert_offset_inches = float(wizvoi)
    const.writein_zone_width_inches = float(wizwi)
    const.writein_zone_height_inches = float(wizhi)

    const.precinct_zone_horiz_offset_inches = float(pizhoi)
    const.precinct_zone_vert_offset_inches = float(pizvoi)
    const.precinct_zone_width_inches = float(pizwi)
    const.precinct_zone_height_inches = float(pizhi)
    const.party_zone_horiz_offset_inches = float(paizhoi)
    const.party_zone_vert_offset_inches = float(paizvoi)
    const.party_zone_width_inches = float(paizwi)
    const.party_zone_height_inches = float(paizhi)
    const.minimum_contest_height_inches = float(mchi)
    const.allowed_corner_black_inches = float(acbi)
    const.allowed_tangent = float(allowed_tangent)
    const.vote_intensity_threshold = float(vit)
    const.problem_intensity_threshold = float(pit)
    const.dark_pixel_threshold = int(dpt)
    const.ballot_dpi = int(bdpi)
    const.dpi = const.ballot_dpi 
    const.template_dpi = int(tdpi)

    const.num_cols = int(noc)
    const.num_pages = int(config.get("Mode", "images_per_ballot"))
    const.layout_brand = config.get("Layout", "brand")
    const.on_new_layout = config.get("Mode", "on_new_layout")
    const.filename_extension = config.get("Mode","filename_extension")

    const.save_vops = yesno(config, "Mode", "save_vops")
    const.save_template_images = yesno(config, "Mode", "save_template_images")
    const.save_composite_images = yesno(config, "Mode", "save_composite_images")
    const.use_db = yesno(config, "Database", "use_db")
    #const.dbname = config.get("Database", "name")
    const.dbname = config.get("Database", "database")
    const.dbuser  = config.get("Database", "user")
    try:
        const.ocr_exec = config.get("Paths","ocrexec")
    except:
        const.ocr_exec = "/usr/bin/tesseract"
    try:
        const.scan_service = config.get("Paths","scan_service")
    except:
        const.scan_service = "/usr/share/tevs/tevsgui_xmlrpc_scanning_service.py"
    try:
        const.scrape_service = config.get("Paths","scrape_service")
    except:
        const.scrape_service = "/usr/share/tevs/tevsgui_xmlrpc_processing_service.py"
    # zones in which to search for images, spec'd in inches
    # positive x,y imply distance from upper left edge,
    # negative x,y imply distance from lower right edge
    const.ulc_zone_x1 = 0.0    
    const.ulc_zone_y1 = 0.0
    const.ulc_zone_x2 = 1.5    
    const.ulc_zone_y2 = 1.5

    const.urc_zone_x1 = -1.5    
    const.urc_zone_y1 = 0.0
    const.urc_zone_x2 = 0.0    
    const.urc_zone_y2 = 1.5

    const.lrc_zone_x1 = -1.5    
    const.lrc_zone_y1 = -1.5
    const.lrc_zone_x2 = 0.0    
    const.lrc_zone_y2 = 0.0

    const.llc_zone_x1 = 0.0    
    const.llc_zone_y1 = -1.5    
    const.llc_zone_x2 = 1.5
    const.llc_zone_y2 = 0 
