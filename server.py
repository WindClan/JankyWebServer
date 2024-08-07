import socketserver
import threading
import re
import os

cacheFiles = not os.path.exists(".DISABLECACHE")
pageCache = {}
errorPageCache = {}

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
class LegacyWebServer(socketserver.BaseRequestHandler):
    def handle(self):
        ip = self.request.getpeername()[0]
        request = self.request.recv(1024).strip()
        if request != None:
            req = request.split()
            if len(req) > 0:
                if req[0] == b"GET":
                    path = "/"
                    try:
                        if len(req) > 1:
                            path = req[1].decode('cp1252')
                        if path == "/" or path[-1] == "/":
                            path = path+"index.html"
                        path = sanitizeUrl(path)
                        if cacheFiles and path in pageCache :
                            self.request.send(pageCache[path])
                            print(str(ip)+" GET "+path+" - cached")
                        elif os.path.exists("webroot"+path) and os.access("webroot"+path, os.R_OK):
                            file = open("webroot"+path,"rb")
                            content = file.read()
                            file.close()
                            self.request.send(content)
                            print(str(ip)+" GET "+path)
                            if cacheFiles and (not path in pageCache or pageCache[path] != content):
                                pageCache[path] = content
                        else:
                            self.request.send(getErrorPage("notfound"))
                            print(str(ip)+" GET "+path+" - Not found")
                    except Exception as e:
                        print(e)
                        print(str(ip)+" GET "+path+" - Internal server error")
                        self.request.send(getErrorPage("servererror"))
                else:
                    print(str(ip)+" - Unsupported request type")
                    self.request.send(getErrorPage("unsupported"))
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
