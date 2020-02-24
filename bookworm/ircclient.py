#!/usr/bin/env python3
import json
import sys
import time
import shlex
import logging

from threading import Thread
from bookworm.constants import IRC, REDIS, JOB_KEY_PREFIX, JOB_TTL_REDIS
from bookworm.utils import random_hash

import redis
import irc.client
import jaraco.stream.buffer

log = logging.getLogger(__name__)

class IRCClient(irc.client.SimpleIRCClient):
    def __init__(self, target, name):
        log.info('startup to %s, as %s', target, name)
        irc.client.SimpleIRCClient.__init__(self)
        irc.client.ServerConnection.buffer_class = jaraco.stream.buffer.LenientDecodingLineBuffer
        self.target = target
        self.name = name
        self.startup = time.time()
        self.r = redis.StrictRedis(host='localhost', port=6379)
        self.busy = False

        self.connect("irc.irchighway.net", 6667, name)

        t = Thread(target=self.start)
        t.daemon = True
        t.start()

    def on_welcome(self, connection, event):
        if irc.client.is_channel(self.target):
            connection.join(self.target)

    def wait_for_commands(self):
        while True:
            if self.busy:
                log.info('Busy with another task..')
                time.sleep(2)
                continue
            log.info('Waiting for message on %s', REDIS.Q_BOOK_COMMANDS)
            topic, message = self.r.blpop(REDIS.Q_BOOK_COMMANDS)
            log.info('got message: %s', message)

            delta = IRC.TIME_TO_FIRST_COMMAND - (time.time() - self.startup)
            while delta > 0:
                delta = IRC.TIME_TO_FIRST_COMMAND - (time.time() - self.startup)
                log.info("I am not ready yet, still %d to go", delta)
                time.sleep(max(min(delta, 2), 0))

            data = message.decode('utf-8')
            log.info('data: %s', data)
            command = json.loads(data)
            log.info('Command: %s', command)

            self.meta = command['meta']
            irc_command = command['command'].strip()
            self.job_key = command['job_key']
            self.fetch_queue = command['meta']['fetch_file_queue']

            self.r.hset(self.job_key, REDIS.STEP_KEY, 'REQUESTED')
            self.connection.privmsg(self.target, irc_command)
            self.busy = True

    def on_pubmsg(self, connection, event):
        log.debug('pubmsg %s', event)

    def on_privmsg(self, connection, event):
        log.info('privmsg %s', event)
    
    def on_ctcp(self, connection, event):
        if event.target != self.name:
            log.debug('ctcp event: %s', event)
            log.debug('ctcp event for someone else')
            return

        log.info('ctcp event: %s', event)
        payload = event.arguments[1]
        parts = shlex.split(payload) # quotes
        log.info(parts)

        command = parts.pop(0)
        if command != "SEND":
            return
        log.info('fname %s', parts[-4])
        log.info('peer_address %s', irc.client.ip_numstr_to_quad(parts[-3]))
        log.info('Port %s', parts[-2])
        log.info('size %s', parts[-1])

        filename, peer_address, peer_port, size = parts
        peer_address = irc.client.ip_numstr_to_quad(peer_address)
        peer_port = int(peer_port)
        data = json.dumps({'ip': peer_address,
                           'port': peer_port,
                           'size': int(size),
                           'filename': filename,
                           "job_key": self.job_key,
                           "meta": self.meta})
        log.info('Publishing to %s: %s', self.fetch_queue, data)
        self.r.rpush(self.fetch_queue, data)
        self.busy = False

    def on_disconnect(self, connection, event):
        sys.exit(0)


def main():

    name = "bookbot" + random_hash()

    c = IRCClient(IRC.CHANNEL, name)
    c.wait_for_commands()
main()
