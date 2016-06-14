from xpaxos.MessageHandler import MessageHandler
import requests
class MyPaxos(object):
    '''
    Implement paxos, with many peers.
    '''
    sequence = []

    def __init__(self, peers, me):
        self.peers = peers
        self.size = len(peers)
        self.me = me

    def allocate_sequence(self,i):
        for j in range(i):
            self.sequence.append(MessageHandler(j,self.size))
