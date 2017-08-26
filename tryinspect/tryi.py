import inspect
import os.path
import sys

def f():
    stack = inspect.stack()
    if "self" in stack[1][0].f_locals:
        the_class = stack[1][0].f_locals["self"].__class__
    else:
        the_class = '<NO CLASS>'
    the_method = '{}()'.format(stack[1][0].f_code.co_name)
    if the_method == '<module>()': the_method = '<NO METHOD>'

    (frame, filename, line_number, function_name, lines, index) = \
        inspect.getouterframes(inspect.currentframe())[1]
    sourcename = os.path.split(filename)[-1]
    print("  I was called by {}({}):{}.{}".format(
        sourcename, line_number, (the_class), the_method))






