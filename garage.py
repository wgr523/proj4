import threading
mutex = threading.RLock()
lock_mem = {}

main_mem = {}

requestid_mutex = threading.RLock()
requestid_mem = set()
class RWOne:
    def __init__(self,key):
        self.key=key
        self.sync = [0,0,0,0] # active reader, waiting reader, active writer, waiting writer
        self.lock = threading.RLock()
        self.okRead = threading.Condition(self.lock)
        self.okWrite = threading.Condition(self.lock)
    def before_read(self):
        ''' reader use this to get synchronization'''
        with self.lock:
            while self.sync[2]+self.sync[3] > 0:
                self.sync[1]=self.sync[1]+1
                self.okRead.wait()
                self.sync[1]=self.sync[1]-1
            self.sync[0]=self.sync[0]+1
    def after_read(self):
        with self.lock:
            self.sync[0]=self.sync[0]-1
            if self.sync[0]==0 and self.sync[3]>0:
                self.okWrite.notify()
    def before_write(self):
        with self.lock: # equivalent to lock.acquire, try, finally
            while self.sync[0]+self.sync[2] > 0:
                self.sync[3]=self.sync[3]+1
                self.okWrite.wait()
                self.sync[3]=self.sync[3]-1
            self.sync[2]=self.sync[2]+1
    def after_write(self):
        with self.lock:
            self.sync[2]=self.sync[2]-1
            if self.sync[3] > 0:
                self.okWrite.notify()
            elif self.sync[1] > 0:
                self.okRead.notify_all()
def get_rw_create(key):
    with mutex:
        if key not in lock_mem:
            lock_mem[key]=RWOne(key)
    return lock_mem[key]


        
def insert(key, value):
    if key not in main_mem:
        main_mem[key]=value
        return True
    else:
        return False
def insert_no_matter_what(key, value):
    main_mem[key]=value
def update(key, value):
    if key in main_mem:
        main_mem[key]=value
        return True
    else:
        return False
def delete(key):
    if key in main_mem:
        ret = main_mem[key]
        del main_mem[key]
        return (True,ret)
    else:
        return (False,'error')
def get(key):
    if key in main_mem:
        ret = main_mem[key]
        return (True,ret)
    else:
        return (False,'error')
def countkey():
    return len(main_mem)
def dump():
    return main_mem
def set_main_mem(_main_mem):
    main_mem.clear()
    main_mem.update(_main_mem)
def request_id_add(rid):
    if rid is None:
        return True
    with requestid_mutex:
        if rid not in requestid_mem:
            requestid_mem.add(rid)
            ret = True
        else:
            ret = False
    return ret
def request_id_test(rid):
    if rid is None:
        return True
    with requestid_mutex:
        if rid not in requestid_mem:
            ret = True
        else:
            ret = False
    return ret
