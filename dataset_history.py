"""Module saving dataset IO stats"""

from collections import deque

MAX_COLLECTED_TIME = 3600
IO_STATS = ["c_total", "reads", "writes", "nread", "b_total", "nwritten", "nunlinks", "nunlinked"]
COLLECT_INTERVAL_SEC = 1
MAX_RECORDS = MAX_COLLECTED_TIME // COLLECT_INTERVAL_SEC

# pylint: disable=too-few-public-methods
class DatasetIOHistory:
    """Class representing dataset io history"""

    def __init__(self):
        self.stats = {}
        for param in IO_STATS:
            init_list = [-1] * MAX_RECORDS
            self.stats[param] = deque(init_list, maxlen=MAX_RECORDS)

    def add_node(self, stat):
        """Add new record"""
        for param in IO_STATS:
            self.stats[param].append(stat[param])
