import logging
import time
import random

import trio
from colorama import Fore

from nexus.module import AsyncRunManager
from .analysis import Analysis


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class AnalysisTrio(Analysis):
    """
    Module for asynchronous data analysis using Trio.

    Upon initialization, starts the asynchronous loop using the {run} function.
    {arun} starts the AsyncRunManager and wait until AsyncRunManager starts the entire thing [get_frame].

    """

    def __init__(self, *args):
        super().__init__(*args)

        self.frame = None
        self.frame_number = 0
        self.result_ex = None

        self.t_per_frame = list()
        self.t_per_put = list()

        self.send_to_queue, self.recv_from_queue = trio.open_memory_channel(100)  # 100 objects before blocking.
        self.send_from_q_in, self.recv_from_q_in = trio.open_memory_channel(0)

    def setup(self):
        pass

    def run(self):
        trio.run(self.arun)

    async def arun(self):
        async with trio.open_nursery() as nursery:
            run_manager = AsyncRunManager(self.name, self.get_frame, self.setup, self.q_sig, self.q_comm, nursery)
            nursery.start_soon(run_manager.start_run_manager)

            nursery.start_soon(trio.to_thread.run_sync, self.q_in.get_trio, self.send_from_q_in)

    async def get_frame(self, nursery):
        """
        Asynchronously gets frame from store and put into queue for [self.analysis].
        If there's a pile-up in the queue, this spawns new [self.analysis] task.

        :param nursery: current nursery session.
        :type nursery: trio.Nursery
        """

        nursery.start_soon(self.analysis)

        while True:
            if self.send_to_queue.statistics().current_buffer_used > 1:
                nursery.start_soon(self.analysis)

            obj_id = await self.recv_from_q_in.receive()

            frame = self.client.getID(obj_id[0][str(self.frame_number)])

            await self.send_to_queue.send([frame, self.frame_number, time.time()])
            # print(Fore.GREEN + f'Put frame {self.frame_number}' + Fore.RESET)
            self.frame_number += 1

    async def analysis(self):
        """
        Performs asynchronous "analysis". Simulates out-sourcing data to an external program.
        Waits until channel (queue) is not empty and perform non-blocking analysis.

        """
        while True:
            frame = await self.recv_from_queue.receive()
            await trio.sleep(0.1 + 0.15 * random.random())  # Simulate
            self.t_per_frame.append(time.time() - frame[2])
            # print(Fore.MAGENTA + f'Analyzed: {frame[1]} Delay: {self.t_per_frame[-1]:.3f}s')
