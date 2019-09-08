import asyncio
import logging
from random import random
import time
from colorama import Fore
import numpy as np
from nexus.actor import Actor, AsyncRunManager

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class AnalysisAsync(Actor):
    ''' Module for asynchronous data analysis using asyncio. This module gets object ID from q_in asynchronously,
    retrieve data from store, and analyze it.
    '''

    def __init__(self, *args):
        super().__init__(*args)

        self.frame_number = 0
        self.aqueue = None
        self.loop = None

        self.t_per_frame = list()
        self.t_per_put = list()

    def setup(self):
        pass

    def run(self):
        ''' Initializes the event loop and starts the asynchronous [self.arun]
        '''
        policy = asyncio.get_event_loop_policy()
        policy.set_event_loop(policy.new_event_loop())
        self.loop = asyncio.get_event_loop()

        self.aqueue = asyncio.Queue()
        self.loop.run_until_complete(self.arun())

    async def arun(self):
        async with AsyncRunManager(self.name, self.get_frame, self.setup, self.q_sig, self.q_comm) as rm:
            logger.info(rm)

        print('Analysis broke, avg time per frame_number: ', np.mean(self.t_per_frame))
        print('Analysis got through ', self.frame_number, ' frames.')

    async def get_frame(self):
        '''
        Asynchronously gets frame from store and put into queue for [self.analysis].
        If there's a pile-up in the queue, this spawns new [self.analysis] task.
        TODO: Check for exploding tasks. Add new actors if needed
        '''

        asyncio.ensure_future(self.analysis(), loop=self.loop)

        while True:
            if self.aqueue.qsize() > 0:
                asyncio.ensure_future(self.analysis(), loop=self.loop)

            obj_id = await self.q_in.get_async()
            if obj_id is not None:
                frame = self.client.getID(obj_id[0][str(self.frame_number)])
                await self.aqueue.put([frame, self.frame_number, time.time()])
                self.frame_number += 1

    async def analysis(self):
        ''' Performs asynchronous analysis
        Simulates out-sourcing data to an external program.
        Waits until queue is not empty and perform non-blocking analysis.
        '''

        while True:
            frame = await self.aqueue.get()
            t = 0.15 * random() + 0.1
            await asyncio.sleep(t)
