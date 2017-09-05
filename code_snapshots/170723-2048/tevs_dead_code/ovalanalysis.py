"""
The ovals from CHAM2FEB are in 108x72 crops.  
Each oval is centered horizontally.  
Most, but not all, are centered vertically.  
The printed oval is 72 pixels wide by 30 pixels tall,
or 1/4" x 1/10".

We will take three vertical one pixel wide strips at 54 and 54+/-20,
and three horizontal vertical strips at 36 and 36 +/- 8.

For each strip, we will record the first encountered pixel 
with average intensity below a dark threshold (192), scanning forwards
and backwards.  We will then record the average and minimum intensities
of those pixels between the first and last, and the number of transitions
from light to dark once the initial dark pixel has been encountered.
As a convenience, we will also record spans (last - first + 1).

Light to dark transitions will be those in which, following a value above
208, the value drops to 184 or below on any color channel.

Where the center span is not long enough to indicate a centered oval,
the results will not be included in the main analysis.  Means will be
multiplied by 10 and rounded to integers.

We will also track the ballot number, the oval's filename, and a serial number
for each oval. This will give us 6x((3x3)+4) + 3 (129) fields

db.schema:
create table feb_ovals (
oval_id integer,
ballot_id integer,
filename varchar,
v34_start smallint,
v34_end smallint,
v34_span smallint,
v34_tcount smallint,
v34_red_min smallint,
v34_red_max smallint,
v34_red_mean smallint,
v34_green_min smallint,
v34_green_max smallint,
v34_green_mean smallint,
v34_blue_min smallint,
v34_blue_max smallint,
v34_blue_mean smallint,

v54_start smallint,
v54_end smallint,
v54_span smallint,
v54_tcount smallint,
v54_red_min smallint,
v54_red_max smallint,
v54_red_mean smallint,
v54_green_min smallint,
v54_green_max smallint,
v54_green_mean smallint,
v54_blue_min smallint,
v54_blue_max smallint,
v54_blue_mean smallint,

v74_start smallint,
v74_end smallint,
v74_span smallint,
v74_tcount smallint,
v74_red_min smallint,
v74_red_max smallint,
v74_red_mean smallint,
v74_green_min smallint,
v74_green_max smallint,
v74_green_mean smallint,
v74_blue_min smallint,
v74_blue_max smallint,
v74_blue_mean smallint,

h28_start smallint,
h28_end smallint,
h28_span smallint,
h28_tcount smallint,
h28_red_min smallint,
h28_red_max smallint,
h28_red_mean smallint,
h28_green_min smallint,
h28_green_max smallint,
h28_green_mean smallint,
h28_blue_min smallint,
h28_blue_max smallint,
h28_blue_mean smallint,

h36_start smallint,
h36_end smallint,
h36_span smallint,
h36_tcount smallint,
h36_red_min smallint,
h36_red_max smallint,
h36_red_mean smallint,
h36_green_min smallint,
h36_green_max smallint,
h36_green_mean smallint,
h36_blue_min smallint,
h36_blue_max smallint,
h36_blue_mean smallint,

h44_start smallint,
h44_end smallint,
h44_span smallint,
h44_tcount smallint,
h44_red_min smallint,
h44_red_max smallint,
h44_red_mean smallint,
h44_green_min smallint,
h44_green_max smallint,
h44_green_mean smallint,
h44_blue_min smallint,
h44_blue_max smallint,
h44_blue_mean smallint
);

"""
import Image, ImageStat
import os
import pdb
import sys

def stats_from_data(data,reverse_data):
    """ return stats from data"""
    start = -1
    end = -1
    for num, pix in enumerate(data):
        if (pix[0]+pix[1]+pix[2]) < (192*3):
            start = num
            break
    for num, pix in enumerate(reverse_data):
        if (pix[0]+pix[1]+pix[2]) < (192*3):
            end = len(reverse_data) - (num + 1)
            break
    totalr, totalg, totalb = 0,0,0
    minr, ming, minb = 255,255,255
    maxr, maxg, maxb = 0,0,0
    count = 0
    dark = True
    tcount = 0
    if start == -1 or end == -1 or start==(end-1):
        return (start,end,(end-start)+1, 0,0,0, 0,0,0, 0,0,0, 0)
    for pix in data[start:end+1]:
        totalr += pix[0]
        totalg += pix[1]
        totalb += pix[2]
        if pix[0]<minr: minr=pix[0]
        if pix[1]<ming: ming=pix[1]
        if pix[2]<minb: minb=pix[2]
        if pix[0]>maxr: maxr=pix[0]
        if pix[1]>maxg: maxg=pix[1]
        if pix[2]>maxb: maxb=pix[2]
#Light to dark transitions will be those in which, following a value above
#208, the value drops to 184 or below on any color channel.
        if (pix[0]+pix[1]+pix[2])<=(184*3) and not dark:
            dark = True
            tcount += 1
        elif (pix[0]+pix[1]+pix[2])>(208*3) and dark:
            dark = False
        count += 1
    meanr = int(round(float(totalr*10)/count))
    meang = int(round(float(totalg*10)/count))
    meanb = int(round(float(totalb*10)/count))
    return (start, end, (end-start)+1, 
            tcount, 
            minr,maxr,meanr, 
            ming,maxg,meang, 
            minb,maxb,meanb)

if __name__ == "__main__":
    which_subdir = int(sys.argv[1])
    m_id = 1
    #rootdir = "/media/CHAMPAIGN2/CHAM2FEB/results/"
    #rootdir = "/media/CHAMPAIGN2/results/"
    rootdir = "/media/CHAMPAIGN/results/"
    outfilename = rootdir+"ovalanalysis%d.csv" % (which_subdir,)
    outfile = open(outfilename,"w")
    dirlist = os.listdir("%s%03d" % (rootdir,which_subdir))
    #filename = get_next_file()
    filecount = 0
    for filename in dirlist:
        if not filename.endswith(".jpg"):
            continue
        fullname = "%s%03d/%s" % (rootdir,which_subdir,filename)
        try:
            im = Image.open(fullname)
        except Exception as e:
            print e
            continue
        filecount += 1
        if (filecount%1000)==0: print filecount, "processed"
        outfields = [filename,m_id]
        for x in (34,54,74):
            outfields.append("[v%d]" % (x,))
            croplist = ((x,0,x+1,im.size[1]))
            crop = im.crop(croplist)
            data = list(crop.getdata())
            reverse_data = list(crop.getdata())
            reverse_data.reverse()
            outfields.extend(stats_from_data(data,reverse_data))
        for y in (28,36,44):
            outfields.append("[h%d]" % (y,))
            croplist = ((0,y,im.size[0],y+1))
            crop = im.crop(croplist)
            data = list(crop.getdata())
            reverse_data = list(crop.getdata())
            reverse_data.reverse()
            outfields.extend(stats_from_data(data,reverse_data))
        outfile.write(str(outfields))
        outfile.write("\n")
    outfile.close()
