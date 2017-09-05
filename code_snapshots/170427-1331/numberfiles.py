import os
n = 0
l = os.listdir(".")
l.sort()
for x in l:
    print "mv %s %06d.jpg" % (x,n)
    n = n+1
