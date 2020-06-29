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
from improv.actor import Actor, Spike, RunManager

class BasicWatcher(Actor):

    def __init__(self, *args):

        super().__init__(*args)

    def setup(self):
