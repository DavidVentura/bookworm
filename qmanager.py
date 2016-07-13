#!/usr/bin/env python3
"""Manage a list of book-jobs,
return a description list for the website"""

import shlex
import re
from time import time
from bot import IRCClient


class qManager:
    """Main module class"""

    tasks = []
    last_id = 0
    PATH = ""

    def __init__(self, path="/tmp/"):
        """Init the manager. Set output path"""
        self.PATH = path

    def new_dl(self, string):
        """Download a book"""
        irc_client = IRCClient(
            string,
            "",
            "BOOK",
            logging=False,
            path=self.PATH)
        self.new_task(string, irc_client)

    def new_search(self, keywords, fmt):
        """Search for a book"""
        irc_client = IRCClient(
            keywords,
            fmt,
            "SEARCH",
            logging=False,
            path=self.PATH)
        self.new_task(keywords, irc_client)

    def new_task(self, query, t):
        """ Add a new 'task' to the list """
        nt = task(query, t, self.last_id)
        self.last_id += 1
        self.tasks.append(nt)

    def task_status(self):
        """ Return a dict with the status of each 'task' """
        ret = []
        for t in self.tasks:
            elapsed = time() - t.START_TIME
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
    """ Task class. Only returns a status"""
    CUR_STATUS = ""
    OUTPUT = ""
    ID = 0
    CLIENT = None
    START_TIME = None
    QUERY = ""

    def __init__(self, query, c, _id):
        """Initialize the task"""
        self.QUERY = query
        self.CLIENT = c
        self.ID = _id
        self.START_TIME = time()

    def get_progress(self):
        """ Return progress."""
        return self.CLIENT.PROGRESS

    def get_extra(self):
        """ Return extra output."""
        return self.CLIENT.EXTRA_OUTPUT

    def get_status(self):
        """ Return status.  If timed out since last call, stop task """
        if time() - self.START_TIME > 600:
            self.CLIENT.do_timeout()
        self.OUTPUT = self.CLIENT.OUTPUT
        return self.CLIENT.STATUS

    def get_type(self):
        """ Return type """
        return self.CLIENT.TYPE

    def get_output(self):
        """Return output:
           If it's just a string, return it (Books).
           If it's a list, parse it and return a representative dict.
           Should cache this or something, doesn't make sense to
           calculate on each call.
        """
        if isinstance(self.OUTPUT, str) or self.OUTPUT is None:
            return self.OUTPUT
        TAGS_R = re.compile(r'[\[(].*?[\])]|\.rar|v\d.*?\s')
        books = self.OUTPUT
        ret = []
        for book in books:
            book = book.replace("---", "")
            groups = re.search(
                r"(?P<BOT>^!\w+)(?P<BOOK>.*?)(?P<INFO>::INFO.*)?$", book)
            if groups is None:
                #print("[No groups] %s" % book)
                return books
            groups = groups.groupdict()

            # remove tags from book
            groups["BOOK"] = re.sub(TAGS_R, "", groups["BOOK"])
            groups["TAGS"] = [r.strip("()[]")
                              for r in re.findall(TAGS_R, book)]
            groups["TEXT"] = book
            ret.append(groups)
        return ret

# BASIC CLI INTERFACE
if __name__ == "__main__":
    q = qManager()
    while True:
        line = input()
        words = shlex.split(line)
        print(q.task_status())
        if len(words) < 2:
            continue
        comm = words[0]
        if comm.lower() == "quit":
            break
        if comm.lower() == "search":
            if len(words) < 3:
                continue
            q.new_search(words[1], words[2])
            continue
        if comm.lower() == "dl":
            q.new_dl(words[1])
            continue

        print("search <'multiple keywords'> <format>|dl <line>|quit")
