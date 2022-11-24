"""Module for historic records for txgs"""

from collections import deque
import utils

COLLECTED_DATA = [
    "index",
    "birth",
    "ndirty",
    "nread",
    "nwritten",
    "reads",
    "writes",
    "otime",
    "qtime",
    "wtime",
    "stime",
    "total_c",
    "total_b",
]
MENU_VIEW_DATA = [
    "index",
    "ndirty",
    "reads",
    "nread",
    "writes",
    "nwritten",
    "otime",
    "wtime",
    "stime",
]
GRAPH_VIEW_DATA = [
    "ndirty",
    "reads",
    "nread",
    "total_c",
    "writes",
    "nwritten",
    "total_b",
    "otime",
    "qtime",
    "wtime",
    "stime",
]
MAX_COLLECTED_TIME = 180
COLLECT_INTERVAL_SEC = 1
MAX_RECORDS = MAX_COLLECTED_TIME // COLLECT_INTERVAL_SEC

CONVERT_MAP = {
    "ndirty": utils.convert_size,
    "nread": utils.convert_size,
    "nwritten": utils.convert_size,
    "total_b": utils.convert_size,
}

# pylint: disable=too-few-public-methods
class TxgHistory:
    """Pool txg history"""

    def __init__(self):
        self.stats = {}
        for param in ["time"] + COLLECTED_DATA:
            init_list = [-1] * MAX_RECORDS
            self.stats[param] = deque(init_list, maxlen=MAX_RECORDS)

    def add_node(self, txg):
        """Add new txg record"""
        self.stats["index"].append(txg.index)
        self.stats["birth"].append(txg.birth)
        for param in GRAPH_VIEW_DATA:
            self.stats[param].append(txg.stats[param])
