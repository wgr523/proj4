import sys
import json
import os
import requests

def setup():
    with open('conf/settings.conf') as f:
        settings = json.load(f)
        list_of_address=[]
        port=int(settings['port'])
        for i in range(1,len(settings)+1):
            tmpstr = 'n%02d' % i
            if tmpstr in settings:
                list_of_address.append(settings[tmpstr])
        list_of_address_long=[]
        for a in list_of_address:
            list_of_address_long.append('http://'+a+':'+str(port))
        return list_of_address_long
if __name__ == '__main__':
    peers=setup()
    size=len(peers)
    arg=None
    if len(sys.argv)>1:
        arg=sys.argv[1]
    if arg == 'starta':
        for i in range(1,size+1):
            tmpstr = 'n%02d' % i
            try:
                c='nohup python3 -u primary_server.py %s > conf/%s.log 2>&1&\necho $! > conf/%s.pid' % (tmpstr,tmpstr,tmpstr)
                os.system(c)
            except:
                pass
    if arg == 'stopa':
        for i in range(1,size+1):
            url=peers[i]
            requests.get(url+'/kvman/stop')
    if arg == 'restarta':
        for i in range(1,size+1):
            url=peers[i]
            requests.get(url+'/kvman/restart')
    if arg == 'killa':
        for i in range(1,size+1):
            tmpstr = 'n%02d' % i
            try:
                c='kill -9 `cat conf/%s.pid`\nrm conf/%s.pid' % (tmpstr,tmpstr)
                os.system(c)
            except:
                pass
    if arg == 'kill':
        t=None
        if len(sys.argv)>2:
            try:
                if sys.argv[2].startswith('n'):
                    t=int(sys.argv[2][1:])
                else:
                    t=int(sys.argv[2])
            finally:
                pass
        if t is not None:
            tmpstr = 'n%02d' % t
            try:
                c='kill -9 `cat conf/%s.pid`\nrm conf/%s.pid' % (tmpstr,tmpstr)
                os.system(c)
            except:
                pass
            
    if arg == 'stop':
        t=None
        if len(sys.argv)>2:
            try:
                if sys.argv[2].startswith('n'):
                    t=int(sys.argv[2][1:])
                else:
                    t=int(sys.argv[2])
            finally:
                pass
        if t is not None:
            url=peers[t-1]
            try:
                requests.get(url+'/kvman/stop')
            except:
                pass
    if arg == 'start':
        t=None
        if len(sys.argv)>2:
            try:
                if sys.argv[2].startswith('n'):
                    t=int(sys.argv[2][1:])
                else:
                    t=int(sys.argv[2])
            finally:
                pass
        if t is not None:
            url=peers[t-1]
            tmpstr = 'n%02d' % t
            try:
                requests.get(url+'/kvman/restart')
                c='nohup python3 -u primary_server.py %s > conf/%s.log 2>&1&\necho $! > conf/%s.pid' % (tmpstr,tmpstr,tmpstr)
                os.system(c)
            except:
                pass

