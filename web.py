#!/usr/bin/env python3
import os
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from qmanager import qManager
import urllib

# Port on which server will run.
PORT = 8080
BASE_PATH="/backend/" #changes based on webserver
FILE_PATH="/tmp/"


class HTTPRequestHandler(BaseHTTPRequestHandler):
    q = qManager()

    def do_GET(self):
        if self.path==BASE_PATH:
        #self.wfile.write(bytes()) #fileHandle.read().encode()
            self.send_200()
            out=json.dumps(self.q.task_status())
            self.wfile.write(bytes(out,"utf-8")) #fileHandle.read().encode()
            return

        p=urllib.parse.unquote(self.path.replace(BASE_PATH,""))
        path=FILE_PATH+p
        print(path)
        #mime=mimetypes.guess_type(path) #fails on mobi, epub
        mime=""
        if p.endswith("mobi"):
            mime="application/x-mobipocket-ebook"
        if p.endswith("epub"):
            mime="application/epub+zip"
        if p.endswith("pdf"):
            mime="application/pdf"
        if p.endswith("html"):
            mime="text/html"
        
        self.send_response(200)
        self.send_header('Content-type', mime)
        self.send_header('Content-Disposition', 'attachment;filename="%s"'%p)
        self.end_headers()

        fp = open(path,'rb')
        while True:
            b = fp.read(8192)
            if b:
                self.wfile.write(b) #fileHandle.read().encode()
            else:
                break

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
