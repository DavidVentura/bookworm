#!/usr/bin/env python3

import asyncore
import threading
import time
import re
import socket
import sys

class IRCClient(asyncore.dispatcher):
    HOST="irc.irchighway.net"
    PORT=6667
    NICK="MauBot3321321"
    IDENT="maubot"
    REALNAME="MauritsBot"
    IGNORE=["NOTICE","PART","QUIT", "332","333", "372", "353","366", "251", "252", "254", "255","265","266","396"]
    LOOKING_FOR="cryptonomicon"
    CHANNEL="#ebooks"


    buffer = []
    readbuffer=b''

    joined=False
    connected=False

    def __init__(self):
        asyncore.dispatcher.__init__(self)
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
        data=self.recv(8192)
        if not (data[-1]==10 and data[-2]==13):
            self.readbuffer+=data
            return

        data=self.readbuffer+data
        data=data.decode('utf-8')
        self.readbuffer=b''

        lines=data.splitlines()

        for line in lines:
            words=line.split(' ')
            if len(words)<2:
                continue
            msg_from=words[0]
            comm=words[1]

#            if comm in self.IGNORE:
#                continue
            if comm=="JOIN" and self.NICK in msg_from:
                print("JOINED")
                print(msg_from)
                #self.who()
                #self.search(self.LOOKING_FOR)
                #self.book("!Mysfyt Neal Stephenson - Cryptonomicon (v5.0) (mobi).rar  ::INFO:: 1.7MB")
                #self.book("!Pondering Neal Stephenson - Cryptonomicon (v5.0) (mobi).rar  ::INFO:: 2.1MB")
                self.joined=True
            if comm=="PRIVMSG":
                if words[2] != self.NICK:
                    continue
                self.parse_msg(line);

            if comm=="PING":
                print("PINGGGGG")
                self.pong(line)
                continue
            if comm=="376": #END MOTD
                self.join(self.CHANNEL)
                continue

#            if not self.joined:
#                continue
            print(line)


    def parse_msg(self,msg):
        msg=msg.split(':')[2]
        msg=msg.replace("\x01","")

        print(msg)
        args=msg.split(" ")
        size=int(args.pop())
        port=int(args.pop())
        ip=self.ip_from_decimal(int(args.pop()))
        args.pop(0) #"DCC"
        args.pop(0) #"SEND"
        print(args)
        filename="_".join(args)

        print("File %s ip %s port: %d size: %d " % (filename,ip,port,size))
        n=self.netcat(ip,port,size)
        fname='/tmp/1234-%s' % filename
        f=open(fname, 'wb')
        f.write(n)
        f.close()

    def search(self,book):
        print("searching for %s" % book)
        self.send_queue("PRIVMSG %s :@search %s \r\n" % (self.CHANNEL,book))

    def pong(self,data):
        #PING :excalibur.pa.us.irchighway.net
        print("PONG??")
        print(data)
        msg=data.split(':')[1]
        print(msg)
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
        print("sending: %s" % msg)
        self.buffer.append(add)

    def book(self,book):
        print("asking for %s" % book)
        self.send_queue("PRIVMSG %s :%s \r\n" % (self.CHANNEL,book))

    def who(self):
        self.send_queue("WHO %s" % self.CHANNEL)


    def ip_from_decimal(self,dec):
        return ".".join([ str(int(b,2)) for b in self.b_octets(bin(dec)[2:]) ])

    def b_octets(self,l):
        return [l[i:i + 8] for i in range(0, len(l), 8)]

    def netcat(self,ip,port,size):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip,port))
        s.shutdown(socket.SHUT_WR)
        out=b''
        char=["-","\\", "|","/"]
        i=0
        while True:
            data = s.recv(1024)
            if data=="":
                break
            out=out+data
            #sys.stdout.write("\r%s" % char[i])
            #i=i+1
            #if i>=len(char):
            #    i=0
            print("got some data")
            if len(out) >= size:
                break
        s.close()
        return out

client = IRCClient()
loop_thread = threading.Thread(target=asyncore.loop, name="Asyncore Loop")
loop_thread.start()
