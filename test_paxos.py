import requests, json
import unittest
import os
from time import sleep
import xpaxos
import threading
import random

class TestPaxos(unittest.TestCase):
    def test_messagehandler(self):
        m=xpaxos.MessageHandler.MessageHandler(0,2)
        n=xpaxos.MessageHandler.MessageHandler(1,2)
        p1=n.propose('<the value to be agreed>')
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
        print('decide on '+str(m.decided_value))
        print('decide on '+str(n.decided_value))

if __name__ == '__main__':
    unittest.main()

