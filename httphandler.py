import io
import os
import shutil
import socket # For gethostbyaddr()
import sys
import time
import re
import signal
import threading
import json
import xmlrpc.client
from urllib.parse import unquote_plus
import requests
import collections

from http import HTTPStatus

from http.server import BaseHTTPRequestHandler

import garage

class RHandler(BaseHTTPRequestHandler):

    """HTTP request handler with GET and HEAD and POST commands.

    This serves files from the current directory and any of its
    subdirectories.  The MIME type for files is determined by
    calling the .guess_type() method.

    The GET and HEAD requests are identical except that the HEAD
    request omits the actual contents of the file.

    """
#self.server
    server_version = "GeruiHTTP/0.0.4"
    backup_address = None
    backup_port = None
    proxy = None

    def do_GET(self):
        """Serve a GET request."""
        f = self.simple_get()
        try:
            self.copyfile(f, self.wfile)
        finally:
            f.close()

    def do_HEAD(self):
        """Serve a HEAD request."""
        f = self.send_head()
        if f:
            f.close()

    def do_POST(self):
        if self.path.startswith('/kv'):
            f = self.simple_post()
            try:
                self.copyfile(f, self.wfile)
            finally:
                f.close()
        elif self.path.startswith('/paxos'):
            f = self.str2file('I have got your message, and I am working on it.')
            try:
                self.copyfile(f, self.wfile)
            finally:
                f.close()
            self.paxos_post()
        else:
            f = self.str2file('Test<br>Client address: '+str(self.client_address)+'<br>Thread: '+threading.currentThread().getName())
            try:
                self.copyfile(f, self.wfile)
            finally:
                f.close()
    
    def simple_get(self):
        if self.path == '/kvman/shutdown':
            pass

        if self.path == '/kvman/countkey':
            with garage.mutex:
                f = self.str2file('{"result": "'+str(garage.countkey())+'"}')
            return f
        if self.path == '/kvman/dump':
            with garage.mutex:
                f = self.dict2file(garage.dump())
            return f
        if self.path == '/kvman/gooddump':
            with garage.mutex:
                f = self.str2file('{"main_mem": '+json.dumps(garage.main_mem)+', "time_stamp": "'+str(garage.get_time_stamp())+'"}')
                garage.clear_fail_backup()
            return f
        if self.path == '/':
            return self.str2file('Test<br>Client address: '+str(self.client_address)+'<br>Thread: '+threading.currentThread().getName())
        pattern = re.compile('/kv/get\?key=(?P<the_key>.+)')
        m = pattern.match(self.path)
        if m:
            the_key = m.group('the_key')
            the_key = unquote_plus(the_key)
            rw_lock = garage.get_rw_create(the_key)
            rw_lock.before_read()
            ret = garage.get(the_key)
            f = self.str2file('{"success":"'+str(ret[0]).lower()+'","value":'+json.dumps(ret[1])+'}')
            rw_lock.after_read()
            return f
        return self.str2file('{"success":"false"}')

    def process_post_data(self):
        length = self.headers.get('content-length')
        try:
            nbytes = int(length)
        except (TypeError, ValueError):
            nbytes = 0
        if nbytes >0:
            data = self.rfile.read(nbytes) # data is bytes not string
        else:
            return ''
        ret = data.decode(sys.getfilesystemencoding()).split('&')
        return ret
    
    def paxos_post(self):
        if self.path == '/paxos/start':
            self.server.px.start('some value')
        elif self.path == '/paxos/propose' or self.path == '/paxos/promise' or self.path == '/paxos/accept' or self.path == '/paxos/ack' or self.path == '/paxos/commit':
            inputs = self.process_post_data()
            msg=[None] * len(inputs)
            for tmpstr in inputs:
                tmpinput = tmpstr.split('=')
                if tmpinput[0].startswith('msg'):
                    tmpi = int(tmpinput[0][3:])
                    msg[tmpi] = unquote_plus(tmpinput[1]) # strip msg0=
            if msg[0]=='propose':
                msg[1]=int(msg[1])
                msg[2]=int(msg[2])
            elif msg[0]=='promise':
                msg[1]=int(msg[1])
                msg[2]=int(msg[2])
                msg[3]=int(msg[3])
            elif msg[0]=='accept':
                msg[1]=int(msg[1])
                msg[2]=int(msg[2])
            elif msg[0]=='ack':
                msg[1]=int(msg[1])
                msg[2]=int(msg[2])
            elif msg[0]=='commit':
                msg[1]=int(msg[1])
            self.server.px.receive(msg)
#if self.path == '/paxos/propose':
    
    def simple_post(self):
        the_key=None
        the_value=None
        inputs = self.process_post_data()
        for tmpstr in inputs:
            tmpinput = tmpstr.split('=')
            if tmpinput[0]=='key':
                the_key=unquote_plus(tmpinput[1])
            elif tmpinput[0]=='value':
                the_value=unquote_plus(tmpinput[1])
        #print(str(data))
        #print('the key and value are',the_key,the_value)
        return self.str2file('{"success":"false"}')

    def copyfile(self, source, outputfile):
        """Copy all data between two file objects.

        The SOURCE argument is a file object open for reading
        (or anything with a read() method) and the DESTINATION
        argument is a file object open for writing (or
        anything with a write() method).

        The only reason for overriding this would be to change
        the block size or perhaps to replace newlines by CRLF
        -- note however that this the default server uses this
        to copy binary data as well.

        """
        shutil.copyfileobj(source, outputfile)


    def dict2file(self,d):
        ''' d is dictionary, similar to str2file(). by wgr'''
        r = []
        enc = sys.getfilesystemencoding()
        od = collections.OrderedDict(sorted(d.items()))
        for key,value in od.items():
            r.append('['+json.dumps(key)+','+json.dumps(value)+']')
        the_string = '['+', '.join(r)+']'
        encoded = the_string.encode(enc, 'surrogateescape')
        f = io.BytesIO()
        f.write(encoded)
        f.seek(0)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-type", "text/html; charset=%s" % enc)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        return f

    def str2file(self,word):
        ''' print string to a file by wgr'''
        enc = sys.getfilesystemencoding()        
        encoded = word.encode(enc, 'surrogateescape')
        f = io.BytesIO()
        f.write(encoded)
        f.seek(0)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-type", "text/html; charset=%s" % enc)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        return f

