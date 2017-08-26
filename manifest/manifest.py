#!/usr/bin/python

"""Create a list of all files sorted by file name within 
   the directory specified on the command line.
   Include columns for file size and modification time.  
   Output is to stdout.
"""

# known bugs
# ----------
# If the output is redirected to the input directory, the manifest file itself
# appears in the manifest directory, but the length is probably wrong.
#

import os
import sys
from stat import *
import datetime

file_paths = []


def walktree(top, callback, toptop):
    """Recursively descend the directory tree rooted at top,
       calling the callback function for each regular file.
       The param toptop is the original top of the hierarchy
       preserved through descending calls."""

    for f in os.listdir(top):
        pathname = os.path.join(top, f)
        mode = os.stat(pathname).st_mode
        if S_ISDIR(mode):
            walktree(pathname, callback, toptop)  # It's a directory, recurse into it
        elif S_ISREG(mode):
            callback(pathname, toptop)  # It's a file, call the callback function
        else:
            sys.stderr.write('Skipping file of unknown type: %s\n' % pathname)


def visitfile(f, toptop):
    file_paths.append(f[len(toptop)+1:]) # path relative to toptop


def make_manifest(start):
    walktree(start, visitfile, start)
    file_paths.sort()
    for f in file_paths:
        s = os.stat(start + os.sep + f)
        timestamp = datetime.datetime.fromtimestamp(s.st_mtime)
        print('{:>10}\t{}\t{}'.format(s.st_size, timestamp, f))


if __name__ == '__main__':
    make_manifest(sys.argv[1])
