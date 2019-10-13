import html
import json
import os
import re
import redis
import sqlite3
from flask import Flask, render_template, make_response, request, g, send_from_directory, redirect, url_for
from bookworm import s3, constants

s3client = s3.client()
app = Flask(__name__, static_url_path='')
r = redis.StrictRedis(host='localhost', port=6379, decode_responses=True)

def get_db():
    def dict_factory(cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d
    db = getattr(g, '_database', None)
    if db is None:
        db = sqlite3.connect('books.db')
        db.row_factory = dict_factory
        g._database = db
    return db

def book_search(terms):
    conditions = []
    for term in terms:
        condition = f"lower(book) like ?"
        conditions.append(condition)

    all_conditions = ' AND '.join(conditions)

    wildcard_terms = [f'%{term}%' for term in terms]
    cur = get_db().cursor()
    rows = cur.execute('SELECT bot, book FROM books where %s LIMIT 30' % all_conditions, wildcard_terms)
    return list(rows)

def current_status():
    keys = r.keys(f'{constants.JOB_KEY_PREFIX}*')
    ret = []
    for key in keys:
        val = r.hgetall(key)
        entry = {'name': key.replace(constants.JOB_KEY_PREFIX, '')}
        entry.update(val)
        ret.append(entry)
    return ret

def clean_book_name(book):
    cbr = re.compile(r'epub|azw3|mobi|retail|\(v[0-9.]+\)', re.I)
    return cbr.sub('', book).rstrip('() .-')

@app.route('/books/status', methods=['GET'])
def status_books():
    return json.dumps(current_status())

@app.route('/static/<path:path>')
def _static(path):
    return send_from_directory('static', path)

@app.route('/books/available')
def available():
    objects = s3client.list_objects_v2(Bucket=constants.BUCKET.PROCESSED_FILE)['Contents']
    objects = sorted(objects, key=lambda x: x['LastModified'], reverse=True)
    books = [(html.escape(obj['Key'], quote=False), clean_book_name(obj['Key'])) for obj in objects]
    return render_template('available_books.html', books=books)

@app.route('/')
def index():
    return render_template('current_status.html', current_status=current_status())

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

@app.route('/book/search', methods=['GET', 'POST'])
def search_books():
    if request.method == 'POST':
        orig_terms = request.form.get('terms')
        terms = orig_terms.split()
        books = book_search(terms)
        return render_template('search_results.html', search_results=books, search_query=orig_terms)
    else:
        terms = request.args.get('terms').split()
        books = book_search(terms)
        return json.dumps(books)

@app.route('/book/fetch', methods=['POST'])
def fetch_books():
    if request.json:
        is_api = True
        fetch = request.json
    else:
        is_api = False
        fetch = request.form
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

    r.hset(job_key, constants.REDIS.STATE_KEY, '')
    r.hset(job_key, constants.REDIS.STEP_KEY, 'QUEUED')
    r.hset(job_key, constants.REDIS.KEY_NAME, job_key)
    r.hset(job_key, constants.REDIS.BOOK_KEY, fetch['book'])
    r.hset(job_key, constants.REDIS.BOT_KEY, fetch['bot'])

    r.expire(job_key, constants.JOB_TTL_REDIS)

    r.rpush(constants.REDIS.Q_BOOK_COMMANDS, json.dumps(data))
    if is_api:
        return job_key
    else:
        return redirect(url_for('index'))

@app.route('/books/batch_update', methods=['POST'])
def batch_update():
    fetch = request.json
    if fetch is None or 'secret_key' not in fetch \
            or fetch['secret_key'] != 'super_secret':
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
    create_statements = [
            'CREATE TABLE IF NOT EXISTS books (bot TEXT(40), book TEXT(200), size INT)',
            'CREATE UNIQUE INDEX IF NOT EXISTS books_unique ON books(bot, book)',
            ]
    db = sqlite3.connect('books.db')
    c = db.cursor()
    for stmt in create_statements:
        c.execute(stmt)
    db.commit()
    db.close()

    app.run(host='0.0.0.0', debug=True)

if __name__ == '__main__':
    main()
