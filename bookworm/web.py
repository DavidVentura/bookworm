from flask import Flask, render_template, make_response, request, g
from bookworm import s3, constants
import sqlite3
import json
import redis
import os
import re

s3client = s3.client()
app = Flask(__name__)
r = redis.StrictRedis(host='localhost', port=6379, decode_responses=True)

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = sqlite3.connect('books.db')
        db.row_factory = dict_factory
        g._database = db
    return db

@app.route('/books/status', methods=['GET'])
def status_books():
    keys = r.keys(f'{constants.JOB_KEY_PREFIX}*')
    ret = {}
    for key in keys:
        val = r.hgetall(key)
        ret[key] = val
    return json.dumps(ret)

def clean_book_name(book):
    cbr = re.compile(r'epub|azw3|mobi|retail|\(v[0-9.]+\)', re.I)
    return cbr.sub('', book).rstrip('() .-')

@app.route('/')
def index():
    objects = s3client.list_objects_v2(Bucket=constants.BUCKET.PROCESSED_FILE)['Contents']
    objects = sorted(objects, key=lambda x: x['LastModified'], reverse=True)
    books = [(obj['Key'], clean_book_name(obj['Key'])) for obj in objects]
    return render_template('kindle-index.j2', books=books)

@app.route('/book/<path:book>')
def serve_books(book):
    obj = s3client.get_object(Bucket=constants.BUCKET.PROCESSED_FILE, Key=book)
    data = obj['Body'].read()
    response = make_response(data)
    response.headers.set('Content-Disposition', f'attachment; filename="{book}"')
    response.headers.set('Content-Length', len(data))

    _, ext = os.path.splitext(book)
    if ext == '.mobi':
        content_type = 'application/x-mobipocket-ebook'
    elif ext == '.azw3':
        content_type = 'application/x-mobi8-ebook'
    else:
        content_type = 'text/plain'

    response.headers.set('Content-Type', content_type)
    return response

@app.route('/book/search', methods=['GET'])
def search_books():
    terms = request.args.get('terms').split()
    cur = get_db().cursor()
    conditions = []
    for term in terms:
        condition = f"lower(book) like '%{term}%'"
        conditions.append(condition)

    all_conditions = ' AND '.join(conditions)

    rows = cur.execute('SELECT bot, book FROM books where %s LIMIT 100' % all_conditions)
    return json.dumps(list(rows))

@app.route('/book/fetch', methods=['POST'])
def fetch_books():
    fetch = request.json
    job_key = constants.JOB_KEY_PREFIX + fetch['book']
    job_key = job_key.strip()
    data = {'command': f'!{fetch["bot"]} {fetch["book"]}',
            'job_key': job_key,
            'meta': {
                'unpack_file_queue': constants.REDIS.Q_UNPACK_FILE,
                'fetch_file_queue': constants.REDIS.Q_FETCH_FILE,
                'raw_file_bucket': constants.BUCKET.RAW_FILE,
                'processed_file_bucket': constants.BUCKET.PROCESSED_FILE,
            }
           }
    r.rpush(constants.REDIS.Q_BOOK_COMMANDS, json.dumps(data))
    return job_key

@app.route('/books/batch_update', methods=['POST'])
def batch_update():
    fetch = request.json
    if fetch['secret_key'] != 'super_secret':
        return '401'

    batch_update_commands = ['@pondering42', '@dv8', '@shytot', '@dragnbreaker', '@Xon-new']
    for command in batch_update_commands:
        job_key = constants.JOB_KEY_PREFIX + command.replace('@', 'batch_')
        data = {'command': command,
                'job_key': job_key,
                'meta': {
                    'unpack_file_queue': constants.REDIS.Q_PROCESS_BATCH_FILE,
                    'fetch_file_queue': constants.REDIS.Q_FETCH_FILE,
                    'raw_file_bucket': constants.BUCKET.RAW_FILE,
                    'processed_file_bucket': constants.BUCKET.PROCESSED_FILE,
                }
               }
        r.rpush(constants.REDIS.Q_BOOK_COMMANDS, json.dumps(data))
    return ''

def main():
    db = sqlite3.connect('books.db')
    c = db.cursor()
    sql = 'CREATE TABLE IF NOT EXISTS books (bot TEXT(40), book TEXT(200), size INT)'
    c.execute(sql)
    sql = 'CREATE UNIQUE INDEX IF NOT EXISTS books_unique ON books(bot, book)'
    c.execute(sql)
    db.commit()
    db.close()

    app.run(host='0.0.0.0', debug=True)

if __name__ == '__main__':
    main()
