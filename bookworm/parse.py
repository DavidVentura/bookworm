import re
import sqlite3
import time

from bookworm import db
ONE_GB = 2**30
ONE_MB = 2**20
ONE_KB = 2**10


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
    insert_books(books)
    return len(books)
    

def insert_books(books):
    _db = db.get_db()
    c = _db.cursor()
    entries = []
    c.executemany('INSERT OR IGNORE INTO books(bot, book, size, valid) values (?,?,?,?)', books)
    c.execute('''
    INSERT INTO tokens(book, pkey)
    SELECT books.book, books.id FROM books
    LEFT JOIN tokens on tokens.pkey = books.id
    WHERE tokens.pkey IS NULL
    AND books.valid
    ''')
    _db.commit()
    _db.close()
