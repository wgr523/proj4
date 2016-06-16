
class MessageHandler(object):
    '''
    This class doesn't contain any communication thing
    '''
    leader = False
    commiter = False
    decided_value = None
    proposal_id = None # n
    proposal_value = None # v'
    highest_proposal_id  = 0 # n_p
    highest_accepted_id  = -1 # n_a
    accepted_value = None # v_a
    promises_received = None
    acks_received = None
    haha_value = 'value' # default value we want to agree on
    highest_buf = -1
    value_buf = None

    def __init__(self, network_uid, total_size):
        self.network_uid = network_uid
        self.total_size = total_size
        self.quorum_size = (total_size)//2+1

    def set_value(self,v):
        self.haha_value = v
    
    def propose(self):
        self.leader              = False
        self.promises_received   = set()
        self.proposal_id         = self.choose_n()
        #self.highest_proposal_id = self.proposal_id # this may be useless
        self.highest_buf = -1
        self.value_buf = None
        #self.current_prepare_msg = (self.network_uid, self.proposal_id)
        return 'propose',self.network_uid, self.proposal_id

    def promise(self,msg):
        if msg[2] >= self.highest_proposal_id:
            self.highest_proposal_id = msg[2]
            return 'promise',self.network_uid, msg[2], self.highest_accepted_id, self.accepted_value

    def accept(self, msg): # aka receive promise
        if self.leader:
            return
        if msg and msg[1] is not None and msg[2]==self.proposal_id:
            self.promises_received.add(msg[1])
            #update
            if msg[2]>self.highest_buf:
                self.highest_buf = msg[3]
                if len(msg)>=5:
                    self.value_buf = msg[4]
                else:
                    self.value_buf = None
        if len(self.promises_received) >= self.quorum_size:
            self.leader = True
            self.commiter = False
            self.acks_received = set()
            self.proposal_value=self.value_buf
            if not self.proposal_value:
                self.proposal_value=self.haha_value
            return 'accept',self.network_uid, self.proposal_id, self.proposal_value

    def ack(self,msg):
        if msg[2] >= self.highest_proposal_id:
            self.highest_proposal_id = msg[2]
            self.highest_accepted_id = msg[2]
            self.accepted_value = msg[3]
            return 'ack',self.network_uid, msg[2]

    def commit(self,msg): # aka receive ack
        if self.commiter:
            return
        if msg and msg[2] == self.proposal_id and msg[1] is not None:
            self.acks_received.add(msg[1])
        if len(self.acks_received) >= self.quorum_size:
            self.commiter = True
            return 'commit',self.network_uid,self.proposal_value

    def receive_commit(self,msg):
        self.decided_value = msg[2]
        return
        
    def choose_n(self):
        ret = self.network_uid+ (int(self.highest_proposal_id/self.total_size)+1)*self.total_size
        return ret
    
    def receive(self,msg):
        if msg and msg[0]:
            if msg[0]=='propose':
                return self.promise(msg)
            elif msg[0]=='promise':
                return self.accept(msg)
            elif msg[0]=='accept':
                return self.ack(msg)
            elif msg[0]=='ack':
                return self.commit(msg)
            elif msg[0]=='commit':
                return self.receive_commit(msg)
