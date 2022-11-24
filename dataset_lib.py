"""Class for zfs datasets"""

import subprocess

import snapshot_lib
import dataset_io


class Dataset:
    """Class representing zfs dataset"""

    def __init__(self, name):
        self.name = name
        self.parent_pool = name.split("/")[0]
        self.get_properties()
        self.snapshot = {}
        self.has_holds = False
        # pylint: disable=invalid-name
        self.io = dataset_io.DatasetIO(self.parent_pool, self.property["objsetid"])

    def get_properties(self):
        """Read properties for dataset"""
        properties = [
            "used",
            "referenced",
            "available",
            "quota",
            "refquota",
            "usedbysnapshots",
            "mountpoint",
            "mounted",
            "recordsize",
            "compressratio",
            "compression",
            "atime",
            "acltype",
            "xattr",
            "devices",
            "exec",
            "setuid",
            "primarycache",
            "secondarycache",
            "sync",
            "encryption",
            "objsetid",
            "usedbydataset",
            "usedbychildren",
            "usedbyrefreservation",
        ]
        try:
            output = subprocess.run(
                ["zfs", "get", "-Hpo", "value", ",".join(properties), self.name],
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

    def get_snapshot(self, name):
        """Return snapshot by name"""
        return self.snapshot[name]

    def get_snapshots(self):
        """Get snapshots for dataset"""
        try:
            output = subprocess.run(
                ["zfs", "list", "-Hpo", "name,used,creation", "-t", "snapshot", self.name],
                stdout=subprocess.PIPE,
                text=True,
                check=True,
            )
            if output.stdout != "":
                for line in output.stdout.splitlines():
                    data = line.split("\t")
                    short_name = data[0].split("@")[1]
                    self.snapshot[short_name] = snapshot_lib.Snapshot(
                        self, data[0], data[1], data[2]
                    )
        except subprocess.CalledProcessError:
            return
