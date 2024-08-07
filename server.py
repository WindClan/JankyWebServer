import socketserver
from datetime import datetime
from http import HTTPStatus
import mimetypes
import threading
import platform
import re
import os

cacheFiles = not os.path.exists(".DISABLECACHE")
pageCache = {}
errorPageCache = {}

serverName = b"JankyWebServer/2.0 Python/"+platform.python_version().encode('cp1252')

def sanitizeUrl(dirtyUrl):
    dirtyUrl = re.sub("[^A-Za-z0-9\/\.\-_]+","",dirtyUrl.split("?")[0])
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
        return b"<h1>Error "+code.encode('cp1252')+b"</h1>\n"+str(exception).encode('cp1252')

def sendResponse(socket,content,isNewHttp=False,status=HTTPStatus.OK):
    header = b""
    if isNewHttp:
        header = header+b"HTTP/1.0 "+(str(status.value)+" "+status.phrase).encode('cp1252')+b"\n"
        header = header+b"Date: "+datetime.now().strftime("%a, %d %b %Y %X %Z").encode('cp1252')+b"\n"
        header = header+b"Server: "+serverName+b"\n"
        if status == 405:
            header = header+b"Allow: GET"
        header = header+b"\n"
    socket.send(header+content)

class LegacyWebServer(socketserver.BaseRequestHandler):
    def handle(self):
        ip = self.request.getpeername()[0]
        request = self.request.recv(1024).strip()
        isNewHttp = False
        if request != None:
            req = request.split()
            if len(req) > 0:
                if req[0] == b"GET":
                    path = "/"
                    try:
                        if len(req) > 1:
                            path = req[1].decode('cp1252')
                        if len(req) > 2:
                            isNewHttp = True
                        if path == "/" or path[-1] == "/":
                            path = path+"index.html"
                        path = sanitizeUrl(path)
                        if cacheFiles and path in pageCache :
                            sendResponse(self.request,pageCache[path],isNewHttp,HTTPStatus.OK)
                            print(str(ip)+" GET "+path+" - cached")
                        elif os.path.exists("webroot"+path) and os.access("webroot"+path, os.R_OK):
                            file = open("webroot"+path,"rb")
                            content = file.read()
                            file.close()
                            if cacheFiles and not path in pageCache:
                                pageCache[path] = content
                            sendResponse(self.request,content,isNewHttp,HTTPStatus.OK)
                            print(str(ip)+" GET "+path)
                        else:
                            sendResponse(self.request,getErrorPage("notfound"),isNewHttp,HTTPStatus.NOT_FOUND)
                            print(str(ip)+" GET "+path+" - Not found")
                    except Exception as e:
                        print(e)
                        sendResponse(self.request,getErrorPage("servererror"),isNewHttp,HTTPStatus.INTERNAL_SERVER_ERROR)
                        print(str(ip)+" GET "+path+" - Internal server error")
                else:
                    print(str(ip)+" - Unsupported request type")
                    sendResponse(self.request,getErrorPage("unsupported"),True,HTTPStatus.METHOD_NOT_ALLOWED)
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
    with socketserver.ThreadingTCPServer(("", 80), LegacyWebServer) as server:
        server.serve_forever()
