import sys
import re
import os
import os.path

fn = "/Users/Wes/Dropbox/Programming/ElectionTransparency/allfilenames.txt"
lc = 0

with open('checkmissingfiles.csv','w') as of:
	with open(fn) as f:
		lines = f.readlines()
		for line in lines:
			lc += 1
			sline = line.strip()
			if len(sline) > 1 and sline[0] != '#' :
				(path, time) = sline.split("\t")
				if not os.path.isfile(path):
					of.write(path+","+time+"\n") 
					print(sline)
