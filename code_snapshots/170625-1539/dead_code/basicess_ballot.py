# basicess_ballot.py
# Part of TEVS
# This file, with basic_ballot_side.py, demos the minimum functions 
# to implement a new vendor ballot style. 

import const
from BallotClass import Ballot
from basicess_ballot_side import BasicessBallotSide

class BasicessBallot(Ballot):
    """Class representing minimal vendor specific ballot.

    The file name basic_ballot.py and the class name BasicBallot
    correspond to the brand entry in tevs.cfg (basic.cfg), 
    the configuration file.
    """

    def __init__(self, image_filenames, extensions):
        super(BasicessBallot, self).__init__(image_filenames, extensions)
        def add_page(number, fname):
            nbs = BasicessBallotSide(
                ballot=self,
                dpi=const.dpi,
                image_filename=fname,
                number=number
            )
            self.side_list.append(nbs)
        if not isinstance(image_filenames, basestring):
            for i, fname in enumerate(image_filenames):
                add_page(i, fname)
        else: #just a filename
            add_page(0, image_filenames)



if __name__ == "__main__":
    print "Test by setting the configuration file to brand Basicess"
    print "and then running __main__ in BallotClass.py"
