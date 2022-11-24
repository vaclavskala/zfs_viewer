"""Module representing zfs subsystem"""

import subprocess
import curses
import threading
import time
import datetime
from collections import deque

import zpool_lib
import arc
import snapshot_lib


FRAGMENTATION_LIMIT_WARN = 20
FRAGMENTATION_LIMIT_ERR = 70
FREEING_LIMIT = 1073741824
CAPACITY_LIMIT_WARN = 85
CAPACITY_LIMIT_ERR = 92


class Zfs:
    """Class representing zfs subsystem"""

    def __init__(self):
        self.zpools = {}
        self.log = deque(maxlen=100)
        self.init_pools()
        self.read_snapshots()
        self.init_dbgmsg()
        self.arc = arc.Arc()

    # pylint: disable=no-self-use
    def read_pools(self):
        """Read pools from zfs"""
        try:
            pools = subprocess.run(
                ["zpool", "list", "-Ho", "name"], stdout=subprocess.PIPE, text=True, check=True
            ).stdout.splitlines()
            return pools
        except subprocess.CalledProcessError:
            curses.ungetch("q")
            return None

    def read_snapshots(self):
        """Get snapshots for dataset"""
        try:
            output = subprocess.run(
                ["zfs", "list", "-Hpo", "name,used,creation,userrefs", "-t", "snapshot"],
                stdout=subprocess.PIPE,
                text=True,
                check=True,
            )
            if output.stdout != "":
                for line in output.stdout.splitlines():
                    data = line.split("\t")
                    name = data[0]
                    used = data[1]
                    creation = data[2]
                    userrefs = data[3]
                    dataset_name = data[0].split("@")[0]
                    short_name = data[0].split("@")[1]
                    pool_name = line.split("/")[0]
                    self.zpools[pool_name].datasets[dataset_name].snapshot[
                        short_name
                    ] = snapshot_lib.Snapshot(
                        self.zpools[pool_name].datasets[dataset_name], name, used, creation
                    )
                    if int(userrefs) > 0:
                        self.zpools[pool_name].datasets[dataset_name].snapshot[
                            short_name
                        ].get_holds()
        except subprocess.CalledProcessError:
            return

    def init_pools(self):
        """Create Zpool class for every pool"""
        for line in self.read_pools():
            pool = zpool_lib.Zpool(line)
            self.zpools[line] = pool

    def get_pools(self):
        """Return list of pools"""
        return list(self.zpools.keys())

    def get_datasets(self):
        """Return list of datasets"""
        datasets = []
        for pool in self.zpools.values():
            for dataset in pool.datasets.values():
                datasets += [dataset.name]
        return datasets

    def rescan_pools(self):
        """Reread pools from zfs"""
        new_zpools = {}
        for line in self.read_pools():
            if line in self.zpools:
                new_zpools[line] = self.zpools[line]
            else:
                new_zpools[line] = zpool_lib.Zpool(line)
        self.zpools = new_zpools

    def dataset_by_name(self, name):
        """Return dataset object identified by dataset name"""
        pool_name = name.split("/")[0]
        return self.zpools[pool_name].datasets[name]

    def init_dbgmsg(self):
        """Run thread to read dbgmsg log"""
        threading.Thread(target=self.__dbgmsg_loop, daemon=True, name="Dbgmsg").start()

    def __dbgmsg_loop(self):
        last_valid_line = ""
        is_open = True
        while True:
            with open("/proc/spl/kstat/zfs/dbgmsg", "r", encoding="utf8") as dbgmsg:
                dbgmsg.readline()
                while True:
                    line = dbgmsg.readline()
                    if line and is_open:
                        timestamp = line.split()[0]
                        payload = line[len(timestamp) + 1 :]
                        time_string = datetime.datetime.fromtimestamp(int(timestamp)).strftime(
                            "%H:%M:%S"
                        )
                        self.log.appendleft(str(time_string) + str(payload))
                        last_line = line
                    if line == last_valid_line:
                        is_open = True
                    if not line:
                        last_valid_line = last_line
                        is_open = False
                        time.sleep(1)
                        break

    def zfs_reads_arc(self):
        """Check if logging arc hits is enabled"""
        with open(
            "/sys/module/zfs/parameters/zfs_read_history_hits", "r", encoding="utf8"
        ) as read_history_hits_file:
            value = read_history_hits_file.read(1)
        return bool(int(value))

    def snapshot_by_name(self, name):
        """Return snapshot object by name"""
        dataset = name.split("@")[0]
        snapshot = name.split("@")[1]
        return self.dataset_by_name(dataset).get_snapshot(snapshot)

    def read_holds(self):
        """Find snapshots with userrefs and than read holds for that snapshots"""
        try:
            output = subprocess.run(
                ["zfs", "get", "-Hpo", "name,value", "userrefs", "-t", "snapshot"],
                stdout=subprocess.PIPE,
                text=True,
                check=True,
            )
            if output.stdout != "":
                for line in output.stdout.splitlines():
                    name = line.split("\t")[0]
                    count = line.split("\t")[1]
                    if int(count) > 0:
                        self.snapshot_by_name(name).get_holds()
        except subprocess.CalledProcessError:
            return


# todo:
#    def rescan_datasets(self):
#        new_datasets = list()
#        for pool in self.zpools.keys():
#            for dataset in self.zpools[pool].datasets.values():
#                if dataset in pool[
#                datasets += [dataset.name]
##                if i == 1:
##                    return datasets
#        return datasets
