import json
import sys
from bookworm.constants import REDIS_BOOK_COMMANDS

import pg_simple
import redis

bot = sys.argv[1]
book = sys.argv[2]

r = redis.StrictRedis(host='localhost', port=6379)
r.rpush(REDIS_BOOK_COMMANDS, json.dumps({'bot': bot, 'book': book}))
