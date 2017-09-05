from inspect import currentframe


def source_line():
    return currentframe().f_back.f_lineno


def dumpdict(d):
    """Use dumpdict because __repr__ doesn't work for NamedNodeMap"""

    return ", ".join(["(%s: %s)" % (key, value) for key, value in d.items()])
