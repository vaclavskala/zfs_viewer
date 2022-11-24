"""Module processing reads by pid"""

import threading
import time

import read_record_lib
import reads_stats_history

COLLECT_INTERVAL_SEC = 5

# ARC_FLAGS = {
#    "SYNC"          : 1 << 0,
#    "ASYNC"         : 1 << 1,
#    "PREFETCH"      : 1 << 2,
#    "CACHED"        : 1 << 3,
#    "ZFETCH"        : 1 << 5,
#    "SEND_PREFETCH" : 1 << 6
# }

# pylint: disable=too-few-public-methods
class ReadsStats:
    """Class saving reads stats for dataset"""

    def __init__(self):
        self.pid_stats = {}
        self.new_pid_stats = {}
        self.flags_stats = {}
        self.count = 0


# pylint: disable=too-many-instance-attributes
class PoolReadsStats:
    """Class saving pool wide read stats"""

    def __init__(self, name, datasets):
        self.pool_name = name
        self.datasets = datasets
        self.pid_map = {}
        self.dataset_stats = {}
        self.history = reads_stats_history.ReadsHistory()
        self.init_read_stats()
        self.data_time_window = 0
        self.last_uid = 0
        self.shift = 0

    def get_dataset_by_id(self, dataset_id):
        """Return dataset by id"""
        for dataset in self.datasets.values():
            if int(dataset.property["objsetid"]) == int(dataset_id, 16):
                return dataset
        if dataset_id == "0x0":
            return self.datasets[self.pool_name]
        return None

    def init_read_stats(self):
        """Fork thread to read reads"""
        threading.Thread(target=self.reads_stats_loop, daemon=True, name="ReadStats").start()

    def reads_stats_loop(self):
        """Loop to read reads stats"""
        self.get_time_shift()
        while True:
            self.load_read_stats()
            time.sleep(1)

    # pylint: disable=no-self-use
    def save_stats(self, dataset_name, dataset_stats, pid, aflags):
        """Save stats record"""
        try:
            _ = dataset_stats[dataset_name]
        except KeyError:
            dataset_stats[dataset_name] = ReadsStats()

        try:
            dataset_stats[dataset_name].pid_stats[pid] += 1
        except KeyError:
            dataset_stats[dataset_name].pid_stats[pid] = 1

        # pylint: disable=consider-using-dict-items
        for flag in read_record_lib.ARC_FLAGS:
            if (int(aflags, 16) & read_record_lib.ARC_FLAGS[flag]) != 0:
                try:
                    dataset_stats[dataset_name].flags_stats[flag] += 1
                except KeyError:
                    dataset_stats[dataset_name].flags_stats[flag] = 0

        dataset_stats[dataset_name].count += 1

    def calculate_stats(self):
        """Recalculate dataset stats"""
        dataset_stats = {}

        for record in self.history.queue:
            self.save_stats(record.dataset_name, dataset_stats, record.pid, record.aflags)

            if record.dataset_name != self.pool_name:
                self.save_stats(self.pool_name, dataset_stats, record.pid, record.aflags)
        self.dataset_stats = dataset_stats

    def get_time_shift(self):
        """Read shift between unix and zfs time"""
        filename = "/proc/spl/kstat/zfs/arcstats"
        with open(filename, "r", encoding="utf8") as temp_file:
            line = temp_file.readline()
            temp_file.close()
            if line:
                zfs_time = line.split()[6]
            timestamp = time.time() * 1000 * 1000 * 1000
            self.shift = timestamp - int(zfs_time)

    # pylint: disable=too-many-locals
    def load_read_stats(self):
        """Read reads for pool"""
        filename = "/proc/spl/kstat/zfs/" + self.pool_name + "/reads"
        with open(filename, "r", encoding="utf8") as read_stat_file:
            read_stat_file.readline()
            first = 0
            dataset_map_cache = {}
            pid_map = {}

            while True:
                line = read_stat_file.readline()
                if line:
                    array = line.split()
                    uid = array[0]
                    start = array[1]
                    if first == 0:
                        first = start
                    objset = array[2]
                    object_id = array[3]
                    aflags = array[6]
                    pid = array[7]
                    process_name = " ".join(map(str, array[8:]))

                    pid_map[pid] = process_name
                    self.pid_map[pid] = process_name

                    try:
                        dataset_name = dataset_map_cache[objset]
                    except KeyError:
                        if self.get_dataset_by_id(objset) is not None:
                            dataset_map_cache[objset] = self.get_dataset_by_id(objset).name
                            dataset_name = dataset_map_cache[objset]
                        else:
                            continue

                    read_stat = read_record_lib.ReadRecord(
                        uid, objset, dataset_name, object_id, aflags, pid, process_name
                    )

                    if int(uid) > self.last_uid:
                        self.history.add_node(read_stat)
                        self.last_uid = int(uid)
                else:
                    break
            self.data_time_window = (time.time() * 1000 * 1000 * 1000 - self.shift) - int(first)
            self.pid_map = pid_map
            self.calculate_stats()
