import config
import const
import getopt
import sys
import os
import os.path

def get_args():
    """Get command line arguments"""
    try:
        opts, args = getopt.getopt(sys.argv[1:],
                                    "tdc:",
                                    ["templates",
                                     "debug",
                                     "config="
                                    ]
                                   ) 
    except getopt.GetoptError:
        sys.stderr.write(
            "usage: %s -tdc --templates --debug --config=file" % sys.argv[0]
        )
        sys.exit(2)
    templates_only = False
    debug = False
    config = "tevs.cfg"
    for opt, arg in opts:
        if opt in ("-t", "--templates"):
            templates_only = True
        if opt in ("-d", "--debug"):
            debug = True
        if opt in ("-c", "--config"):
            config = arg

    if not os.path.isabs(config):
        config = os.path.join(os.path.expanduser("~"),config)
    const.templates_only = templates_only
    const.debug = debug
    return config

if __name__ == '__main__':
    config = get_args()
    print "Config",config
    print "Templates only",const.templates_only    
    print "Debug",const.debug
