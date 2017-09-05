"""
BallotRegions.py (change to BallotLandmarks.py)
 part of TEVS
 defines classes representing Point and four points

While two landmarks, or a landmark and a rotation are sufficient
for an affine transformation, additional landmarks will often 
prove useful.  We will use four at minimum, allowing us to see
if a ballot has rotated during the scan.  Where ballot types
allow for many additional landmarks, these may usefully be
stored in a subclass of Landmarks, and the ballot style may
provide a replacement to the standard transformation routine. 

"""


class Point(object):
    """A 2D point."""
    def __init__(self,x,y):
        self.x = x
        self.y = y

    def __repr__(self):
        return "(%s,%s)" % (self.x,self.y)

class Landmarks(object):
    """Four landmark points, often the four corners of a printed rectangle."""
    def __init__(self,ulc,urc,lrc,llc,extensions=None):
        self.ulc, self.urc, self.lrc, self.llc = ulc, urc, lrc, llc 
        self.extensions = extensions
    def __repr__(self):
        return "Landmarks ulc=%(ulc)s urc=%(urc)s lrc=%(lrc)s llc=%(llc)s\n extensions=%(extensions)s" % (self.__dict__)

if __name__ == "__main__":
    p1 = Point(1,2)
    p2 = Point(11,22)
    p3 = Point(111,222)
    p4 = Point(1111,2222)
    print p1,p2,p3,p4
    landmarks = Landmarks(p1,p2,p3,p4)
    print landmarks
