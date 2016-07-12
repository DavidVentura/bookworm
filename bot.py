#!/usr/bin/env python3

import random
import threading
import re
import socket
import sys
from unzipper import unar

class IRCClient():
    HOST="irc.irchighway.net"
    PORT=6667
    NICK=""
    IDENT=""
    REALNAME=""
    IGNORE=["NOTICE","PART","QUIT", "332","333", "372", "353","366", "251", "252", "254", "255","265","266","396"]
    CHANNEL="#ebooks"
    STATUS=""
    PROGRESS=0
    TYPE="SEARCH"
    OUTPUT=""
    buffer = []
    readbuffer=b''
    NOT_EXITED=True
    EXTRA_OUTPUT=""
    PATH=""
    joined=False
    connected=False

    def __init__(self,book,extension,t,logging=False,path="/tmp/"):

        self.TYPE=t
        self.EXTENSION=extension
        self.LOOKING_FOR=book
        self.LOGGING=logging
        self.PATH=path

        name="bookbot"+self.random_hash()
        self.NICK=name
        self.IDENT=name
        self.REALNAME=name

        self.socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect( (self.HOST, self.PORT) )
        self.handle_connect()

        nickstr="NICK %s" % self.NICK
        userstr="USER %s %s bla :%s" % (self.IDENT, self.HOST, self.REALNAME)

        self.t=threading.Thread(target=self.handle_read)
        self.t.start()
        self.send_queue(nickstr)
        self.send_queue(userstr)

    def random_hash(self):
        return ("%032x" % random.getrandbits(128))[:10]

    def handle_connect(self):
        self.log("connected")
        self.STATUS="CONNECTED"
        self.connected=True
        pass

    def handle_close(self):
        self.NOT_EXITED=False
        self.log("closed")
        self.STATUS="DISCONNECTED"
        self.connected=False
        self.socket.close()

    def do_timeout(self):
        if not self.NOT_EXITED:
            return
        self.NOT_EXITED=False
        self.log("Abort mission")
        self.STATUS="TIMED OUT"
        self.connect=False
        self.socket.close()


    def handle_read(self):
        while self.NOT_EXITED:
            try:
                data=self.socket.recv(1024)
            except e:
                break
            if len(data) < 2:
                continue
            if not (data[-1]==10 and data[-2]==13):
                self.readbuffer+=data
                continue
    
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
                    if self.NICK not in msg_from: #msg "NICK joined the channel" not about me
                        continue
                    self.STATUS="JOINED"
                    self.log("Joined channel %s" % self.CHANNEL)
                    self.run_query()
                    self.joined=True
                    continue
    
                if comm=="PRIVMSG":
                    if words[2] != self.NICK: #private message not addressed to me
                        continue
                    self.parse_msg(line);
    
                if comm=="PING" or msg_from=="PING": #respond ping to avoid getting kicked
                    self.pong(line)
                    continue
                if comm=="376": #END MOTD
                    self.join_channel(self.CHANNEL) #MOTD complete, lets join the channel
                    continue
    
                if not self.joined: #waiting 
                    continue


    def run_query(self):
        self.STATUS="WAITING"
        if self.TYPE=="SEARCH":
            self.search(self.LOOKING_FOR)
            return

        self.book(self.LOOKING_FOR)

    def parse_msg(self,msg):
        msg=msg.split(':')[2]
        msg=msg.replace("\x01","")
        if not msg.startswith("DCC"):
            self.EXTRA_OUTPUT=msg;
            self.log(msg)
            return

        args=msg.replace("DCC SEND ","").split(" ")
        size=int(args.pop())
        port=int(args.pop())
        ip=self.ip_from_decimal(int(args.pop()))
        filename="_".join(args).replace('"','')
        self.STATUS="RECEIVING"

        n=self.netcat(ip,port,size,filename)
        files=unar(n,self.PATH)

        out=[]
        for f in files:
            if "searchbot" in f.lower():
                out.append(self.list_books(f))

        self.OUTPUT=[]
        if len(out)>0:
            if type(out[0]) is list:
                self.OUTPUT=[item for sublist in out for item in sublist]
            else:
                self.OUTPUT=out
            self.OUTPUT=list(set(self.OUTPUT))
        else:
            self.OUTPUT=files

        if self.TYPE == "BOOK":
            self.log("Files: ")
            self.log(self.OUTPUT)

        self.OUTPUT=[i.replace(self.PATH,"") for i in self.OUTPUT  ]
        self.handle_close()

    def list_books(self,f):
        f=open(f,"r")
        lines=f.readlines()
        lines=[l.strip().replace('\r','') for l in lines if self.EXTENSION in l.lower() and l.startswith('!') and "htm" not in l.lower() ]
        for l in lines:
            self.log(l)
        return lines

    def netcat(self,ip,port,size,filename):
        s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.log("Receiving file")
        s.connect((ip,port))
        sizelen=len(str(size))
        fname=('%s/%s' % (self.PATH,filename)).replace("//","/")
        f=open(fname, 'wb')
        count=0
        while True:
            data = s.recv(4096)
            if len(data)==0:
                self.log("empty")
                break
            count+=len(data)
            f.write(data)
            perc=int(100*count/size)
            self.STATUS="DOWNLOADING" #% perc #progress
            self.PROGRESS=perc

            self.log("\r%d%%" % perc,instant=True)
            if count >= size:
                break

        s.close()
        f.close()
        self.log("") #newline
        return fname

    def search(self,book):
        self.log("searching for %s" % book)
        self.send_queue("PRIVMSG %s :@search %s " % (self.CHANNEL,book))

    def pong(self,data):
        msg=data.replace("PING ","")
        self.send_queue("PONG %s" % msg)

    def join_channel(self,channel):
        self.send_queue("JOIN %s" % channel)

    def send_queue(self,msg):
        add=bytes(str(msg),"utf-8")+bytes([13,10])
        self.socket.send(add)

    def book(self,book):
        self.log("Asking for '%s'" % book)
        self.send_queue("PRIVMSG %s :%s " % (self.CHANNEL,book))

    def who(self):
        self.send_queue("WHO %s" % self.CHANNEL)

    def ip_from_decimal(self,dec):
        return ".".join([ str(int(b,2)) for b in self.b_octets(bin(dec)[2:]) ])

    def b_octets(self,l):
        l=l.zfill(32)
        return [l[0:8],l[8:16],l[16:24],l[24:32]]

    def log(self,val,instant=False):
        if self.LOGGING:
            if not instant:
                print(val)
            else:
                sys.stdout.write(val)

def usage():
    print("USAGE:")
    print("\t %s SEARCH <BOOK> <FORMAT>" % sys.argv[0])
    print("\t %s BOOK <BOT COMMAND>" % sys.argv[0])
    sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv)==4:
        if(sys.argv[1] != "SEARCH"):
            usage()
        mode  = sys.argv[1]
        query = sys.argv[2]
        grep  = sys.argv[3]

    elif len(sys.argv)==3:
        if(sys.argv[1] != "BOOK"):
            usage()
        mode  = sys.argv[1]
        query = sys.argv[2]
        grep  = ""
    else:
        usage()
    
    if mode == "SEARCH":
        print("Looking for '%s' in format '%s'" % (query,grep))
    if mode == "BOOK":
        print("Downloading %s" % query)

    client = IRCClient(query,grep,mode,logging=True)
