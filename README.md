# Requirements

* S3 (minio can be used for a local instance).
* redis
* sqlite
* python3.6

# Services

## Diagram

![](docs/services.png)

## Installation

```
sudo cp services/bookworm@.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start bookworm@ircclient.service
sudo systemctl start bookworm@file_fetcher.service
sudo systemctl start bookworm@unpacker.service
sudo systemctl start bookworm@web.service
sudo systemctl start bookworm@db_cache_populate.service
```

## IRC Client
In charge of processing received commands and sending them via IRC.  
Will forward details from DCC to the file fetcher via redis.

## File fetcher
In charge of fetching files specified via DCC.  
Will store the file in S3 and notify file details to the unpacker.

## Unpacker
In charge of taking a file (as provided from IRC), unpacking it and, if necessary, converting it to `mobi`.

## Web

### API

* Lists jobs in progress (`/books/status`)
* Serves available books (Anything in the S3 bucket)
* Exposes a search endpont `/book/search?terms=...`
* Fetches books via `/book/fetch/`


### Web interface
TODO

### Basic (Kindle) Web interface
The kindle has a very basic webbrowser (I believe it renders up to HTML4, CSS2.1), which can be used to download (available) books directly.  
At the moment I re-route at nginx based on user agent

To test, you can use `dillo` which has a set of features similar to the kindle's web browser.

```
if ($http_user_agent ~* "armv7l") {
    rewrite ^/(.*)$ /books/kindle;
}
```

# Batch process

To remove the initial roundtrip when searching for books, I keep a cache in a
local sqlite database.  
To populate this cache, there's an API endpoint (`books/batch_update`) that triggers each bot's `LIST` command, at `#ebooks`

# CLI

For now, you can control this via HTTP.

```bash
$ # populate the index, only once in a while for new books
$ http POST localhost:5000/books/batch_update
$ # search the book that you want
$ http localhost:5000/book/search terms=='brandon sanderson'
$ # download book, will be placed in the S3 bucket
$ http POST localhost:5000/book/fetch bot=Pondering42 book="some-book-from the
index"
```

# TODO

* Proper status of requests in progress
* Web UI 

# Misc

To update the graph in the README
```
$ dot docs/services.dot -Tpng > docs/services.png
```
