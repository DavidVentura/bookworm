import os
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from qmanager import qManager

# Port on which server will run.
PORT = 8080


class HTTPRequestHandler(BaseHTTPRequestHandler):
    q = qManager()

    def do_GET(self):
        self.send_200()
        out=json.dumps(self.q.task_status())
        #self.wfile.write(bytes()) #fileHandle.read().encode()
        self.wfile.write(bytes(out,"utf-8")) #fileHandle.read().encode()

    def send_400(self):
        self.send_response(400, 'NOT OK')
        self.send_header('Content-type', 'text/json')
        self.end_headers()

    def send_200(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/json')
        self.end_headers()

    def do_POST(self):
        # Check if path is there.
        if self.path:
            length = self.headers['content-length']
            if length is None:
               self.send_400()
               return


            data = self.rfile.read(int(length))
            data = data.decode("utf-8")
            try:
                d=json.loads(data)
            except:
                print("no json")
                self.send_400()
                return

            if not "type" in d or not "book" in d:
                self.send_400()
                return
            if d["type"].upper()=="SEARCH":
                self.q.new_search(d["book"],d["extension"])
                self.send_200()
                return

            if d["type"]=="BOOK":
                self.q.new_dl(d["book"])
                self.send_200()
                return


if __name__ == '__main__':

    HTTPDeamon = HTTPServer(('', PORT), HTTPRequestHandler)

    print("Listening at port", PORT)

    try:
        HTTPDeamon.serve_forever()
    except KeyboardInterrupt:
        pass

    HTTPDeamon.server_close()
    print("Server stopped")
