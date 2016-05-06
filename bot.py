#!/usr/bin/env python3

import asyncore
import threading
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
    STATUS=""
    OUT_DIR="/tmp"
    OUTPUT_VALUE=""

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
        nickstr="NICK %s" % self.NICK
        userstr="USER %s %s bla :%s" % (self.IDENT, self.HOST, self.REALNAME)

        self.send_queue(nickstr)
        self.send_queue(userstr)

    def handle_connect(self):
        print("connected")
        self.STATUS="CONNECTED"
        self.connected=True
        pass

    def handle_close(self):
        print("closed")
        self.STATUS="DISCONNECTED"
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
                self.STATUS="JOINED"
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

        args=msg.replace("DCC SEND ","").split(" ")
        size=int(args.pop())
        port=int(args.pop())
        ip=self.ip_from_decimal(int(args.pop()))
        filename="_".join(args)
        self.STATUS="RECEIVING"

        n=self.netcat(ip,port,size,filename)
        files=unar(n,"/tmp/")

        self.OUTPUT_VALUE=[]
        for f in files:
            if "searchbot" in f.lower():
                self.list_books(f)

    def list_books(self,f):
        f=open(f,"r")
        lines=f.readlines()
        lines=[l.strip() for l in lines if self.EXTENSION in l.lower() ]
    #    for l in lines:
    #        print(l)
        return lines

    def netcat(self,ip,port,size,filename):
        s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip,port))
        #s.shutdown(socket.SHUT_WR)
        sizelen=len(str(size))
        fname='%s/%s' % (self.OUT_DIR,filename)
        f=open(fname, 'wb')
        count=0
        while True:
            data = s.recv(1024)
            if len(data)==0:
                print("empty")
                break
            count+=len(data)
            f.write(data)
            #sys.stdout.write("\r%s/%d" % (str(count).zfill(sizelen),size)) #progress
            if count >= size:
                break

        s.close()
        f.close()
        return fname

    def search(self,book):
        print("searching for %s" % book)
        self.send_queue("PRIVMSG %s :@search %s " % (self.CHANNEL,book))

    def pong(self,data):
        msg=data.replace("PING ","")
        self.send_queue("PONG %s" % msg)

    def join(self,channel):
        self.send_queue("JOIN %s" % channel)

    def writable(self):
        return (len(self.buffer) > 0 and self.connected)

    def handle_write(self):
        out=self.buffer.pop()
        self.send(out)

    def send_queue(self,msg):
        add=bytes(str(msg),"utf-8")+bytes([13,10])
        self.buffer.append(add)

    def book(self,book):
        print("asking for %s" % book)
        self.send_queue("PRIVMSG %s :%s " % (self.CHANNEL,book))

    def who(self):
        self.send_queue("WHO %s" % self.CHANNEL)

    def ip_from_decimal(self,dec):
        return ".".join([ str(int(b,2)) for b in self.b_octets(bin(dec)[2:]) ])

    def b_octets(self,l):
        l=l.zfill(32)
        return [l[0:8],l[8:16],l[16:24],l[24:32]]

    def stop(self):
        self.close()


if __name__ == "__main__":
    if len(sys.argv)!=3:
        print("USAGE: %s <BOOK> <FORMAT>" % sys.argv[0])
        sys.exit(1)
    
    print("Looking for %s in format %s" % (sys.argv[1],sys.argv[2]))
    client = IRCClient(sys.argv[1],sys.argv[2])
    loop_thread = threading.Thread(target=asyncore.loop)
    loop_thread.start()
