"""Module for saving history stats"""

from collections import deque
import utils

EXPORTED_DATA = ["hits", "misses", "io_total", "size", "mru_size", "mfu_size", "hitrate"]
COLLECTED_DATA = ["hits", "misses", "size", "mru_size", "mfu_size", "hitrate"]
GRAPH_1 = ["mru_size", "mfu_size"]
GRAPH_2 = ["data_size", "metadata_size", "dnode_size", "dbuf_size", "bonus_size", "hdr_size"]
MAX_COLLECTED_TIME = 300
COLLECT_INTERVAL_SEC = 1
MAX_RECORDS = MAX_COLLECTED_TIME // COLLECT_INTERVAL_SEC

CONVERT_MAP = {
    "hitrate": utils.add_percent,
    "size": utils.convert_size,
    "mru_size": utils.convert_size,
    "mfu_size": utils.convert_size,
}

# pylint: disable=too-few-public-methods
class ArcHistory:
    """Class saving arcstats"""

    def __init__(self):
        self.stats = {}
        self.graph1_data = deque(maxlen=MAX_RECORDS)
        self.graph2_data = deque(maxlen=MAX_RECORDS)
        for param in ["time"] + EXPORTED_DATA:
            init_list = [-1] * MAX_RECORDS
            self.stats[param] = deque(init_list, maxlen=MAX_RECORDS)

        init_list = []
        for _ in range(0, MAX_RECORDS):
            node = []
            for param in GRAPH_1 + ["other_size"]:
                node.append(-1)
            init_list.append(node)
        self.graph1_data = deque(init_list, maxlen=MAX_RECORDS)

        init_list = []
        for _ in range(0, MAX_RECORDS):
            node = []
            for param in GRAPH_2:
                node.append(-1)
            init_list.append(node)
        self.graph2_data = deque(init_list, maxlen=MAX_RECORDS)

    def add_node(self, stat):
        """Add new stats to history queue"""
        for param in ["time"] + COLLECTED_DATA:
            self.stats[param].append(stat[param])
        self.stats["io_total"].append(int(stat["hits"]) + int(stat["misses"]))
        other_size = (
            stat["dnode_size"]
            + stat["dbuf_size"]
            + stat["bonus_size"]
            + stat["anon_size"]
            + stat["hdr_size"]
        )
        self.graph1_data.append((stat["mru_size"], stat["mfu_size"], other_size))
        self.graph2_data.append(
            (
                stat["data_size"],
                stat["metadata_size"],
                stat["dnode_size"],
                stat["dbuf_size"],
                stat["bonus_size"],
                stat["hdr_size"],
            )
        )
