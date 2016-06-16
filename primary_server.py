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
    def set_conf(self):
        tmp=['http://localhost:8001','http://localhost:8002']
        self.px = xpaxos.MyPaxos.MyPaxos(tmp, 0)
#    backup_address = None
#    backup_port = None
#    def set_backup(self,a,p):
#        self.backup_address=a
#        self.backup_port=p

def run(handler_class, address , portnumber ):
    server_class = ThreadedHTTPServer
    server_address = (address,portnumber)
    httpd = server_class(server_address,handler_class)
    httpd.set_conf()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()
run(RHandler,'localhost',8001)
