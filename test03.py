import requests, json
import unittest
import os
from time import sleep
import xpaxos
import threading
import random
def parse_output(r,k):
    if not r or not r.text:
        return None
    #print(r.text)
    output = json.loads(r.text)
    if k in output:
        return output[k]
    else:
        return None

class TestStringMethods(unittest.TestCase):
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

    def tone(self):
        d=[1,'mm',4]
        payload={}
        cnt=0
        for i in d:
            payload['msg'+str(cnt)]=i
            cnt+=1
        print(payload)
    
    def todo(self, url, key, value):
        try:
            r=requests.post(url,data={'key': '1'+key, 'value': value,'requestid':random.randint(0,10000)})
            print(r.text)
        except:
            print('wrong')
    def onekey(self,i):
        i=int(i)
        self.todo(self.list_of_address_long[i%self.size]+self.path_insert,str(i+1), '_')
        self.todo(self.list_of_address_long[i%self.size]+self.path_update,str(i+1), '+')
        #self.todo(self.list_of_address_long[i%self.size]+self.path_delete,str(i+1), None)
    def testinsert(self):
        tt=[]
        for i in range(100):
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

    def est111(self):
        requests.get(self.list_of_address_long[2]+self.path_get+'1&requestid='+str(random.randint(0,10000000)))

    def paxos(self):
        m=xpaxos.MessageHandler.MessageHandler(0,2)
        n=xpaxos.MessageHandler.MessageHandler(1,2)
        p1=n.propose()
        print(p1)
        p2=m.promise(p1)
        #p2=m.receive(p1)
        p3=n.receive(p1)
        print(p2)
        print(p3)
        p4=n.receive(p2)
        p5=n.receive(p3)
        print(p4)
        print(p5)
        p6=m.receive(p5)
        p7=n.receive(p5)
        print(p6)
        print(p7)
        p8=n.receive(p6)
        p9=n.receive(p7)
        print('decide?'+str(n.decided_value))
        print(p8)
        print(p9)
        m.receive(p9)
        n.receive(p9)
        print(json.dumps(p9))
        print('decide?'+str(m.decided_value))
        print('decide?'+str(n.decided_value))

if __name__ == '__main__':
    unittest.main()

