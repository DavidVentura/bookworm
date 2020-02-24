import datetime
import html
import json
import logging
import os
import re
import redis
import time

import waitress

from flask import Flask, render_template, make_response, request, g, send_from_directory, redirect, url_for

from bookworm import s3, constants, db

s3client = s3.client()
app = Flask(__name__, static_url_path='')
r = redis.StrictRedis(host='localhost', port=6379, decode_responses=True)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


@app.before_request
def before_request():
    g.start = time.time()


@app.teardown_request
def teardown_request(exception=None):
    log.debug(f'request took %sms', time.time()-g.start)


def get_db():
    _db = getattr(g, '_database', None)
    if _db is None:
        _db = db.get_db()
        g._database = db
    return _db

def book_search(terms):
    conditions = []
    valid_terms = []
    for term in terms:
        if len(term) <= 2:
            continue
        valid_terms.append(term)

    all_conditions = ' AND '.join(valid_terms)

    log.info('Querying: %s: %s', valid_terms, all_conditions)
    start = datetime.datetime.now()
    cur = get_db().cursor()
    rows = cur.execute('SELECT bot, books.book FROM books inner join tokens on books.id = tokens.pkey where valid AND tokens.book match \'%s\' LIMIT 30' % all_conditions)
    rows = list(rows)
    time_taken = datetime.datetime.now() - start
    log.info('Done querying: %s, took: %s', valid_terms, time_taken)
    return rows

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

    batch_update_commands = ['@pondering42', '@dv8', '@shytot', '@dragnbreaker', '@Xon-new', '@oatmeal']
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
        log.info('Pushing command: %s', data)
        r.rpush(constants.REDIS.Q_BOOK_COMMANDS, json.dumps(data))
    return ''

def main():
    db.init_db()
    port = 5000
    log.info("Starting server listening on %s", port)
    waitress.serve(app, listen='0.0.0.0:%s' % port)

if __name__ == '__main__':
    main()
