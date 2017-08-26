from PIL import Image
import glob
import os

def make_dirs(p):
    """Create any needed directories in the target."""
    path, file = os.path.split(p)
    if os.path.exists(path): return
    os.makedirs(path)
    return


for imgpath in glob.glob('/Volumes/Seagate Backup Plus Drive/2017-05/*/*.jpg'):
    img = Image.open(imgpath)
    img2 = img.crop((0, 0, int(300*8.5), int(300*11)))
    splitpath = imgpath.split(os.path.sep)
    outpath = os.path.join('.', splitpath[-2], splitpath[-1])
    make_dirs(outpath)
    img2.save(outpath)
    print outpath
