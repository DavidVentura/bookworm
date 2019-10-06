import sys
import logging

FORMAT = '%(asctime)s - %(threadName)s - %(levelname)s - %(message)s'

log = logging.getLogger(__name__)
def setup_logger():
    global log
    formatter = logging.Formatter(FORMAT)
    handler = logging.StreamHandler(sys.stdout)
    
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    log.setLevel(logging.INFO)
    log.addHandler(handler)
    
