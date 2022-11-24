"""Module for reading and storing eventlog"""

import threading
import subprocess
import os
import time
import weakref
import signal
import ctypes
from collections import deque


# pylint: disable=too-few-public-methods
class EventRecord:
    """One record in event log"""

    def __init__(self):
        self.rows = []

    def add_row(self, row):
        """Add row to record"""
        self.rows.append(row)


class EventLog:
    """Class for event log"""

    def __init__(self, name):
        self.__pool_name = name
        self.logs = deque(maxlen=100)
        self.__init_event_log()

    def __init_event_log(self):
        """Fork thread to stream event log"""
        threading.Thread(
            target=self.__event_log_loop, daemon=True, args=(weakref.ref(self),), name="EventLog"
        ).start()

    def __add_record(self, record):
        """Add record to event log"""
        if len(record.rows) > 0:
            record.add_row("\n")
            self.logs.appendleft(record)

    # pylint: disable=no-self-use
    def set_pdeathsig(self, sig=signal.SIGTERM):
        """Send kill to thread when parent terminates"""

        def kill_callable():
            libc = ctypes.CDLL("libc.so.6")
            return libc.prctl(1, sig)

        return kill_callable

    def __event_log_loop(self, _):
        # not important parameters, not needed to store
        field_blacklist = ["version", "history_hostname", "pool_guid", "history_time", "time"]
        # pylint: disable=subprocess-popen-preexec-fn
        with (
            subprocess.Popen(
                ["zpool", "events", "-vf", self.__pool_name],
                bufsize=1,
                preexec_fn=self.set_pdeathsig(signal.SIGTERM),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding="utf-8",
                errors="replace",
            )
        ) as process:
            os.set_blocking(process.stdout.fileno(), True)
            # read and ignore header
            process.stdout.readline()
            record = EventRecord()
            while True:
                real_self = self
                if real_self is None:
                    break
                del real_self
                line = process.stdout.readline()
                # start of new event
                if line and line[0] != " " and line[0] != "\n":
                    self.__add_record(record)
                    record = EventRecord()
                    record.add_row(line)
                # end of event
                if line and line[0] == "\n":
                    # usefull only to save record when waiting for output
                    self.__add_record(record)
                    record = EventRecord()
                # text of events
                if line and line[0] == " ":
                    event_type = line.split()[0]
                    if event_type not in field_blacklist:
                        record.add_row(line)
                #  wait for output
                if not line:
                    time.sleep(1)
            process.kill()
