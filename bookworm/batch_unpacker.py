import os
import json
import socket
import sys
import time
import tempfile
import logging
from threading import Thread
from subprocess import check_output
from bookworm import s3, parse
from bookworm.constants import UNPACKABLE_EXTENSIONS, REDIS
import redis


log = logging.getLogger(__name__)


def should_unpack(fname):
    fname = fname.lower()
    return fname.endswith('rar') or fname.endswith('zip')

def archive_contents(fd):
    to_extract = {}
    contents = check_output(['lsar', '-j', fd.name]).decode('utf-8')
    contents = json.loads(contents)
    
    log.debug(contents['lsarContents'])
    for f in contents['lsarContents']:
        fname = f['XADFileName']
        log.info('Found file %s in the archive', fname)
        if any([extension in fname.lower() for extension in ['.txt'] + UNPACKABLE_EXTENSIONS]):
            log.info('Extracting %s from the archive', fname)
            to_extract[f['XADIndex']] = fname
    return to_extract

def delete_raw_file(s3client, s3key, meta):
    log.info('Deleting %s from %s', s3key, meta['raw_file_bucket'])
    s3client.delete_object(Bucket=meta['raw_file_bucket'], Key=s3key)

def unpack_and_store(job_key, s3key, s3client, redis, meta):
    redis.hset(job_key, REDIS.STEP_KEY, 'UNPACKING')
    unpacked_files = unpack(s3key, s3client, redis, meta)
    redis.hset(job_key, REDIS.STEP_KEY, 'UNPACK_DONE')
    log.info('Done unpacking job %s', job_key)

    for fname, data in unpacked_files:
        log.info('Batch process file: %s', fname)
        try:
            decoded = data.decode('utf-8')
        except UnicodeDecodeError:
            decoded = data.decode('latin-1')

        found = parse.parse_and_insert_lines(decoded.replace('\r', '').splitlines())
        log.info('Found %d books in this batch', found)

    #delete_raw_file(s3client, s3key, meta)
    redis.hset(job_key, REDIS.STEP_KEY, 'DONE')
    redis.hdel(job_key, REDIS.STATE_KEY)

def unpack(s3key, s3client, redis, meta):
    log.info('Got a request to unpack %s', s3key)
    data = s3client.get_object(Key=s3key, Bucket=meta['raw_file_bucket'])
    with tempfile.NamedTemporaryFile() as fd:
        raw_file_contents = data['Body'].read()
        fd.write(raw_file_contents)
        fd.flush()

        if not should_unpack(s3key):
            log.info("Not unpacking %s", s3key)
            return [(s3key, raw_file_contents)]

        to_extract = archive_contents(fd)
        if not to_extract:
            log.error("Could not find any valid file")
            return []

        ret = []
        for index, fname in to_extract.items():
            log.info('Processing %s %s', index, fname)
            file_contents = check_output(['unar', '-o', '-', '-i', fd.name, str(index)])
            log.info('Got %d bytes', len(file_contents))
            ret.append((fname, file_contents))
        return ret


def main():
    r = redis.StrictRedis(host='localhost', port=6379)
    s3client = s3.client()
    while True:
        log.info('Waiting for message on %s', REDIS.Q_PROCESS_BATCH_FILE)
        topic, message = r.blpop(REDIS.Q_PROCESS_BATCH_FILE)

        log.info('got message: %s', message)
        params = json.loads(message.decode('utf-8'))
        log.info('params for unpacker: %s', params)
        params['s3client'] = s3client
        params['redis'] = r

        t = Thread(target=unpack_and_store, kwargs=params)
        t.daemon = True
        t.start()
