from multiprocessing import Process, Queue, Manager, cpu_count, set_start_method
import numpy as np
import pyarrow.plasma as plasma
import asyncio
import subprocess
import signal
import time
from queue import Empty
import numpy as np
import logging; logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
import asyncio
import concurrent
from pyarrow.plasma import ObjectNotAvailable
from improv.actor import Actor, Spike, RunManager, AsyncRunManager

class BasicWatcher(Actor):

    def __init__(self, *args):

        super().__init__(*args)

    def setup(self):
        self.numSaved= 0
        self.tasks= []
        self.polling= self.watchin
        self.setUp= False

    def run(self):

        with RunManager(self.name, self.watchrun, self.setup, self.q_sig, self.q_comm) as rm:
            logger.info(rm)

        print('watcher saved '+ str(self.numSaved)+ ' objects')

    def watchrun(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.watch())

    async def watch(self):

        if self.setUp== False:
            for q in self.polling:
                self.tasks.append(asyncio.ensure_future(q.get_async()))
            self.setUp = True

        done, pending= await asyncio.wait(self.tasks, return_when= concurrent.futures.FIRST_COMPLETED)

        for i,t in enumerate(self.tasks):
            if t in done or self.polling[i].status == 'done':
                r= self.polling[i].result # r should be array with id and name
                obj= self.client.getID(r[0])
                np.save('save/'+r[1], obj)
                self.tasks[i] = (asyncio.ensure_future(self.polling[i].get_async()))