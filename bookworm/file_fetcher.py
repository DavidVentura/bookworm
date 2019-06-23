import json
import socket
import sys
import time
from threading import Thread
from bookworm.constants import RAW_FILE_BUCKET, REDIS_UNPACK_FILE, REDIS_FETCH_FILE
from bookworm.logger import log, setup_logger
from bookworm import s3

import redis

def netcat(filename, ip, port, size, job_key, s3client, redis):
    log.info('netcat: %s %d %d %s', ip, port, size, filename)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    log.info("Fetching %s", filename)
    s.connect((ip, port))
    log.info("Receiving file %s", filename)

    buff = b''
    count = 0
    last_perc = 0
    while True:
        data = s.recv(16384)
        if len(data) == 0:
            log.info("No data received - finished")
            break
        count += len(data)
        buff += data
        perc = int(100 * count / size)
        if perc % 5 == 0 and perc != last_perc:
            log.info("Download percentage: %d", perc)
            # TODO set_job_state(job_key, 'DOWNLOADING', "%d%%" % perc)
            last_perc = perc
        if count >= size:
            break
    log.info("Download complete")
    s.close()
    log.info("Putting file in s3")
    # TODO set_job_state(job_key, 'DOWNLOAD_DONE', job_key)
    s3client.put_object(Body=buff, Bucket=RAW_FILE_BUCKET, Key=job_key)
    log.info("File %s in s3 with key %s", filename, job_key)
    redis.rpush(REDIS_UNPACK_FILE, json.dumps({'job_key': job_key}))

def main():
    r = redis.StrictRedis(host='localhost', port=6379)
    setup_logger()

    while True:
        log.info('Waiting for message...')
        topic, message = r.blpop(REDIS_FETCH_FILE)

        log.info('got message: %s', message)
        params = json.loads(message.decode('utf-8'))
        log.info('params for netcat: %s', params)
        params['s3client'] = s3.client()
        params['redis'] = r

        t = Thread(target=netcat, kwargs=params)
        t.daemon = True
        t.start()

main()
