"""Module for collecting pool IO."""

import subprocess
import threading
import time
import os
from collections import deque


RAID_TYPE = ["raidz", "raidz1", "raidz2", "raidz3", "mirror", "stripe"]
VDEV_TYPE = ["cache", "logs", "special", "spare", "data"]

MAX_SAMPLES = 300


class Device:
    """Class representing leaf vdev."""

    def __init__(self, name):
        """Initialize Device class

        Parameters:
        name - name of device
        """
        self.name = name
        self.device_io_stats = DeviceIOStats()
        self.device_latency_stats = DeviceLatencyStats()
        self.smart_stats = DeviceSmartStats()

    def get_io(self):
        """Returns read and write count a bandwidth

        Return touple (read_counts, write_counts, read_bandwith, write_bandwith)
        """
        return [
            self.device_io_stats.r_c,
            self.device_io_stats.w_c,
            self.device_io_stats.r_b,
            self.device_io_stats.w_b,
        ]

    def get_capacity(self):
        """Get capacity for vdev

        Return touple (used_space, free_space)
        """
        return [self.device_io_stats.c_u, self.device_io_stats.c_f]


class Raid:
    """Class representing raid of vdevs

    Vdevs are represented as Device class.
    Contains io and latency stats agregated from devices in raid.
    """

    def __init__(self, name, raid_type):
        """Create Raid class

        Parameters:
        name - name of raid (mirror-1, raidz2-3, ...)
        raid_type - redundany type of raid (mirror, stripe, raidz ...)
        """
        if raid_type == "raidz":
            raid_type = "raidz1"
        self.name = name
        self.raid_type = raid_type
        self.drive_count = 0
        self.devices = {}
        self.device_io_stats = DeviceIOStats()
        self.device_latency_stats = DeviceLatencyStats()

    def add_device(self, name, pool):
        """Add device to raid and pool

        Parameters:
        name - name of device
        pool - name of pool containing device
        """
        self.devices[name] = Device(name)
        pool.device[name] = self.devices[name]
        self.drive_count += 1

    def sum_io(self, sum_type):
        """Sum IO from devices in raid

        Parameters:
        sum_type - whether count logical or physical IO
        """
        if sum_type == "physical":
            return self.sum_io_physical()
        if sum_type == "logical":
            return self.sum_io_logical()
        return [0, 0, 0, 0]

    def sum_io_physical(self):
        """Sum physical IO"""
        io_stats = [0, 0, 0, 0]
        for drive in self.devices.values():
            # pylint: disable=consider-using-enumerate
            for stat in range(0, len(io_stats)):
                io_stats[stat] += drive.get_io()[stat]
        return io_stats

    def sum_io_logical(self):
        """Sum logical IO"""
        io_stats = self.sum_io_physical()
        mult_coef = 1
        div_coef = 1
        # coeficients for raids how to divide or multiply io stats
        if self.raid_type == "mirror":
            mult_coef = 1
            div_coef = self.drive_count
        # raidz write stripes of variable length, this calculation is only aproximation
        if self.raid_type == "raidz1":
            mult_coef = self.drive_count - 1
            div_coef = self.drive_count
        if self.raid_type == "raidz2":
            mult_coef = self.drive_count - 2
            div_coef = self.drive_count
        if self.raid_type == "raidz3":
            mult_coef = self.drive_count - 3
            div_coef = self.drive_count
        # pylint: disable=consider-using-enumerate
        for stat in range(0, len(io_stats)):
            io_stats[stat] = io_stats[stat] * mult_coef // div_coef
        return io_stats


# pylint: disable=too-few-public-methods
class PoolIOHistory:
    """Class storing pool io history records

    History is represented as queue of fixed length, initialy filled by -1.
    When new data are loaded from iostat thread, new values are appended to queues
    """

    def __init__(self):
        init_list = [-1] * MAX_SAMPLES
        self.physical_io_stats = {}
        self.logical_io_stats = {}
        self.latency_stats = {}
        for param in ["r_c", "w_c", "t_c", "r_b", "w_b", "t_b"]:
            self.physical_io_stats[param] = deque(init_list, maxlen=MAX_SAMPLES)
            self.logical_io_stats[param] = deque(init_list, maxlen=MAX_SAMPLES)
        for param in ["r_tw", "r_dw", "r_sw", "r_aw", "w_tw", "w_dw", "w_sw", "w_aw", "s_w", "t_w"]:
            self.latency_stats[param] = deque(init_list, maxlen=MAX_SAMPLES)


# pylint: disable=too-many-instance-attributes
class PoolIO:
    """Class storing pool IO

    Containt superset of Device class atributes

    Important atributes:
    name - name of pool
    raids - dictionary of raids by type
    devices - dictionary of devices by name
    """

    def __init__(self, name):
        self.name = name
        self.longest_drive_name = 0
        self.raids = {}
        self.device = {}
        self.device_io_stats_logical = DeviceIOStats()
        self.device_io_stats_physical = DeviceIOStats()
        self.device_io_stats = self.device_io_stats_logical
        self.device_latency_stats = DeviceLatencyStats()
        self.history = PoolIOHistory()
        self.device_io_new_data = False
        self.read_topology()

    def save_io_stats(self):
        """Save pool IO to history queue"""
        self.history.physical_io_stats["r_c"].append(self.device_io_stats_physical.r_c)
        self.history.physical_io_stats["w_c"].append(self.device_io_stats_physical.w_c)
        self.history.physical_io_stats["t_c"].append(
            self.device_io_stats_physical.r_c + self.device_io_stats_physical.w_c
        )
        self.history.physical_io_stats["r_b"].append(self.device_io_stats_physical.r_b)
        self.history.physical_io_stats["w_b"].append(self.device_io_stats_physical.w_b)
        self.history.physical_io_stats["t_b"].append(
            self.device_io_stats_physical.r_b + self.device_io_stats_physical.w_b
        )

        self.history.logical_io_stats["r_c"].append(self.device_io_stats_logical.r_c)
        self.history.logical_io_stats["w_c"].append(self.device_io_stats_logical.w_c)
        self.history.logical_io_stats["t_c"].append(
            self.device_io_stats_logical.r_c + self.device_io_stats_logical.w_c
        )
        self.history.logical_io_stats["r_b"].append(self.device_io_stats_logical.r_b)
        self.history.logical_io_stats["w_b"].append(self.device_io_stats_logical.w_b)
        self.history.logical_io_stats["t_b"].append(
            self.device_io_stats_logical.r_b + self.device_io_stats_logical.w_b
        )

    def save_latency_stats(self):
        """Save pool latency to history queue"""
        for param in ["r_tw", "r_dw", "r_sw", "r_aw", "w_tw", "w_dw", "w_sw", "w_aw", "s_w", "t_w"]:
            if self.device_latency_stats.stat[param] == "-":
                # Graph need numbers
                self.history.latency_stats[param].append(0)
            else:
                self.history.latency_stats[param].append(int(self.device_latency_stats.stat[param]))

    def read_topology(self):
        """Run zpool list and call parse_topology"""
        self.datasets = {}
        try:
            output = subprocess.run(
                ["/sbin/zpool", "list", "-vHLP", self.name],
                stdout=subprocess.PIPE,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError:
            return
        self.parse_topology(output.stdout.splitlines())

    def parse_topology(self, output):
        """Parse zpool list output and create topology graph"""
        self.longest_drive_name = 0
        raid_type = "data"
        raid = None
        output.pop(0)
        for line in output:
            field = line.split("\t")
            drive_type = field[0]

            try:
                drive_name = field[1]
            except IndexError:
                drive_type = line.split(" ")[0]
                drive_name = ""

            if drive_name.split("-")[0] in RAID_TYPE:
                raid = Raid(drive_name, drive_name.split("-")[0])
                try:
                    self.raids[raid_type].append(raid)
                except KeyError:
                    self.raids[raid_type] = []
                    self.raids[raid_type].append(raid)
                continue
            if drive_type in VDEV_TYPE:
                raid_type = drive_type
                raid = None
                continue
            if raid is None:
                raid = Raid("stripe0", "stripe")
                try:
                    self.raids[raid_type].append(raid)
                except KeyError:
                    self.raids[raid_type] = []
                    self.raids[raid_type].append(raid)

            if len(drive_name) > self.longest_drive_name:
                self.longest_drive_name = len(drive_name)
            index = len(self.raids[raid_type]) - 1
            self.raids[raid_type][index].add_device(drive_name, self)

    # pylint: disable=too-many-nested-blocks
    def fix_stripe_stats(self):
        """Calculate stats for stripes missing in zpool iostat"""
        for raid_type in self.raids.values():
            for raid in raid_type:
                if raid.raid_type == "stripe":
                    raid.device_io_stats.c_u = 0
                    raid.device_io_stats.c_f = 0
                    for param in [
                        "r_tw",
                        "r_dw",
                        "r_sw",
                        "r_aw",
                        "w_tw",
                        "w_dw",
                        "w_sw",
                        "w_aw",
                        "s_w",
                        "t_w",
                    ]:
                        raid.device_latency_stats.stat[param] = "-"
                    for device in raid.devices:
                        raid.device_io_stats.c_u += raid.devices[device].device_io_stats.c_u
                        raid.device_io_stats.c_f += raid.devices[device].device_io_stats.c_f
                        for param in [
                            "r_tw",
                            "r_dw",
                            "r_sw",
                            "r_aw",
                            "w_tw",
                            "w_dw",
                            "w_sw",
                            "w_aw",
                            "s_w",
                            "t_w",
                        ]:
                            if raid.devices[device].device_latency_stats.stat[param] != "-":
                                if raid.device_latency_stats.stat[param] == "-":
                                    raid.device_latency_stats.stat[param] = 0
                                raid.device_latency_stats.stat[param] += (
                                    int(raid.devices[device].device_latency_stats.stat[param])
                                    // raid.drive_count
                                )

    def calc_pool_io(self, sum_type):
        """Sum IO for pool"""
        io_stats = [0, 0, 0, 0]
        for raids in self.raids.values():
            for raid in raids:
                raid_io = raid.sum_io("physical")
                # pylint: disable=consider-using-enumerate
                for i in range(0, len(io_stats)):
                    io_stats[i] += raid_io[i]

        self.device_io_stats_physical.r_c = io_stats[0]
        self.device_io_stats_physical.w_c = io_stats[1]
        self.device_io_stats_physical.r_b = io_stats[2]
        self.device_io_stats_physical.w_b = io_stats[3]

        io_stats = [0, 0, 0, 0]
        # pylint: disable=consider-using-dict-items
        for raid_type in self.raids:
            for raid in self.raids[raid_type]:
                raid_io = raid.sum_io("logical")
                if raid_type in ("data", "special"):
                    # pylint: disable=consider-using-enumerate
                    for i in range(0, len(io_stats)):
                        io_stats[i] += raid_io[i]
                if raid_type == "cache":
                    io_stats[0] += raid_io[0]
                    io_stats[2] += raid_io[2]
                if raid_type == "logs":
                    io_stats[1] += raid_io[1]
                    io_stats[3] += raid_io[3]

        self.device_io_stats_logical.r_c = io_stats[0]
        self.device_io_stats_logical.w_c = io_stats[1]
        self.device_io_stats_logical.r_b = io_stats[2]
        self.device_io_stats_logical.w_b = io_stats[3]

        if sum_type == "physical":
            self.device_io_stats = self.device_io_stats_physical
        if sum_type == "logical":
            self.device_io_stats = self.device_io_stats_logical


class ZpoolWatcher:
    """Class running collecting threads"""

    def __init__(self, name, devices, raids, pool_io):
        self.pool_name = name
        self.pool_io = pool_io
        self.raids = raids
        self.devices = devices
        self.init_zpool_watcher()
        self.histogram = ["Collecting"]

    def get_raid_by_name(self, name):
        """Return Raid object by name"""
        for raid_type in self.raids.values():
            for raid in raid_type:
                if name == raid.name:
                    return raid
        return None

    def start_watchers(self):
        """Start collecting threads"""
        self.init_zpool_io_watcher()
        self.init_zpool_latency_watcher()
        self.init_zpool_histogram_watcher()
        self.get_smart()

    def init_zpool_watcher(self):
        """Fork collecting threads outside of main thread"""
        threading.Thread(target=self.start_watchers, daemon=True, name="WatcherStarter").start()

    def init_zpool_io_watcher(self):
        """Start pool IO collecting thread"""
        threading.Thread(target=self.zpool_io_watcher, daemon=True, name="ZpoolIOWatcher").start()

    def init_zpool_latency_watcher(self):
        """Start pool latency collecting thread"""
        threading.Thread(
            target=self.zpool_latency_watcher, daemon=True, name="ZpoolLatencyWatcher"
        ).start()

    def init_zpool_histogram_watcher(self):
        """Start pool histogram collecting thread"""
        threading.Thread(
            target=self.zpool_histogram_watcher, daemon=True, name="ZpoolHistogramWatcher"
        ).start()

    def init_smart(self):
        """Fork thread to collect smart"""
        threading.Thread(target=self.get_smart, daemon=True, name="Smart").start()

    def zpool_io_watcher(self):
        """IO and capacity collecting thread"""
        with subprocess.Popen(
            ["/sbin/zpool", "iostat", "-vHPLlp", self.pool_name, "5"],
            bufsize=1,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            errors="replace",
            env={"ZPOOL_SCRIPTS_AS_ROOT": "yes"},
        ) as process:
            os.set_blocking(process.stdout.fileno(), False)
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    time.sleep(5)
                if not line:
                    self.pool_io.calc_pool_io("logical")
                    self.pool_io.save_io_stats()
                    time.sleep(5)
                if line:
                    if len(line) > 3:
                        out = line.split()
                        name = out[0].replace("-part1", "")

                        c_u = out[1]
                        c_f = out[2]
                        r_c = out[3]
                        w_c = out[4]
                        r_b = out[5]
                        w_b = out[6]

                        if name[0] != "/":
                            raid = self.get_raid_by_name(name)
                            if raid is not None:
                                target = raid
                            else:
                                target = self.pool_io
                            target.device_io_stats.set_capacity_stats(c_u, c_f)

                            index = 7
                            for param in [
                                "r_tw",
                                "w_tw",
                                "r_dw",
                                "w_dw",
                                "r_sw",
                                "w_sw",
                                "r_aw",
                                "w_aw",
                                "s_w",
                                "t_w",
                            ]:
                                target.device_latency_stats.stat[param] = out[index]
                                index += 1
                            if raid is None:
                                target.save_latency_stats()
                                target.device_io_new_data = True
                            continue

                        index = 7
                        for param in [
                            "r_tw",
                            "w_tw",
                            "r_dw",
                            "w_dw",
                            "r_sw",
                            "w_sw",
                            "r_aw",
                            "w_aw",
                            "s_w",
                            "t_w",
                        ]:
                            self.devices[name].device_latency_stats.stat[param] = out[index]
                            index += 1

                        self.devices[name].device_io_stats.set_io_stats(r_c, w_c, r_b, w_b)
                        self.devices[name].device_io_stats.set_capacity_stats(c_u, c_f)

    def zpool_latency_watcher(self):
        """Latency collecting thread"""
        with subprocess.Popen(
            ["/sbin/zpool", "iostat", "-vHPL", "-c", "iostat-10s,temp", self.pool_name, "10"],
            bufsize=1,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            errors="replace",
            env={"ZPOOL_SCRIPTS_AS_ROOT": "yes"},
        ) as process:
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    time.sleep(5)
                if line:
                    if len(line) > 3:
                        out = line.split()
                        name = out[0]

                        if name[0] != "/":
                            continue

                        util = out[-2]
                        temp = out[-1]

                        if util == "-":
                            util = "?"
                        if len(out) > 9:
                            self.devices[name].device_io_stats.util = util
                        self.devices[name].smart_stats.temp = temp

    def zpool_histogram_watcher(self):
        """IO histogram collecting thread"""
        with subprocess.Popen(
            ["/sbin/zpool", "iostat", "-r", self.pool_name, "5"],
            bufsize=1,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            errors="replace",
            env={"ZPOOL_SCRIPTS_AS_ROOT": "yes"},
        ) as process:
            histogram = [""]
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    self.histogram = histogram
                    time.sleep(5)
                if line:
                    if "-----------------------------" in line:
                        self.histogram = histogram
                        histogram = [""]
                    else:
                        histogram.append(line)

    def get_smart(self):
        """Read smart for devices"""
        try:
            output = subprocess.run(
                [
                    "/sbin/zpool",
                    "iostat",
                    "-vHPL",
                    self.pool_name,
                    "-c",
                    "smart,smartx,realloc,serial,vendor,media,size,model",
                ],
                stdout=subprocess.PIPE,
                text=True,
                check=True,
                env={"ZPOOL_SCRIPTS_AS_ROOT": "yes"},
            )
        except subprocess.CalledProcessError:
            return
        for line in output.stdout.splitlines():
            if len(line) > 3:
                out = line.split()
                name = out[0].replace("-part1", "")

                c_u = out[1]
                c_f = out[2]

                if name[0] != "/":
                    raid = self.get_raid_by_name(name)
                    if raid is not None:
                        raid.device_io_stats.set_capacity_stats(c_u, c_f)
                    continue
                device = self.devices[name].smart_stats

                index = 7
                for param in [
                    "health",
                    "realloc",
                    "temp",
                    "ata_err",
                    "rep_ucor",
                    "cmd_to",
                    "pend_sec",
                    "off_ucor",
                    "hours_on",
                    "pwr_cyc",
                    "serial",
                    "vendor",
                    "media",
                    "size",
                ]:
                    try:
                        device.stat[param] = out[index]
                    except IndexError:
                        pass
                    index += 1
                device.stat["model"] = " ".join(out[index:])
                self.devices[name].device_io_stats.set_capacity_stats(c_u, c_f)


class DeviceIOStats:
    """Class contains device IO and capacity"""

    def __init__(self):
        self.c_u = 0
        self.c_f = 0
        self.r_c = 0
        self.r_b = 0
        self.w_c = 0
        self.w_b = 0
        self.util = "-"

    def set_capacity_stats(self, c_u, c_f):
        """Save device capacity"""
        if c_u == "-":
            self.c_u = "-"
        if c_f == "-":
            self.c_f = "-"
        if self.c_u != "-" and c_u.isnumeric():
            self.c_u = int(c_u)
        if self.c_f != "-" and c_f.isnumeric():
            self.c_f = int(c_f)

    def set_io_stats(self, r_c, w_c, r_b, w_b):
        """Set device IO stats"""
        self.r_c = int(r_c)
        self.r_b = int(r_b)
        self.w_c = int(w_c)
        self.w_b = int(w_b)


# pylint: disable=too-few-public-methods
# will be data class
class DeviceLatencyStats:
    """Class contains device IO latency"""

    def __init__(self):
        self.stat = {}
        for param in ["r_tw", "r_dw", "r_sw", "r_aw", "w_tw", "w_dw", "w_sw", "w_aw", "s_w", "t_w"]:
            self.stat[param] = "-"


# pylint: disable=too-few-public-methods
# will be data class
class DeviceSmartStats:
    """Smart stats for device"""

    def __init__(self):
        self.stat = {}
        for param in [
            "health",
            "realloc",
            "temp",
            "ata_err",
            "rep_ucor",
            "cmd_to",
            "pend_sec",
            "off_ucor",
            "hours_on",
            "pwr_cyc",
            "serial",
            "model",
            "vendor",
            "media",
            "size",
        ]:
            self.stat[param] = "?"


# pylint: disable=too-few-public-methods
# will be data class
class DeviceInfo:
    """Basic info about device"""

    def __init__(self):
        self.serial = ""
        self.model = ""
        self.vendor = ""
        self.type = ""
