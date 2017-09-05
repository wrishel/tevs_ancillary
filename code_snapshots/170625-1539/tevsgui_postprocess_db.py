import sys
import gtk  
import pygtk  

import const
import db_merge_variants
import exceptions
import gobject
import os
import pdb
import pickle
# each "requestor" sets up and communicates with a subprocess 
# to handle tasks that would otherwise freeze the GUI
import tevsgui_db_query_requestor
import tevsgui_print
import tevsgui_status


votecount_query = """select count(*) as votes, %s, cv.orig_ocr_text, chv.orig_ocr_text  from ballots b join voteops v on b.ballot_id = v.ballot_id join ocr_variants cv on cv.id = v.contest_text_standardized_id join ocr_variants chv on chv.id = v.choice_text_standardized_id where was_voted and not overvoted group by %s cv.orig_ocr_text, chv.orig_ocr_text order by %s cv.orig_ocr_text, chv.orig_ocr_text;""" 

votecount_pickle_file = "/tmp/votecount.pickle"

#*************************************************************************
# Votecount button triggers two database requests, 
# updating GUI table when request calls back.
#*************************************************************************

def on_delete_event(widget, event):
    return True

class PostProcessDB(object):

    def __init__(self,tevs=None,dbc=None):
        self.tevs = tevs
        self.dbc = dbc
        self.votecountListInitted = False
        self.last_votecount = []
        self.window = None
        # set variantsList initted True when you first create a set of OCR
        # variants in response to user request for merge or vote count
        self.variantsListInitted = False

    def do_hide(self,button,window):
        window.hide()

    def do_print(self,button,data):
        # data is list_store
        p = tevsgui_print.PrintTotals(data,self.window)

    def votecount_data2_ready_cb(self,line,data):
        """async queries complete, data available, display in table"""
        #print "Votecount2 cb"
        #print "Ambig data ready in /tmp/ambig.pickle"
        picklefile = open(votecount_pickle_file,"rb")
        retval = pickle.load(picklefile)
        picklefile.close()
        os.unlink(votecount_pickle_file)
        for record in retval:
            data.append(record)
        self.last_votecount.extend(retval)
        self.show_votecount(data)

    def votecount_data1_ready_cb(self,line,data):
        self.tevs.status.update("Retrieving per-precinct data.")
        picklefile = open(votecount_pickle_file,"rb")
        retval = pickle.load(picklefile)
        picklefile.close()
        os.unlink(votecount_pickle_file)
        for record in retval:
            data.append(record)
        self.last_votecount = retval
        # make new async query to database, calling back when done
        qr = tevsgui_db_query_requestor.QueryRequestor(
            stdout_cb = self.votecount_data2_ready_cb,
            stdout_cb_data = data,
            user = const.dbuser,
            database = const.dbname,
            query = votecount_query %("precinct","precinct,","precinct, " ),
            retfile = votecount_pickle_file)

    def show_votecount(self,data):
        """ present votecount in window defined in glade """
        self.window = self.tevs.builder.get_object ("windowVoteCounts")
        self.window.connect("delete-event",on_delete_event)

        treeview = self.tevs.builder.get_object("voteCountsTreeView")
        treeview.set_model(data)

        printButton = self.tevs.builder.get_object("voteCountsPrint")
        printButton.connect("clicked",self.do_print,self.last_votecount)

        closeButton = self.tevs.builder.get_object("voteCountsClose")
        closeButton.connect("clicked",self.do_hide,self.window)

        if not self.votecountListInitted:
            cr0 = gtk.CellRendererText()
            tvc0 = gtk.TreeViewColumn("Votes")
            treeview.append_column(tvc0)
            tvc0.pack_start(cr0,True)
            tvc0.set_attributes(cr0,text=0)

            cr1 = gtk.CellRendererText()
            tvc1 = gtk.TreeViewColumn("Precinct")
            treeview.append_column(tvc1)
            tvc1.pack_start(cr1,True)
            tvc1.set_attributes(cr1,text=1)

            cr2 = gtk.CellRendererText()
            tvc2 = gtk.TreeViewColumn("Contest")
            treeview.append_column(tvc2)
            tvc2.pack_start(cr2,True)
            tvc2.set_attributes(cr2,text=2)

            cr3 = gtk.CellRendererText()
            tvc3 = gtk.TreeViewColumn("Choice")
            treeview.append_column(tvc3)
            tvc3.pack_start(cr3,True)
            tvc3.set_attributes(cr3,text=3)
            self.votecountListInitted = True

        self.window.show_all()
        self.tevs.status.update("Showing %d count records." % (len(self.last_votecount),))


    def process_overvotes(self,line,stage):
        stages = [
(db_merge_variants.update_id_contests_str,"Updating contest variants"),

(db_merge_variants.update_id_choices_str,"Updating choice variants"),

("drop table if exists overvotes cascade;","Dropping old tables"),

("drop table if exists overvote_ids cascade;","Dropping old tables"),

("drop table if exists overvote_values cascade;","Dropping old tables"),

("drop table if exists overvote_diffs cascade;","Dropping old tables"),

("""select count(*) as votes, contest_text_standardized_id, filename into overvotes from voteops where was_voted group by contest_text_standardized_id, filename;""","Determining votes per contest per ballot"),

("""select v.voteop_id into overvote_ids from overvotes o join voteops v on o.contest_text_standardized_id = v.contest_text_standardized_id join ocr_variants ocr on v.contest_text_standardized_id = ocr.id and o.filename = v.filename where o.votes > ocr.max_votes_in_contest;""",
"Getting ids of overvoted votes"),

("""select v.voteop_id, v.filename, substring(v.contest_text,1,30) as contest, substring(v.choice_text,1,30) as choice,v.red_darkest_pixels as darkest, v.red_mean_intensity as intensity into overvote_values from overvote_ids o join voteops v on o.voteop_id = v.voteop_id where was_voted;
""",
"Getting intensity values of overvoted votes for comparison"),

("""select voteop_id, filename, contest, intensity, intensity - avg(intensity) over (partition by filename, contest) as intensity_less_avg into overvote_diffs from overvote_values;""",
"Determining darkness spread for overvoted votes."
),
("""update voteops set was_voted=False,overvoted=True,suspicious=True where voteop_id in (select voteop_id from overvote_diffs where intensity_less_avg >= -5 and intensity_less_avg <= 5);""",
"Leaving overvotes unvoted where intensity within 10 of average."
)

]
        
        #print stage
        #if stage == 0: 
        #    print "Stage 0"
        if stage < len(stages)-1:
            qr = tevsgui_db_query_requestor.QueryRequestor(
                #stdout_cb = self.process_overvotes,
                #stdout_cb_data = stage+1,
                hup_cb = self.process_overvotes,
                hup_cb_data = stage+1,
                user = const.dbuser,
                database = const.dbname,
                query = stages[stage+1][0],
                retfile = votecount_pickle_file)
            self.tevs.status.update("%s. %d further tasks after this." % (stages[stage+1][1],len(stages)-(stage+2)))
            print "%s. %d further tasks after this." % (stages[stage+1][1],len(stages)-(stage+2))
        else:
            self.tevs.status.update("Done processing overvotes")
            print ("Done processing overvotes")
            self.only_get_vote_counts()

    def execute_merge_updates_in_background(self,dummy,stage):
        stages = [
            (db_merge_variants.update_id_contests_str,
             "Updating contest standard ids"),
            (db_merge_variants.update_id_choices_str,
             "Updating choice standard ids")
            ]

        if stage < (len(stages)-1):
            qr = tevsgui_db_query_requestor.QueryRequestor(
                hup_cb = self.execute_merge_updates_in_background,
                hup_cb_data = stage + 1,
                user = const.dbuser,
                database = const.dbname,
                query = stages[stage+1][0],
                retfile = votecount_pickle_file)
            self.tevs.status.update("%s. %d tasks remain." % (stages[stage+1][1],len(stages)-(stage+2)))
            print "%s. %d tasks remain of %d." % (stages[stage+1][1],len(stages)-(stage+2),len(stages))
        else:
            self.tevs.status.update("Done merging variants.")
            msg = self.tevs.builder.get_object("messagedialog_overvotes")
            msg.connect("delete-event",on_delete_event)
            response = msg.run()
            msg.hide()
            if response == gtk.RESPONSE_YES:
                self.process_overvotes("",-1)
            else:
                self.only_get_vote_counts()

    def only_get_vote_counts(self):
        ls = gtk.ListStore(gobject.TYPE_LONG,
                               gobject.TYPE_STRING,
                               gobject.TYPE_STRING,
                               gobject.TYPE_STRING)
        try:
            self.last_votecount = []
        except Exception,e:
            print e
            pdb.set_trace()

        # make async query to database, calling back when done
        query = votecount_query % ("'ALL'","","" )
        qr = tevsgui_db_query_requestor.QueryRequestor(
            stdout_cb = self.votecount_data1_ready_cb,
            stdout_cb_data = ls,
            user = const.dbuser,
            database = const.dbname,
            query = query,
            retfile = votecount_pickle_file)

    def get_vote_counts_querying_process_overvotes(self):
        " retrieve and display vote counts, and allow for printing"
        msg = self.tevs.builder.get_object("messagedialog_overvotes")
        msg.connect("delete-event",on_delete_event)
        response = msg.run()
        msg.hide()
        self.tevs.status.update("Retrieving full jurisdiction data.")
        if response == gtk.RESPONSE_YES:
            self.process_overvotes("",-1)
        else:
            self.only_get_vote_counts()

    def text_merge_cr_edited(self,cellrenderertext,path,new_text,user_param1):
        #print cellrenderertext
        #print path
        #print new_text
        ls_contests = user_param1[0]
        print ls_contests[path][1], type(ls_contests[path][1])
        ls_contests[path][1]=int(new_text)
        print ls_contests[path][1], type(ls_contests[path][1])
        try:
            self.dbc.query_no_returned_values(
                """update ocr_variants 
set standardized_id = %d where id = %d""" % (ls_contests[path][1],
                                             ls_contests[path][0]))
        except Exception,e:
            print e


        #associations = user_param1[1]
        #print len(associations)
        #print associations[0]

    def text_merge_cr_maxvotesedited(self,cellrenderertext,path,new_text,user_param1):
        #print cellrenderertext
        #print path
        #print new_text
        ls_contests = user_param1[0]
        print ls_contests[path][2], type(ls_contests[path][2])
        ls_contests[path][2]=int(new_text)
        print ls_contests[path][2], type(ls_contests[path][2])
        try:
            self.dbc.query_no_returned_values(
                """update ocr_variants 
set max_votes_in_contest = %d where id = %d""" % (ls_contests[path][2],
                                             ls_contests[path][0]))
        except Exception,e:
            print e


        #associations = user_param1[1]
        #print len(associations)
        #print associations[0]

    def text_merge_associate(self,button,data):
        treeview = data[0]
        e1 = data[1]
        e2 = data[2]
        b2 = data[3]
        associations = data[4]
        # get the row to modify from e1
        try:
            e1_value = int(e1.get_text())
        except:
            print "Not an integer"
            return
        try:
            e2_value = int(e2.get_text())
        except:
            print "Not an integer"
            return
        tm = treeview.get_model()
        # set the value of the 1st field of row e1 (-1) to the value given in e2
        # assumes row numbering in database starts at 1

        # WRONG: tm[e1_value-1][1] = e2_value
        # really need to search for the item in the tm array 
        # which has e1_value-1 as one of its values, and update that item;
        # we must NOT use the array offset as is done above
        for n in range(len(tm)):
            if tm[n][0] == e1_value:
                tm[n][1] = e2_value
                break


        # send the update to the ocr_variants table in the db
        # associate first row mentioned standardized_id
        # with regular id of second row mentioned
        try:
            self.dbc.query_no_returned_values(
                """update ocr_variants 
set standardized_id = %d where id = %d""" % (e1_value,e2_value))
        except Exception,e:
            print e

    def is_variants_table_wanted(self):
        # if the ocr_variants table exists, you may not need to redo the merge
        retval = self.dbc.query("""select table_name 
from information_schema.tables 
where table_catalog = CURRENT_CATALOG 
and table_schema = CURRENT_SCHEMA 
and table_name = 'ocr_variants'""")
        if len(retval) == 0:
            return False

            # table exists, prompt to find out if user wants to re-create it
        msg = self.tevs.builder.get_object("messagedialog_ocr")
        msg.connect("delete-event",on_delete_event)
        response = msg.run()
        msg.hide()
        if response == gtk.RESPONSE_YES:
            # rebuild table
            return True
        return False
        
    def text_merge_done(self,button,data):
        "update voteops from merged text, then get vote counts"
        window, store = data
        window.hide()
        dummy = 0
        initial_stage = -1
        self.execute_merge_updates_in_background(dummy,initial_stage)

    def on_buildVariantsTable_clicked(self, button, data):
        window = self.tevs.builder.get_object ("windowTextMerge")
        window.connect("delete-event",on_delete_event)
        treeview = self.tevs.builder.get_object("textMergeTreeView")


        associations = db_merge_variants.create_ocr_variants_list(self.dbc)
        ls_contests = gtk.ListStore(
            gobject.TYPE_LONG,
            gobject.TYPE_LONG,
            gobject.TYPE_LONG,
            gobject.TYPE_STRING,
            gobject.TYPE_STRING)
        treeview.set_model(ls_contests)
        #tvselection = treeview.get_selection()

        for record in associations:
            ls_contests.append(record)
        b2 = self.tevs.builder.get_object("textMergeClose")
        b2.connect("clicked",self.text_merge_done,(window,ls_contests))

        if not self.variantsListInitted:
            cr0 = gtk.CellRendererText()
            tvc0 = gtk.TreeViewColumn("Row\n#")
            treeview.append_column(tvc0)
            tvc0.pack_start(cr0,True)
            tvc0.set_attributes(cr0,text=0)

            cr1 = gtk.CellRendererText()
            cr1.connect("edited", self.text_merge_cr_edited,(ls_contests,associations))
            cr1.set_property("editable",True)
            tvc1 = gtk.TreeViewColumn("Standard\nID")
            treeview.append_column(tvc1)
            tvc1.pack_start(cr1,True)
            tvc1.set_attributes(cr1,text=1)

            cr2 = gtk.CellRendererText()
            cr2.connect("edited", self.text_merge_cr_maxvotesedited,(ls_contests,associations))
            cr2.set_property("editable",True)
            tvc2 = gtk.TreeViewColumn("Max\nChoices")
            treeview.append_column(tvc2)
            tvc2.pack_start(cr2,True)
            tvc2.set_attributes(cr2,text=2)

            cr3 = gtk.CellRendererText()
            tvc3 = gtk.TreeViewColumn("Contest and Choice Text Variants")
            treeview.append_column(tvc3)
            tvc3.pack_start(cr3,True)
            tvc3.set_attributes(cr3,text=4)
            self.variantsListInitted = True
        window.show_all()

    def on_showVoteCounts_clicked(self, button, data):
        print "Show vote counts clicked."

        print self
        print button
        print data

        # to generate useful vote counts, we have to have the ability
        # to merge variants of contest text that occur on different 
        # templates.  We need user involvement, but can do much prior
        # to displaying to user.
        
        vtw = self.is_variants_table_wanted()

        if vtw:
            self.on_buildVariantsTable_clicked(None,None)
            # when close button is pressed, 
            # we proceed to the callback at "text_merge_done"
            # which calls get vote counts for us

        else:
            self.get_vote_counts_querying_process_overvotes()



    def on_printVoteCounts_clicked(self, button, data):
        print "Print vote counts clicked."
        print "Same SQL as for showVotes, feed csv into table, probably in Reportlab"
        print self
        print button
        print data
        retval1 = [
("a","b","c"),
("1","2","3"),
("4","5","6")
]
        retval2 = [
("2a","2b","2c"),
("21","22","23"),
("24","25","26")
]
        self.do_print(button,retval1)

