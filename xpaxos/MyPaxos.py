from xpaxos.MessageHandler import MessageHandler
import requests
import json
import time
class MyPaxos(object):
    '''
    Implement paxos, with many peers.
    '''
    sequence = {}

    def __init__(self, peers, me):
        self.peers = peers
        self.size = len(peers)
        self.me = me
        self.sequence[0]=MessageHandler(self.me,self.size)

    def allocate_sequence(self,s):
        for j in range(1,s):
            self.sequence[j]=MessageHandler(self.me,self.size)
    
    def deal_with_msg(self,msg):
        payload={}
        cnt=0
        for i in msg:
            payload['msg'+str(cnt)]=i
            cnt+=1
        return payload

    def start(self,v,seq=0):
        msghdl = self.sequence[seq]
        path='/paxos/propose'
        while not msghdl.decided_value:
            payload = self.deal_with_msg(msghdl.propose())
            for i in range(self.size):
                url=self.peers[i]+path
                try:
                    print(str(self.me)+' send a propose to '+str(i))
                    requests.post(url,data=payload)
                except:
                    print(str(i)+' deny me') 
            print('a round')
            time.sleep(5) # something like timeout
        print('!!!!!!!!! Agree on '+msghdl.decided_value)

    def receive(self,msg,seq=0):
        msghdl = self.sequence[seq]
        reply = msghdl.receive(msg)
        if reply and reply[0]:
            payload = self.deal_with_msg(reply)
            if reply[0]=='promise':
                url=self.peers[msg[1]]+'/paxos/'+reply[0]
                try:
                    print(str(self.me)+' send a promise to '+str(msg[1]))
                    requests.post(url,data=payload)
                except:
                    print(str(msg[1])+' deny me') 
            if reply[0]=='ack':
                url=self.peers[msg[1]]+'/paxos/'+reply[0]
                try:
                    print(str(self.me)+' send a ack to '+str(msg[1]))
                    requests.post(url,data=payload)
                except:
                    print(str(msg[1])+' deny me') 
            if reply[0]=='accept':
                path='/paxos/'+reply[0]
                for i in range(self.size):
                    url=self.peers[i]+path
                    try:
                        print(str(self.me)+' send a accept to '+str(i))
                        requests.post(url,data=payload)
                    except:
                        print(str(i)+' deny me') 
            if reply[0]=='commit':
                path='/paxos/'+reply[0]
                for i in range(self.size):
                    url=self.peers[i]+path
                    try:
                        print(str(self.me)+' send a commit to '+str(i))
                        requests.post(url,data=payload)
                    except:
                        print(str(i)+' deny me') 
            # reply may be none cuz msg may be commit
