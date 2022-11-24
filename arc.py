"""Module for loading arc statistics"""

import threading
import time
import datetime
import re

import arc_history


class Arc:
    """Class representing arc cache"""

    def __init__(self):
        self.arc_history = arc_history.ArcHistory()
        self.stats = {}
        self.init_arc_stats()

    def init_arc_stats(self):
        """Start thread to load arc stats"""
        threading.Thread(target=self.arc_stats_loop, daemon=True, name="ArcStat").start()

    def arc_stats_loop(self):
        """Loop to periodicaly load stats"""
        self.stats["hits_total"] = 0
        self.stats["miss_total"] = 0
        # read arc stats after zfs_viewer init completed
        time.sleep(1)
        while True:
            self.load_stats()
            time.sleep(arc_history.COLLECT_INTERVAL_SEC)

    def load_stats(self):
        """Open arcstats and load statistics"""
        with open("/proc/spl/kstat/zfs/arcstats", "r", encoding="utf8") as arcstat:
            # header
            arcstat.readline()
            arcstat.readline()

            while True:
                line = arcstat.readline()
                if line:
                    parsed_line = re.sub(" +", " ", line)
                    name = parsed_line.split(" ")[0]
                    value = parsed_line.split(" ")[2]
                    self.stats[name] = int(value)
                else:
                    break

            if int(self.stats["hits_total"]) > 0:
                hits = int(self.stats["hits"]) - int(self.stats["hits_total"])
                miss = int(self.stats["misses"]) - int(self.stats["miss_total"])
                self.stats["hits_total"] = self.stats["hits"]
                self.stats["miss_total"] = self.stats["misses"]
                self.stats["hits"] = hits
                self.stats["misses"] = miss
                self.stats["time"] = datetime.datetime.fromtimestamp(int(time.time())).strftime(
                    "%H:%M:%S"
                )
                try:
                    self.stats["hitrate"] = round(
                        100
                        * int(self.stats["hits"])
                        / (int(self.stats["hits"]) + int(self.stats["misses"])),
                        2,
                    )
                except ZeroDivisionError:
                    self.stats["hitrate"] = 100
                self.arc_history.add_node(self.stats)
            else:
                self.stats["hits_total"] = self.stats["hits"]
                self.stats["miss_total"] = self.stats["misses"]
