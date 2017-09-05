# SessionStrings.py
# creates a dictionary of all strings encountered 
# in a scanning and OCR session, with each assigned
# a serial number.

class SessionStrings(object):
    """Maintain a list of all unique strings OCR'd

    Maintain a list of all strings OCR'd, possibly uploading
    each entry to a SQL database table.  

    Provide functions which can be used to indicate a likelihood
    that two strings are variants of the same text.
"""


    def __init__(self,start_counter=0):
        counter = start_counter
        string_list = []
        string_dict = {}

    def add_string(self,the_string, code=None):
        if the_string not in my_dict:
            string_dict[the_string] = self.counter
            string_list.append(the_string)
            codes_list.append(code) 
            # perhaps upload the_string and counter to database
            # 
            self.counter += 1

    def list_strings(self):
        return self.string_list

    def string_from_number(self,num):
        return self.string_list[num]

    # now provide functions for comparing strings 
    # to see if they probably represent OCR variants
    def otherfuncs(self):
        pass
