from flask import Flask, render_template, make_response, request
from bookworm import s3, constants
import pg_simple
import json
import redis

s3client = s3.client()
app = Flask(__name__)
pool = pg_simple.config_pool(dsn='dbname=david user=david')
db = pg_simple.PgSimple(pool)
r = redis.StrictRedis(host='localhost', port=6379, decode_responses=True)

@app.route('/books/status', methods=['GET'])
def status_books():
    keys = r.keys('book_*')
    ret = {}
    for key in keys:
        val = r.hgetall(key)
        ret[key] = val
    print(ret)
    return json.dumps(ret)

@app.route('/')
def index():
    objects = s3client.list_objects_v2(Bucket=constants.PROCESSED_FILE_BUCKET)['Contents']
    objects = sorted(objects, key=lambda x: x['LastModified'], reverse=True)
    books = [obj['Key'] for obj in objects]
    return render_template('kindle-index.j2', books=books)

@app.route('/book/<path:book>')
def serve_books(book):
    obj = s3client.get_object(Bucket=constants.PROCESSED_FILE_BUCKET, Key=book)
    data = obj['Body'].read()
    response = make_response(data)
    response.headers.set('Content-Disposition', 'attachment', filename=book)
    response.headers.set('Content-Length', len(data))
    return response

@app.route('/book/search', methods=['GET'])
def search_books():
    terms = request.args.get('terms').split()
    terms = [f'%{term}%' for term in terms]

    books = db.fetchall('books',
                        fields=['bot', 'book'],
                        where=('lower(book) like all(%s)', [terms]),
                        limit=100)
    return json.dumps([b._asdict() for b in books])

@app.route('/book/fetch', methods=['POST'])
def fetch_books():
    fetch = request.json
    print(fetch)
    r.rpush(constants.REDIS_BOOK_COMMANDS, json.dumps({'bot': fetch['bot'], 'book': fetch['book']}))
    return ''


def main():
    app.run(host='0.0.0.0', debug=True)

if __name__ == '__main__':
    main()
