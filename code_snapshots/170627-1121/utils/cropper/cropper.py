'''Crop the files pointed to by image_glob to 8-1/2x11. Used to correct setup 
   error when scanning.

   Currently sends the cropped files and their immediate superior directories 
   to out_path
'''

from PIL import Image
import glob
import os

image_glob = '/home/tevs/2017wes/unproc/*/*.jpg'
out_dir = '/home/tevs/cropout'


def make_dirs(p):
    """Create any needed directories in the target."""
    path, file = os.path.split(p)
    if os.path.exists(path): return
    os.makedirs(path)
    return


for imgpath in glob.glob(image_glob):
    img = Image.open(imgpath)
    img2 = img.crop((0, 0, int(300*8.5), int(300*11)))
    splitpath = imgpath.split(os.path.sep)
    outpath = os.path.join(out_dir, splitpath[-2], splitpath[-1])
    make_dirs(outpath)
    img2.save(outpath)
    print outpath
