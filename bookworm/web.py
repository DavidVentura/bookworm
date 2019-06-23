from flask import Flask, render_template, make_response
from bookworm import s3, constants

s3client = s3.client()
app = Flask(__name__)

@app.route('/')
def index():
    objects = s3client.list_objects_v2(Bucket=constants.PROCESSED_FILE_BUCKET)['Contents']
    objects = sorted(objects, key=lambda x: x['LastModified'], reverse=True)
    books = [obj['Key'] for obj in objects]
    return render_template('kindle-index.j2', books=books)

@app.route('/books/<path:book>')
def serve_books(book):
    obj = s3client.get_object(Bucket=constants.PROCESSED_FILE_BUCKET, Key=book)
    data = obj['Body'].read()
    response = make_response(data)
    response.headers.set('Content-Disposition', 'attachment', filename=book)
    response.headers.set('Content-Length', len(data))
    return response

if __name__ == '__main__':
    app.run()
