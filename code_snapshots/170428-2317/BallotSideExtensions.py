import ocr

def IsWriteIn():
    return False

def IsVoted():
    return False

class Extensions(object):
    """A bag for all the various extension objects and functions
    to be passed around to anyone who needs one of these tools
    All extensions must be in the _xpts dict below and must be
    callable"""

    ocr_engine = ocr.tesseract
    ocr.cleaner = ocr.clean_ocr_text
    _xpts = {
        "ocr_engine":     ocr.tesseract,#_with_prefix_and_postfix, 
        "ocr_cleaner":    ocr.clean_ocr_text,
        "IsWriteIn":      IsWriteIn,
        "IsVoted":        IsVoted,
    }


