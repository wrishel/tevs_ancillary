from PIL import Image
from PIL import ImageChops
import glob
import os

image_glob = '/home/tevs/2017wes/unproc/*/*.jpg'
out_dir = '/home/tevs/pillfout'

im1 = Image.open('/home/tevs/2017wes/unproc/000/000000.jpg')
im2 = Image.open('/home/tevs/2017wes/unproc/000/000002.jpg')
im1 = im1.convert('1')
im2 = im2.convert('1')
print(im1.mode, im2.mode)
im3 = ImageChops.logical_and(im1, ImageChops.invert(im2))
im3.show()
exit(0)
def make_dirs(p):
    """Create any needed directories in the target."""
    path, file = os.path.split(p)
    if os.path.exists(path): return
    os.makedirs(path)
    return

def XORCompare(im1, im2, mode="pct", alpha=.01):
    if im1.size == im2.size and im1.mode == im2.mode:
        XORCount = []
        randPix = im1.getpixel((0,0))
        for channel in range(len(randPix)):
            XORCount += [0.0]
        width = im1.size[0]
        height = im1.size[1]
        imXOR = ImageXOR(im1, im2)
        maxSum = 0.0
        for i in range(width):
            for j in range(height):
                pixel = imXOR.getpixel((i,j))
                for channel in range(len(pixel)):
                    XORCount[channel] += pixel[channel]
                maxSum += 255
        if mode == "pct":
            ret = ()
            for channel in range(len(randPix)):
                ret += (XORCount[channel]/maxSum,)
            return ret
        for channel in range(len(randPix)):
            if XORCount[channel] > alpha*maxSum:
                return False
        return True
    return False



for imgpath in glob.glob(image_glob):
    img = Image.open(imgpath)
    splitpath = imgpath.split(os.path.sep)

    outpath = os.path.join(out_dir, splitpath[-1])
    make_dirs(outpath)
    img2.save(outpath)
    print outpath
