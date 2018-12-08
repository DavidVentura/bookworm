#!/usr/bin/env python3
import logging
import os
import queue
import socket
import time
import utils
import re

from unzipper import unar
from threading import Thread
from collections import defaultdict

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

MODE_SEARCH = 'search'
MODE_BOOK = 'book'
results_key = re.compile(r'_results_for[_ ]+(?P<key>.*?)\.', re.I)

def query_to_job_key(query):
    job = query
    if job.startswith('!'):
        # !Ook Brandon Sanderson - [Skyward 01] - Skyward (retail) (epub).rar  ::INFO:: 3.5MB
        # !Horla-new Brandon Sanderson - Skyward (US) (epub).epub
        job = ' '.join(job.split(' ')[1:]).strip()
        # Brandon Sanderson - [Skyward 01] - Skyward (retail) (epub).rar  ::INFO:: 3.5MB
        # Brandon Sanderson - Skyward (US) (epub).epub
        job = re.sub(r'::.*$', '', job).strip()
    return job.lower()

def filename_to_job(fname):
    match = results_key.search(fname)
    if match: # list of results
        return match.group('key').replace('_', ' ').lower()
    # brandon_sanderson_-_skyward_(uk)_(epub).rar
    return fname.replace('_', ' ').lower()

def get_dcc_args(msg):
    msg = msg.split(':')[2]
    msg = msg.replace("\x01", "")
    if not msg.startswith("DCC"):
        return None
    args = msg.replace("DCC SEND ", "").split(" ")
    size = int(args.pop())
    port = int(args.pop())
    ip = utils.ip_from_decimal(int(args.pop()))
    filename = "_".join(args).replace('"', '')
    return ip, port, size, filename


class IRCClient(Thread):
    TIME_TO_FIRST_COMMAND = 30
    HOST = "irc.irchighway.net"
    PORT = 6667
    CHANNEL = "#ebooks"
    PATH = "/tmp/"
    SEARCH_BOT = "searchook"
    # ^ config
    IGNORE = [
        "NOTICE",
        "PART",
        "QUIT",
        "332",
        "333",
        "372",
        "353",
        "366",
        "251",
        "252",
        "254",
        "255",
        "265",
        "266",
        "396"]
    joined_channel = False
    connected = False
    name = "bookbot" + utils.random_hash()
    readbuffer = b''
    time_joined = None
    jobs = defaultdict(dict)
    busy = False

    def __init__(self, command_queue, results_queue):
        super(IRCClient, self).__init__(daemon=True)
        self.socket = None
        self.command_queue = command_queue
        self.results_queue = results_queue
        self.send_queue = queue.Queue()

        nickstr = "NICK %s" % self.name
        userstr = "USER %s %s bla :%s" % (self.name, self.HOST, self.name)

        self.send_queue.put(nickstr)
        self.send_queue.put(userstr)

    def run(self):
        self.handle_connect()
        while True:
            if self.connected and self.joined_channel:
                self.handle_commands()
            self.process_send_queue()
            try:
                self.handle_read()
            except socket.timeout:
                continue
            except socket.error as e:
                log.error('socket error')
                log.exception(e)
                self.handle_connect()
            except Exception as e:
                log.exception(e)
                break
        self.handle_close()
        log.info('Exiting RUN')

    def handle_commands(self):
        if self.command_queue.empty():
            time.sleep(0.2)
            return

        elapsed = time.time() - self.time_joined
        if elapsed < self.TIME_TO_FIRST_COMMAND:
            log.info("commands to process, but we have to wait %d", self.TIME_TO_FIRST_COMMAND - elapsed)
            time.sleep(1)
            return
        command = self.command_queue.get()
        log.info("command %s", command)
        job = query_to_job_key(command['query'])
        self.set_job_state(job, 'pending')

        if command['mode'] == MODE_SEARCH:
            self.send_queue.put("PRIVMSG %s :@%s %s " % (self.CHANNEL, self.SEARCH_BOT, command['query']))
            return
        self.send_queue.put("PRIVMSG %s :%s " % (self.CHANNEL, command['query']))

    def set_job_state(self, job, state):
        log.info("Setting job [%s] to %s", job, state)
        self.jobs[job].update({'state': state})
        self.results_queue.put({'type': 'status', 'status': state, 'key': job})
        if state == 'done':
            del self.jobs[job]

    def handle_connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.HOST, self.PORT))
        self.socket.settimeout(2)
        log.info("connected")
        self.connected = True

    def handle_close(self):
        log.info("closed")
        self.connected = False
        self.socket.close()

    def get_data_from_irc(self):
        data = self.socket.recv(4096)
        if len(data) < 2:
            return ""
        # newline at the end?
        if not (data[-1] == 10 and data[-2] == 13):
            self.readbuffer += data
            return ""

        data = self.readbuffer + data
        self.readbuffer = b''

        # purge crap
        data = (data.replace(b'\x95', b'').replace(b'0xc2', b'').decode('utf-8', 'ignore'))
        return data

    def handle_read(self):
        lines = self.get_data_from_irc().splitlines()

        for line in lines:
            words = line.split(' ')
            if len(words) < 2:
                continue
            msg_from = words[0]
            comm = words[1]

            if self.joined_channel:
                # log.debug(line)
                pass

            if comm in self.IGNORE:
                continue

            if comm == "JOIN":
                if self.name not in msg_from:  # msg "NICK joined the channel" not about me
                    continue
                log.info("Joined channel %s", self.CHANNEL)
                self.time_joined = time.time()
                self.joined_channel = True
                continue

            if comm == "PRIVMSG":
                # private message not addressed to me
                if words[2] != self.name:
                    continue
                log.info("privmsg: %s", line)
                dcc_args = get_dcc_args(line)
                if dcc_args is None:
                    continue
                ip, port, size, filename = dcc_args
                job = filename_to_job(filename)
                self.set_job_state(job, 'downloading')
                self.busy = True
                downloaded_filename = self.netcat(ip, port, size, filename, job)
                self.set_job_state(job, 'unarchiving')
                # TODO save state in redis on ip port size filename + output of handle files
                files = unar(downloaded_filename, self.PATH)
                self.busy = False
                self.results_queue.put({'type': 'files', 'files': files})
                self.set_job_state(job, 'done')

            if comm == "PING" or msg_from == "PING":  # respond ping to avoid getting kicked
                self.pong(line)
                continue

            if comm == "376":  # END MOTD
                # MOTD complete, lets join the channel
                self.join_channel(self.CHANNEL)
                continue

    def netcat(self, ip, port, size, filename, job_key):
        filename = os.path.basename(filename).replace(" ", "_")
        log.info('netcat: %s %d %d %s', ip, port, size, filename)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        log.info("Receiving file")
        s.connect((ip, port))

        fname = os.path.join(self.PATH, filename)
        f = open(fname, 'wb')
        count = 0
        last_perc = 0
        while True:
            data = s.recv(16384)
            if len(data) == 0:
                log.info("No data received - finished")
                break
            count += len(data)
            f.write(data)
            perc = int(100 * count / size)
            if perc % 10 == 0 and perc != last_perc:
                log.info("Download percentage: %d", perc)
                self.set_job_state(job_key, "%d%%" % perc)
                last_perc = perc
            if count >= size:
                break
        s.close()
        f.close()
        return fname

    def pong(self, data):
        msg = data.replace("PING ", "")
        self.send_queue.put("PONG %s" % msg)

    def join_channel(self, channel):
        self.send_queue.put("JOIN %s" % channel)

    def process_send_queue(self):
        if self.send_queue.empty():
            return
        data = self.send_queue.get()
        if not data.startswith("PONG"):
            log.info("Sending %s", data)
        add = bytes(str(data), "utf-8") + bytes([13, 10])
        self.socket.send(add)
