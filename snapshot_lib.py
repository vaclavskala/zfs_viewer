"""Module for snapshots"""

import datetime
import subprocess
import time

# pylint: disable=too-few-public-methods
class Snapshot:
    """Class representing zfs snapshot"""

    def __init__(self, parent, name, size, creation):
        self.name = name
        self.short_name = name.split("@")[1]
        self.size = size
        self.parent = parent
        self.creation = creation
        self.holds = {}
        self.creation_human = datetime.datetime.fromtimestamp(int(creation)).strftime(
            "%b %d %H:%M %Y"
        )

    def get_holds(self):
        """Read holds for snapshot"""
        try:
            output = subprocess.run(
                ["/sbin/zfs", "holds", "-H", self.name],
                stdout=subprocess.PIPE,
                text=True,
                check=True,
                env={"LC_TIME": "c"},
            )
            if output.stdout != "":
                for line in output.stdout.splitlines():
                    self.parent.has_holds = True
                    tag = line.split("\t")[1]
                    creation_time = line.split("\t")[2]
                    timestamp = time.mktime(
                        datetime.datetime.strptime(creation_time, "%a %b %d %H:%M %Y").timetuple()
                    )
                    self.holds[tag] = int(timestamp)
        except subprocess.CalledProcessError:
            return
