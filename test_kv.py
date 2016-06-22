import requests, json
import unittest
import os
from time import sleep
import xpaxos
import threading
import random

class TestKV(unittest.TestCase):
    url = 'http://localhost:'
    port = 8001
    path_insert='/kv/insert'
    path_update='/kv/update'
    path_delete='/kv/delete'
    path_get='/kv/get?key='
    list_of_address_long=[]
    size=None

    def setUp(self):
        with open('conf/settings.conf') as f:
            settings = json.load(f)
            list_of_address=[]
            port=int(settings['port'])
            for i in range(1,len(settings)+1):
                tmpstr = 'n%02d' % i
                if tmpstr in settings:
                    list_of_address.append(settings[tmpstr])
            for a in list_of_address:
                self.list_of_address_long.append('http://'+a+':'+str(port))
            self.size = len(self.list_of_address_long)

    def action(self, url, key, value):
        return requests.post(url,data={'key': 'w'+key, 'value': value,'requestid':random.randint(0,10000)})
    
    def onekey(self,i):
        i=int(i)
        the='null'
        try:
            self.action(self.list_of_address_long[i%self.size]+self.path_insert,str(i+1), '&')
            the='a'
        except:
            pass
        try:
            self.action(self.list_of_address_long[i%self.size]+self.path_update,str(i+1), '=')
            the='b'
        except:
            pass

    def testinsertupdateget(self):
        tt=[]
        for i in range(15):
            t=threading.Thread(target=self.onekey,args=(str(i),))
            t.start()
            tt.append(t)
        for t in tt:
            t.join()
        for i in range(self.size):
            try:
                requests.get(self.list_of_address_long[i]+self.path_get+'1&requestid='+str(random.randint(0,10000)))
            except:
                print('wrong at get server'+str(i))


if __name__ == '__main__':
    unittest.main()

