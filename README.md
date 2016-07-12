# CLI

```bash
$ ./bot.py
USAGE:
	./bot.py SEARCH <BOOK> <FORMAT>
	./bot.py BOOK <BOT COMMAND>

$ ./bot.py SEARCH "revival stephen king" "epub"
Looking (SEARCH) for revival stephen king in format epub
connected
Joined channel #ebooks
searching for revival stephen king
!Trainfiles Stephen King - Revival (epub).rar  ::INFO:: 395.0KB
!Trainfiles Stephen King - Revival (retail) (epub).rar  ::INFO:: 1.4MB
!Xon Stephen King - Revival (retail) (epub).rar
!Xon Stephen King - Revival (epub).rar
!Ook Stephen King - Revival (epub).rar  ::INFO:: 395.0KB
!Ook Stephen King - Revival (retail) (epub).rar  ::INFO:: 1.4MB
!Mysfyt Stephen King - Revival (epub).rar  ::INFO:: 395.0KB
!Mysfyt Stephen King - Revival (retail) (epub).rar  ::INFO:: 1.4MB
!Pondering Stephen King - Revival (epub).rar  ::INFO:: 395.0KB
!Pondering Stephen King - Revival (retail) (epub).rar  ::INFO:: 1.4MB
closed

$ ./bot.py BOOK "\!Ook Stephen King - Revival (epub).rar  ::INFO:: 395.0KB"
Downloading !Ook Stephen King - Revival (epub).rar  ::INFO:: 395.0KB
connected
Joined channel #ebooks
Asking for '!Ook Stephen King - Revival (epub).rar  ::INFO:: 395.0KB'
Receiving file
100%
Files: 
['/tmp/Stephen King - Revival (epub).epub']
closed
```

Note: Most likely you'll have to escape '!' on your shell.


# Basic Web interface
Work in progress
##Screenshots

Waiting for a list of books that match the query
![1](/screenshots/1.png?raw=true)

Selecting a book from the list
![2](/screenshots/2.png?raw=true)

Waiting for the book to download ( to the server )
![3](/screenshots/3.png?raw=true)

Downloading the book
![4](/screenshots/4.png?raw=true)

