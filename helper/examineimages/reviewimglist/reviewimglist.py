import sys the path from the input in the first c
import re
import os
 

'''Accept a CSV file named in open statement below which contains a list
   of paths to images. Compute the actual path to the file using imagebase.

   For each such file attempt to open it with Ubuntu's EOG.

   After displaying file accept a line of raw input and create a row
   in the output csv that concists ofolumn
   and the raw input converted to upper.
'''

progbase = os.path.dirname(os.path.abspath(__file__))

extr = re.compile('(\d\d\d)\_(\d+)')

lc = 0
imagebase=os.path.join('~', '2017wes', 'proc' ) + os.path.sep
lasts = ''

def pathmaker(fname):
	return os.path.join(imagebase, fname[0:3], fname)

s = os.path.join(progbase, 'zero_vote_ballots.csv')
with open(s, 'r') as inf:
	with open(os.path.join(progbase, 'xmissing.csv'),'w') as of:
		for il in inf:
			print il.strip().split(',')
			(imagepath, therest) = il.strip().split(',')
			imagename = os.path.split(imagepath)[-1]
			lc += 1
			cmd = 'eog {0}'.format(pathmaker(imagename))
			print cmd
			if os.system(cmd) != 0:
				s = '???'
				print "skipping {0}".format(imagename)
			else:
				s = raw_input('({0}) input? '.format(str(lc)))
				if s == '' : s = lasts
				lasts = s
			outl = '"{0}",\'{1}'.format(il, s.upper())
			print outl
			of.write(outl+"\n")
			of.flush()


