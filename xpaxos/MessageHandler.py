
class MessageHandler(object):
    '''
    This class doesn't contain any communication thing
    '''
    leader = False
    commiter = False
    proposal_id = None # n
    proposal_value = None # v'
    highest_proposal_id  = 0 # n_p
    highest_accepted_id  = -1 # n_a
    accepted_value = None # v_a
    promises_received = None
    acks_received = None

    def __init__(self, network_uid, total_size):
        self.network_uid = network_uid
        self.total_size = total_size
        self.quorum_size = (total_size+1)//2
    
    def propose(self):
        self.leader              = False
        self.promises_received   = set()
        self.proposal_id         = self.choose_n()
        self.highest_proposal_id = self.proposal_id # this may be useless
        #self.current_prepare_msg = (self.network_uid, self.proposal_id)
        return 'propose',self.network_uid, self.proposal_id

    def promise(self,msg):
        if msg[2] >= self.highest_proposal_id:
            self.highest_proposal_id = msg[2]
            return 'promise',self.network_uid, self.highest_accepted_id, self.accepted_value

    def accept(self, msg): # aka reveive promise
        if self.leader:
            return
        if msg:
            self.promises_received.add(msg)
        if len(self.promises_received) >= self.quorum_size:
            self.leader = True
            self.commiter = False
            self.acks_received = set()
            vlist = [(v[2],v[3]) for v in self.promises_received if v[3] ]
            if len(vlist):
                vlist.sort(reverse=True)
                self.proposal_value=vlist[0][1]
            else:
                self.proposal_value=='arbitrary'
            return 'accept',self.network_uid, self.proposal_id, self.proposal_value

    def ack(self,msg):
        if msg[2] >= self.highest_proposal_id:
            self.highest_proposal_id = msg[2]
            self.highest_accepted_id = msg[2]
            self.accepted_value = msg[3]
            return 'ack',self.network_uid, msg[2]

    def commit(self,msg): # aka reveive ack
        if self.commiter:
            return
        if msg and msg[2] == self.proposal_id:
            self.acks_received.add(msg)
        if len(self.acks_received) >= self.quorum_size:
            self.commiter = True
            return 'commit',self.network_uid,self.proposal_value
        
    def choose_n(self):
        ret = self.network_uid+ (int(self.highest_proposal_id/self.total_size)+1)*self.total_size
        return ret
    
