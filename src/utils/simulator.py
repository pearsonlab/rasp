import time

from pyarrow.plasma import ObjectID

from nexus.module import Module, RunManager
from nexus.store import LMDBStore


class Simulator(Module):

    def __init__(self, *args, lmdb_path=None, emulate: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.lmdb = LMDBStore(path=lmdb_path, load=True)
        self.lmdb_values: list = self.get_lmdb_values(emulate)

        self.gui_messages: dict = self.get_lmdb_values('GUI', func=lambda x: {lmdbdata.obj: lmdbdata.time for lmdbdata in x})
        self.t_saved_run = self.gui_messages['run']  # TODO Add GUI interventions
        self.t_start_run = None

    def get_lmdb_values(self, emulate: str, func=None):
        # Get all out queue names
        emulate = f'q__{emulate}'
        keys = [key.decode() for key in self.lmdb.get_keys() if key.startswith(emulate.encode())]

        # Get relevant keys, convert to str, and sort. Then convert back to bytes.
        keys = [key.encode() for key in keys]
        lmdb_values = sorted(self.lmdb.get(keys, include_metadata=True), key=lambda lmdb_value: lmdb_value.time)

        if func is not None:
            return func(lmdb_values)
        return lmdb_values

    def setup(self):
        self.client.use_hdd = False
        self.move_to_plasma(self.lmdb_values)
        self.put_setup(self.lmdb_values)

    def move_to_plasma(self, lmdb_values):
        """ Put objects into current plasma store and update object ID """
        # TODO Make async to enable queue-based fetch system tp avoid loading everything at once.
        for lmdbdata in lmdb_values:
            try:
                if len(lmdbdata.obj) == 1 and isinstance(lmdbdata.obj[0], dict):  # Raw frames
                    data = lmdbdata.obj[0]
                    for i, obj_id in data.items():
                        if isinstance(obj_id, ObjectID):
                            actual_obj = self.lmdb.get(obj_id, include_metadata=True)
                            lmdbdata.obj = [{i: self.client.put(actual_obj.obj, actual_obj.name)}]

                elif all([isinstance(obj, ObjectID) for obj in lmdbdata.obj]):  # Processor output
                    actual_objs = self.lmdb.get(lmdbdata.obj, include_metadata=True)
                    lmdbdata.obj = [self.client.put(obj.obj, obj.name) for obj in actual_objs]  # TODO Batch put in store

                else:  # Not object ID, do nothing.
                    pass

            except (TypeError, AttributeError):  # Something else.
                pass

    def put_setup(self, lmdb_values):
        for lmdb_value in lmdb_values:
            if lmdb_value.time < self.t_saved_run:
                getattr(self, lmdb_value.queue).put(lmdb_value.obj)

    def run(self):
        self.t_start_run = time.time()
        with RunManager(self.name, self.runner, self.setup, self.q_sig, self.q_comm) as rm:
            print(rm)

    def runner(self):
        for lmdb_value in self.lmdb_values:
            if lmdb_value.time >= self.t_saved_run:
                t_sleep = (lmdb_value.time + self.t_start_run - self.t_saved_run) - time.time()
                if t_sleep > 0:
                    time.sleep(t_sleep)
                getattr(self, lmdb_value.queue).put(lmdb_value.obj)

    #     policy = asyncio.get_event_loop_policy()
    #     policy.set_event_loop(policy.new_event_loop())
    #     self.loop = asyncio.get_event_loop()
    #
    #     self.aqueue = asyncio.Queue()
    #     self.loop.run_until_complete(self.arun())
    #
    # async def arun(self):
    #
    #
    #     funcs_to_run = [self.send_q, self.fetch_lmdb]
    #     async with AsyncRunManager(self.name, funcs_to_run, self.setup, self.q_sig, self.q_comm) as rm:
    #         print(rm)
    #
    # async def send_q(self):
    #
    #     for t in self.times:
    #         now = time.time()
    #         await asyncio.sleep(t - now)
    #         self.q_out.put(list(dict()))
    #
    # async
#
if '__name__' == '__main__':
    t = Simulator(name='test')
