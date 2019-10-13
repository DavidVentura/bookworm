from datetime import timedelta
from enum import Enum

UNPACKABLE_EXTENSIONS = ['epub', 'mobi', 'azw3']
JOB_KEY_PREFIX = 'job_'
JOB_TTL_REDIS = timedelta(days=5)

class REDIS():
    KEY_NAME = 'KEY'
    BOOK_KEY = 'BOOK'
    BOT_KEY = 'BOT'
    Q_BOOK_COMMANDS = 'BOOK_COMMANDS'
    Q_FETCH_FILE = 'FETCH_FILE'
    Q_UNPACK_FILE = 'UNPACK_FILE'
    Q_PROCESS_BATCH_FILE = 'PROCESS_BATCH_FILE'
    STEP_KEY = 'STEP'
    STATE_KEY = 'STATE'

class IRC():
    TIME_TO_FIRST_COMMAND = 32
    CHANNEL = "#ebooks"

class BUCKET():
    RAW_FILE = 'rawfiles'
    PROCESSED_FILE = 'files'
