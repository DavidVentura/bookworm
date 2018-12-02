#!/usr/bin/env python3.7
import queue
import shlex
import sys

from ircclient import IRCClient, MODE_SEARCH, MODE_BOOK

def usage():
    print("USAGE:")
    print("\t SEARCH <BOOK> <FORMAT>")
    print("\t BOOK <BOT COMMAND>")

def main():
    q = queue.Queue()
    client = IRCClient(q)
    client.start()

    for line in sys.stdin:
        line = line.strip().lower()
        try:
            split = shlex.split(line)
        except Exception as e:
            print(e)
            continue

        if len(split) < 2 or len(split) > 3 or split[0].lower() not in [MODE_SEARCH, MODE_BOOK]:
            usage()
            continue

        mode = split[0]
        query = split[1]
        grep = ""
        if len(split) == 3:
            grep = split[2]
        data = {'query': query, 'mode': mode, 'grep': grep}
        q.put(data)
    client.join()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBye")
