import sys
import re
import os
'''Accept a set of file paths from the file in fn. Remap each file path to the current image location and
   issue a unix command line open command for each image. Append an input line that is intended to be
   the HART precinct ID for the image. Write the original image path and the HART precinct ID to the 
   output file x.csv.
'''
extr = re.compile('(\d\d\d)\_(\d+)')

fn = "/Users/Wes/Dropbox/Programming/ElectionTransparency/helper/imagepaths.txt"
lc = 0

with open('x.csv','a') as of:
	with open(fn) as f:
		lines = f.readlines()
		for line in lines:
			lc += 1
			sline = line.strip()
			if len(sline) > 1 and sline[0] != '#' :
				result = extr.search(sline)
				cmd = 'open "/Volumes/Seagate Backup Plus Drive/november  2016/' + result.group(1) + '/' + result.group(2) + '.jpg"'
				if os.system(cmd) != 0:
					s = '???'
					print "skipping {0}".format(sline)
				else:
					s = raw_input('({0}) precinct ID? '.format(str(lc)))
					if s == '' : s = lasts
					lasts = s
				outl = '"{0}",\'{1}'.format(sline, s.upper())
				print outl
				of.write(outl+"\n")
				of.flush()


