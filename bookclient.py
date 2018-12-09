from threading import Thread
from ircclient import IRCClient, MODE_SEARCH, MODE_BOOK
import logging
import queue
import subprocess

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

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
        return out

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
    return out

def handle_results(q, cb):
    while True:
        try:
            item = q.get(timeout=1)
            if item is None:
                break
        except queue.Empty:
            continue
        log.info("Got a result! %s", item)
        if item['type'] == 'status':
            cb((item['key'], item['status']))
        elif item['type'] == 'files':
            cb(handle_files(item['files']))

class BookClient:
    workers = []
    def __init__(self, cb):
        self.q = queue.Queue()
        self.rq = queue.Queue()

        self.results_t = Thread(target=handle_results, args=(self.rq, cb))
        self.results_t.daemon = True
        self.results_t.start()

        self.create_worker()

    def create_worker(self):
        print("Spawning a new worker")
        worker = IRCClient(command_queue=self.q, results_queue=self.rq)
        worker.start()
        self.workers.append(worker)

    def free_workers(self):
        return any([not worker.busy for worker in self.workers])

    def request(self, mode, query):
        if not self.free_workers():
            self.create_worker()

        if mode not in [MODE_SEARCH, MODE_BOOK]:
            print('Invalid mode')
            return

        self.q.put({'query': query, 'mode': mode})
        print("Command acknowledged")

    def __del__(self):
        print("Cleaning up workers")
        for worker in self.workers:
            worker.stop()
            worker.join(timeout=5)
        print("Cleaning up results")
        self.rq.put(None)
        self.results_t.join(timeout=5)
