import json
import socket
import sys
import time
import tempfile
from threading import Thread
from subprocess import check_output
from bookworm import s3
from bookworm.logger import log, setup_logger
from bookworm.constants import RAW_FILE_BUCKET, PROCESSED_FILE_BUCKET, UNPACKABLE_EXTENSIONS, REDIS_UNPACK_FILE
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

def store_file(s3client, fname, file_contents):
    log.info('Puttin in s3 under bucket %s with key %s', PROCESSED_FILE_BUCKET, fname)
    s3client.put_object(Body=file_contents, Bucket=PROCESSED_FILE_BUCKET, Key=fname)
    log.info('Put in s3 under bucket %s with key %s', PROCESSED_FILE_BUCKET, fname)

def delete_raw_file(s3client, job_key):
    log.info('Deleting %s from %s', job_key, RAW_FILE_BUCKET)
    s3client.delete_object(Bucket=RAW_FILE_BUCKET, Key=job_key)

def unpack(job_key, s3client, redis):
    log.info('Got a request to unpack %s', job_key)
    data = s3client.get_object(Key=job_key, Bucket=RAW_FILE_BUCKET)
    with tempfile.NamedTemporaryFile() as fd:
        raw_file_contents = data['Body'].read()
        fd.write(raw_file_contents)
        fd.flush()

        if should_unpack(job_key):
            to_extract = archive_contents(fd)
        else:
            log.info("Not unpacking %s", job_key)
            store_file(s3client, job_key, raw_file_contents)
            delete_raw_file(s3client, job_key)
            return

        if not to_extract:
            log.info(contents['lsarContents'])
            log.error("Could not find any valid file")
            return

        for index, fname in to_extract.items():
            log.info('Processing %s %s', index, fname)
            file_contents = check_output(['unar', '-o', '-', '-i', fd.name, str(index)])
            log.info('Got %d bytes', len(file_contents))
            store_file(s3client, fname, file_contents)

    # TODO set_job_state(job_key, 'UNPACK_DONE', job_key)
    delete_raw_file(s3client, job_key)
    log.info('Done with job %s', job_key)

def main():
    r = redis.StrictRedis(host='localhost', port=6379)
    setup_logger()
    s3client = s3.client()
    while True:
        log.info('Waiting for message...')
        topic, message = r.blpop(REDIS_UNPACK_FILE)

        log.info('got message: %s', message)
        params = json.loads(message.decode('utf-8'))
        log.info('params for unpacker: %s', params)
        params['s3client'] = s3client
        params['redis'] = r

        t = Thread(target=unpack, kwargs=params)
        t.daemon = True
        t.start()

main()
