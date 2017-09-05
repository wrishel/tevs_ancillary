class _bag(object):
    def __repr__(self):
        return repr(self.__dict__)

class IStats(object): 
    def __init__(self, stats):
       self.red, self.green, self.blue = _bag(), _bag(), _bag()
       self.adjusted = _bag()
       (self.red.intensity,
        self.red.darkest_fourth,
        self.red.second_fourth,
        self.red.third_fourth,
        self.red.lightest_fourth,

        self.green.intensity,
        self.green.darkest_fourth,
        self.green.second_fourth,
        self.green.third_fourth,
        self.green.lightest_fourth,

        self.blue.intensity,
        self.blue.darkest_fourth,
        self.blue.second_fourth,
        self.blue.third_fourth,
        self.blue.lightest_fourth,

        self.adjusted.x,
        self.adjusted.y,

        self.suspicious) = stats
       self._mean_intensity = None
       self._mean_darkness = None
       self._mean_lightness = None

    def mean_intensity(self):
        if self._mean_intensity is None:
            self._mean_intensity = int(round(
                (self.red.intensity +
                 self.green.intensity +
                 self.blue.intensity)/3.0
            ))
        return self._mean_intensity

    def mean_darkness(self): 
       """compute mean darkness over each channel using lowest
       three quartiles."""
       # Note: changed to include third fourth 
       # because very light pencil may not set pixels into lower half.
       # This will require adjustment to default values in config files
       # to account for typical load of third fourth pixels in unvoted targets.
       if self._mean_darkness is None:
           self._mean_darkness = int(round(
               (self.red.darkest_fourth   + self.red.second_fourth   +
                #self.red.third_fourth +
                self.blue.darkest_fourth  + self.blue.second_fourth  +
                #self.blue.third_fourth +
                self.green.darkest_fourth + self.green.second_fourth #+
                #self.green.third_fourth 
               )/3.0
           ))
       return self._mean_darkness

    def mean_lightness(self):
        """compute mean lightness over each channel using last
        two quartiles."""
        if self._mean_lightness is None:
            self._mean_lightness = int(round(
                (self.red.lightest_fourth   + self.red.third_fourth   +
                 self.blue.lightest_fourth  + self.blue.third_fourth  +
                 self.green.lightest_fourth + self.green.third_fourth
                )/3.0
            ))
        return self._mean_lightness

    def __iter__(self):
        return (x for x in (
            self.red.intensity,
            self.red.darkest_fourth,
            self.red.second_fourth,
            self.red.third_fourth,
            self.red.lightest_fourth,

            self.green.intensity,
            self.green.darkest_fourth,
            self.green.second_fourth,
            self.green.third_fourth,
            self.green.lightest_fourth,

            self.blue.intensity,
            self.blue.darkest_fourth,
            self.blue.second_fourth,
            self.blue.third_fourth,
            self.blue.lightest_fourth,

            self.adjusted.x,
            self.adjusted.y,

            self.suspicious,
       ))

    def CSV(self):
        return ",".join(str(x) for x in self)

    def __repr__(self):
        return str(self.__dict__)

def _stats_CSV_header_line():
    return (
        "red_intensity,red_darkest_fourth,red_second_fourth,red_third_fourth,red_lightest_fourth," +
        "green_intensity,green_darkest_fourth,green_second_fourth,green_third_fourth,green_lightest_fourth," +
        "blue_intensity,blue_darkest_fourth,blue_second_fourth,blue_third_fourth,blue_lightest_fourth," +
        "adjusted_x,adjusted_y,was_suspicious"
    )

_bad_stats = IStats([-1]*18)

