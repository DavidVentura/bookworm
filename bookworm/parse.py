import time
import re
from collections import namedtuple
import pg_simple

ONE_GB = 2**30
ONE_MB = 2**20
ONE_KB = 2**10

connection_pool = pg_simple.config_pool(dsn='dbname=david user=david')

r = re.compile(r'^!(?P<bot>[a-z0-9-]+?) (?P<book>.+)\s(::INFO::|-+)\s+(?P<size>[0-9.]+\s*[BKMG]+)\s*$', re.I)
tags_re = re.compile(r'[\[\(](?P<tag>.*?)[\]\)]')
books = []
Book = namedtuple('Book', 'raw bot book size')

for line in open('all_books_2.txt', 'r'):
    line = line.strip()
    match = r.match(line)
    bot = match.group('bot').strip()
    book = match.group('book').strip()
    size = match.group('size').strip().lower()

    if 'gb' in size:
        size = float(size.replace('gb', '')) * ONE_GB
    elif 'mb' in size:
        size = float(size.replace('mb', '')) * ONE_MB
    elif 'kb' in size:
        size = float(size.replace('kb', '')) * ONE_KB
    elif 'b' in size:
        size = float(size.replace('b', ''))

    books.append(Book(line, bot, book, size)._asdict())

print('db..')
with pg_simple.PgSimple(connection_pool) as db:
    t = time.time()
    vals = [tuple(book.values()) for book in books]
    print('making tuples', time.time() - t)

    db.insert_many('books', keys=books[0].keys(), values=vals, page_size=1000)
    print('commiting..')
    db.commit()
    print('done..')
