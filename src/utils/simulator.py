import time

from nexus.module import Module, RunManager
from nexus.store import LMDBStore


class Simulator(Module):

    def __init__(self, *args, lmdb_path=None, emulate:str=None, **kwargs):
        super().__init__(*args, **kwargs)
        lmdb_path = 'output/lmdb_20190902_103315/'
        self.lmdb = LMDBStore(path=lmdb_path, load=True)

        self.lmdbdata: list = self.parse_obj_ids('Acquirer')
        self.gui_messages: dict = self.parse_obj_ids('GUI', type_='GUI')

        self.t0 = self.gui_messages['run']

    def parse_obj_ids(self, emulate: str, type_=None):
        # Get all out queue names
        emulate = f'q__{emulate}'
        keys = [key.decode() for key in self.lmdb.get_keys() if key.startswith(emulate.encode())]

        # Get relevant keys, convert to str, and sort. Then convert back to bytes.
        keys = [key.encode() for key in keys]

        lmdbdata_list = sorted(self.lmdb.get(keys, include_metadata=True), key=lambda lmdbdata: lmdbdata.time)

        # Extract data from stored objects
        if type_ == 'GUI':
            return {lmdbdata.obj: lmdbdata.time for lmdbdata in lmdbdata_list}

        else:
            return lmdbdata_list

    def move_to_plasma(self):
        for lmdbdata in self.lmdbdata:
            try:
                for i, obj_id in lmdbdata.obj[0].items():  # Get object ID
                    actual_obj = self.lmdb.get(obj_id)
                    lmdbdata.obj = [{i: self.client.put(actual_obj, lmdbdata.name)}]

            except AttributeError:
                pass

    def setup(self):
        self.client.use_hdd = False
        self.move_to_plasma()

    def run(self):
        with RunManager(self.name, self.runner, self.setup, self.q_sig, self.q_comm) as rm:
            print(rm)

    def runner(self):
        self.t_run = time.time()

        for i, lmdbdata in enumerate(self.lmdbdata):
            t_sleep = (lmdbdata.time + self.t_run - self.t0) - time.time()
            if t_sleep > 0:
                time.sleep(t_sleep)

            if self._get_queue_name(lmdbdata.name) == 'q_out':
                getattr(self, self._get_queue_name(lmdbdata.name)).put(lmdbdata.obj)

    def _get_queue_name(self, name):
        # Expected: 'q__Acquirer.q_out__124' -> {'q_out'}
        try:
            return name.split('__')[1].split('.')[1]
        except IndexError:
            return 'q_comm'


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
