# JankyWebServer - Implementation of HTTP/0.9 and HTTP/1.0 in python

HTTP/1.0 server written in python, I tried to make it as fast and stable as possible

It *should* be secure but I personally wouldn't trust a Python socket server on the public web

It implements basic features like custom error screens and page caching but not much else.

If you need page caching disabled you can create a file named `.DISABLECACHE` in the same directory as server.py