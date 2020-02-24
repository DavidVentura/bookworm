import sqlite3

def init_db():
    create_statements = [
            '''CREATE TABLE IF NOT EXISTS books(id INTEGER PRIMARY KEY autoincrement,
                                                bot,
                                                book,
                                                size INT,
                                                inserted_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                                valid BOOLEAN)''',
            'CREATE UNIQUE INDEX IF NOT EXISTS books_unique ON books(bot, book)',
            'CREATE VIRTUAL TABLE IF NOT EXISTS tokens USING fts4(book, pkey INT)',
            ]
    db = sqlite3.connect('books.db')
    c = db.cursor()
    for stmt in create_statements:
        c.execute(stmt)
    db.commit()
    db.close()


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def get_db():
    db = sqlite3.connect('books.db')
    db.row_factory = dict_factory
    return db


def update_fts():
    db = get_db()
    cur = db.cursor()
    cur.execute('''
    INSERT INTO tokens(book, pkey)
    SELECT books.book, books.id FROM books
    LEFT JOIN tokens on tokens.pkey = books.id
    WHERE tokens.pkey = NULL
    ''')
