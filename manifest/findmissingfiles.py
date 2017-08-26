import os
infilename = '/Users/Wes/NotForTheCloud/Ballots.file1.201611.tsv'
numlist = [os.path.split(record.strip())[-1][:-4] for record in open(infilename, 'r')]



max = int(numlist[-1])+1  # file names start with 000000
count = len(numlist)
print '''Ballot records compared to maximum file name
max: {:,}; count: {:,}; difference: {:,}; {:5.2f}%'''\
       .format(max, count, max-count, 100*(1. - float(count)/max))

