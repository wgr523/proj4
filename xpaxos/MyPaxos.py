from xpaxos.MessageHandler import MessageHandler
import requests
import json
import time
import threading
import gc

import garage

class MyPaxos(object):
    '''
    Implement paxos, with many peers.
    '''
    sequence = []
    sequence_result = []
    dead = False
    lo = 0
    #hi = -1
    mutex = threading.RLock()
    def __init__(self, peers, me):
        self.peers = peers
        self.size = len(peers)
        self.me = me

    def allocate_sequence(self,seq):
        with self.mutex:
            length = seq-len(self.sequence)+1
            for i in range(length):
                self.sequence.append(MessageHandler(self.me,self.size))
            self.sequence_result.extend([None]*length)
            #self.hi = seq
    def kill(self):
        self.dead = True
    def deal_with_msg(self,msg,seq):
        payload={}
        payload['seq']=seq
        cnt=0
        for i in msg:
            payload['msg'+str(cnt)]=i
            cnt+=1
        return payload

    def start(self,v,seq):
        self.allocate_sequence(seq)
        with self.mutex:
            msghdl = self.sequence[seq]
        path='/paxos/propose'
        cnt=0
        while not msghdl.decided_value and not self.dead:
            cnt+=1
            print('seq '+str(seq)+'. proposer round '+str(cnt))
            reply = msghdl.propose(v)
            self.receive(reply,seq) # special case for send msg to itself, do we need new thread here?
            payload = self.deal_with_msg(reply,seq)
            for i in range(self.size):
                if self.me != i:
                    url=self.peers[i]+path
                    try:
                        print(str(self.me)+' send a propose to '+str(i))
                        requests.post(url,data=payload)
                    except:
                        print(str(i)+' deny me')
            timeslp=0.01
            for tmpcnt in range(8):
                if msghdl.decided_value or self.dead:
                    break
                time.sleep(timeslp) # something like timeout
                timeslp*=2
        print('As leader, Agree on '+msghdl.decided_value)

    def receive(self,msg,seq):
        self.allocate_sequence(seq)
        with self.mutex:
            msghdl = self.sequence[seq]
        reply = msghdl.receive(msg)
        if reply and reply[0]:
            payload = self.deal_with_msg(reply,seq)
            if reply[0]=='promise':
                if self.me == msg[1]: # special case for send msg to itself
                    self.receive(reply,seq)
                else:
                    url=self.peers[msg[1]]+'/paxos/'+reply[0]
                    try:
                        print(str(self.me)+' send a promise to '+str(msg[1]))
                        requests.post(url,data=payload)
                    except:
                        print(str(msg[1])+' deny me') 
            if reply[0]=='ack':
                if self.me == msg[1]: # special case for send msg to itself
                    self.receive(reply,seq)
                else:
                    url=self.peers[msg[1]]+'/paxos/'+reply[0]
                    try:
                        print(str(self.me)+' send a ack to '+str(msg[1]))
                        requests.post(url,data=payload)
                    except:
                        print(str(msg[1])+' deny me') 
            if reply[0]=='accept':
                self.receive(reply,seq)
                path='/paxos/'+reply[0]
                for i in range(self.size):
                    if self.me != i:
                        url=self.peers[i]+path
                        try:
                            print(str(self.me)+' send a accept to '+str(i))
                            requests.post(url,data=payload)
                        except:
                            print(str(i)+' deny me') 
            if reply[0]=='commit':
                self.receive(reply,seq)
                path='/paxos/'+reply[0]
                for i in range(self.size):
                    if self.me != i:
                        url=self.peers[i]+path
                        try:
                            print(str(self.me)+' send a commit to '+str(i))
                            requests.post(url,data=payload)
                        except:
                            print(str(i)+' deny me')
        elif msg[0]=='commit': # I will have no reply but I should do something to kv
            payload = json.loads(msg[2])
            the_key = None
            the_value = None
            the_requestid=None
            if 'key' in payload:
                the_key = payload['key']
            if 'value' in payload:
                the_value = payload['value']
            if 'requestid' in payload:
                the_requestid= payload['requestid']
            if payload['action']=='insert':
                rw_lock = garage.get_rw_create(the_key)
                rw_lock.before_write()
                ret = garage.insert(the_key,the_value)
                rw_lock.after_write()
                self.sequence_result[seq]=ret
                

    def status(self,seq):
        if seq>=len(self.sequence):
            return None
        msghdl = self.sequence[seq]
        if not msghdl:
            return None
        if msghdl.decided_value:
            decided = True
        else:
            decided = False
        return {'decided':decided,'v':msghdl.decided_value}
    
    def kv_status(self,seq): # to see if kv action is done
        if seq>=len(self.sequence):
            return None
        ret = self.sequence_result[seq]
        return ret
    def action_status(self,seq): # to see if the action is done, or other action is done?
        if seq>=len(self.sequence):
            return False
        msghdl = self.sequence[seq]
        if not msghdl:
            return False
        return msghdl.potential_value == msghdl.decided_value


    def get_max(self):
        return len(self.sequence)-1
        #return self.hi
    def get_min(self):
        tmp_seq = self.sequence
        for i in range(self.lo,len(tmp_seq)):
            if tmp_seq[i] is not None:
                self.lo=i
                break
        return self.lo
    def done(self,seq):
        with mutex:
            for i in range(seq+1):
                if i >= len(self.sequence):
                    break
                self.sequence[i]=None
            #if self.lo < seq+1:
                #self.lo=seq+1
        gc.collect()
            
