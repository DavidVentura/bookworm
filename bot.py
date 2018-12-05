#!/usr/bin/env python3.7
import logging
import queue
import shlex
import subprocess
import sys

from threading import Thread
from ircclient import IRCClient, MODE_SEARCH, MODE_BOOK

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

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


def handle_files(files, mode):
    log.info("Unarchived files %s", files)
    out = []
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
        if item['type'] == 'files':
            handle_files(item['files'], item['mode'])
def main():
    q = queue.Queue()
    rq = queue.Queue()
    client = IRCClient(command_queue=q, results_queue=rq)
    client.start()

    results_t = Thread(target=handle_results, args=(rq,))
    results_t.daemon = True
    results_t.start()
    for line in sys.stdin:
        line = line.strip().lower()
        try:
            split = shlex.split(line)
        except Exception as e:
            print(e)
            continue

        if split[0].lower() not in [MODE_SEARCH, MODE_BOOK]:
            usage()
            continue

        mode = split[0]
        query = " ".join(split[1:])
        data = {'query': query, 'mode': mode}
        q.put(data)
    client.join()
    results_t.join()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBye")
