import sys
import json
import os
from http.server import HTTPServer
from socketserver import ThreadingMixIn
from httphandler import RHandler
import garage
import xpaxos
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    px = None
    def set_conf(self,list_of_address,me):
        self.px = xpaxos.MyPaxos.MyPaxos(list_of_address, me)

def run(handler_class, me):
    with open('conf/settings.conf') as f:
        settings = json.load(f)
        list_of_address=[]
        for i in range(1,len(settings)+1):
            if 'n0'+str(i) in settings:
                list_of_address.append(settings['n0'+str(i)])
        server_class = ThreadedHTTPServer
        server_address = ('localhost',8000+me)
        httpd = server_class(server_address,handler_class)
        httpd.set_conf(list_of_address,me-1)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            httpd.server_close()
if __name__ == '__main__':
    if len(sys.argv)>1:
        me=int(sys.argv[1])
    else:
        me=1
    run(RHandler,me)
