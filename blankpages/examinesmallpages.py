'''
    This program was developed to verify an approach to determining whether an image is
    a ballot or the "this side left intentionally blank" side.

    For HART ballots as used in Humboldt County, using 300 dpi jpegs if the getredhist()
    function returns a value < 60K the image is a ballot. If it is > 70K the image
    is a blank page. Experimentally, there are no images that return a value in between.

    NOTE: as written this will mistake some upside down ballots for a blank page. To be
    more complete it would have to check a zone at the right bottom of the page point-symmetric
    to the currently checked zone.

    It also may not handle ballots with the stub still attached.

    Wes Rishel 8/28/17
'''

import os
import util
import const
import config
import tevsgui_get_args
from PIL import Image
import csv
import random
import time


cfg_file = tevsgui_get_args.get_args()
config.get(cfg_file)

maximum_actual_ballot_file = 243548

class img():    # naked object
    pass

def makepath(image_num):
    return "%s/unproc/%03d/%06d.jpg" % (const.root, int(image_num) / 1000, int(image_num))

def getredhist(f):
    '''Compute the brightess of a swath in the page in the upper left column. If the image is
       not a blank side, this area will have printing. Brightness is the sum of the top 8
       levels in the histogram.
    '''
    im = Image.open(f)
    im = im.crop((500, 350, 600, 1100))
    return sum(im.histogram()[248:256])


''' Pick a random set of files smaller than a limit based 
    on max_blank_page_file_size, compute a score, and
    output to a CSV.
'''

cumtime = 0
smallimages = []
imgcnt = 0
outcnt = 0
for root, dirs, files in (os.walk(util.root('unproc'))):
    files.sort()
    for file in files:
        imgcnt += 1
        image_num = int(file[:-4])
        if image_num <= maximum_actual_ballot_file:
            if random.random() < 1:  # fraction of the files to test
                x = makepath(image_num)
                flen = os.stat(x).st_size
                if True: #flen <= const.max_blank_page_file_size + 50000:
                    starttime =  time.time()
                    outcnt += 1
                    t = img()
                    t.flen = flen
                    t.image_num = image_num
                    t.score = getredhist(x)
                    timediff = time.time() - starttime
                    cumtime += timediff
                    smallimages.append(t)
                    print '{:6} {:7} {:7} {:7} {:7} {:5.3f} {:5.3f}'\
                        .format(imgcnt, outcnt, t.image_num, imgcnt, t.score, timediff,
                                cumtime / outcnt)

print len(smallimages)

outputs = []
with open('/media/psf/Home/NotForTheCloud/scores.csv', 'wb') as f:
    writer = csv.writer(f)
    for img in smallimages:
        writer.writerow((img.image_num, img.flen, img.score))
        outputs.append([img.image_num, img.flen, img.score, 0])

outputs.sort(key=lambda r: r[2]) # sort on score

threshold = 65000
for t in range(1, len(outputs)):
    if outputs[t][2] > threshold: break


# smax = 0
# ismax = None
# for i in range(1, len(outputs)):
#     r = outputs[i]
#     r[3] = abs(r[2] - outputs[i-1][2])
#     if r[3] > smax:
#         smax = r[3]
#         ismax = i
#     outputs[i] = r

bottom = max(t-5, 0)
top = min(t+5, len(outputs))
for i in range(bottom, top):
    im = Image.open(makepath(outputs[i][0]))
    im = im.resize((im.size[0]/10, im.size[1]/10))
    im.show()
    if raw_input(outputs[i]).lower().strip() == 's': break






exit(0)

l = [125971,
157697,
34071,
42167]

h = [getredhist(i) for i in l]

print l
fmth = ' , '.join((['"{}"'] * (len(l)+1))) + '\n'
fmtl =  ', '.join((['{}']   * (len(l)+1))) + '\n'

with open('/media/psf/Home/NotForTheCloud/hists.csv', 'w') as of:
    of.write(fmth.format('Level', *l))
    # print ('-'*10 + ' ') * 5
    for i in range(256):
        o = [h[j][i] for j in range(len(l))]
        of.write(fmtl.format(i, *o))

exit(0)

smallimages = sorted(smallimages, key=lambda si: (si.flen, si.image_num))
outimages = []
for i in range(0,len(smallimages),100):
    smi = smallimages[i]
    im = Image.open(makepath(smi.image_num))
    im = im.crop((500, 350, 600, 1100))
    smi.redhist = sum(im.histogram()[255:256])     # use red histogram as proxy for white, 1 whites pixel counts
    if smi.redhist < 100000:
        outimages.append(smi)
    # im.show()

smallimages = sorted(outimages, key=lambda si: (si.redhist, si.flen, si.image_num))

with open('/tmp/hists.txt', 'w') as of:
    for i in range(len(outimages)):
        smi = outimages[i]
        of.write('sum: {:10,}; length: {:8,}; image: {:0>6}\n'.format(smi.redhist, smi.flen, smi.image_num))
