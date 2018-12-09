#!/usr/bin/env python3.7
import logging
import shlex
import readline
import os
from collections.abc import Iterable

from bookclient import BookClient

histfile = os.path.join(os.path.expanduser("~"), ".book_history")

def usage():
    print("USAGE:")
    print("\t SEARCH <BOOK>")
    print("\t BOOK <BOT COMMAND>")

def cb(arg):
    print("Called callback!")
    if isinstance(arg, Iterable):
        for item in arg:
            print(item)
    else:
        print(arg)

def main():
    b = BookClient(cb)
    while True:
        line = input('> ').strip().lower()
        try:
            split = shlex.split(line)
        except Exception as e:
            print(e)
            continue

        if len(split) == 0:
            continue

        mode = split[0]
        query = " ".join(split[1:])
        b.request(mode, query)


if __name__ == "__main__":
    try:
        readline.read_history_file(histfile)
        # default history len is -1 (infinite), which may grow unruly
        readline.set_history_length(10000)
    except FileNotFoundError:
        pass

    try:
        main()
    except KeyboardInterrupt:
        print("\nBye")
    except EOFError:
        print("\nBye")
    readline.write_history_file(histfile)
