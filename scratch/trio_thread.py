from random import random

import colorama
import numpy as np
import time
import trio

class TestAsync:
    def __init__(self):
        self.frame_number = -1
        self.send_chan, self.recv_chan = trio.open_memory_channel(100)
        self.send_chan: trio.MemorySendChannel = self.send_chan
        self.recv_chan: trio.MemoryReceiveChannel = self.recv_chan

        self.send_from_thread, self.recv_from_thread = trio.open_memory_channel(0)
        self.another = AnotherThread()

    async def run(self):
        async with trio.open_nursery() as nursery:
            # nursery.start_soon(self.get_frame, nursery)
            nursery.start_soon(trio.to_thread.run_sync, self.another.func, self.send_from_thread)
            nursery.start_soon(self.analysis)
            nursery.start_soon(self.analysis)

    async def analysis(self):
        while True:
            frame = await self.recv_from_thread.receive()
            t = random() + 1
            await trio.sleep(t)
            print(colorama.Fore.GREEN + f'Analyzed: {frame[1]} Delay: {time.time() - frame[2] - t:.3f}s')


class AnotherThread:
    def __init__(self):
        self.frame_number = -1

    def func(self,  send_to_trio):
        while True:
            # Since we're in a thread, we can't call methods on Trio
            # objects directly -- so we use trio.from_thread to call them.
            self.frame_number += 1
            frame = np.zeros((100, 100, 1))
            trio.from_thread.run(send_to_trio.send, [frame, self.frame_number, time.time()])
            time.sleep(0.5)

            print(colorama.Fore.CYAN + f'Frame {self.frame_number} available.')


test = TestAsync()
trio.run(test.run)
