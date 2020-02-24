import logging
import sys

FORMAT = '%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s'
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format=FORMAT)
