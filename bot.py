#!/usr/bin/env python3.7
import logging
import queue
import shlex
import subprocess
import sys
import readline
import os

from threading import Thread
from ircclient import IRCClient, MODE_SEARCH, MODE_BOOK

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
histfile = os.path.join(os.path.expanduser("~"), ".book_history")

def usage():
    print("USAGE:")
    print("\t SEARCH <BOOK>")
    print("\t BOOK <BOT COMMAND>")

def get_books_from_list(filename):
    f = open(filename, "r")
    ret = []
    for line in f.readlines():
        line = line.lower().strip()
        if not line.startswith('!') or not any(_type in line for _type in ['epub', 'mobi']):
            continue
        ret.append(line)
        log.info("Book matches: %s", line)
    ret = list(set(ret)) # dedup
    return ret

def mode_from_files(files):
    for f in files:
        f = f.lower()
        if 'searchbot' in f or 'searchook' in f.lower():
            return MODE_SEARCH
    return MODE_BOOK

def handle_files(files):
    log.info("Unarchived files %s", files)
    out = []
    mode = mode_from_files(files)
    if mode == MODE_SEARCH:
        for f in files:
            if "searchbot" not in f.lower() and "searchook" not in f.lower():
                continue
            out.extend(get_books_from_list(f))
        return

    for f in files:
        if f.lower().endswith(".epub"):
            log.info("EPUB %s", f)
            new_fname = f.replace("epub", "mobi")
            p = subprocess.Popen(["ebook-convert", f, new_fname], stdout=subprocess.DEVNULL)
            # TODO log to file?
            p.wait()
            out.append(new_fname)
        out.append(f)
    # TODO make paths absolute?
    for filename in out:
        log.info(filename)

def handle_results(q):
    while True:
        item = q.get()
        log.info("Got a result! %s", item)
        if item['type'] == 'status':
            print(item['key'], item['status'])
        elif item['type'] == 'files':
            handle_files(item['files'])

def main():
    q = queue.Queue()
    rq = queue.Queue()

    workers = []
    worker = IRCClient(command_queue=q, results_queue=rq)
    worker.start()
    workers.append(worker)

    results_t = Thread(target=handle_results, args=(rq,))
    results_t.daemon = True
    results_t.start()
    while True:
        line = input('> ').strip().lower()
        try:
            split = shlex.split(line)
        except Exception as e:
            print(e)
            continue
        if len(split) == 0:
            continue

        if split[0].lower() not in [MODE_SEARCH, MODE_BOOK]:
            usage()
            continue

        if not any([ not worker.busy for worker in workers]):
            print("Spawning a new worker as all are busy...")
            worker = IRCClient(command_queue=q, results_queue=rq)
            worker.start()
            workers.append(worker)

        mode = split[0]
        query = " ".join(split[1:])
        data = {'query': query, 'mode': mode}
        q.put(data)
        print("Command acknowledged")

    results_t.join()
    for worker in workers:
        worker.join()

if __name__ == "__main__":
    try:
        readline.read_history_file(histfile)
        # default history len is -1 (infinite), which may grow unruly
        readline.set_history_length(10000)
    except FileNotFoundError:
        pass

    try:
        main()
    except KeyboardInterrupt:
        print("\nBye")
    except EOFError:
        print("\nBye")
    readline.write_history_file(histfile)
