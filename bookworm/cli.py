import json
import requests
import sys
import time

if len(sys.argv) == 1:
    print("You must give search parameters")
    sys.exit(1)

SEPARATOR = ' ~ '
r = requests.get('http://localhost:5000/book/search', params={'terms': ' '.join(sys.argv[1:])})
r.raise_for_status()
entries = r.json()

for i, e in enumerate(entries):
    print('%02d) %s' % (i, e))

index = int(input('Input the number to download: '))
entry = entries[index]

bot, book = entry['bot'], entry['book']
r = requests.post('http://localhost:5000/book/fetch', json={'bot': bot, 'book': book})
if not r.ok:
    print(r.text)
    sys.exit(1)

_id = r.text
book_status = None
while True:
    r = requests.get('http://localhost:5000/books/status')
    all_statuses = r.json()
    for s in all_statuses:
        if s['KEY'] == _id:
            _b_status = s
            break

    if _b_status != book_status:
        book_status = _b_status
        print('Status change', book_status['STEP'], book_status.get('STATE'))
    if book_status['STEP'] == 'DONE':
        break
    time.sleep(1)
