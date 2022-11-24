"""Module for saving historic stats for pool reads"""

from collections import deque

MAX_RECORDS = 300

# pylint: disable=too-few-public-methods
class ReadsHistory:
    """Class representing history of pool reads"""

    def __init__(self):
        self.queue = deque(maxlen=MAX_RECORDS)

    def add_node(self, record):
        """Add new reads to queue"""
        self.queue.appendleft(record)
