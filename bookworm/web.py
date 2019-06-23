#!/usr/bin/env python3
import os
import json
from datetime import datetime
from websocket_server import WebsocketServer
from qmanager import qManager
import urllib

# Port on which server will run.
PORT = 8080
BASE_PATH='/backend/' #changes based on webserver
last_msg = datetime.now()

def send_status(server, client=None, force=False):
    global last_msg
    if client is None and not force:
        if (datetime.now() - last_msg).total_seconds() < 2:
            return
        last_msg = datetime.now()
    #status = { 'SEARCH': q.search_status(), 'BOOKS': q.books_status()}
    status = None
    if client is None:
        ws.send_message_to_all(json.dumps(status))
    else:
        server.send_message(client, json.dumps(status))

def new_client(client, server):
    send_status(server, client)

def message_received(client, server, message):
    j = json.loads(message)
    print(j)
    if j['type'].upper() == 'SEARCH':
        #q.new_search(j['book'], j['extension'])
        pass

    if j['type'].upper() == 'BOOK':
        pass

    send_status(server)

def updated(force=False):
    send_status(ws, force=force)


if __name__ == '__main__':
    ws = WebsocketServer(8081, host='127.0.0.1')
    ws.set_fn_new_client(new_client)
    ws.set_fn_message_received(message_received)
    ws.run_forever()
