import requests, json
import unittest
import os
from time import sleep
import xpaxos
import threading
import random

class TestKVMethods(unittest.TestCase):
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

    def todo(self, url, key, value):
        try:
            r=requests.post(url,data={'key': key, 'value': value,'requestid':random.randint(0,10000)})
            print(r.text)
        except:
            print('wrong')
    def onekey(self,i):
        i=int(i)
        self.todo(self.list_of_address_long[i%self.size]+self.path_insert,str(i+1), '_')
        self.todo(self.list_of_address_long[i%self.size]+self.path_update,str(i+1), '+')
        self.todo(self.list_of_address_long[i%self.size]+self.path_delete,str(i+1), None)
    def testinsertupdatedeleteget(self):
        tt=[]
        for i in range(102):
            t=threading.Thread(target=self.onekey,args=(str(i),))
            t.start()
            tt.append(t)
        for t in tt:
            t.join()
        for i in range(self.size):
            try:
                requests.get(self.list_of_address_long[i]+self.path_get+'1&requestid='+str(random.randint(0,10000)))
            except:
                print('wrong')


if __name__ == '__main__':
    unittest.main()

