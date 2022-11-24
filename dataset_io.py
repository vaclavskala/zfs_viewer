"""Class for reading dataset IO"""

import threading
import time

import dataset_history

IO_STATS = [
    "c_total",
    "reads",
    "writes",
    "b_total",
    "nread",
    "nwritten",
    "nunlinks",
    "nunlinked",
    "del_queue",
]
COLLECT_INTERVAL_SEC = 5


class DatasetIO:
    """Class representing IO for one dataset"""

    def __init__(self, pool_name, objsetid):
        self.pool_name = pool_name
        self.objsetid = objsetid
        self.stats = {}
        self.stats_old = {}
        self.abs_stats = {}
        self.valid = -1
        for param in IO_STATS:
            self.abs_stats[param] = 0

        self.history = dataset_history.DatasetIOHistory()
        self.init_dataset_io_watcher()

    def init_dataset_io_watcher(self):
        """Run thread to start reading dataset_io"""
        threading.Thread(
            target=self.dataset_io_watcher, daemon=True, name="DatasetIOWatcher"
        ).start()

    def read_stats(self):
        """Read stats for dataset"""
        file_name = (
            "/proc/spl/kstat/zfs/" + self.pool_name + "/objset-" + str(hex(int(self.objsetid)))
        )
        try:
            with open(file_name, "r", encoding="utf8") as dataset_io:
                dataset_io.readline()
                dataset_io.readline()
                while True:
                    self.stats_old = self.stats
                    line = dataset_io.readline()
                    if line:
                        name = line.split()[0]
                        if name != "dataset_name":
                            value = int(line.split()[2])
                            self.stats[name] = value - self.abs_stats[name]
                            self.abs_stats[name] = value
                    else:
                        break
                self.stats["c_total"] = self.stats["reads"] + self.stats["writes"]
                self.stats["b_total"] = self.stats["nread"] + self.stats["nwritten"]
                self.stats["del_queue"] = self.abs_stats["nunlinks"] - self.abs_stats["nunlinked"]
                if self.valid < 1:
                    self.valid += 1
                else:
                    self.history.add_node(self.stats)
        except FileNotFoundError:
            self.valid = 0
            time.sleep(COLLECT_INTERVAL_SEC * 10)
            return

    def dataset_io_watcher(self):
        """Periodicaly read stats for dataset"""
        self.read_stats()
        time.sleep(COLLECT_INTERVAL_SEC)
        while True:
            self.read_stats()
            time.sleep(COLLECT_INTERVAL_SEC)
