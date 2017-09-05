import gtk
import glib
import gobject
import logging
import pdb
import subprocess
global extraction_stdin
global extraction_stdout
global extraction_stderr
global extraction_pid 
global extraction_object 
global extraction_process_output 
global extraction_process_calling_object 
global extraction_count
global timeout_id 

global ioin_watch
global iohup_watch
global iopri_watch
global ioerr_watch

extraction_stdin = None
extraction_stdout = None
extraction_stderr = None
extraction_pid = None
extraction_object = None
extraction_process_output = ""
extraction_process_calling_object = None
extraction_count = 0
timeout_id = None

ioin_watch = None
iohup_watch = None
iopri_watch = None
ioerr_watch = None

"""
The data_available_from_extraction_process is set up to be called back
when data is available on stdout of the extraction program, currently
hardcoded to process_ballot_on_input.py.
The extraction program must prompt by sending "READY:" or "SKIP:" 
and the value of the next ballot to process must be included 
in the prompt line following "Next=".  

The line is processed as soon as the prompt string is encountered, 
so the "Next=" must precede the prompt string on the same line.
""" 


def set_up_extraction_process(calling_object):
    """ 
    run process_ballot_on_input in separate Python, 
    asking it to extract one ballot per request and print back
    the number of the processed ballot.  
    """
    global extraction_stdin
    global extraction_stdout
    global extraction_stderr
    global extraction_object
    global extraction_pid
    global extraction_process_calling_object
    global ioin_watch, iohup_watch, iopri_watch, ioerr_watch
    global extraction_count
    extraction_count = 0
    extraction_process_calling_object = calling_object
    try:
        extraction_object = subprocess.Popen(
            ["/usr/bin/python", "process_ballot_on_input.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds = True)
        extraction_pid = extraction_object.pid
        (extraction_stdin,
         extraction_stdout,
         extraction_stderr) = (extraction_object.stdin,
                               extraction_object.stdout,
                               extraction_object.stderr)
        ioin_watch = glib.io_add_watch(extraction_object.stdout,
                          glib.IO_IN,
                          data_available_from_extraction_process, 
                          calling_object.status)
        iohup_watch = glib.io_add_watch(extraction_object.stdout,
                          glib.IO_HUP,
                          extraction_process_done, 
                          calling_object.status)
        ioerr_watch = glib.io_add_watch(extraction_object.stdout,
                          glib.IO_ERR,
                          error_from_extraction_process, 
                          calling_object.status)
        iopri_watch = glib.io_add_watch(extraction_object.stdout,
                          glib.IO_PRI,
                          pri_from_extraction_process, 
                          calling_object.status)
        return extraction_pid

    except Exception,e:
        print e
        return -1
            
def take_down_extraction_process():
    """terminate extraction and reset related variables"""
    global extraction_stdin
    global extraction_stdout
    global extraction_stderr
    global extraction_object
    global extraction_pid
    global ioin_watch, iohup_watch, iopri_watch, ioerr_watch
    glib.source_remove(ioin_watch)
    glib.source_remove(iohup_watch)
    glib.source_remove(iopri_watch)
    glib.source_remove(ioerr_watch)
    saved_extraction_pid = extraction_pid
    try:
        if extraction_object is not None:
            extraction_object.terminate()
    except Exception,e:
        print e
    extraction_pid = None
    extraction_stdin = None
    extraction_stdout = None
    extraction_stderr = None
    extraction_object = None
    return saved_extraction_pid

def error_from_extraction_process(fd,condition,status):
    print "Error from extraction process"
    pdb.set_trace()
def pri_from_extraction_process(fd,condition,status):
    print "PRI from extraction process"
    pdb.set_trace()

def extraction_process_done(fd,condition,status):
    """extraction process ended; reset related variables"""
    global extraction_stdin
    global extraction_stdout
    global extraction_stderr
    global extraction_object
    global extraction_pid
    global ioin_watch, iohup_watch, iopri_watch, ioerr_watch
    glib.source_remove(ioin_watch)
    glib.source_remove(iohup_watch)
    glib.source_remove(iopri_watch)
    glib.source_remove(ioerr_watch)
    if condition == glib.IO_HUP:
        extraction_object = None
        extraction_pid = None
        extraction_stdin = None
        extraction_stdout = None
        extraction_stderr = None
        status.update("Extraction process has ended (IOHUP).")
    return False

def restart_extraction(data):
    timeout_id = None
    if extraction_object is not None:
        log = logging.getLogger('')
        take_down_extraction_process()
        set_up_extraction_process(extraction_process_calling_object)
    return False

def data_available_from_extraction_process(fd,condition,status):
    """ extraction will prompt for number of ballots to scan, ending with ?
        We accumulate output and send request for 1 more ballot at ?.
    """
    global extraction_process_output
    global extraction_stdin
    global extraction_stdout
    global extraction_stderr
    global extraction_pid
    global timeout_id
    global extraction_count
    log = logging.getLogger('')
    # so tevsgui.py app can get next to process
    global extraction_process_calling_object
    if condition == glib.IO_IN:
        char = fd.read(1)
        extraction_process_output = "%s%s" % (
            extraction_process_output,char)
        # support process will send "!" to request shutdown, 
        # "READY:" or "SKIP:" to request next instruction;
        # acceptable prompts may expand to end with "?"
        if char == '?' or char == ':' :
            # remove registered timeout if you get here in time
            if timeout_id is not None:
                gobject.source_remove(timeout_id)
                timeout_id = None
            # set watchdog timer for 2 minutes to trigger restart
            timeout_id = gobject.timeout_add(
                120000,
                restart_extraction, 
                None)
            #print "OUTPUT Rcd: [%s]\n" % (extraction_process_output,)
            # if the : is in a line saying READY:, send next request
            if extraction_process_output.find("READY:")>-1:
                extraction_count += 1
                if extraction_count > 500:
                    log.debug("Restarting extraction.")
                    restart_extraction(None)
                start_offset=extraction_process_output.find("Next=")
                if start_offset > -1:
                    start_offset += len("Next=")
                    next_to_process = int(
                        extraction_process_output[start_offset:].split()[0]
                        ) 
                    status.update("Next number to process: %d" % (next_to_process,))
                    try:
                        extraction_process_calling_object.last_processed_number = next_to_process
                        extraction_process_calling_object.builder.get_object("lastExtractedEntry").set_text("%s" % (next_to_process,))
                    except Exception, e:
                        print "Could not set last_processed_number"
                        print "on calling object in main program,"
                        print "during call to tevsgui_processing_requestor"
                        print "data available from extraction process cb"
                        print e
                    
                extraction_process_output = ""
            #print "Requesting next ballot"
            # extraction process will eventually accept:
            # S for single (counts one more ballot)
            # + for increment next_ballot_count by const.num_pages, process one
            # =nnn for set next_ballot_count to nnn, process one 
            # 0 for no more requests, shut down extraction
            # but now accepts only a number followed by the newline,
            # as an instruction to proceed for that number of ballots,
            # where 0 means terminate
            # or + for increment
                try:
                    extraction_stdin.write("1\n")
                    extraction_stdin.flush()
                except AttributeError:
                    status.update("Extraction process has ended.")
                    extraction_process_output = ""
            elif extraction_process_output.find("SKIP:")>-1:
                try:
                    md = gtk.MessageDialog(
                        #type = gtk.MESSAGE_QUESTION,
                        flags = (gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT),
                        buttons = (gtk.BUTTONS_YES_NO),
                        message_format = "Problem finding ballot.\nIncrement and continue?\n\n[%s]" % (extraction_process_output,))
                    extraction_process_output = ""
                except TypeError, e:
                    print e
                response = md.run()
                md.destroy()
                if response == gtk.RESPONSE_YES:
                    try:
                        extraction_stdin.write("+\n")
                        extraction_stdin.flush()
                    except AttributeError:
                        status.update("Yes, but extraction process has ended.")
                else:
                    try:
                        extraction_stdin.write("0\n")
                        extraction_stdin.flush()
                        extraction_stdin = None
                    except AttributeError:
                        status.update("No, but extraction process has ended.")

        return True
    else:
        status.update("Extraction process had problem.")
        return False
