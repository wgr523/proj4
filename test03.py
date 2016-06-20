import requests, json
import unittest
import os
from time import sleep
import xpaxos
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

    def setUp(self):
        pass

    def tone(self):
        d=[1,'mm',4]
        payload={}
        cnt=0
        for i in d:
            payload['msg'+str(cnt)]=i
            cnt+=1
        print(payload)

    def testinsert(self):
        for i in range(21):
            try:
                requests.post(self.url+str(self.port+(i%3))+self.path_insert,data={'key': str(i+1), 'value': '_'})
            except:
                pass

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

