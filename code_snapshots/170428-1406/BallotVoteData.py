class VoteData(object):
    """All of the data associated with a single vote.

    The below information is relative to the Page this VOP came from.
       * self.filename - the filename of the ballot image
       * self.barcode - the layout code of the ballot
       * self.jurisdiction - the text of the jurisdiction header of this VOP
       * self.contest - the text of the contest header of this VOP
       * self.choice - the text of this VOP
       * self.coords - the pair of (x, y) coordinates of the upperleft corner
          of the VOP
       * self.maxv - the max votes allowed in the contest of this VOP
       * self.stats - an IStats object for self.image
       * self.image - a crop from the image in self.filename containig the VOP
          (including write in if applicable)
       * self.is_writein - Boolean 
       * self.was_voted - Boolean
       * self.ambiguous - True if we're not 100% sure a VOP was indeed voted.
       * self.number - the page number this VOP came from

    Called with no keyword arguments it creates the special VoteData object
    represinting an improperly processed vote.
    """
    def __init__(self,
                 filename=None,
                 barcode=None,
                 jurisdiction=None, 
                 contest=None, 
                 choice=None,
                 coords=(-1, -1), #XXX just save bbox?
                 maxv=1,
                 stats=_bad_stats,
                 image=None,
                 is_writein=None,
                 was_voted=None,
                 ambiguous=None,
                 number=-1):
        self.filename = filename
        self.barcode = barcode
        self.contest = contest
        self.jurisdiction = jurisdiction
        if contest is not None:
            self.contest = contest.description
        self.choice = None
        if choice is not None:
            self.choice = choice.description
        self.coords = coords
        self.maxv = maxv
        self.image = image
        self.was_voted = was_voted
        self.is_writein = is_writein
        self.ambiguous = ambiguous
        self.stats = stats
        self.number = number

    def __repr__(self):
        return str(self.__dict__)

    def CSV(self):
        "return this vote as a line in CSV format"
        return ",".join(str(s) for s in (
            self.filename,
            self.barcode,
            self.jurisdiction,
            self.contest,
            self.choice,
            self.coords[0], self.coords[1],
            self.stats.CSV(),
            self.maxv,
            self.was_voted,
            self.ambiguous,
            self.is_writein,
        ))

def results_to_CSV(results, heading=False): #TODO need a results_from_CSV
    """Take a list of VoteData and return a generator of CSV 
    encoded information. If heading, insert a descriptive
    header line."""
    if heading:
        yield ( #note that this MUST be kept in sync with the CSV method on VoteData
            "filename,barcode,jurisdiction,contest,choice,x,y," +
            _stats_CSV_header_line() + "," +
            "max_votes,was_voted,is_ambiguous,is_writein\n")
    for out in results:
        yield out.CSV() + "\n"

