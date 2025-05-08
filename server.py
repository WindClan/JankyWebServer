# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import socketserver
from datetime import datetime
from http import HTTPStatus
import psutil
import gzip
import magic
import threading
import platform
import time
import re
import os

cacheFiles = not os.path.exists(".DISABLECACHE")
pageCache = {}
errorPageCache = {}

serverName = "JankyWebServer/4.1 Python/"+platform.python_version()

def sanitizeUrl(dirtyUrl):
    dirtyUrl = re.sub("[^A-Za-z0-9\\/\\.\\-_]+","",dirtyUrl.split("?")[0])
    newUrl = ""
    parts = re.findall("[^/]+",dirtyUrl)
    result = []
    for part in parts:
        if part == ".." and len(result) > 0:
           result.pop(len(result)-1)
        elif part != ".." and part != ".":
             result.append(part)
    for part in result:
        newUrl = newUrl+"/"+part
    if newUrl == "":
        newUrl = "/index.html"
    return newUrl
def createDir(dir):
    if not os.path.exists(dir):
        os.mkdir(dir)
def encode(string):
    return string.encode('iso-8859-1')
def getErrorPage(code,exception=""):
    if cacheFiles and code in errorPageCache:
        return errorPageCache[code]
    elif os.path.exists("weberrors/"+code+".html"):
        file = open("weberrors/"+code+".html","rb")
        content = file.read()
        file.close()
        return content
    else:
        return b"<h1>Error "+encode(code)+b"</h1>\n"+encode(str(exception))
def parseHeaders(reqString):
    newReq = reqString.decode('iso-8859-1')
    headers = newReq.split('\r\n')
    returnHeaders = {}
    headers.pop(0)
    for i in headers:
        new = i.lower().split(':',1)
        returnHeaders[new[0]] = new[1]
    return returnHeaders
def redoErrorCache():
    while True:
        time.sleep(60)
        for fileName in os.listdir("weberrors"):
            path = "weberrors/"+fileName
            file = open(path,"rb")
            content = file.read()
            file.close()
            errorPageCache[fileName.split(".")[0]] = content
def cullCaching():
    while True:
        time.sleep(7.5)
        time2 = datetime.now().timestamp()
        if psutil.virtual_memory().available < 536870912:
            for i, _ in enumerate(data.copy()):
                data.pop(i)
        for i,v in pageCache.copy().items():
            if time2-v["age"] >= 45:
                pageCache.pop(i)
class JankyWebServer(socketserver.BaseRequestHandler):
    reqHeaders = {}
    respHeaders = {}
    def addHeader(self,header1,header2):
        self.respHeaders[encode(header1)] = encode(header2)
    def sendResponse(self,content,isNewHttp=False,status=HTTPStatus.OK, modifiedDate=None):
        header = b""
        if isNewHttp:
            header = header+b"HTTP/1.1 "+encode(str(status.value)+" "+status.phrase)+b"\r\n"
            self.addHeader("Date",datetime.now().strftime("%a, %d %b %Y %X %Z"))
            self.addHeader("Server",serverName)
            self.addHeader("Content-Type",magic.from_buffer(content,mime=True))
            if len(content) >= 1350 and 'accept-encoding' in self.reqHeaders and (self.reqHeaders['accept-encoding'] == "*" or self.reqHeaders['accept-encoding'].find('gzip') != -1):
                self.addHeader("Content-Encoding","gzip")
                content = gzip.compress(content)
            self.addHeader("Content-Length",str(len(content)))
            if not cacheFiles:
                self.addHeader("Cache-Control","no-store")
            else:
                self.addHeader("Cache-Control","max-age=86400")
            self.addHeader("Connection","close")
            for key, value in self.respHeaders.items():
                header = header+key+b": "+value+b"\r\n"
            header = header+b"\r\n"
        self.request.send(header+content)
    def handle(self):
        ip = self.request.getpeername()[0]
        request = self.request.recv(8190).strip()
        isNewHttp = False
        if request != None and len(request) > 0:
            if request[0:3] == b"GET":
                req = request.split()
                self.reqHeaders = parseHeaders(request)
                path = "/"
                try:
                    if len(req) > 1:
                        path = req[1].decode('iso-8859-1')
                    if len(req) > 2:
                        isNewHttp = True
                    if path == "/" or path[-1] == "/":
                        path = path+"index.html"
                    path = sanitizeUrl(path)
                    canAccess = False
                    if cacheFiles and not path in pageCache and os.path.exists("webroot"+path) and not os.access("webroot"+path, os.R_OK):
                        for i in range(1,15):
                            if os.access("webroot"+path, os.R_OK):
                                canAccess = True
                                break
                            else:
                                time.sleep(1/2)
                    if cacheFiles and path in pageCache:
                        self.sendResponse(pageCache[path]["page"],isNewHttp,HTTPStatus.OK)
                        print(str(ip)+" GET "+path+" - cached")
                    elif os.path.exists("webroot"+path) and os.access("webroot"+path, os.R_OK):
                        file = open("webroot"+path,"rb")
                        content = file.read()
                        file.close()
                        if cacheFiles and psutil.virtual_memory().available > len(content)+536870912:
                            pageCache[path] = {
                                "page": content,
                                "age": datetime.now().timestamp()
                            }
                        self.sendResponse(content,isNewHttp,HTTPStatus.OK)
                        print(str(ip)+" GET "+path)
                    elif os.path.exists("webroot"+path) and not canAccess:
                        self.sendResponse(getErrorPage("unavailable"),isNewHttp,HTTPStatus.SERVICE_UNAVAILABLE)
                        print(str(ip)+" GET "+path+" - Unable to open file")
                    else:
                        self.sendResponse(getErrorPage("notfound"),isNewHttp,HTTPStatus.NOT_FOUND)
                        print(str(ip)+" GET "+path+" - Not found")
                except Exception as e:
                    print(e)
                    self.sendResponse(getErrorPage("servererror"),isNewHttp,HTTPStatus.INTERNAL_SERVER_ERROR)
                    print(str(ip)+" GET "+path+" - Internal server error")
            else:
                print(str(ip)+" - Unsupported request type")
                self.addHeader("Allow","GET")
                self.sendResponse(getErrorPage("unsupported"),True,HTTPStatus.METHOD_NOT_ALLOWED)
        self.request.close()
createDir("webroot")
createDir("weberrors")
if cacheFiles:
    for fileName in os.listdir("weberrors"):
        path = "weberrors/"+fileName
        file = open(path,"rb")
        content = file.read()
        file.close()
        errorPageCache[fileName.split(".")[0]] = content
if __name__ == "__main__":
    x = threading.Thread(target=cullCaching)
    x2 = threading.Thread(target=redoErrorCache)
    x.start()
    x2.start()
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("", 80), JankyWebServer) as server:
        print("Server started on port 80!")
        server.serve_forever()
