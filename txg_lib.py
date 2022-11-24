"""Module for txg"""


class Txg:
    """Class representing one txg"""

    def __init__(self, index, birth):
        self.index = index
        self.birth = birth
        self.stats = {}

    def set_io_stats(self, ndirty, nread, nwritten, reads, writes):
        """Save io stats"""
        self.stats["ndirty"] = ndirty
        self.stats["nread"] = nread
        self.stats["nwritten"] = nwritten
        self.stats["reads"] = reads
        self.stats["writes"] = writes
        self.stats["total_b"] = nread + nwritten
        self.stats["total_c"] = reads + writes

    def set_time_stats(self, otime, qtime, wtime, stime):
        """Save time stats"""
        self.stats["otime"] = otime
        self.stats["qtime"] = qtime
        self.stats["wtime"] = wtime
        self.stats["stime"] = stime
