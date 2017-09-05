import glob
import sys
import os



if __name__ == "__main__":
    print sys.argv
    path = sys.argv[1]
    pathlist = glob.iglob(path)
    index = 0
    for p in pathlist:
        print p
        os.symlink(p,"/tmp/%d.jpg" % (index,))
        index = index + 1
