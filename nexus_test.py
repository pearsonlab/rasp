from multiprocessing import Process, Queue, Manager, cpu_count, set_start_method
import numpy as np
import pyarrow.plasma as plasma
import asyncio
import subprocess
import signal
import time
from queue import Empty
import numpy as np
from pyarrow.plasma import ObjectNotAvailable

def random_object_id():
    return plasma.ObjectID(np.random.bytes(20))

def Link(name, start, end):
    ''' Abstract constructor for a queue that Nexus uses for
    inter-process/actor signaling and information passing

    A Link has an internal queue that can be synchronous (put, get)
    as inherited from multiprocessing.Manager.Queue
    or asynchronous (put_async, get_async) using async executors
    '''

    m = Manager()
    q = AsyncQueue(m.Queue(maxsize=0), name, start, end)
    return q

class AsyncQueue(object):
    def __init__(self,q, name, start, end):
        self.queue = q
        self.real_executor = None
        self.cancelled_join = False

        # Notate what this queue is and from where to where
        # is it passing information
        self.name = name
        self.start = start
        self.end = end
        self.status = 'pending'
        self.result = None

    def getStart(self):
        return self.start

    def getEnd(self):
        return self.end

    @property
    def _executor(self):
        if not self.real_executor:
            self.real_executor = ThreadPoolExecutor(max_workers=cpu_count())
        return self.real_executor

    def __getstate__(self):
        self_dict = self.__dict__
        self_dict['_real_executor'] = None
        return self_dict

    def __getattr__(self, name):
        if name in ['qsize', 'empty', 'full', 'put', 'put_nowait',
                    'get', 'get_nowait', 'close']:
            return getattr(self.queue, name)
        else:
            raise AttributeError("'%s' object has no attribute '%s'" %
                                    (self.__class__.__name__, name))

    def __repr__(self):
        #return str(self.__class__) + ": " + str(self.__dict__)
        return 'Link '+self.name #+' From: '+self.start+' To: '+self.end

    async def put_async(self, item):
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(self._executor, self.put, item)
        return res

    async def get_async(self):
        loop = asyncio.get_event_loop()
        self.status = 'pending'
        try:
            self.result = await loop.run_in_executor(self._executor, self.get)
            self.status = 'done'
            return self.result
        except Exception as e:
            pass

    def cancel_join_thread(self):
        self._cancelled_join = True
        self._queue.cancel_join_thread()

    def join_thread(self):
        self._queue.join_thread()
        if self._real_executor and not self._cancelled_join:
            self._real_executor.shutdown()

class Nexus():

    def __init__(self, size):

        self.p_store = subprocess.Popen(['plasma_store',
                            '-s', '/tmp/store',
                            '-m', str(size)],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)

        self.client: plasma.PlasmaClient = plasma.connect('/tmp/store', 10)
        self.client.subscribe()
        self.processes=[]
        self.name= 'nexus'


    def createActors(self):

        self.createPutter()
        self.createGetter()
        self.createWatcher()

        self.q_sig_watch = Link('watcher_sig', self.name, self.watcher.name)
        self.q_comm_watch= Link('watcher_comm', self.watcher.name, self.name)
        self.q_sig_put= Link('putter_sig', self.name, self.putter.name)
        self.q_comm_put= Link('putter_comm', self.putter.name, self.name)
        self.q_sig_get= Link('getter_sig', self.name, self.getter.name)
        self.q_comm_get= Link('getter_comm', self.getter.name, self.name)

        q_put_get= Link('put to get', self.putter.name, self.getter.name)
        q_put_watch= Link('put to watch', self.putter.name, self.watcher.name)
        q_get_watch= Link('get to watch', self.getter.name, self.watcher.name)

        self.putter.connectLinks(self.q_comm_put, self.q_sig_put, [q_put_get, q_put_watch])
        self.getter.connectLinks(self.q_comm_get, self.q_sig_get, [q_put_get, q_get_watch])
        self.watcher.connectLinks(self.q_comm_watch, self.q_sig_watch, [q_put_watch, q_get_watch])

    def createPutter(self):

        self.putter= putter('putter')
        p= Process(target=self.putter.run, name='putter')
        self.processes.append(p)

    def createGetter(self):

        self.getter= getter('getter')
        p= Process(target=self.getter.run, name='getter')
        self.processes.append(p)

    def createWatcher(self):

        self.watcher= watcher('watcher')
        p= Process(target=self.watcher.run, name='getter')
        self.processes.append(p)

    def  start(self):
        for p in self.processes:
            p.start()


class Actor():

    def __init__(self, name):
        self.client: plasma.PlasmaClient = plasma.connect('/tmp/store', 10)
        self.name= name

    def connectLinks(self, q_comm, q_sig):
        self.q_comm= q_comm
        self.q_sig= q_sig

class putter(Actor):

    def __init__(self, name):
        super(putter, self).__init__(name)

    def connectLinks(self, q_comm, q_sig, links):
        super(putter, self).connectLinks(q_comm, q_sig)
        self.connections= links

    def put(self, object, ID, save=False):
        self.client.put(object, ID)

        if save:
            self.connections[1].put(ID)

        self.connections[0].put(ID)

    def run(self):

        while True:
            try:
                signal= self.q_sig.get(timeout=0.000001)
                #signal will be object, ID, save

                self.put(signal[0], signal[1], save=signal[2])

            except Empty as e:
                pass

class getter(Actor):

    def __init__(self, name):
        super(getter, self).__init__(name)

    def connectLinks(self, q_comm, q_sig, links):
        super(getter, self).connectLinks(q_comm, q_sig)
        self.connections=links

    def run(self):
        
        while True:
            try:
                signal= self.q_sig.get(timeout=0.000001)

                if (signal== 'run'):

                    while True:
                        try:
                            signal= self.connections[0].get(timeout=0.000001)

                            obj= self.client.get(signal)
                            print(obj[0:5])
                            print('successfully received object')
                            #signal will just be object ID 


            except Empty as e:
                pass

class watcher(Actor):

    def __init__(self, name):
        super(watcher, self).__init__(name)

    def connectLinks(self, q_comm, q_sig, links):
        super(watcher, self).connectLinks(q_comm, q_sig)
        self.connections=links

    def run(self):

        while True:
            try:
                signal= self.connections[0].get(timeout=0.000001)

                obj= self.client.get(signal)

                np.savetxt('asdf.txt', obj)

            except Empty as e:
                pass


if __name__== '__main__':

    nexus= Nexus(10000)
    nexus.createActors()
    nexus.start()

    id1= random_object_id()
    ar= np.ones(500)

    nexus.q_sig_put.put([ar, id1, False])

    id2= random_object_id()
    nexus.q_sig_put.put([ar+ar, id2, True])

    id3= random_object_id()
    nexus.q_sig_put.put([ar+ar+ar, id3, False])

    nexus.q_sig_get.put('run')

    time.sleep(1)

    nexus.p_store.kill()
    for p in nexus.processes:
        p.kill()


        
