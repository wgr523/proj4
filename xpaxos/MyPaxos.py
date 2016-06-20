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
    lo_mutex = threading.RLock()
    lo_buf = 0
    peer_buf = set()
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
    def catchup_sequence(self,beg,end): #[beg,end)
        for i in range(beg,end):
            t=threading.Thread(target = self.start, args=('(this should not be agreed)',i) )
            t.start()
            t.join() # correct?
        self.done(end-1)
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
        if not msghdl:
            return
        path='/paxos/propose'
        cnt=0
        while not msghdl.decided_value and not self.dead:
            cnt+=1
            '''do we need a round test? like > 10 rounds, we just return fail?'''
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
            for tmpcnt in range(7):
                if msghdl.decided_value or self.dead:
                    break
                time.sleep(timeslp) # something like timeout
                timeslp*=2
        print('As leader, Agree on '+msghdl.decided_value)

    def receive(self,msg,seq):
        flag_to_catch_up = self.get_max()+1, seq
        self.allocate_sequence(seq)
        self.catchup_sequence(flag_to_catch_up[0],flag_to_catch_up[1])
        with self.mutex:
            msghdl = self.sequence[seq]
        if not msghdl:
            return
        flag_to_do_action = msg[0]=='commit' and msghdl.decided_value is None
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
        elif flag_to_do_action:# msg[0]=='commit' I will have no reply but I should do something to kv
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
            if payload['action']=='get':
                rw_lock = garage.get_rw_create(the_key)
                rw_lock.before_read()
                ret = garage.get(the_key)
                rw_lock.after_read()
                self.sequence_result[seq]=ret
            if payload['action']=='insert':
                rw_lock = garage.get_rw_create(the_key)
                rw_lock.before_write()
                ret = garage.insert(the_key,the_value)
                rw_lock.after_write()
                self.sequence_result[seq]=ret
            '''done, collect garbage'''
            self.done(seq)
                

    def status(self,seq):
        with self.mutex:
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
        with self.mutex:
            if seq>=len(self.sequence):
                return None
            ret = self.sequence_result[seq]
        return ret
    def action_status(self,seq): # to see if the action is done, or other action is done?
        with self.mutex:
            if seq>=len(self.sequence):
                return False
            msghdl = self.sequence[seq]
        if not msghdl:
            return False
        return msghdl.potential_value == msghdl.decided_value

    def get_max(self):
        with self.mutex:
            ret = len(self.sequence)
        return ret-1
        #return self.hi
    def get_min(self):
#        tmp_seq = self.sequence
#        for i in range(self.lo,len(tmp_seq)):
#            if tmp_seq[i] is not None:
#                self.lo=i
#                break
        with self.lo_mutex:
            ret = self.lo_buf
        return ret
    def done(self,seq):
        with self.lo_mutex:
            l1=self.lo
        for i in range(l1,seq+1):
            with self.mutex:
                msghdl = self.sequence[i]
            if not msghdl.decided_value:
                with self.lo_mutex:
                    self.lo = i
                break
            if i==seq:
                with self.lo_mutex:
                    self.lo = seq+1
        with self.lo_mutex:
            self.lo_buf = self.lo
            self.peer_buf = set([self.me])
        for i in range(self.size):
            if self.me != i:
                url=self.peers[i]+'/paxos/done/ask'
                try:
                    print(str(self.me)+' send a done number ask to '+str(i))
                    requests.post(url,data={'asker':self.me})
                except:
                    print(str(i)+' deny me')
    def answer_done(self,asker):
        with self.lo_mutex:
            ret = self.lo
        url=self.peers[asker]+'/paxos/done/answer'
        payload={'answerer':self.me,'min':ret}
        try:
            print(str(self.me)+' send a done number answer to '+str(asker)+', value is '+str(ret))
            requests.post(url,data=payload)
        except:
            print(str(asker)+' deny me')
    def receive_done(self,lo,answerer):
        with self.lo_mutex:
            self.peer_buf.add(answerer)
            if lo<self.lo_buf:
                self.lo_buf = lo
            if len(self.peer_buf) == self.size:
                for i in range(self.lo_buf-1,-1,-1):
                    if not self.sequence[i]:
                        break
                    self.sequence[i]=None
                    print('trash seq='+str(i))
                gc.collect()
#                if i >= len(self.sequence):
#                    break
#            for i in range(seq+1):
#                if i >= len(self.sequence):
#                    break
#                self.sequence[i]=None

    def show_off(self):
        s=['<h2>This is server '+str(self.me)+'</h2>\n<h3>paxos status:</h3>\n']
        s.append('lo='+str(self.lo)+' , hi='+str(len(self.sequence)-1))
        for i in range(self.lo,len(self.sequence)):
            msghdl = self.sequence[i]
            s.append(str(i)+': decided_value='+msghdl.decided_value+' , kv status='+str(self.sequence_result[i]))
        return s
