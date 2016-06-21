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
from urllib.parse import urlparse
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

    def do_GET(self):
        """Serve a GET request."""
        if self.server.deadpool and self.path != '/kvman/restart':
            return
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
        if self.server.deadpool:
            return        
        if self.path.startswith('/kv'):
            f = self.kv_post()
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
        if self.path == '/kvman/stop':
            self.server.deadpool = True
        if self.path == '/kvman/restart':
            self.server.deadpool = False

        elif self.path == '/kvman/countkey':
            with garage.mutex:
                f = self.str2file('{"result": "'+str(garage.countkey())+'"}')
            return f
        elif self.path == '/kvman/dump':
            with garage.mutex:
                f = self.dict2file(garage.dump())
            return f
        elif self.path == '/kvman/kvpaxos':
            s=self.server.px.show_off()
            #print(s)
            return self.str2file('<br>\n'.join(s))
        elif self.path == '/':
            return self.str2file('This address: '+str(self.server.server_address)+'<br>Client address: '+str(self.client_address)+'<br>Thread: '+threading.currentThread().getName())
        p = urlparse(self.path)
        if p.path == '/kv/get':
            the_key = None
            the_requestid = None
            for tmpstr in p.query.split('&'):
                tmpinput = tmpstr.split('=')
                if tmpinput[0]=='key':
                    the_key = unquote_plus(tmpinput[1])
                elif tmpinput[0]=='requestid':
                    the_requestid=unquote_plus(tmpinput[1])
            if garage.request_id_test(the_requestid) and the_key:
                payload={'action':'get','key':the_key,'requestid':the_requestid}
                px = self.server.px
                while True:
                    seq = px.get_max()+1
                    px.start(json.dumps(payload),seq)
                    # wait for finish
                    timeslp=0.01
                    tmp_status = px.kv_status(seq)
                    while tmp_status is not None and not tmp_status['decided']:
                        time.sleep(timeslp) # something like timeout
                        if timeslp<1.0:
                            timeslp*=2
                        tmp_status = px.status(seq)
                    action_status = px.action_status(seq)
                    if action_status:
                        px.do_kv_actions(seq)
                        ret = px.kv_status(seq)# note that tmp_status might not be in format of get, thus we need action_status
                        garage.request_id_add(the_requestid)
                        return  self.str2file('{"success":"'+str(ret[0]).lower()+'","value":'+json.dumps(ret[1])+'}')
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
        if self.path == '/paxos/propose' or self.path == '/paxos/promise' or self.path == '/paxos/accept' or self.path == '/paxos/ack' or self.path == '/paxos/commit':
            inputs = self.process_post_data()
            msg=[None] * (len(inputs)-1) #cuz we have seq that is not in msg
            seq=None
            for tmpstr in inputs:
                tmpinput = tmpstr.split('=')
                if tmpinput[0].startswith('msg'):
                    tmpi = int(tmpinput[0][3:])
                    msg[tmpi] = unquote_plus(tmpinput[1]) # strip msg0=
                elif tmpinput[0]=='seq':# and tmpinput[1].isdecimal():
                    seq=int(tmpinput[1])
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
            self.server.px.receive(msg,seq)
        elif self.path == '/paxos/done/ask':
            inputs = self.process_post_data()
            asker=None
            for tmpstr in inputs:
                tmpinput = tmpstr.split('=')
                if tmpinput[0] == 'asker':
                    asker = int(tmpinput[1])
            px = self.server.px
            px.answer_done(asker)
        elif self.path == '/paxos/done/answer':
            inputs = self.process_post_data()
            answerer=None
            lo=None
            for tmpstr in inputs:
                tmpinput = tmpstr.split('=')
                if tmpinput[0] == 'answerer':
                    answerer = int(tmpinput[1])
                elif tmpinput[0] == 'min':
                    lo = int(tmpinput[1])
            px = self.server.px
            px.receive_done(lo,answerer)
    
    def kv_post(self):
        the_key=None
        the_value=None
        the_requestid=None
        inputs = self.process_post_data()
        for tmpstr in inputs:
            tmpinput = tmpstr.split('=')
            if tmpinput[0]=='key':
                the_key=unquote_plus(tmpinput[1])
            elif tmpinput[0]=='value':
                the_value=unquote_plus(tmpinput[1])
            elif tmpinput[0]=='requestid':
                the_requestid=unquote_plus(tmpinput[1])
        if self.path == '/kv/insert':
            if garage.request_id_test(the_requestid) and the_key and the_value:
                payload={'action':'insert','key':the_key,'value':the_value,'requestid':the_requestid}
                px = self.server.px
                data=json.dumps(payload)
                while True:
                    seq = px.get_max()+1
                    px.start(data,seq)
                    # wait for finish
                    timeslp=0.01
                    tmp_status = px.status(seq)
                    while tmp_status is not None and not tmp_status['decided']:
                        time.sleep(timeslp) # something like timeout
                        if timeslp<1.0:
                            timeslp*=2
                        tmp_status = px.status(seq)
                    action_status = px.action_status(seq)
                    if action_status:
                        px.do_kv_actions(seq)
                        ret = px.kv_status(seq)
                        garage.request_id_add(the_requestid)
                        return self.str2file('{"success":"'+str(ret).lower()+'"}')
        if self.path == '/kv/delete':
            if garage.request_id_test(the_requestid) and the_key:
                payload={'action':'delete','key':the_key,'requestid':the_requestid}
                px = self.server.px
                data=json.dumps(payload)
                while True:
                    seq = px.get_max()+1
                    px.start(data,seq)
                    # wait for finish
                    timeslp=0.01
                    tmp_status = px.status(seq)
                    while tmp_status is not None and not tmp_status['decided']:
                        time.sleep(timeslp) # something like timeout
                        if timeslp<1.0:
                            timeslp*=2
                        tmp_status = px.status(seq)
                    action_status = px.action_status(seq)
                    if action_status:
                        px.do_kv_actions(seq)
                        ret = px.kv_status(seq)
                        garage.request_id_add(the_requestid)
                        return self.str2file('{"success":"'+str(ret[0]).lower()+'","value":"'+ret[1]+'"}')
        if self.path == '/kv/update':
            if garage.request_id_test(the_requestid) and the_key and the_value:
                payload={'action':'update','key':the_key,'value':the_value,'requestid':the_requestid}
                px = self.server.px
                data=json.dumps(payload)
                while True:
                    seq = px.get_max()+1
                    px.start(data,seq)
                    # wait for finish
                    timeslp=0.01
                    tmp_status = px.status(seq)
                    while tmp_status is not None and not tmp_status['decided']:
                        time.sleep(timeslp) # something like timeout
                        if timeslp<1.0:
                            timeslp*=2
                        tmp_status = px.status(seq)
                    action_status = px.action_status(seq)
                    if action_status:
                        px.do_kv_actions(seq)
                        ret = px.kv_status(seq) # note tmp_status may not be insert's result
                        garage.request_id_add(the_requestid)
                        return self.str2file('{"success":"'+str(ret).lower()+'"}')
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

