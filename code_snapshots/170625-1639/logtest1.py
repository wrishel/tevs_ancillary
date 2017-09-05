import logging
import logtest2

if __name__=='__main__':
    logging.basicConfig(filename='test.log',
                        format = '%(asctime)s %(levelname)s %(module)s %(message)s',
                        level=logging.DEBUG)
    logging.info("Starting")
    logtest2.testlog("Hello")
    logging.info("Done")
