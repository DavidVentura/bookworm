import re
import sqlite3
import time
import logging

from threading import Lock
from bookworm import db
ONE_GB = 2**30
ONE_MB = 2**20
ONE_KB = 2**10

db_lock = Lock()

log = logging.getLogger(__name__)
r = re.compile(r'^!(?P<bot>[a-z0-9-]+?) (?P<book>.+)\s(::INFO::|-+)\s+(?P<size>[0-9.]+\s*[BKMG]+)\s*$', re.I)
# tags_re = re.compile(r'[\[\(](?P<tag>.*?)[\]\)]')

def _lines_to_dicts(lines):
    books = []

    for line in lines:
        line = line.strip()
        match = r.match(line)
        if match is None:
            continue
        bot = match.group('bot').strip()
        book = match.group('book').strip()
        size = match.group('size').strip().lower()

        if 'gb' in size:
            size = int(float(size.replace('gb', '')) * ONE_GB)
        elif 'mb' in size:
            size = int(float(size.replace('mb', '')) * ONE_MB)
        elif 'kb' in size:
            size = int(float(size.replace('kb', '')) * ONE_KB)
        elif 'b' in size:
            size = int(float(size.replace('b', '')))

        b = book.lower()
        valid = 'pdf' not in b and 'html' not in b and 'txt' not in b
        books.append((bot, book, size, valid))
    return books

def parse_and_insert_lines(lines):
    books = _lines_to_dicts(lines)
    log.info('Acquiring DB lock..')
    with db_lock:
        log.info('Got DB lock!')
        insert_books(books)
    log.info('Released DB lock..')
    return len(books)

def count_books_without_tokens(c):
    rows = c.execute('''
    SELECT count(1) FROM books
    LEFT JOIN tokens on tokens.pkey = books.id
    WHERE tokens.pkey IS NULL
    AND books.valid
    ''')
    count = rows[0][0]
    log.info('There are %s books without tokens', count)
    return count

def insert_books(books):
    _db = db.get_db()
    c = _db.cursor()
    entries = []
    log.info('About to insert %s books', len(books))
    c.executemany('INSERT OR IGNORE INTO books(bot, book, size, valid) values (?,?,?,?)', books)
    log.info('Finished inserting books, will now update FTS tokens table')
    while count_books_without_tokens(c) > 0:
        c.execute('''
        INSERT INTO tokens(book, pkey)
        SELECT books.book, books.id FROM books
        LEFT JOIN tokens on tokens.pkey = books.id
        WHERE tokens.pkey IS NULL
        AND books.valid
        LIMIT 10000
        ''')

    log.info('Finished updating FTS, committing')
    _db.commit()
    log.info('DONE')
    _db.close()
