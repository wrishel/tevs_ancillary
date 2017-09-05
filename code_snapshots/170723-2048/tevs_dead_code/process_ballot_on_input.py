#!/usr/bin/env python

import signal
import sys
import os
import os.path
import pdb
import shutil
import errno
import getopt
import logging
import gc
import site; site.addsitedir(os.path.expanduser("~/tevs")) 
import Image, ImageStat, ImageDraw 
import gobject

import const #To be deprecated
import config
import util
import db
import next
import Ballot
BallotException = Ballot.BallotException
global timeout
#global extraction_count
#extraction_count = 0
"""
This is the main ballot processing loop for TEVS, which can be run
as an independent program or as a support program for TEVSGUI.
It prompts by sending "READY:" or "SKIP:" and the value of the
next ballot to process is included in the prompt line following
"Next=" and followed by a space.  
The prompt is recognized as soon as the prompt string 
is encountered, so the "Next=" must precede the prompt string on
the same line.""" 

class DoIncrementException(Exception):
    def __init__(self,value=""):
        self.value = value
    def __str__(self):
        return repr(self.value)



class FileNotPresentException(Exception):
    def __init__(self,value):
        self.value = value
    def __str__(self):
        return repr(self.value)

def results_to_vop_files(results,resultsfilename):
    """Save all ovals from a list of Votedata"""
    for r in results:
        label = "%s_%04d_%04d_%s_%s.jpg" % (
            os.path.join(
                os.path.dirname(resultsfilename),
                os.path.basename(r.filename[:-4]),
                ),
            r.coords[0],
            r.coords[1],
            "V" if r.was_voted else "v",
            "A" if r.ambiguous else "a"
        )
        try:
            if r.image is not None:
                r.image.save(label)
        except Exception as e:
            print e


def results_to_CSV(results):
    """Save all ovals from a list of Votedata"""
    log = logging.getLogger('')
    log.info("About to return joined results")
    log.info("Type of results is")
    log.info(str(type(results)))
    outlines = []
    for out in results:
        try:
            log.info(str(type(out)))
            outline = out.CSV() 
            log.info(outline)
            outlines.append(outline)
        except Exception, e:
            print e
            log.info(e)
            outlines = [e,]
    log.info("Returning from results_to_CSV")
    return "\n".join(outlines)

def get_args():
    """Get command line arguments"""
    try:
        opts, args = getopt.getopt(sys.argv[1:],
                                    "tdc:",
                                    ["templates",
                                     "debug",
                                     "config="
                                    ]
                                   ) 
    except getopt.GetoptError:
        #note that logging doesn't exist yet
        sys.stderr.write(
            "usage: %s -tdc --templates --debug --config=file" % sys.argv[0]
        )
        sys.exit(2)
    templates_only = False
    debug = False
    config = "tevs.cfg"
    for opt, arg in opts:
        if opt in ("-t", "--templates"):
            templates_only = True
        if opt in ("-d", "--debug"):
            debug = True
        if opt in ("-c", "--config"):
            config = arg

    const.templates_only = templates_only
    const.debug = debug
    return config

def remove_partial(fname):
    try:
        os.unlink(fname)
    except KeyboardInterrupt:
        raise
    except Exception: 
        pass

def _fn(n):
    return "%03d" % (n/1000,)

def incomingn(n):
    return filen(os.path.join(const.incoming, _fn(n)), n) + const.filename_extension

def dirn(dir, n): # where dir is the "unrooted" name
    return util.root(dir, _fn(n))

def filen(dir, n): #where dir is from dirn
    return os.path.join(dir, "%06d" % n)

def mark_error(e, *files):
    log = logging.getLogger('')
    if e is not None:
        log.error(e)
    for file in files:
        log.error("Could not process ballot " + os.path.basename(file))
        try:
            shutil.copy2(file, util.root("errors", os.path.basename(file)))
        except IOError:
            log.error("Could not copy unprocessable file to errors dir")
    return len(files)

def results_to_vop_files(results,resultsfilename):
    """Save all ovals from a list of Votedata"""
    for r in results:
        label = "%s_%04d_%04d_%s_%s.jpg" % (
            os.path.join(
                os.path.dirname(resultsfilename),
                os.path.basename(r.filename[:-4]),
                ),
            r.coords[0],
            r.coords[1],
            "V" if r.was_voted else "v",
            "A" if r.ambiguous else "a"
        )
        try:
            if r.image is not None:
                r.image.save(label)
        except Exception as e:
            print e

def signal_func(signum,frame):
    print "Next=%06d , READY:" % (999,)
    sys.stdout.flush()

def get_count_to_process(num,log):
    global timeout
    #global extraction_count
    retval = None
    while True:
        try:
            sys.stdout.flush()
            # start a timeout and give up 
            # if you haven't received input
            # in a certain amount of time
            #timeout = gobject.timeout_add(1000,timeout_func,num)
            signal.signal(signal.SIGALRM,signal_func)
            signal.alarm(60)
            try:
                retval = raw_input("")
            except EOFError:
                log.info("Input delay caused timeout after 60 seconds.")
                sys.exit(0)
            signal.alarm(0)
            if retval is None:
                continue
            retval = retval.strip()
            if retval=='S':
                retval = num
            elif retval=='+':
                raise DoIncrementException
            else:
                retval = int(retval)
            break
        except DoIncrementException, e:
            raise DoIncrementException
    return retval

def main():
    NextEqualsPrefix = "Next="
    MorePrompt = ":"
    NextToProcessFile = ""
    miss_counter = 0
    # get command line arguments
    cfg_file = get_args()

    # read configuration from tevs.cfg and set constants for this run
    config.get(cfg_file)
    util.mkdirp(const.root)
    log = config.logger(util.root("extraction.log"))

    # create initial toplevel directories if they don't exist
    for p in (
        "%s" % ("templates"), 
        "%s" % ("template_images"), 
        "%s" % ("composite_images"), 
        "results", 
        "proc",
        "errors"):
        util.mkdirp(util.root(p))

    # make sure you have code for ballot type spec'd in config file
    try:
        ballotfrom = Ballot.LoadBallotType(const.layout_brand)
    except KeyError as e:
        util.fatal("No such ballot type: %s check %s !", 
                   (const.layout_brand,cfg_file))

    cache = Ballot.TemplateCache(util.root("templates"))
    extensions = Ballot.Extensions(template_cache=cache)
   
    # connect to db and open cursor
    if const.use_db:
        try:
            dbc = db.PostgresDB(database=const.dbname, user=const.dbuser)
        except db.DatabaseError:
            util.fatal("Could not connect to database!")
    else:
        dbc = db.NullDB()
    log.info("Database connected.")

    total_images_processed, total_images_left_unprocessed = 0, 0
    base = os.path.basename
    # Each time given a signal to proceed for count_to_process ballots,
    # create ballot from images, get landmarks, get layout code, get votes.
    # Write votes to database and results directory.  
    # for profiling
    # from guppy import hpy;hp=hpy();hp.setref();
    # import gc;gc.disable();gc.collect();hp.setref()

    NextToProcessFile = util.root("nexttoprocess.txt")
    count_to_process = 0
    file_problem = False
    while True:
        log.debug("Top of loop.")
        next_ballot_number = int(
            util.readfrom(NextToProcessFile))
        log.debug("Read %d from %s" % (next_ballot_number,NextToProcessFile))
        if count_to_process == 0:
            # send prompt to controlling process, "READY:" or "+ for SKIP:"
            if file_problem:
                file_problem = False
                # do not remove space after %06d
                print "Next=%06d , + to SKIP:" % (next_ballot_number,)
            else:
                # do not remove space after %06d
                print "Next=%06d , READY:" % (next_ballot_number,)
            sys.stdout.flush()
            # wait here until get_count_to_process returns
            # it will wait on input instruction from stdio
            try:
                count_to_process = get_count_to_process(next_ballot_number,log)
            except DoIncrementException, e:
                log.debug("Do increment exception")
                util.writeto(NextToProcessFile,
                             next_ballot_number+const.num_pages)
                log.debug("Wrote %d to next_ballot_number, count to process is %d" % (next_ballot_number+const.num_pages,count_to_process))
                count_to_process=0
                log.debug("Setting count to process to 0.")
                continue
            # we're done when we get instructed to process 0
            if count_to_process == 0:
                break
        count_to_process -= 1
        try:
            # get number of next image, 
            # clean up, in case...
            gc.collect()
            log.debug("Request for %d" % (next_ballot_number,))
            unprocs = [incomingn(next_ballot_number + m) for m in range(const.num_pages)]
            log.info(unprocs)
            # we need all images for sheet to be available to process it
            for filename in unprocs:
                log.info("Checking for path.")
                if not os.path.exists(filename):
                    log.info("File not present.")
                    errmsg = "File %s not present or available!!!" % (
                        base(filename),) 
                    log.info(errmsg.replace("!!!",""))
                    print errmsg
                    sys.stdout.flush()
                    raise FileNotPresentException(filename) 
                log.info("Path found.")
           #Processing
            log.debug("Creating ballot.")
            try:
                ballot = ballotfrom(unprocs, extensions)
                log.debug("Created ballot, processing." )
                results = ballot.ProcessPages()
                log.debug("Processed.")
            except BallotException as e:
                total_images_left_unprocessed += mark_error(e, *unprocs)
                log.exception("Could not process ballot")
                util.writeto(NextToProcessFile,
                             next_ballot_number+const.num_pages)
                continue

            #Write all data
            #make dirs:
            proc1d = dirn("proc", next_ballot_number)
            resultsd = dirn("results", next_ballot_number)
            
            resultsfilename = filen(resultsd, next_ballot_number)
            for p in (proc1d, resultsd):
                util.mkdirp(p)
            #try:
            #    results_to_vop_files(results,resultsfilename)
            #except Exception as e:
            #    log.info(e)
            #    print e
            #write csv and mosaic
            #log.info("local results_to_CSV")
            #csv = results_to_CSV(results,log)
            #log.info("Back from results_to_CSV")
            #util.genwriteto(resultsfilename + ".csv", csv)
            #write to the database
            try:
                log.debug("Inserting to db")
                dbc.insert(ballot)
            except db.DatabaseError:
                #dbc does not commit if there is an error, just need to remove 
                #partial files
                remove_partial(resultsfilename + ".txt")
                remove_partial(resultsfilename + const.filename_extension)
                log.info("Could not commit to db")
                print "Could not commit to db!"
                util.fatal("Could not commit vote information to database")

            #Post-processing

            # move the images from unproc to proc
            log.debug("Renaming")
            procs = [filen(proc1d, next_ballot_number + m) + const.filename_extension
                        for m in range(const.num_pages)]
            for a, b in zip(unprocs, procs):
                try:
                    os.rename(a, b)
                except OSError as e:
                    log.info("Could not rename %s" % a)
                    util.fatal("Could not rename %s", a)
            total_images_processed += const.num_pages
            # Tell caller you've processed all images of this ballot
            log.debug("Requesting next")
            util.writeto(NextToProcessFile,
                         next_ballot_number+const.num_pages)
            # update next ballot file with next image number
            log.debug("Done writing nexttoprocess.txt")
            #print "%d extracted. " % (next_ballot_number,)

            log.info("%d images processed", const.num_pages)

            # for profiling
            # hp.heap().dump('prof.hpy');hp.setref();gc.collect();
            # hp.setref();hp.heap().dump('prof.hpy')
        except FileNotPresentException,e:
            file_problem = True
            print "FileNotPresentException"
            sys.stdout.flush()
            log.info("FileNotPresentException occurred")
            continue
    dbc.close()
    log.info("%d images processed", total_images_processed)
    if total_images_left_unprocessed > 0:
        log.warning("%d images NOT processed.", total_images_left_unprocessed)

if __name__ == "__main__":
    main()
    #import cProfile as profile
    #profile.Profile.bias = 3.15e-6
    #profile.run('main()', 'prof.%s' % sys.argv[1])
