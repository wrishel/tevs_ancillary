import Image
import ImageChops
import ImageStat
import ImageMath

def bw(p,threshold=192):
    if p > threshold: return 255
    else: return 0


def crop_edges_get_sum(im,save_as,edge=25):
    c = im.crop((edge,edge,im.size[0]-edge,im.size[1]-edge))
    c.save(save_as)
    s = ImageStat.Stat(c)
    return int(s.sum[0]/1000.)

i1 = Image.open("/home/mitch/data/hart/unproc/000/000001.jpg")
marked = Image.open("/home/mitch/data/hart/unproc/000/000001m.jpg")

# shrink as much as possible, but make sure lines still register as pixels
scaling_factor = 2
small = i1.resize((i1.size[0]/scaling_factor,i1.size[1]/scaling_factor))
marked = marked.resize(
    (marked.size[0]/scaling_factor,
     marked.size[1]/scaling_factor)
    )
i1 = Image.eval(small,bw)
i1.save("/tmp/i1.jpg")
print "I1, orig, saved."
i2 = ImageChops.duplicate(i1)
marked = Image.eval(marked,bw)

merge = i2

# calculate spread that works well with your scaling factor
spread = int(round(i1.size[0]/(scaling_factor*75.)))

# wherever there's a dark pixel, darken all pixels within spread pixels
for x in range(-spread,spread,1):
    for y in range(-spread,spread,1):
        print spread, x,y
        newi = ImageChops.offset(i2,x,y)
        merge = ImageChops.darker(merge, newi)
i2=merge
i2.save("/tmp/i2.jpg")
print "I2, mask, saved"
i3 = i2.resize((i1.size[0],i1.size[1]))
i3.save("/tmp/i3.jpg")
print "I3 saved"

i4 = Image.eval(i3,bw)

rot = i1.rotate(.5)
i5 = ImageChops.darker(rot, i4)

rot = i1.rotate(1.)
i6 = ImageChops.darker(rot, i4)


i7 = ImageChops.darker(marked,i2)
print i2.size
print i7.size
# Hard to believe this is the correct approach, 
# but we look for white a and black b,
# meaning areas marked on b but not marked on a.  
# These give us 1s as opposed to 0s.
# We then convert image result from "I" 32 bit signed integer pixels 
# to "L"uminance 8 bit signed pixels, and invert the result.
# (Alternatively, we could paint the result onto the original image
# with only one color channel operating.)
i8 = ImageMath.eval("convert((a & ~b),'RGB')",a=i2,b=i7)
i8.save("/tmp/i8.jpg")
i8r,i8g,i8b = i8.split()

i8r = i2
i8b = i2
i8g = ImageChops.darker(i7,i2)
i9 = Image.merge('RGB',(i8r,i8g,i8b))
i9.save("/tmp/i9.jpg")

i8s = ImageStat.Stat(i8)
print "i8s.sum",i8s.sum

print "mask",crop_edges_get_sum(i4,"/tmp/i4.jpg")
print "half degree", crop_edges_get_sum(i5,"/tmp/i5.jpg")
print "full degree", crop_edges_get_sum(i6,"/tmp/i6.jpg")
print "marker",crop_edges_get_sum(i7,"/tmp/i7.jpg")
print "Done"
