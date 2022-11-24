"""Module for zpool"""

import subprocess
import threading
import re

import dataset_lib
import event_log
import zpool_io
import txgs
import reads_stats_lib

# pylint: disable=too-many-instance-attributes
class Zpool:
    """Class representing zfs pool"""

    def __init__(self, name):
        self.name = name
        self.init_datasets()
        self.get_properties()
        self.frag_hist = "... Collecting Data ...\n".splitlines()
        self.get_fragmentation()
        self.event_log = event_log.EventLog(name)
        self.pool_io = zpool_io.PoolIO(name)
        self.zpool_io_watcher = zpool_io.ZpoolWatcher(
            self.name, self.pool_io.device, self.pool_io.raids, self.pool_io
        )
        self.txgs = txgs.Txgs(self.name)
        self.read_stats = reads_stats_lib.PoolReadsStats(self.name, self.datasets)

    def init_datasets(self):
        """Create class for child datasets"""
        self.datasets = {}
        try:
            output = subprocess.run(
                ["zfs", "list", "-rHo", "name", self.name],
                stdout=subprocess.PIPE,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError:
            return
        for line in output.stdout.splitlines():
            self.datasets[line] = dataset_lib.Dataset(line)

    def get_fragmentation(self):
        """Call zdb in new thread to read fragmentation histogram"""
        threading.Thread(target=self.get_fragmentation_async, daemon=True, name="zdb").start()

    def get_fragmentation_async(self):
        """Parse zdb histogram output"""
        try:
            proc_out = subprocess.run(
                ["zdb", "-LM", self.name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
            output = proc_out.stdout
        except subprocess.CalledProcessError as exception:
            self.frag_hist = "ZDB error:\n".splitlines()
            self.frag_hist.append(exception.stderr)
            return
        match_vdev = re.compile(r"metaslabs.*\tpool", re.DOTALL)
        self.frag_hist = (
            match_vdev.search(output)
            .group()
            .replace("\t", "")
            .replace("fragmentation", "\nfragmentation")
            .splitlines()[:-1]
        )
        self.property["metaslabs"] = re.sub(r"( )(\1+)", r"\1", self.frag_hist[0]).split(" ")[1]
        self.frag_hist.pop(0)
        self.frag_hist.pop(0)

    def get_properties(self):
        """Read zpool properties"""
        properties = [
            "health",
            "size",
            "capacity",
            "dedupratio",
            "allocated",
            "free",
            "fragmentation",
            "autotrim",
            "freeing",
            "checkpoint",
            "readonly",
        ]
        try:
            output = subprocess.run(
                ["zpool", "get", "-Hpo", "value", ",".join(properties), self.name],
                stdout=subprocess.PIPE,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError:
            return
        i = 0
        self.property = {}
        for line in output.stdout.splitlines():
            self.property[properties[i]] = line
            i += 1
        self.property["metaslabs"] = "unknown"

    def get_datasets(self):
        """Return list of all pool datasets"""
        for dataset in self.datasets.values():
            datasets += [dataset.name]
        return datasets

    def get_dataset_by_id(self, dataset_id):
        """Return dataset by id"""
        for dataset in self.datasets.values():
            if int(dataset.property["objsetid"]) == int(dataset_id, 16):
                return dataset
        if dataset_id == "0x0":
            return self.datasets[self.name]
        return None
