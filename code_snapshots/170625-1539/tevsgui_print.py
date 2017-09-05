import gtk
import pdb
import pango
global test_array
test_array = [
# count, jur, contest, choice
[1,"JurisdictionA","Contest1","ChoiceA"],
[11,"JurisdictionA","Contest1","ChoiceB"],
[111,"JurisdictionA","Contest1","ChoiceC"],
[2,"JurisdictionA","Contest2","ChoiceA"],
[21,"JurisdictionA","Contest2","ChoiceB"],
[3,"JurisdictionA","Contest3","ChoiceA"],
[31,"JurisdictionA","Contest3","ChoiceB"],
[311,"JurisdictionA","Contest3","ChoiceC"],
[312,"JurisdictionA","Contest3","ChoiceD"],
[313,"JurisdictionA","Contest3","ChoiceE"],
[4,"JurisdictionA","Contest4","ChoiceA"],
[41,"JurisdictionA","Contest4","ChoiceB"],
[110,"JurisdictionB","Contest1","ChoiceA"],
[111,"JurisdictionB","Contest1","ChoiceB"],
[112,"JurisdictionB","Contest1","ChoiceC"],
[120,"JurisdictionB","Contest2","ChoiceA"],
[121,"JurisdictionB","Contest2","ChoiceB"],
[130,"JurisdictionB","Contest3","ChoiceA"],
[131,"JurisdictionB","Contest3","ChoiceB"],
[132,"JurisdictionB","Contest3","ChoiceC"],
[133,"JurisdictionB","Contest3","ChoiceD"],
[134,"JurisdictionB","Contest3","ChoiceE"],
[140,"JurisdictionB","Contest4","ChoiceA"],
[141,"JurisdictionB","Contest4","ChoiceB"]
]

class PrintErrors(object):
    def __init__(self,error_file,window):
        self.error_file = error_file 
        self.page_starts = []
        self.line_array = []
        self.paginated_pages = 0
        self.window = window
        print_op = gtk.PrintOperation()
        print_op.connect("begin_print",self.begin_print,None)
        print_op.connect("paginate",self.paginate,None)
        print_op.connect("request_page_setup",self.request_page_setup,None)
        print_op.connect("draw_page",self.draw_page,None)
        print_op.connect("end_print",self.end_print,None)
        res = print_op.run(gtk.PRINT_OPERATION_ACTION_PRINT_DIALOG, self.window)

    def begin_print(self,printop,context,data):
        pass

    def end_print(self,printop,context,data):
        pass

    def request_page_setup(self,printop,context,page_number,setup,data):
        pass

    def paginate(self,printop,context,data):
        """ paginate """
        # For some reason, paginate gets called twice.
        if self.paginated_pages > 0:
            return True
        line_count = 0
        efile = open(self.error_file,"r")
        for line in efile.readlines():
            try:
                if line.find("ERR")>-1:
                    self.line_array.append(line[:-1])
                    if (line_count % 40)==0:
                        self.page_starts.append(line_count)
                        #print self.page_starts
                    line_count += 1
            except Exception, e:
                print e
        self.page_starts.append(line_count)
        #print self.page_starts
        self.paginated_pages = len(self.page_starts)-1
        #print "Page starts",self.page_starts
        #print self.paginated_pages
        printop.set_n_pages(self.paginated_pages)
        return True

    def draw_page(self,printop,context,page_number,data):
        #print "****Draw Page",page_number
        #print "Printop",printop
        #print "Context",context
        #print "Page number",page_number
        #print "Data for this page"
        
        try:
            start = self.page_starts[page_number]
        except:
            return
        try:
            end = self.page_starts[page_number+1]
        except:
            end = len(self.line_array)
        if start > end:
            return
            
        textarray = []
        header = "<big>Errors in extraction log, page %d of %d.\n</big>" % (
            page_number+1,
            len(self.page_starts)-1)

        textarray.append(header)
            
        for index in range(start,end):
            textarray.append(self.line_array[index])
        if end == len(self.line_array):
            textarray.append(" ")
            textarray.append("Errors from extraction log ENDS")

        cr = context.get_cairo_context()
        width = context.get_width()
        layout = context.create_pango_layout()
        desc = pango.FontDescription("monospace 10")
        layout.set_font_description(desc)
        layout.set_width(-1)
        layout.set_markup("\n".join(textarray))
        layout.set_alignment(pango.ALIGN_LEFT)
        x,layout_height = layout.get_size()
        #print layout.get_size()
        text_height = layout_height/pango.SCALE
        cr.move_to(context.get_dpi_x()/2,context.get_dpi_y()/2)
        cr.show_layout(layout)
                        
class PrintTotals(object):
    def __init__(self,data_array,window):
        #data array is last_vote_counts from calling App class
        self.data = data_array
        self.window = window
        self.page_breaks = []
        self.paginated_pages = 0
        print_op = gtk.PrintOperation()
        print_op.connect("begin_print",self.begin_print,self.data)
        print_op.connect("paginate",self.paginate,self.data)
        print_op.connect("request_page_setup",self.request_page_setup,self.data)
        print_op.connect("draw_page",self.draw_page,self.data)
        print_op.connect("end_print",self.end_print,self.data)
        res = print_op.run(gtk.PRINT_OPERATION_ACTION_PRINT_DIALOG, self.window)
        
    def begin_print(self,printop,context,data):
        #print "*****Begin Print*****"
        pass

    def end_print(self,printop,context,data):
        #print "*****End Print*****"
        pass

    def request_page_setup(self,printop,context,page_number,setup,data):
        #print "*****Request page setup",
        pass

    def paginate(self,printop,context,data):
        self.page_breaks = [0]
        last_page_break = 0
        #initialize lastjur and lastcontest to 0th entries
        lastjur = data[0][1]
        lastcontest = data[0][2]
        for index in range(len(data)):
            count = data[index][0]
            jur = data[index][1]
            contest = data[index][2]
            choice = data[index][3]
            if jur != lastjur or contest != lastcontest:
                # put in a page break when the jurisdiction changes,
                # or when there is a contest break and 
                # there have been more than 40 lines since last pb
                if jur!=lastjur or (index > (last_page_break+40)) :
                    self.page_breaks.append(index)
                    last_page_break = index
                lastjur = jur
                lastcontest = contest

        self.paginated_pages = len(self.page_breaks)
        printop.set_n_pages(self.paginated_pages)
        #print "set n pages to ",self.paginated_pages
        return (self.paginated_pages!=0)

    def draw_page(self,printop,context,page_number,data):
        try:
            start = self.page_breaks[page_number]
        except:
            return
        try:
            end = self.page_breaks[page_number+1]
        except:
            end = len(data)
        if start > end:
            return
        textarray = []
        if page_number == 0:
            textarray.append("<big>Election results</big>")
        #textarray.append("Database %s at %s, page %d" % (
        #        const.dbname, time.asctime(), page_number))
        textarray.append("Page %d of %d" % (page_number+1,self.paginated_pages))
        textarray.append(" ")
        lastcontest = ""
        for index in range(start,end):
            count = data[index][0]
            jur = data[index][1]
            contest = data[index][2]
            choice = data[index][3]
            if contest != lastcontest:
                textarray.append("")
                lastcontest = contest
            try:
                textarray.append("%s\t%8s\t%20s\t%20s" % (count,jur,contest[:20],choice[:20]))
            except:
                pass
        cr = context.get_cairo_context()
        width = context.get_width()
        layout = context.create_pango_layout()
        desc = pango.FontDescription("monospace 10")
        layout.set_font_description(desc)
        layout.set_width(-1)
        layout.set_markup("\n".join(textarray))
        layout.set_alignment(pango.ALIGN_LEFT)
        x,layout_height = layout.get_size()
        #print layout.get_size()
        text_height = layout_height/pango.SCALE
        cr.move_to(context.get_dpi_x()/2,context.get_dpi_y()/2)
        cr.show_layout(layout)
                        

class App(object):

    def do_print_totals(self,button,data):
        # data is array then window
        pt = PrintTotals(data[0],data[1])

    def do_print_errors(self,button,data):
        # data is info then window
        pe = PrintErrors(data[0],data[1])
        
    def do_exit(self,button,data):
        gtk.main_quit()

    def delete_event(self,widget,event,data):
        return False

    def __init__(self):
        global test_array
        self.builder = gtk.Builder()
        self.builder.add_from_file("tevsgui_print.glade")
        self.window = self.builder.get_object("windowMain")
        self.window.set_title("TEVSGUI Print Test Version")
        self.peb = self.builder.get_object("printErrorsButton")
        self.ptb = self.builder.get_object("printTotalsButton")
        self.eb = self.builder.get_object("exitButton")
        self.window.connect("delete_event",
                            self.delete_event,
                            None)
        self.peb.connect("clicked",
                         self.do_print_errors,
                         ("/home/mitch/nov2011/extraction.log",self.window))    
        self.ptb.connect("clicked",
                         self.do_print_totals,
                         (test_array,self.window))    
        self.eb.connect("clicked",
                        self.do_exit, 
                        None)
                        

        
if __name__ == "__main__":
    app = App()
    app.window.show()
    gtk.main()
