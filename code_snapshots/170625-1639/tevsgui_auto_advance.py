# tevsgui_auto_advance.py
# part of TEVS

import gobject

class AutoAdvance(object):


    def timer_func(self):
        """Function to auto-advance"""
        self.nextImage.clicked()
        # ask to be called again
        return True

    def __init__(self,nextImage,seconds=1):
        """Create an object to manage auto-advance state"""
        self.nextImage = nextImage
        self.seconds = seconds
        self.timer_id = None
        self.advancing = False

    def toggled(self,tevsgui,widget,data):
        if widget.get_active():
            # set up a timer to advance
            self.timer_id = gobject.timeout_add(self.seconds*1000,self.timer_func)
            self.advancing = True
        else:
            # remove the existing timer
            try:
                gobject.source_remove(self.timer_id)
                self.advancing = False
            except:
                pass

    def seconds_value_changed(self,tevsgui,widget,data):
        self.seconds = widget.get_value_as_int()
        # unregister old timer
        if not self.advancing:
            return
        try:
            gobject.source_remove(self.timer_id)
        except:
            pass
        #register timer with new standard delay
        self.timer_id = gobject.timeout_add(self.seconds*1000,self.timer_func)
        
