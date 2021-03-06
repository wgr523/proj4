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
    lo_of_none = 0
    peer_buf = set()
    action_mutex = threading.RLock()
    def __init__(self, peers, me):
        self.peers = peers
        self.size = len(peers)
        self.me = me

    def allocate_sequence(self,seq):
        length = seq-len(self.sequence)+1
        for i in range(length):
            self.sequence.append(MessageHandler(self.me,self.size))
        self.sequence_result.extend([None]*length)
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
        with self.mutex:
            self.allocate_sequence(seq)
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
            for tmpcnt in range(4):
                if msghdl.decided_value or self.dead:
                    break
                time.sleep(timeslp) # something like timeout
                timeslp*=2
        print('As leader, agree on seq='+str(seq)+' , value= '+msghdl.decided_value)

    def receive(self,msg,seq):
        with self.mutex:
            self.allocate_sequence(seq)
            msghdl = self.sequence[seq]
        if not msghdl:
            return
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
            elif reply[0]=='ack':
                if self.me == msg[1]: # special case for send msg to itself
                    self.receive(reply,seq)
                else:
                    url=self.peers[msg[1]]+'/paxos/'+reply[0]
                    try:
                        print(str(self.me)+' send a ack to '+str(msg[1]))
                        requests.post(url,data=payload)
                    except:
                        print(str(msg[1])+' deny me') 
            elif reply[0]=='accept':
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
            elif reply[0]=='commit':
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
#            elif reply[0]=='nuh':
#                t_reply='commit',reply[1],reply[2]
#                payload = self.deal_with_msg(t_reply,seq)
#                if self.me == msg[1]: # special case for send msg to itself
#                    self.receive(t_reply,seq)
#                else:
#                    url=self.peers[msg[1]]+'/paxos/'+reply[0]
#                    try:
#                        print(str(self.me)+' send a commit to '+str(msg[1]))
#                        requests.post(url,data=payload)
#                    except:
#                        print(str(msg[1])+' deny me')
    def do_kv_actions(self,seq):
        end=seq+1
        timeslp=0.25
        with self.action_mutex:
            beg=self.get_useful_min()
            for i in range(beg,end):
                with self.mutex:
                    msghdl = self.sequence[i]
                ret = self.sequence_result[i]
                if msghdl:
                    if not msghdl.decided_value:
                        if timeslp:
                            time.sleep(timeslp) # this is to minimize the error action below
                        if not msghdl.decided_value:
                            timeslp/=2
                            if timeslp<0.001:
                                timeslp=0
                            print('wait for '+str(i))
                            self.start('{"action":"get","key":"ERROR: this instance is used to catch up"}',i)
                            print('wait done for '+str(i)+' whose action is '+msghdl.decided_value)
                    payload = json.loads(msghdl.decided_value)
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
                        if garage.request_id_add(the_requestid):
                            rw_lock = garage.get_rw_create(the_key)
                            rw_lock.before_read()
                            ret = garage.get(the_key)
                            rw_lock.after_read()
                            self.sequence_result[i]=ret
                    elif payload['action']=='insert':
                        if garage.request_id_add(the_requestid):
                            rw_lock = garage.get_rw_create(the_key)
                            rw_lock.before_write()
                            ret = garage.insert(the_key,the_value)
                            rw_lock.after_write()
                            self.sequence_result[i]=ret
                    elif payload['action']=='delete':
                        if garage.request_id_add(the_requestid):
                            rw_lock = garage.get_rw_create(the_key)
                            rw_lock.before_write()
                            ret = garage.delete(the_key)
                            rw_lock.after_write()
                            self.sequence_result[i]=ret
                    elif payload['action']=='update':
                        if garage.request_id_add(the_requestid):
                            rw_lock = garage.get_rw_create(the_key)
                            rw_lock.before_write()
                            ret = garage.update(the_key,the_value)
                            rw_lock.after_write()
                            self.sequence_result[i]=ret
                else:
                    print('do actions - error!!!')
            '''done, collect garbage'''
            self.done(seq)
                

    def status(self,seq):
        with self.mutex:
            if seq>=len(self.sequence):
                msghdl = None
            else:
                msghdl = self.sequence[seq]
        if not msghdl:
            return None
        if msghdl.decided_value:
            decided = True
        else:
            decided = False
        return {'decided':decided,'v':msghdl.decided_value}
    
    def kv_status(self,seq):
        with self.mutex:
            if seq>=len(self.sequence):
                ret = None
            else:
                ret = self.sequence_result[seq]
        return ret
    def action_status(self,seq): # to see if it is the action we need
        with self.mutex:
            if seq>=len(self.sequence):
                msghdl = None
            else:
                msghdl = self.sequence[seq]
        if not msghdl:
            return False
        return msghdl.potential_value == msghdl.decided_value

    def get_max(self):
        with self.mutex:
            ret = len(self.sequence)
        return ret-1
    def get_min(self):
        with self.lo_mutex:
            ret = self.lo_of_none
        return ret
    def get_useful_min(self):
        with self.lo_mutex:
            ret = self.lo
        return ret
    
    def done(self,seq):
        with self.lo_mutex:
            if self.lo<seq+1:
                self.lo = seq+1
            tmp = self.lo-self.lo_of_none
        '''the step about forget'''
        if tmp<10: # 10 is some parameter, how large should it be?
            return
        with self.lo_mutex:
            self.lo_buf = self.lo
            self.peer_buf = set([self.me])
        for i in range(self.size):
            if self.me != i:
                url=self.peers[i]+'/paxos/done/ask'
                try:
                    print(str(self.me)+' send a done number ask to '+str(i))
                    requests.post(url,data={'asker':str(self.me)})
                except:
                    print(str(i)+' deny me')
    def answer_done(self,asker):
        url = self.peers[asker]+'/paxos/done/answer'
        lo=self.get_useful_min()
        payload={'answerer':str(self.me),'min':str(lo)}
        try:
            print(str(self.me)+' send a done number answer to '+str(asker)+', value is '+str(lo))
            requests.post(url,data=payload)
        except:
            print(str(asker)+' deny me')
    def receive_done(self,lo,answerer):
        with self.lo_mutex:
            self.peer_buf.add(answerer)
            if lo<self.lo_buf:
                self.lo_buf = lo
        if len(self.peer_buf) == self.size:
            with self.lo_mutex:
                beg=self.lo_of_none
                end=self.lo_buf
            with self.mutex:
                for i in range(beg,end):
                    self.sequence[i]=None
                    print('trash seq='+str(i))
            with self.lo_mutex:
                if self.lo_of_none < end:
                    self.lo_of_none = end
            gc.collect()

    def show_off(self):
        beg=self.get_min()
        end=self.get_max()
        s=['<h2>This is server '+str(self.me)+'</h2>\n<h3>paxos status:</h3>\n']
        s.append('lo='+str(beg)+' , hi='+str(end)+' , useful lo='+str(self.get_useful_min()))
        for i in range(beg,end+1):
            msghdl = self.sequence[i]
            if msghdl:
                s.append(str(i)+': decided_value='+msghdl.decided_value+' , kv status='+str(self.sequence_result[i]))
            else:
                s.append('Err, instance is null.')
        return s
