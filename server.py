# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import socketserver
from datetime import datetime
from http import HTTPStatus
import magic
import threading
import platform
import re
import os

cacheFiles = not os.path.exists(".DISABLECACHE")
pageCache = {}
errorPageCache = {}

serverName = b"JankyWebServer/3.0 Python/"+platform.python_version().encode('iso-8859-1')

def sanitizeUrl(dirtyUrl):
    dirtyUrl = re.sub("[^A-Za-z0-9\\/\\.\\-_]+","",dirtyUrl.split("?")[0])
    newUrl = ""
    parts = re.findall("[^/]+",dirtyUrl)
    result = []
    for part in parts:
        if part == ".." and len(result) > 0:
           result[len(result)-1] = None
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
def getErrorPage(code,exception=""):
    if cacheFiles and code in errorPageCache:
        return errorPageCache[code]
    elif os.path.exists("weberrors/"+code+".html"):
        file = open("weberrors/"+code+".html","rb")
        content = file.read()
        file.close()
        return content
    else:
        return b"<h1>Error "+code.encode('iso-8859-1')+b"</h1>\n"+str(exception).encode('iso-8859-1')

class JankyWebServer(socketserver.BaseRequestHandler):
    def sendResponse(self,content,isNewHttp=False,status=HTTPStatus.OK):
        header = b""
        if isNewHttp:
            header = header+b"HTTP/1.0 "+(str(status.value)+" "+status.phrase).encode('iso-8859-1')+b"\r\n"
            header = header+b"Date: "+datetime.now().strftime("%a, %d %b %Y %X %Z").encode('iso-8859-1')+b"\r\n"
            header = header+b"Server: "+serverName+b"\r\n"
            header = header+b"Content-Type: "+magic.from_buffer(content,mime=True).encode('iso-8859-1')+b"\r\n"
            if status == 405:
                header = header+b"Allow: GET\r\n"
            header = header+b"\r\n"
        self.request.send(header+content)
    def handle(self):
        ip = self.request.getpeername()[0]
        request = self.request.recv(8190).strip()
        isNewHttp = False
        if request != None:
            req = request.split()
            if len(req) > 0:
                if req[0] == b"GET":
                    path = "/"
                    try:
                        if len(req) > 1:
                            path = req[1].decode('iso-8859-1')
                        if len(req) > 2:
                            isNewHttp = True
                        if path == "/" or path[-1] == "/":
                            path = path+"index.html"
                        path = sanitizeUrl(path)
                        if cacheFiles and path in pageCache :
                            self.sendResponse(pageCache[path],isNewHttp,HTTPStatus.OK)
                            print(str(ip)+" GET "+path+" - cached")
                        elif os.path.exists("webroot"+path) and os.access("webroot"+path, os.R_OK):
                            file = open("webroot"+path,"rb")
                            content = file.read()
                            file.close()
                            if cacheFiles and not path in pageCache:
                                pageCache[path] = content
                            self.sendResponse(content,isNewHttp,HTTPStatus.OK)
                            print(str(ip)+" GET "+path)
                        else:
                            self.sendResponse(getErrorPage("notfound"),isNewHttp,HTTPStatus.NOT_FOUND)
                            print(str(ip)+" GET "+path+" - Not found")
                    except Exception as e:
                        print(e)
                        self.sendResponse(getErrorPage("servererror"),isNewHttp,HTTPStatus.INTERNAL_SERVER_ERROR)
                        print(str(ip)+" GET "+path+" - Internal server error")
                else:
                    print(str(ip)+" - Unsupported request type")
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
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("", 80), JankyWebServer) as server:
        print("Server started on port 80!")
        server.serve_forever()
