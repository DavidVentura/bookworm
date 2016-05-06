#!/usr/bin/env python3

import asyncore
import threading
import time
import re
import socket
import sys
from unzipper import unar

class IRCClient(asyncore.dispatcher):
    HOST="irc.irchighway.net"
    PORT=6667
    NICK="booksbot3321321"
    IDENT="booksbot"
    REALNAME="NotABot"
    IGNORE=["NOTICE","PART","QUIT", "332","333", "372", "353","366", "251", "252", "254", "255","265","266","396"]
    LOOKING_FOR="cryptonomicon"
    CHANNEL="#ebooks"
    EXTENSION="epub"

    buffer = []
    readbuffer=b''

    joined=False
    connected=False

    def __init__(self,book,extension):
        asyncore.dispatcher.__init__(self)

        self.EXTENSION=extension
        self.LOOKING_FOR=book

        self.create_socket()
        self.connect( (self.HOST, self.PORT) )
        nickstr="NICK %s\r\n" % self.NICK
        userstr="USER %s %s bla :%s\r\n" % (self.IDENT, self.HOST, self.REALNAME)

        self.send_queue(nickstr)
        self.send_queue(userstr)

    def handle_connect(self):
        print("connected")
        self.connected=True
        pass

    def handle_close(self):
        print("closed")
        self.connected=False
        self.close()

    def handle_read(self):
        data=self.recv(1024)
        if not (data[-1]==10 and data[-2]==13):
            self.readbuffer+=data
            return

        data=self.readbuffer+data
        data=data.replace(b'\x95', b'').replace(b'0xc2',b'').decode('utf-8','ignore') #purge mojibake
        self.readbuffer=b''

        lines=data.splitlines()

        for line in lines:
            words=line.split(' ')
            if len(words)<2:
                continue
            msg_from=words[0]
            comm=words[1]

            if comm in self.IGNORE:
                continue
            if comm=="JOIN":
                if self.NICK not in msg_from:
                    continue
                print("Joined channel %s" % self.CHANNEL)
                self.search(self.LOOKING_FOR)
                self.joined=True

            if comm=="PRIVMSG":
                if words[2] != self.NICK:
                    continue
                self.parse_msg(line);

            if comm=="PING" or msg_from=="PING":
                self.pong(line)
                continue
            if comm=="376": #END MOTD
                self.join(self.CHANNEL)
                continue

            if not self.joined:
                continue


    def parse_msg(self,msg):
        msg=msg.split(':')[2]
        msg=msg.replace("\x01","")

        args=msg.split(" ")
        size=int(args.pop())
        port=int(args.pop())
        ip=self.ip_from_decimal(int(args.pop()))
        args.pop(0) #"DCC"
        args.pop(0) #"SEND"
        filename="_".join(args)
        fname='/tmp/1234-%s' % filename

        n=self.netcat(ip,port,size,fname)
        files=unar(fname,"/tmp/")
        for f in files:
            if "searchbot" in f.lower():
                self.list_books(f)


    def list_books(self,f):
        f=open(f,"r")
        lines=f.readlines()
        lines=[l.strip() for l in lines if self.EXTENSION in l.lower() ]
        for l in lines:
            print(l)
        return lines

    def search(self,book):
        print("searching for %s" % book)
        self.send_queue("PRIVMSG %s :@search %s \r\n" % (self.CHANNEL,book))

    def pong(self,data):
        msg=data.replace("PING ","")
        self.send_queue("PONG %s\r\n" % msg)

    def join(self,channel):
        self.send_queue("JOIN %s\r\n" % channel)

    def writable(self):
        return (len(self.buffer) > 0 and self.connected)

    def handle_write(self):
        out=self.buffer.pop()
        self.send(out)

    def send_queue(self,msg):
        add=bytes(str(msg),"utf-8")
        self.buffer.append(add)

    def book(self,book):
        print("asking for %s" % book)
        self.send_queue("PRIVMSG %s :%s \r\n" % (self.CHANNEL,book))

    def who(self):
        self.send_queue("WHO %s" % self.CHANNEL)


    def ip_from_decimal(self,dec):
        return ".".join([ str(int(b,2)) for b in self.b_octets(bin(dec)[2:]) ])

    def b_octets(self,l):
        l=l.zfill(32)
        return [l[0:8],l[8:16],l[16:24],l[24:32]]

    def netcat(self,ip,port,size,fname):
        s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip,port))
        #s.shutdown(socket.SHUT_WR)
        sizelen=len(str(size))
        f=open(fname, 'wb')
        count=0
        while True:
            data = s.recv(1024)
            if len(data)==0:
                print("empty")
                break
            count+=len(data)
            f.write(data)
            #sys.stdout.write("\r%s/%d" % (str(count).zfill(sizelen),size))
            #progress
            if count >= size:
                break

        s.close()
        f.close()

if len(sys.argv)!=3:
    print("USAGE: %s <BOOK> <FORMAT>" % sys.argv[0])
    sys.exit(1)

print("Looking for %s in format %s" % (sys.argv[1],sys.argv[2]))
client = IRCClient(sys.argv[1],sys.argv[2])
loop_thread = threading.Thread(target=asyncore.loop, name="Asyncore Loop")
loop_thread.start()
