from darkstripes import darkstripes
import Image
import ImageStat
import sys
from ocr import tesseract, clean_ocr_text
import copy
import pdb
import const
"""
TODO: targets are coming out with the correct height, but with the y
offset starting at the bottom of the target.
"""

"""
Earlier routines provide us with a list of vertical offsets
of the targets within a contest, and a list of vertical offsets
of text lines in the contest.

We take this information, along with the image containing
the text lines, and associate each text line with the appropriate
target, ocr'ing text from the image along the way.

The result is a dictionary keyed by the target offsets
and containing a list of triplets for each text line
associated with the target: starting y offset, ending y offset, text.

"""
def text_code(im,threshold = 128):
    """ unique identifier for the un-OCRd text in the image

    OCR may misread, but we should be able to merge misreads
    by using a code that is more robust.
    This will be time consuming, but...
    Split the line into pixel wide vertical stripes,
    determine whether each stripe has any dark pixels after trim,
    get lengths of horizontal strips with and w/o dark pixels,
    determine median length, divide all lengths by median,
    use single character to represent each length 0-9 A-Z for >10
    """

    trim = 0
    coldata = []
    for col in range(trim,im.size[0]-trim):
        coldatacrop = im.crop((col,trim,col+1,im.size[1]-trim))
        coldark = False
        for d in coldatacrop.getdata(): 
            try:
                coldark = (d < threshold)
            except:
                coldark = (d[0] < threshold)
            if coldark: break
        coldata.append(coldark)
    #print im.size[0],len(coldata)
    # get length of light and dark zones
    lengths = []
    in_dark = False
    light_length, dark_length = 0,0
    for dark in coldata:
        if dark and in_dark: 
            dark_length += 1
        elif (not dark) and in_dark: 
            lengths.append(dark_length)
            dark_length = 0
            light_length = 1
            in_dark = False
        elif dark and (not in_dark):
            #use dark lengths only
            #lengths.append(light_length)
            light_length = 0
            in_dark = True
            dark_length = 1
        else:
            light_length += 1
    # get median length
    median = 0
    lengths_copy = None
    if len(lengths)>0:
        lengths_copy = copy.copy(lengths)
        lengths.sort()
        median = lengths[len(lengths)/2]
    else:
        return "?"
    #print "Lengths:", lengths
    #print "Median length:",median
    #if median > 0:
    #    out_lengths = map(lambda a: int(round(float(a)/median)), lengths_copy)
    #else:
    #    out_lengths = []
    # divide into long zones and short zones at median
    out_string = ""
    for ol in lengths:
        try:
            letter = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"[ol]
        except:
            letter = "!"
        out_string = "%s%s" % (out_string,letter)
    #print out_lengths
    #print out_string
    return str(out_string)

def target_and_text_from_images(targetimage,textimage,debug=False):
    if debug: 
        targetimage.save("/tmp/targets.jpg")
        textimage.save("/tmp/text.jpg")
        print "Debug stop at target and text from images."
    targetstripes = darkstripes(targetimage)
    # had to lower threshold to split some strips
    textstripes = darkstripes(textimage,threshold=200)
    tt,tc = target_and_text(targetstripes,textstripes,textimage,debug=debug)
    return tt,tc

def target_and_text(targetlist,textlist,textimage,debug=False):
    """associate each zone in textlist with best zone in first list

    Best is defined as follows:
    * text goes to the target that begins at or above 
    the end of the text plus 1/8 the text's height
    and is closest
    """
    target_text = {}
    target_text_code = {}

    try:
        targetlist.sort(key = lambda a: -a[0])
    except KeyError:
        print "KeyError trying to sort targetlist"
        #pdb.set_trace()
        pass
    textlist.sort()
    try:
        textlist = map(lambda a:list(a), textlist)
    except KeyError:
        print "KeyError trying to map textlist"
        #pdb.set_trace()
        pass
    if debug:
        print "Debug in target_and_text"
        print targetlist
        pdb.set_trace()
    img_num = 0
    for text in textlist:
        text_begin,text_end,eighth_text_height = text[0],text[1],(text[1]-text[0])/8
        # skip text not tall enough
        # pdb.set_trace()
        if text_end < (text_begin+(const.dpi/20)):
            continue
        print "Checking targets against text beginnning %d ending %d" % (
            text_begin,text_end)
        for target in targetlist:
            code_strings = []
            #print "Target",target
            #pdb.set_trace()
            # skip targets not tall enough
            if target[1] <= (target[0]+(const.dpi/20)):
                continue
            print "Target begins at %d ends at %d" % (target[0],target[1])
            target_begin = target[0]
            if (text_end + eighth_text_height) >= target_begin:
                if text_end > text_begin:
                    # in addition to ocr of the text, 
                    # we also want a text-code that will
                    # allow us to merge OCR misreads.
                    # for starters, let's try getting
                    # the distance between mostly dark
                    # and mostly light stripes on the 
                    # text line
                    cropped_image = textimage.crop((0,
                                                    text_begin, 
                                                    textimage.size[0],
                                                    text_end
                                                    )
                                                   )
                    cropped_image.save("/tmp/cropped_image%d.jpg" % (img_num,))
                    img_num += 1
                    # pdb.set_trace()
                    text_ocr = tesseract(cropped_image)
                    text_ocr = clean_ocr_text(text_ocr.strip())
                    try:
                        code_string = text_code(cropped_image)
                    except Exception, e:
                        print "Could not get code string, using '?'",
                        print e
                        code_string = "?"
                else:
                    text_ocr = ""
                    code_string = "0"
                text.append(text_ocr)
                code_strings.append(code_string)
                if target in target_text:
                    target_text[target].append(text)
                    target_text_code[target].append(code_strings)
                else:
                    target_text[target] = []
                    target_text[target].append(text)
                    target_text_code[target] = []
                    target_text_code[target].append(code_strings)
                break

    return target_text, target_text_code


if __name__ == "__main__":
    if len(sys.argv)<3:
        print "usage: python target_and_text.py targetimage.jpg textimage.jpg"
    im = None
    try:
        targetimage = Image.open(sys.argv[1])
    except Exception, e:
        print e
        print "Could not open file",sys.argv[1],"as targetimage"
        sys.exit(0)
    try:
        textimage = Image.open(sys.argv[2])
    except Exception, e:
        print e
        print "Could not open file",sys.argv[2],"as textimage"
        sys.exit(0)
    tt,tc = target_and_text_from_images(targetimage,textimage)
    #targetstripes = darkstripes(targetimage)
    #textstripes = darkstripes(textimage)
    #tt = target_and_text(targetstripes,textstripes,textimage)
    keys = tt.keys()
    keys.sort()
    for k in keys:
        print "Target",k,"text",tt[k],tc[k]
    print "END"
