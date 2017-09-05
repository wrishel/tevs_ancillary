#!/usr/bin/env python

import sys
try:
 	import pygtk
  	pygtk.require("2.0")
except:
  	pass
try:
	import gtk
  	#import gtk.glade
except:
	sys.exit(1)
import const
import scanconfig
import copy
import glob
import gobject
import logging
import multiprocessing
import os
import subprocess
import sane
import tevsgui_get_args
import threading
import time
import StringIO
import pdb
import Queue
import zipfile

global sane_error
global testnumberfile
global testmode
global logger
global dpi
global source 
global endorse_int
global page_width_mm
global page_height_mm
global endorser_y
global current_root
#global dvd_file = "/tmp/todvd.zip"

sane_units = ['NONE','PIXEL','BIT','MM','DPI','PERCENT','OTHER']
sane_types = ['BOOL','INT','FIXED','STRING','BUTTON','GROUP']

endorser_y = 0
class SerialNumber(object):
    """Maintain a value that is stored to disk after each increment."""
    def __init__(self,filename,initial_value_if_no_file=0):
        self.filename = filename
        # confirm that filename can be opened for reading and writing
        try:
            f = open(filename,'r')
            line = f.readline()
            self.number = int(line)
        except Exception as e:
            logger.error( e)
            logger.error("Setting initial value to %d" % (initial_value_if_no_file,))
            self.number = initial_value_if_no_file
        else:
            f.close()
        try:
            f = open(filename,'w')
            f.write(str(self.number))
            f.close()
        except Exception as e:
            logger.error( e)
            raise Exception

        # read first line, save value in number
        # close the file

    def incr(self,amount):
        self.number += amount

    def set(self,value):
	    self.number = value

    def save(self):
        # open file for writing
        f = open(self.filename,"w")
        # write the value of number
        f.write(str(self.number))
        # close the file
        f.close()

    def incr_and_save(self,amount):
        self.incr(amount)
        self.save()

    def set_and_save(self,value):
        self.set(value)
        self.save()

class Scanner(object):
    """Store and control a SANE scanner device and its returned image(s)."""

    def advancedSettingsDialogHideCallback(self,w,d):
	    self.advanced_settings_dialog.hide()

    def check_toggled(self,w,data):
	    print self,data,"to",w.get_active()

    def entry_activated(self,w,data):
	    print self,data,"to",w.get_text()

    def create_control_window(self):
	self.option_groups = []
	dialog = gtk.Dialog("Advanced Settings",
                   None,
                   gtk.DIALOG_DESTROY_WITH_PARENT,
                   (
                    gtk.STOCK_CLOSE,gtk.RESPONSE_CLOSE 
		    )
		    )
	self.advanced_settings_dialog = dialog#gtk.Window()
	close_button = dialog.get_widget_for_response(gtk.RESPONSE_CLOSE)
	close_button.connect("clicked",self.advancedSettingsDialogHideCallback,None)
	# The dialog's main area will contain a notebook 
	# with one page for each "group" as returned by SANE.
	notebook = gtk.Notebook()
	#dialog.vbox.pack_start(notebook)

	self.notebook = notebook
	self.advanced_settings_dialog.add(notebook)
	self.advanced_settings_dialog.set_title("Advanced Settings")
	latest_pane = None
	latest_pane_label = None
	y_offset = -20
	for x in self.options_as_list:
		y_offset += 30
		# New pane for each new group
		if x[4]==sane.TYPE_GROUP:
			self.option_groups.append(x)
			if latest_pane is not None:
				notebook.append_page(
					latest_pane,gtk.Label(
						latest_pane_label))
			latest_pane = gtk.ScrolledWindow()
			latest_pane.set_policy(gtk.POLICY_ALWAYS,gtk.POLICY_ALWAYS)
			latest_pane.set_size_request(400,100)
			latest_layout = gtk.Layout()
			#latest_layout.set_size(300,1000)
			latest_pane.add(latest_layout)
			latest_pane.show()
			latest_layout.show()
			latest_pane_label = x[1]
			y_offset = -20
		elif x[4]==sane.TYPE_BUTTON:
			pass
		else:
			opt = self.device.opt[x[1].replace("-","_")]
			label = gtk.Label()
			label.set_text(opt.desc)
			latest_layout.put(label,0,y_offset)
			label.show()
			y_offset += 30
			if sane_types[opt.type]=='BOOL':
				check = gtk.CheckButton(x[1])
				check.show()
				check.set_sensitive(opt.is_active() and opt.is_settable())
				# determine the option's current value, and set the widget accordingly
				try:
					cur_value = repr(getattr(self.device,opt.py_name))
				except AttributeError:
					cur_value = "***Inactive option*** %s" % (opt.py_name,) 
				try:
					check.set_active(int(cur_value))
				except ValueError:
					pass
				# set up callback for check, with the option name as data to the callback 
				
				check.connect("toggled",self.check_toggled,opt.py_name)
				latest_layout.put(check,20,y_offset)
			else:
				hbox = gtk.HBox()
				label = gtk.Label(x[1])
				entry = gtk.Entry(20)
				entry.set_sensitive(
					opt.is_active() and opt.is_settable())
				# determine the option's current value, 
			        #set the widget accordingly
				try:
					cur_value = repr(
						getattr(self.device,opt.py_name))
				except AttributeError:
					cur_value = "***Inactive option*** %s" % (opt.py_name,)

				entry.set_text(str(cur_value).strip("'"))
				# set up callback for entry, with the option name as data to the callback 
				
				entry.connect("activate",self.entry_activated,opt.py_name)

				hbox.pack_start(label)
				hbox.pack_start(entry)
				latest_layout.put(hbox,20,y_offset)
				hbox.show()
				label.show()
				entry.show()
			print "Output type must be %s, unit %s is active %s is settable %s" % (sane_types[opt.type],sane_units[opt.unit],opt.is_active(),opt.is_settable())
			if type(opt.constraint)==type([]): 
				print "Build options for option menu %s" % (opt.constraint,)
			if type(opt.constraint) == type(()):
				print "Min %s max %s step %s" % (opt.constraint[0],opt.constraint[1],opt.constraint[2])
			       
			
	if latest_pane is not None:
		notebook.append_page(
			latest_pane,gtk.Label(
				latest_pane_label))
	self.advanced_settings_dialog.vbox.pack_start(notebook)
	self.notebook.show()
	self.advanced_settings_dialog.show()
	return self.advanced_settings_dialog

    def reset(self):
	self.device.close()
	sane.exit()
	sane.init()
	devices = sane.get_devices()
	self.device = sane.open(devices[0][0])
	self.initialize()

    def initialize(self):
	    global dpi
	    global source
	    global endorse_int
	    global endorser_y
	    global page_height_mm
	    global page_width_mm

	    self.set_option('mode','Color')
	    self.set_option('resolution',dpi)
	    self.set_option('source',source)
	    self.set_option('endorser',endorse_int) # SANE_BOOL requires integer

	    if endorse_int > 0:
		    self.set_option('endorser_bits',24)
		    self.set_option('endorser_step',1)
		    self.set_option('endorser_string', '%08ud')
		    self.set_option('endorser_val', self.sn.number)
		    self.set_option('endorser_y',endorser_y)

    def __init__(self,device=None,sn=None,logger=None):
	    if device is None:
		    devices = sane.get_devices()
		    try:
			    self.device = sane.open(devices[0][0])
		    except Exception as e:
			    print "Could not open scanner"
	    else:
		    self.device = device
	    self.sn = sn
	    self.logger = logger

	    self.img = None
	    self.img1 = None
	    self.img2 = None
	    self.options_as_list = self.device.dev.get_options()
	    self.options_as_list.sort(key=lambda a:a[0])
	    self.initialize()

    def set_option(self,option,arg):
        try:
		setattr(self.device,option,arg)
		logger.info( "Set %s to %s" % (option,arg))
        except Exception as e:
		logger.error(e)
		logger.error( "Could not set %s to %s" % (option,arg))
            

    def show_option(self,opt):
        try:
            print self.device[opt]
        except AttributeError as e:
            print e

    def scan_simplex(self,filename=None):
	    try:
		self.device.start()
		self.logger.debug("Start")
		self.img = self.device.snap(no_cancel=True)
		self.logger.debug("Snap no cancel")
		self.device.cancel()
		self.logger.debug("Cancel")
		if filename is not None:
		    self.save(filename)
		    self.logger.info("Saved %s\n" % (filename,))
	    except Exception as e:
		    self.device.cancel()
		    raise

    def save(self,filename):
        if self.img is not None:
            self.img.save(filename)
	(a,b) = os.path.split(filename)
	ffilename = os.path.join(a,"F"+b)
	bfilename = os.path.join(a,"B"+b)
	# check for existence of 1000s directory
        if self.img1 is not None:
            self.img1.save(ffilename)
        if self.img2 is not None:
            self.img2.save(bfilename)

    def scan_duplex(self,filename=None):
	    try:
		    self.logger.debug("Start duplex")
		    self.device.start()
		    self.img1 = self.device.snap(no_cancel=True)
		    self.device.start()
		    self.img2 = self.device.snap(no_cancel=True)
		    self.device.cancel()
		    if filename is not None:
			    self.save(filename)
	    except Exception as e:
		    self.device.cancel()
		    raise

class ZipThread(threading.Thread):
	active = 0
	q = Queue.Queue()

	def zip_status(self):
		msg= self.q.get()
		self.zdialog.set_markup(msg)
		return False

	def __init__(self,current_root,zdialog,filename=None,path=None):
		super(ZipThread, self).__init__()
		self.filename = filename
		self.zdialog = zdialog
		self.current_root = current_root
		if self.filename == None:
			self.filename = "/tmp/todvd.zip"
		self.zipfile = zipfile.ZipFile("/tmp/todvd.zip","w",zipfile.ZIP_DEFLATED,allowZip64=True)
		if path == None:
			self.path = self.current_root + "/unproc"
		else:
			self.path = path
		self.path=os.path.join(self.path,"*")
		self.iter = glob.iglob(self.path)

	def run(self):
		if ZipThread.active > 0:
		    return
		ZipThread.active = 1
		logger.info("Starting zip thread")
		#subprocess.call("zip -r %s %s" % (self.filename,self.path),shell=True)
		try:
			while True:
				zipme = self.iter.next()
				try:
					self.zipfile.write(zipme)
				except Exception as e:
					failmsg = "Failed to zip\n%s\n%s" % (
						zipme,e)
					print failmsg
					self.q.put(copy.copy(failmsg))
					gobject.idle_add(self.zip_status)
					break
				self.q.put(copy.copy("Added "+zipme))
				print zipme
				gobject.idle_add(self.zip_status)
				time.sleep(0.1)
		except StopIteration as si:
			print si
			self.q.put("Zipping successfully completed.")
			gobject.idle_add(self.zip_status)
		finally:
			self.zipfile.close()

		logger.info("Back from zip thread call to zip")
		ZipThread.active = 0
	
class SignThread(threading.Thread):
	active = 0
	retcode = 0
	sio_stdout = None
	sio_stderr = None

	def __init__(self,sdialog,filename=None):
		super(SignThread, self).__init__()
		self.filename = filename
		if self.filename == None:
			self.filename = "/tmp/todvd.zip"
		gnupg_list = glob.glob("/media/*/GNUPG")
		try:
			self.homedir=gnupg_list[0]
		except IndexError:
			self.homedir=None

	def run(self):
		if SignThread.active > 0:
		    return
		if self.homedir is None:
			logger.error("Will not sign; no external media with a toplevel GNUPG directory was found.")
			return
		SignThread.active = 1
		logger.info("Starting signing thread")
		SignThread.sio_stdout = open("/tmp/gpg_stdout.txt","w")
		SignThread.sio_stderr = open("/tmp/gpg_stderr.txt","w")
		print "IO created and opened"
		try:
			SignThread.retcode = subprocess.call(
				"gpg --homedir '%s' -b %s" % (self.homedir,self.filename,),
				stdout=SignThread.sio_stdout,
				stderr=SignThread.sio_stderr,
				shell=True)
		except Exception as e:
			logger.error("Failure in signing thread.")
			logger.error(e)

		logger.info("Back from signing thread call to gpg")
		SignThread.sio_stdout.close()
		SignThread.sio_stderr.close()
		SignThread.active = 0

class WriteThread(threading.Thread):
	active = 0
	retcode = 0
	sio_stdout = None
	sio_stderr = None
	q = Queue.Queue()

	def __init__(self,wdialog,filename=None):
		super(WriteThread, self).__init__()
		self.filename = filename
		if self.filename == None:
			self.filename = "/tmp/todvd.zip"

	def run(self):
		if WriteThread.active > 0:
		    return
		WriteThread.active = 1
		logger.info("Starting writing thread")
		WriteThread.sio_stdout = open("/tmp/dvdwrite_stdout.txt","w")
		WriteThread.sio_stderr = open("/tmp/dvdwrite_stderr.txt","w")
		print "IO created and opened"
		try:
			WriteThread.retcode = subprocess.call(
				"growisofs -Z /dev/dvd -dvd-compat -R -J /tmp/todvd*",
				stdout=WriteThread.sio_stdout,
				stderr=WriteThread.sio_stderr,
				shell=True)
		except Exception as e:
			logger.error("Failure in DVD writing thread.")
			logger.error(e)

		WriteThread.sio_stdout.close()
		WriteThread.sio_stderr.close()
		logger.info("Back from writing DVD.")
		WriteThread.active = 0
	
class ScanThread(threading.Thread):
    """Scan a set of docs until error, stop request, or end of doc stack."""
    active = False
    def __init__(self,scanapp):
        super(ScanThread, self).__init__()
	self.scanapp = scanapp
        self.scanner = scanapp.sc
        self.serial_number = scanapp.sn
        self.next_sn_label = scanapp.nextLabel
	self.count_label = scanapp.countLabel
	self.start_label = scanapp.startLabel
	self.start_number = self.serial_number.number
	self.start_label.set_text( str(self.start_number) )
	self.count_label.set_text("0")
	self.stopobject = scanapp.stopobject
	self.logstring = "start %s pct %s person %s note %s" % (
		self.start_number,
		scanapp.builder.get_object("precinctEntry").get_text(),
		scanapp.builder.get_object("personEntry").get_text(),
		scanapp.builder.get_object("notesEntry").get_text(),
		)
	
        self.logger = scanapp.logger
	self.logger.info("Scan thread: %s" % (
			self.logstring,))

    def stopped(self):
	    return self.stopobject.is_set()

    def update_labels(self, number, info):
        self.next_sn_label.set_text("%06i" % number)
	self.count_label.set_text( str(self.serial_number.number - self.start_number) )
	if info is not None:
		d = gtk.MessageDialog(message_format="",
				      parent=None,
				      flags = 0,
				      type=gtk.MESSAGE_INFO,
				      buttons=gtk.BUTTONS_OK)
		d.set_markup(info)
		response = d.run()
		d.hide()

        return False

    def run(self):
	    global testmode
	    global sane_error
	    global source
	    if ScanThread.active > 0:
		    self.logger.debug( "Scan thread in progress, skipping.")
		    return
	    ScanThread.active = 1
	    if sane_error is not None:
		    print "sane_error set to ",sane_error
		    if sane_error.find("out of documents")<0:
			    print "Performing reset"
			    self.scanner.reset()
		    else:
			    print "No reset needed, just out of docs."
	    sane_error = None
	    self.logger.debug("Setting endorser value")
	    try:
		    self.scanner.set_option('endorser_val', 
					    self.serial_number.number)
	    except sane.error as e:
		    print "ERROR IN SETTING ENDORSER OPTION",
		    print e
		    print "SETTING sane_error AND RETURNING FROM THREAD"
		    sane_error = copy.copy(str(e))
		    ScanThread.active = 0
		    return

	    self.logger.debug( "Scan thread into loop." )
	    while not self.stopped():
		    #filename = "/tmp/%04i.jpg" % (self.serial_number.number,)
		    if not testmode:
			    # check for directory existence on new 1000s
			    if (self.serial_number.number%1000) == 0:
				    dir_must_exist = os.path.join(
					    self.scanapp.current_root,
					    "unproc",
					    "%03d" % (self.serial_number.number/1000,))
				    if not os.path.isdir(dir_must_exist):
					    os.makedirs(dir_must_exist)
			    filename = self.scanapp.current_root+"/unproc/%03d/%06d.jpg" % (self.serial_number.number/1000,self.serial_number.number)
		    else:
			    filename = "/tmp/%06d.jpg" % (self.serial_number.number,)
		    try:
			    if source == 'ADF Front':
				    self.scanner.scan_simplex(filename=filename)
				    self.logger.debug("Back from scan_simplex.")
			    else:
				    self.scanner.scan_duplex(filename=filename)
				    self.logger.debug("Back from scan_duplex.")
			    # incr serial number by 1 even if duplex
			    # save duplex as F# and B#
			    self.serial_number.incr_and_save(1)
			    try:
				    self.scanner.set_option('endorser_val', 
						    self.serial_number.number)
			    except Exception:
				    pass
		    except sane.error as e:
			    print "ERROR WHILE SCANNING",e
			    sane_error = copy.copy(str(e))
			    self.logger.debug(e)
			    self.logger.debug("Breaking from while loop in thread")
			    gobject.idle_add(self.update_labels, 
					     self.serial_number.number,
					     sane_error)
			    break
		    gobject.idle_add(self.update_labels, self.serial_number.number,sane_error)
		    time.sleep(0.05)
	    self.stopobject.clear()
	    ScanThread.active = 0


class ScanApp:
	"""This is a glade UI application"""

	def get_current_root(self):return self.current_root
	def pageWidthCallback(self,w,d):
		global page_width_mm
		v = w.get_value()
		page_width_mm = int(round(v*25.4))
		self.sc.set_option("page_width",page_width_mm)
		self.sc.set_option("br_x",page_height_mm)
		self.sc.show_option("br_x")

	def pageHeightCallback(self,w,d):
		global page_height_mm
		v = w.get_value()
		page_height_mm = int(round(v*25.4))
		self.sc.set_option("page_height",page_height_mm)
		self.sc.set_option("br_y",page_height_mm)
		self.sc.show_option("br_y")

	def endorserYCallback(self,w,d):
		global endorser_y
		v = w.get_value()
		endorser_y = int(round(v*25.4))
		self.sc.set_option("endorser_y",endorser_y)
		self.sc.show_option("endorser_y")



	def doublesidedCallback(self,w,d):
		global source
		if w.get_active():
			source = 'ADF Duplex'
		else:
			source = 'ADF Front'
		self.sc.set_option('source',source) 

	def endorseCallback(self,w,d):
		global endorse_int
		if w.get_active():
			endorse_int = 1
		else:
			endorse_int = 0
		# SANE_BOOL requires integer
		self.sc.set_option('endorser',endorse_int) 
		
		sb = self.builder.get_object("endorserYSpinbutton")
		sb.set_sensitive(endorse_int)

	def templateResCallback(self,w,d):
		global dpi
		if w.get_active():
			dpi = 300
		else:
			dpi = 150

		self.sc.set_option('resolution',dpi) 

	def changeCallback(self,w,d):
		tw = gtk.Dialog("New next number",
				None,
				gtk.DIALOG_MODAL,
				(gtk.STOCK_OK,gtk.RESPONSE_OK,
				 gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL))
		textentry = gtk.Entry(6)
		label = gtk.Label("Enter new number")
		tw.vbox.pack_start(label)
		tw.vbox.pack_start(textentry)
		
		textentry.show()
		label.show()
		tw.show()
		response = tw.run()
		tw.hide()
		if response==gtk.RESPONSE_OK:
			try:
				newnum = int(textentry.get_text())
				self.sn.set_and_save(newnum)
				self.nextLabel.set_text(str(newnum))
			except Exception as e:
				print "No update"
				print e

	def updateNumberCallback(self,w,d):
		w.hide()

	def doneCallback(self,w,d):
		sys.exit(0)

	def scanCallback(self,w,d):
		self.logger.debug( "Scan callback")
		self.startLabel.set_text(str(self.sn.number))
		self.nextLabel.set_text(str(self.sn.number))
		self.countLabel.set_text("0")
		self.scanthread = ScanThread(self)
		self.scanthread.start()

	def stopCallback(self,w,d):
		self.logger.debug( "Stop callback")
		self.stopobject.set()

	def basicSettingsCallback(self,w,d):
		self.basic_settings_dialog.show()

	def advancedSettingsCallback(self,w,d):
		self.advanced_settings_dialog = self.sc.create_control_window()
		self.advanced_settings_dialog.show()

	def basicSettingsDialogHideCallback(self,w,d):
		self.basic_settings_dialog.hide()

	def showFilesCallback(self,w,d):
		subprocess.call("nautilus %s" % (os.path.join(self.current_root,"unproc")),shell=True)

	def aboutDialogCallback(self,w,d):
		self.builder.get_object("aboutDialog").show()


	def sign_status(self,st,sd):
		if st.active > 0:
			return True
		if st.retcode <> 0:
			failurestring = "Signing failed (return code %d)\n" % (st.retcode)
			f = open("/tmp/gpg_stdout.txt")
			failurestring+=f.read()
			f.close()
			f = open("/tmp/gpg_stderr.txt")
			failurestring+=f.read()
			f.close()
			sd.set_markup(failurestring)
		else:
			sd.set_markup("Signing successfully completed.")

		return False

	def write_status(self,wt,wd):
		if wt.active > 0:
			return True
		if wt.retcode <> 0:
			failurestring = "DVD writing failed (return code %d)\n" % (wt.retcode)
			f = open("/tmp/dvdwrite_stdout.txt")
			failurestring+=f.read()
			f.close()
			f = open("/tmp/dvdwrite_stderr.txt")
			failurestring+=f.read()
			f.close()
			wd.set_markup(failurestring)
		else:
			wd.set_markup("DVD writing successfully completed.")
		return False

	def zipCallback(self,w,d):
		""" Start zip thread, show dialog, idle updates when complete."""
		try:
			os.remove("/tmp/todvd.zip.sig")
		except Exception as e:
			print e
		self.zdialog = gtk.MessageDialog(
			message_format="Zipping please wait.")
		z = ZipThread(self.current_root,self.zdialog)
		z.start()
		self.zdialog.show()


	def signCallback(self,w,d):
		print "Sign callback"
		dialog = gtk.MessageDialog(message_format="""
You MUST insert a removable device
with a toplevel GNUPG folder
to sign these images.

You should keep this device locked away
when not in use, or your signature can
be forged.
""")
		dialog.run()
		try:
			os.remove("/tmp/todvd.zip.sig")
		except Exception as e:
			print e
		st = SignThread("/tmp/todvd.zip")

		self.sdialog = gtk.MessageDialog(message_format="Signing via 'Seahorse' agent\n\nPlease provide signature if asked, then wait.")
		gobject.idle_add(self.sign_status,st,self.sdialog)
		self.sdialog.show()
		st.start()

	def writeCallback(self,w,d):
		print "Write callback"
		self.wdialog = gtk.MessageDialog(message_format="Writing to DVD.")
		wt = WriteThread(self.wdialog)
		self.wdialog.show()
		#subprocess.call("growisofs -Z /dev/dvd -dvd-compat -R -J /tmp/todvd*",shell=True)
		gobject.idle_add(self.write_status,wt,self.wdialog)
		self.wdialog.show()
		wt.start()

	def testToggledCallback(self,w,d):
		global testmode
		print "Testmode toggled",self,w,w.get_active()
		testmode = w.get_active()
	def precinctCallback(self,w,d):
		print "Precinct entry activated.",self, w, w.get_text()
	def personCallback(self,w,d):
		print "Person entry activated.",self, w, w.get_text()
	def notesCallback(self,w,d):
		print "Notes entry activated.",self, w, w.get_text()

	def fileSetCallback(self,fcb):
		print "File set callback"
		# check for existence of subdirectories
		# and ability to write
		self.current_root = fcb.get_current_folder()

	def folderSetCallback(self,fcb):
		""" update current folder and prompt for missing subfolder """
		print "Folder set callback"
		# check for existence of subdirectories
		# and ability to write
		old_root = self.current_root
		new_root = fcb.get_current_folder()
		# No change, no action
		if old_root == new_root:
			return
		self.current_root = new_root

		# New folder has tree, show its unproc folder and return
		if os.path.exists(os.path.join(self.current_root,"unproc")):
			subprocess.call("nautilus %s" % (os.path.join(self.current_root,"unproc")),shell=True)
			return
		# Offer to create new folder tree, show it if created
		dialog = gtk.MessageDialog(
			type = gtk.MESSAGE_QUESTION,
			buttons = gtk.BUTTONS_YES_NO,
			message_format="Create unproc folder(s) under %s?" % (self.current_root,))
		response = dialog.run()
		dialog.destroy()
		if response == gtk.RESPONSE_NO:
			return
		try:
			os.mkdir(os.path.join(self.current_root,"unproc"))
			os.mkdir(os.path.join(self.current_root,"unproc/000"))
		except OSError as e:
			wdialog = gtk.MessageDialog( 
				type = gtk.MESSAGE_ERROR,
				buttons = gtk.BUTTONS_OK,
				message_format=
				"Could not create %s/unproc and/or unproc/000\n\n%s" % (self.current_root,e))
			wdialog.run()
			wdialog.destroy()
		else:
			subprocess.call("nautilus %s" % (os.path.join(self.current_root,"unproc")),shell=True)

	def fileSelectionChangedCallback(self,fcb):
		print "File selection changed"
		# check for existence of subdirectories
		# and ability to write
		print fcb.get_current_folder()
		self.current_root = fcb.get_current_folder()

	def fileActivatedCallback(self,fcb):
		print "File activated"
		# check for existence of subdirectories
		# and ability to write
		print fcb.get_current_folder()
		self.current_root = fcb.get_current_folder()

	def __init__(self,sc,sn):
		#Set the Glade file
		global logger
		self.logger = logger
		self.scanthread = None
		self.stopobject = threading.Event()
		self.builder = gtk.Builder()
 		self.sc = sc # the scanner object
		runpath = os.path.split(__file__)[0]
 		self.gladefile = os.path.join(runpath,"scanapp.glade")
		self.sn = sn # the 'serial number from file' object
		self.builder.add_from_file(self.gladefile)
		self.window = self.builder.get_object("window1")
		if (self.window):
			self.window.connect("destroy", gtk.main_quit)
		self.dir_chooser = self.builder.get_object("dirChooser")
		self.basic_settings_dialog = self.builder.get_object("basicSettingsDialog")
		self.nextLabel = self.builder.get_object("nextLabel")
		self.startLabel = self.builder.get_object("startLabel")
		self.countLabel = self.builder.get_object("countLabel")
		self.startLabel.set_text(str(sn.number))
		self.nextLabel.set_text(str(sn.number))
		self.countLabel.set_text("0")
		
		self.builder.get_object("pageHeightSpinbutton").set_value(11.0)
		self.builder.get_object("pageWidthSpinbutton").set_value(8.5)
		self.builder.get_object("templateResCheckbutton").set_active(False)
		self.builder.get_object("doublesidedCheckbutton").set_active(False)
		if source == 'ADF Duplex':
			self.builder.get_object("doublesidedCheckbutton").set_active(True)
		else:
			self.builder.get_object("doublesidedCheckbutton").set_active(False)
		self.current_root = const.root
		self.dir_chooser.set_current_folder(self.current_root)
		self.dir_chooser.connect('current-folder-changed',self.folderSetCallback)
		self.builder.get_object("endorserCheckbutton").set_active(endorse_int)
		self.builder.get_object("endorserYSpinbutton").set_sensitive(endorse_int)
		connex = (            
			("endorserYSpinbutton",
			 "NI",
			 "value_changed",
			 self.endorserYCallback
			 ),
			("dialogOK",
			 "NI",
			 "clicked",
			 self.basicSettingsDialogHideCallback
			),
			("doublesidedCheckbutton",
			 "NI",
			 "clicked",
			 self.doublesidedCallback
			),
			("endorserCheckbutton",
			 "NI",
			 "clicked",
			 self.endorseCallback
			),
			("templateResCheckbutton",
			 "NI",
			 "clicked",
			 self.templateResCallback
			),
			("pageWidthSpinbutton",
			 "NI",
			 "value_changed",
			 self.pageWidthCallback
			),
			("pageHeightSpinbutton",
			 "NI",
			 "value_changed",
			 self.pageHeightCallback
			),
			("changeButton",
			 "NI",
			 "clicked",
			 self.changeCallback
			),
			("doneButton",
			 "NI",
			 "clicked",
			 self.doneCallback
			),
			("scanButton",
			 "NI",
			 "clicked",
			 self.scanCallback
			),
			("stopButton",
			 "NI",
			 "clicked",
			 self.stopCallback
			),
			("stopButton",
			 "NI",
			 "clicked",
			 self.stopCallback
			),
			("basicSettingsMenuItem",
			 "NI",
			 "activate",
			 self.basicSettingsCallback
			),
			("advancedSettingsMenuItem",
			 "NI",
			 "activate",
			 self.advancedSettingsCallback
			),
			("aboutMenuItem",
			 "NI",
			 "activate",
			 self.aboutDialogCallback
			),
			("showFilesMenuItem",
			 "NI",
			 "activate",
			 self.showFilesCallback
			),
			("zipMenuItem",
			 "NI",
			 "activate",
			 self.zipCallback
			),
			("signMenuItem",
			 "NI",
			 "activate",
			 self.signCallback
			),
			("writeMenuItem",
			 "NI",
			 "activate",
			 self.writeCallback
			),
			("precinctEntry",
			 "NI",
			 "activate",
			 self.precinctCallback
			),
			("personEntry",
			 "NI",
			 "activate",
			 self.personCallback
			),
			("notesEntry",
			 "NI",
			 "activate",
			 self.notesCallback
			),
			("testToggle",
			 "NI",
			 "toggled",
			 self.testToggledCallback
			),
		)
		for x in connex:
			try:
				self.builder.get_object(x[0]).connect(
				x[2],x[3],None)
			except Exception, e:
				print x
				print e

  
		self.window.show()
		#self.dialog.show()

def scanner_init(sc):
	"""Set initial values for scanner."""
	global dpi
	global source
	global endorse_int
	global page_height_mm
	global page_width_mm
	sc.set_option('mode','Color')
	sc.set_option('resolution',dpi)
	sc.set_option('source',source)
	sc.set_option('endorser',endorse_int) # SANE_BOOL requires integer
	if endorse_int > 0:
		sc.set_option('endorser_bits',24)
		sc.set_option('endorser_step',1)
		sc.set_option('endorser_string', '%08ud')
		sc.set_option('endorser_val', sc.sn.number)
		sc.set_option('endorser_y',endorser_y)

def create_required_dirs(new_path):
	try:
		os.mkdir(os.path.join(new_path,"unproc"))
		os.mkdir(os.path.join(new_path,"unproc/000"))
	except OSError as e:
		print "Could not create %s/unproc and/or unproc/000" % (
			new_path,)
		print e


def run_scanapp():
	global logger
	global dpi
	global source 
	global endorse_int
	global page_width_mm
	global page_height_mm
	global testmode
	global sane_error
	global current_root
	sane_error = None
	testmode = 0
	source = 'ADF Front'
	dpi = 150
	endorse_int = 1 # begin with endorser on, 
	# so that you can set other endorser characteristics
	page_width_mm = int(round(25.4*8.5))
	page_height_mm = int(round(25.4*11))
	gobject.threads_init()
        # read configuration from tevs.cfg and set constants for this run
	cfg_file = tevsgui_get_args.get_args()
	scanconfig.get(cfg_file)
	homepath = os.path.expanduser("~")
	rootpath = homepath
	logbasefilename = os.path.basename(const.logfilename)
	logcompletefilename = os.path.join(homepath,logbasefilename)
	logger = scanconfig.logger(logcompletefilename)
	#print dir(const)
	# The file numbers and endorser values will come from a SerialNumber.
	endorser_step = 1

	testnumberfile = os.path.join(homepath,"nexttoscan.txt")
	sn = SerialNumber(testnumberfile,initial_value_if_no_file=50)
	if not os.path.exists(testnumberfile):
		try:
			f=open(testnumberfile,"w")				 
			f.write("0\n")
			f.close()
		except Exception as e:
			print e

			
        # Initialize sane and set the scanner's defaults prior to the thread.
	s = sane.init()
	devices = sane.get_devices()
	try:
		s = sane.open(devices[0][0])
	except IndexError:
		print "No devices found."
		builder = gtk.Builder()
		runpath = os.path.split(__file__)[0]
		gladefile = os.path.join(runpath,"scanapp.glade")  
		builder.add_from_file(gladefile)
		nsd = builder.get_object("noScannerDialog")
		nsd.run()
		#gtk.main()
		sys.exit(-1)

	sc = Scanner(None,sn,logger)
	scanner_init(sc)
	sa = ScanApp(sc,sn)

	gtk.main()

if __name__ == "__main__":
	run_scanapp()

