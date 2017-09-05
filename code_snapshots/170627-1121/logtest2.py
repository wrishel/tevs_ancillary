import logging

def testlog(msg):
    logger = logging.getLogger(__name__)
    logger.info(msg)

if __name__ == "__main__":
    testlog("From main")
