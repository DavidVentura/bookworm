#!/usr/bin/env python3

from  bot import IRCClient
import queue
import shlex
import asyncore
import datetime
from time import strftime,time

class qManager:

    tasks = []
    last_id=0
    PATH=""

    def __init__(self,path="/tmp/"):
        self.PATH=path

    def new_dl(self,string):
        self.new_task(string,IRCClient(string,"","BOOK",logging=False,path=self.PATH))

    def new_search(self,keywords,format):
        self.new_task(keywords,IRCClient(keywords,format,"SEARCH",logging=False,path=self.PATH))

    def new_task(self,query,t):
        nt = task(query,t,self.last_id)
        self.last_id+=1
        self.tasks.append(nt)

    def task_status(self):
        ret=[]
        for t in self.tasks:
            elapsed= time()-t.START_TIME
            ret.append({"ID": t.ID,
                "STATUS": t.get_status(),
                "PROGRESS": t.get_progress(),
                "OUT": t.get_output(),
                "ELAPSED": int(elapsed),
                "QUERY": t.QUERY,
                "EXTRA": t.get_extra(),
                "TYPE": t.get_type()})

        return ret
class task:
    CUR_STATUS=""
    OUTPUT=""
    ID=0
    CLIENT=None
    START_TIME=None
    QUERY=""
    def __init__(self,query,c,id):
        self.QUERY=query
        self.CLIENT=c
        self.ID=id
        self.START_TIME=time()
        pass

    def get_progress(self):
        return self.CLIENT.PROGRESS;

    def get_extra(self):
        return self.CLIENT.EXTRA_OUTPUT;
    def get_status(self):
       if time() - self.START_TIME > 600:
           self.CLIENT.do_timeout()
       self.OUTPUT=self.CLIENT.OUTPUT
       return self.CLIENT.STATUS 

    def get_type(self):
       return self.CLIENT.TYPE
    def get_output(self):
       return self.OUTPUT




#BASIC CLI INTERFACE
if __name__ == "__main__":
    q = qManager()
    while True:
        line=input()
        words=shlex.split(line)
        print(q.task_status())
        if len(words)<2:
            continue
        comm=words[0]
        if comm.lower()=="quit":
            break
        if comm.lower()=="search":
            if len(words)<3:
                continue
            q.new_search(words[1],words[2])
            continue
        if comm.lower()=="dl":
            q.new_dl(words[1])
            continue
    
        print("search <'multiple keywords'> <format>|dl <line>|quit")
