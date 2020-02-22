import re
import sqlite3
import time

ONE_GB = 2**30
ONE_MB = 2**20
ONE_KB = 2**10


r = re.compile(r'^!(?P<bot>[a-z0-9-]+?) (?P<book>.+)\s(::INFO::|-+)\s+(?P<size>[0-9.]+\s*[BKMG]+)\s*$', re.I)
# tags_re = re.compile(r'[\[\(](?P<tag>.*?)[\]\)]')

def lines_to_dicts(lines):
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
    
        books.append((bot, book, size))
    return books
    
def insert_books(books):
    db = sqlite3.connect('books.db')
    c = db.cursor()
    entries = []
    c.executemany('INSERT OR IGNORE INTO books(bot, book, size) values (?,?,?)', books)
    db.commit()
    db.close()
