"""Module for reading txgs stats"""

import threading
import time

import txg_lib
import txg_history


class Txgs:
    """Class for reading txfs stats"""

    def __init__(self, pool_name):
        self.__pool_name = pool_name
        self.history = txg_history.TxgHistory()
        self.last_txg = 0
        self.init_txg_stats()

    def init_txg_stats(self):
        """Fork thread to read txgs"""
        threading.Thread(target=self.txg_stats_loop, daemon=True, name="TxgReader").start()

    def txg_stats_loop(self):
        """Periodicaly collect stats"""
        while True:
            self.load_txgs()
            time.sleep(txg_history.COLLECT_INTERVAL_SEC)

    # pylint: disable=too-many-locals
    def load_txgs(self):
        """Load txgs stats"""
        filename = "/proc/spl/kstat/zfs/" + self.__pool_name + "/txgs"
        with open(filename, "r", encoding="utf8") as txg_stat:

            txg_stat.readline()

            while True:
                line = txg_stat.readline()
                if line:
                    array = line.split()
                    index = int(array[0])
                    state = array[2]

                    if (int(index) > self.last_txg) and (state == "C"):
                        birth = int(array[1])
                        ndirty = int(array[3])
                        nread = int(array[4])
                        nwritten = int(array[5])
                        reads = int(array[6])
                        writes = int(array[7])
                        otime = int(array[8])
                        qtime = int(array[9])
                        wtime = int(array[10])
                        stime = int(array[11])

                        txg = txg_lib.Txg(index, birth)
                        txg.set_io_stats(ndirty, nread, nwritten, reads, writes)
                        txg.set_time_stats(otime, qtime, wtime, stime)
                        self.history.add_node(txg)
                        self.last_txg = index
                else:
                    break

            txg_stat.close()
