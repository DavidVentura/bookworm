import os
import json
import socket
import sys
import time
import tempfile
from threading import Thread
from subprocess import check_output
from bookworm import s3
from bookworm.logger import log, setup_logger
from bookworm.constants import UNPACKABLE_EXTENSIONS, REDIS
import redis

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
        if any([extension in fname.lower() for extension in UNPACKABLE_EXTENSIONS]):
            log.info('Extracting %s from the archive', fname)
            to_extract[f['XADIndex']] = fname
    return to_extract

def convert_to_mobi(orig_fname) -> bytes:
    with tempfile.NamedTemporaryFile(suffix='.mobi') as fd:
        log.info('Converting %s to mobi at %s', orig_fname, fd.name)
        check_output(['ebook-convert', orig_fname, fd.name, '--output-profile=kindle_pw'])
        log.info('Done converting')
        buff = open(fd.name, 'rb').read()
        return buff

def store_file(s3client, fname, file_contents, meta):
    log.info('Puttin in s3 under bucket %s with key %s', meta['processed_file_bucket'], fname)
    s3client.put_object(Body=file_contents, Bucket=meta['processed_file_bucket'], Key=fname)
    log.info('Put in s3 under bucket %s with key %s', meta['processed_file_bucket'], fname)

def delete_raw_file(s3client, s3key, meta):
    log.info('Deleting %s from %s', s3key, meta['raw_file_bucket'])
    s3client.delete_object(Bucket=meta['raw_file_bucket'], Key=s3key)

def unpack_and_convert(job_key, s3key, s3client, redis, meta):
    redis.hset(job_key, REDIS.STEP_KEY, 'UNPACKING')
    unpacked_files = unpack(s3key, s3client, redis, meta)
    redis.hset(job_key, REDIS.STEP_KEY, 'UNPACK_DONE')
    log.info('Done unpacking job %s', job_key)

    for fname, data in unpacked_files:
        if not fname.lower().endswith('mobi'):
            redis.hset(job_key, REDIS.STEP_KEY, 'CONVERTING')
            redis.hset(job_key, REDIS.STATE_KEY, fname)
            log.info('Asked to store %s, need to convert first', fname)
            fname_no_ext, ext = os.path.splitext(fname)
            with tempfile.NamedTemporaryFile(suffix=ext) as original:
                original.write(data)
                original.flush()
                converted_data = convert_to_mobi(original.name)
                data = converted_data
            fname = fname_no_ext + '.mobi'
        store_file(s3client, fname, data, meta)

    delete_raw_file(s3client, s3key, meta)
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
    setup_logger()
    s3client = s3.client()
    while True:
        log.info('Waiting for message on %s', REDIS.Q_UNPACK_FILE)
        topic, message = r.blpop(REDIS.Q_UNPACK_FILE)

        log.info('got message: %s', message)
        params = json.loads(message.decode('utf-8'))
        log.info('params for unpacker: %s', params)
        params['s3client'] = s3client
        params['redis'] = r

        t = Thread(target=unpack_and_convert, kwargs=params)
        t.daemon = True
        t.start()

main()
