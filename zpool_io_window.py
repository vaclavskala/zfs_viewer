"""Module for zpool io window"""

import curses

import graphic
import app_window
import scroll_pad
import utils
import gui
import time_graph
import zpool_io


PHYSICAL_IO_GRAPH_STATS = ["r_c", "w_c", "t_c", "r_b", "w_b", "t_b"]
LOGICAL_IO_GRAPH_STATS = PHYSICAL_IO_GRAPH_STATS
LATENCY_GRAPH_STATS = ["r_tw", "r_dw", "r_sw", "r_aw", "w_tw", "w_dw", "w_sw", "w_aw", "s_w", "t_w"]


class ZpoolIOSmallWindow(scroll_pad.ScrollPad):
    """Class for subwindow on zpool io window"""

    dist = 9

    def __init__(self, s_r, s_c, v_size_c, size_r, size_c, zfs, pool_menu, selection_menu):
        self.zfs = zfs
        self.pool_menu = pool_menu
        self.selection_menu = selection_menu
        super().__init__(s_r, s_c, 1, v_size_c, size_r, size_c, True)

    def print_header(self):
        """Call correct function to print header based on selected info type"""
        if (
            self.selection_menu.selected() == "IO-physical"
            or self.selection_menu.selected() == "IO-logical"
        ):
            self.print_io_header()
        if self.selection_menu.selected() == "latency":
            self.print_latency_header()
        if self.selection_menu.selected() == "smart":
            self.print_smart_header()
        if self.selection_menu.selected() == "info":
            self.print_info_header()

    def print_io_header(self):
        """Print header for logical and physical IO"""
        row = 0
        col = self.zfs.zpools[self.pool_menu.selected()].pool_io.longest_drive_name + self.dist
        # row1
        self.window.addstr(row, col + 1 * self.dist + 2, "capacity")
        self.window.addstr(row, col + 4 * self.dist + 0, "operations")
        self.window.addstr(row, col + 7 * self.dist + 0, "bandwidth")

        row += 1

        # row2
        self.window.addstr(row, col + 1 * self.dist, "used")
        self.window.addstr(row, col + 2 * self.dist, "free")
        self.window.addstr(row, col + 3 * self.dist, "read")
        self.window.addstr(row, col + 4 * self.dist, "write")
        self.window.addstr(row, col + 5 * self.dist, "total")
        self.window.addstr(row, col + 6 * self.dist, "read")
        self.window.addstr(row, col + 7 * self.dist, "write")
        self.window.addstr(row, col + 8 * self.dist, "total")
        self.window.addstr(row, col + 9 * self.dist, "util")

    def print_latency_header(self):
        """Print header for latency"""
        row = 0
        col = self.zfs.zpools[self.pool_menu.selected()].pool_io.longest_drive_name + self.dist
        # row1
        self.window.addstr(row, col + 1 * self.dist + 1, "total_wait")
        self.window.addstr(row, col + 3 * self.dist + 2, "disk_wait")
        self.window.addstr(row, col + 5 * self.dist + 2, "sync_wait")
        self.window.addstr(row, col + 7 * self.dist + 1, "async_wait")
        self.window.addstr(row, col + 9 * self.dist, "scrub")
        self.window.addstr(row, col + 10 * self.dist, "trim")

        row += 1

        # row2
        self.window.addstr(row, col + 1 * self.dist, "read")
        self.window.addstr(row, col + 2 * self.dist, "write")
        self.window.addstr(row, col + 3 * self.dist, "read")
        self.window.addstr(row, col + 4 * self.dist, "write")
        self.window.addstr(row, col + 5 * self.dist, "read")
        self.window.addstr(row, col + 6 * self.dist, "write")
        self.window.addstr(row, col + 7 * self.dist, "read")
        self.window.addstr(row, col + 8 * self.dist, "write")
        self.window.addstr(row, col + 9 * self.dist, "wait")
        self.window.addstr(row, col + 10 * self.dist, "wait")

    def print_smart_header(self):
        """Print header for smart"""
        row = 0
        col = self.zfs.zpools[self.pool_menu.selected()].pool_io.longest_drive_name + self.dist

        index = 1
        for param in [
            "health",
            "realloc",
            "ata_err",
            "rep_ucor",
            "cmd_to",
            "pend_sec",
            "off_ucor",
            "pwr_cyc",
            "hours_on",
            "temp",
        ]:
            self.window.addstr(row, col + index * self.dist, param)
            index += 1

    def print_info_header(self):
        """Print header for device info"""
        row = 0
        col = self.zfs.zpools[self.pool_menu.selected()].pool_io.longest_drive_name + self.dist

        index = 1
        for param in ["size", "media", "vendor", "serial", "model"]:
            self.window.addstr(row, col + index * self.dist * 2, param)
            index += 1

    def write_disk_data(self, row, device):
        """Call correct function to print device data based on selected data type"""
        col = self.zfs.zpools[self.pool_menu.selected()].pool_io.longest_drive_name + self.dist
        if (
            self.selection_menu.selected() == "IO-physical"
            or self.selection_menu.selected() == "IO-logical"
        ):
            self.write_disk_io_stats(row, col, device)
        if self.selection_menu.selected() == "latency":
            self.write_disk_latency_stats(row, col, device)
        if self.selection_menu.selected() == "smart":
            self.write_smart_stats(row, col, device)
        if self.selection_menu.selected() == "info":
            self.write_info_data(row, col, device)

    def write_raid_data(self, row, device):
        """Call correct function to print raid data based on selected data type"""
        col = self.zfs.zpools[self.pool_menu.selected()].pool_io.longest_drive_name + self.dist
        if (
            self.selection_menu.selected() == "IO-physical"
            or self.selection_menu.selected() == "IO-logical"
        ):
            self.write_raid_io_stats(row, col, device)
        if self.selection_menu.selected() == "latency":
            self.write_disk_latency_stats(row, col, device)

    def write_disk_io_stats(self, row, col, device):
        """Write disk IO stats"""
        self.add_line(row, col + 1 * self.dist, utils.convert_count(device.device_io_stats.c_u))
        self.add_line(row, col + 2 * self.dist, utils.convert_count(device.device_io_stats.c_f))
        self.add_line(row, col + 3 * self.dist, utils.convert_count(device.device_io_stats.r_c))
        self.add_line(row, col + 4 * self.dist, utils.convert_count(device.device_io_stats.w_c))
        self.add_line(
            row,
            col + 5 * self.dist,
            utils.convert_count(device.device_io_stats.r_c + device.device_io_stats.w_c),
        )
        self.add_line(row, col + 6 * self.dist, utils.convert_size(device.device_io_stats.r_b))
        self.add_line(row, col + 7 * self.dist, utils.convert_size(device.device_io_stats.w_b))
        self.add_line(
            row,
            col + 8 * self.dist,
            utils.convert_size(device.device_io_stats.r_b + device.device_io_stats.w_b),
        )
        self.add_line(row, col + 9 * self.dist, device.device_io_stats.util)

    def write_disk_latency_stats(self, row, col, device):
        """Write disk latency"""
        index = 1
        for param in ["r_tw", "w_tw", "r_dw", "w_dw", "r_sw", "w_sw", "r_aw", "w_aw", "s_w", "t_w"]:
            self.window.addstr(
                row,
                col + index * self.dist,
                utils.convert_time_ns(device.device_latency_stats.stat[param]),
            )
            index += 1

    def write_raid_io_stats(self, row, col, raid):
        """Write raid io stats"""
        if self.selection_menu.selected() == "IO-physical":
            io_stats = raid.sum_io("physical")
        if self.selection_menu.selected() == "IO-logical":
            io_stats = raid.sum_io("logical")
        self.add_line(row, col + 1 * self.dist, utils.convert_size(raid.device_io_stats.c_u))
        self.add_line(row, col + 2 * self.dist, utils.convert_size(raid.device_io_stats.c_f))
        self.add_line(row, col + 3 * self.dist, utils.convert_count(io_stats[0]))
        self.add_line(row, col + 4 * self.dist, utils.convert_count(io_stats[1]))
        self.add_line(row, col + 5 * self.dist, utils.convert_count(io_stats[0] + io_stats[1]))
        self.add_line(row, col + 6 * self.dist, utils.convert_size(io_stats[2]))
        self.add_line(row, col + 7 * self.dist, utils.convert_size(io_stats[3]))
        self.add_line(row, col + 8 * self.dist, utils.convert_size(io_stats[2] + io_stats[3]))

    def write_smart_stats(self, row, col, device):
        """Write smart stats for device"""
        if not isinstance(device, zpool_io.Device):
            return
        index = 1
        for param in [
            "health",
            "realloc",
            "ata_err",
            "rep_ucor",
            "cmd_to",
            "pend_sec",
            "off_ucor",
            "pwr_cyc",
            "hours_on",
            "temp",
        ]:
            self.window.addstr(row, col + index * self.dist, device.smart_stats.stat[param])
            index += 1

    def write_info_data(self, row, col, device):
        """Write device info"""
        if not isinstance(device, zpool_io.Device):
            return

        index = 1
        for param in ["size", "media", "vendor", "serial", "model"]:
            self.window.addstr(row, col + index * self.dist * 2, device.smart_stats.stat[param])
            index += 1

    # pylint: disable=too-many-branches,too-many-statements
    def _draw(self):
        """Main draw function"""
        color_map = {
            "data": graphic.COLOR_FG_GREEN,
            "cache": graphic.COLOR_FG_BLUE,
            "logs": graphic.COLOR_FG_CYAN,
            "special": graphic.COLOR_FG_YELLOW,
            "spare": graphic.COLOR_FG_RED,
        }

        self.zfs.zpools[self.pool_menu.selected()].pool_io.fix_stripe_stats()

        self.window.erase()
        pool = self.zfs.zpools[self.pool_menu.selected()]

        if self.selection_menu.selected() == "IO-physical":
            pool.pool_io.calc_pool_io("physical")
        if self.selection_menu.selected() == "IO-logical":
            pool.pool_io.calc_pool_io("logical")

        self.print_header()

        if self.selection_menu.selected() == "histogram":
            row = 0
            for line in pool.zpool_io_watcher.histogram[2:5]:
                self.window.addstr(row, 1, line)
                row += 1
            for line in pool.zpool_io_watcher.histogram[5:]:
                col = 1
                fields = line.split()
                for field in fields:
                    if field == "0":
                        self.add_line(row, col, field, curses.A_DIM)
                    else:
                        self.add_line(row, col, field)
                    if col == 1:
                        col = 17
                    else:
                        col += 7
                row += 1
            return

        raids = pool.pool_io.raids

        self.window.addstr(2, 2, self.pool_menu.selected())
        self.write_disk_data(2, self.zfs.zpools[self.pool_menu.selected()].pool_io)
        row = 3
        shift = 2
        col = 2
        for raid_type in raids:
            color = color_map[raid_type]
            self.window.attrset(curses.color_pair(color))
            col += shift
            self.window.addstr(row, col, raid_type)
            self.window.addch(
                row, col - shift + 1, curses.ACS_HLINE, curses.color_pair(graphic.COLOR_FG_WHITE)
            )
            if raid_type != list(raids.keys())[-1]:
                self.window.addch(
                    row, col - shift, curses.ACS_LTEE, curses.color_pair(graphic.COLOR_FG_WHITE)
                )
            else:
                self.window.addch(
                    row, col - shift, curses.ACS_LLCORNER, curses.color_pair(graphic.COLOR_FG_WHITE)
                )
            row += 1
            for raid in raids[raid_type]:
                col += shift
                if raid != raids[raid_type][-1]:
                    self.window.addch(row, col - shift, curses.ACS_LTEE)
                else:
                    if raid_type == "spare":
                        self.window.addch(row, col - shift, curses.ACS_LTEE)
                    else:
                        self.add_ch(row, col - shift, curses.ACS_LLCORNER)
                if raid_type != "spare":
                    self.window.hline(row, col - shift + 1, curses.ACS_HLINE, shift - 1)
                    self.window.addstr(row, col, raid.name)
                    self.write_raid_data(row, raid)
                else:
                    row -= 1
                if raid_type != list(raids.keys())[-1]:
                    self.window.addch(
                        row,
                        col - shift * 2,
                        curses.ACS_VLINE,
                        curses.color_pair(graphic.COLOR_FG_WHITE),
                    )
                row += 1
                for device in raid.devices:
                    col += shift
                    self.add_line(row, col - shift, "")
                    self.window.addch(row, col - shift, curses.ACS_LTEE)
                    if raid_type != "spare":
                        self.window.hline(row, col - shift + 1, curses.ACS_HLINE, shift - 1)
                    else:
                        self.window.hline(row, col - 2 * shift + 1, curses.ACS_HLINE, shift)
                        self.window.addch(row, col - 2 * shift, curses.ACS_LTEE)
                        col -= shift
                    self.window.addstr(
                        row, col, raid.devices[device].name, curses.color_pair(color)
                    )
                    self.write_disk_data(row, raid.devices[device])
                    row += 1
                    col -= shift
                    try:
                        if raid != raids[raid_type][-1]:
                            self.window.addch(row - 1, col - shift, curses.ACS_VLINE)
                    except KeyError:
                        pass
                    try:
                        if raid_type != list(raids.keys())[-1]:
                            self.window.addch(
                                row - 1,
                                col - shift * 2,
                                curses.ACS_VLINE,
                                curses.color_pair(graphic.COLOR_FG_WHITE),
                            )
                    except KeyError:
                        pass
                    if raid_type == "spare":
                        col += shift

                if raid_type == "spare":
                    col -= shift
                self.window.addch(row - 1, col, curses.ACS_LLCORNER)
                col -= shift
            col -= shift
            self.window.attrset(0)


# pylint: disable=too-many-instance-attributes
class ZpoolIOWindow(app_window.AppWindow):
    """Class for zpool_io window"""

    def __init__(self, main_screen, zfs):
        self.zfs = zfs
        super().__init__(main_screen, 3, 1)
        rows, cols = self.window.getmaxyx()
        row, col = self.window.getbegyx()

        self.pool_menu = graphic.VerticalMenu(zfs.get_pools(), row + 1, col + 2)

        self.selection_menu = graphic.HorizontalMenu(
            ["IO-physical", "IO-logical", "latency", "histogram", "smart", "info"],
            row + 1,
            col + 2 + self.pool_menu.get_size()[1],
            br=curses.ACS_RTEE,
            bl=curses.ACS_BTEE,
        )

        self.zpool_io_win = ZpoolIOSmallWindow(
            row + 3,
            col + 2 + self.pool_menu.get_size()[1],
            60,
            25,
            cols - 3 - self.pool_menu.get_size()[1],
            self.zfs,
            self.pool_menu,
            self.selection_menu,
        )

        self.time_graph_pio_menu = graphic.HorizontalMenu(
            PHYSICAL_IO_GRAPH_STATS,
            row + rows // 2 - 3,
            col,
            br=curses.ACS_BTEE,
            bl=curses.ACS_LTEE,
        )

        self.time_graph_lio_menu = graphic.HorizontalMenu(
            LOGICAL_IO_GRAPH_STATS, row + rows // 2 - 3, col, br=curses.ACS_BTEE, bl=curses.ACS_LTEE
        )

        self.time_graph_lat_menu = graphic.HorizontalMenu(
            LATENCY_GRAPH_STATS, row + rows // 2 - 3, col, br=curses.ACS_BTEE, bl=curses.ACS_LTEE
        )

        self.set_time_menu_visibility()

        self.time_graph = time_graph.TimeGraph(
            row + rows // 2 + 2,
            col + 1,
            rows // 2 - 2,
            cols - 2,
            self.zfs.zpools[self.pool_menu.selected()].pool_io.history.physical_io_stats["t_c"],
        )
        self.time_graph.enable_x_scale(5, utils.convert_time_s)

        self.register_element(self.zpool_io_win)
        self.zpool_io_win.select()
        self.set_time_graph_source()

        self.menu_convert_map = {
            "r_c": utils.convert_count,
            "w_c": utils.convert_count,
            "t_c": utils.convert_count,
            "r_b": utils.convert_size,
            "w_b": utils.convert_size,
            "t_b": utils.convert_size,
        }

        self.set_correct_covert_funct()

    def set_correct_covert_funct(self):
        """What function to use to convert values"""
        funct = utils.cat
        if self.selection_menu.selected() in ("IO-physical", "histogram", "smart", "info"):
            try:
                funct = self.menu_convert_map[self.time_graph_pio_menu.selected()]
            except KeyError:
                funct = utils.cat
        if self.selection_menu.selected() == "IO-logical":
            try:
                funct = self.menu_convert_map[self.time_graph_lio_menu.selected()]
            except KeyError:
                funct = utils.cat
        if self.selection_menu.selected() == "latency":
            funct = utils.convert_time_ns
        self.time_graph.set_convert_funct(funct)

    def set_time_menu_visibility(self):
        """Show correct menu for time graph"""
        self.time_graph_pio_menu.hide(True)
        self.time_graph_lio_menu.hide(True)
        self.time_graph_lat_menu.hide(True)
        self.active_menu = self.time_graph_pio_menu
        if self.selection_menu.selected() == "IO-physical":
            self.time_graph_pio_menu.hide(False)
        if self.selection_menu.selected() == "IO-logical":
            self.time_graph_lio_menu.hide(False)
            self.active_menu = self.time_graph_lio_menu
        if self.selection_menu.selected() == "latency":
            self.time_graph_lat_menu.hide(False)
            self.active_menu = self.time_graph_lat_menu
        if self.selection_menu.selected() in ("info", "smart", "histogram"):
            self.time_graph_pio_menu.hide(False)

    def resize(self, s_r, s_c, row, col):
        """Resize objects on screen"""
        self.resize_window()
        row, col = self.window.getbegyx()
        rows, cols = self.window.getmaxyx()

        if gui.Gui.gui_hidden:
            pad_c = 1
        else:
            pad_c = 2

        self.pool_menu.resize()
        self.pool_menu.move_window(row + 1, col + 2)
        self.zpool_io_win.resize(
            row + 3,
            self.pool_menu.get_size()[1] + col + 2,
            (rows - row) // 2 - 2,
            cols - col - self.pool_menu.get_size()[1] + pad_c - 4,
        )
        self.time_graph.resize(
            row + rows - (rows // 2) - pad_c + 3, col + 1, rows - (rows - row) // 2 - 4, cols - 2
        )
        self.selection_menu.move_window(row + 1, cols - 67 + pad_c)

        self.time_graph_pio_menu.move_window(row + rows - rows // 2 + 1 - pad_c, col + 1)
        self.time_graph_lio_menu.move_window(row + rows - rows // 2 + 1 - pad_c, col + 1)
        self.time_graph_lat_menu.move_window(row + rows - rows // 2 + 1 - pad_c, col + 1)

        self.draw()
        self.refresh()

    def rescan(self):
        """Rescan when new pool created"""

    #        pass
    #        entry_id = self.pool_menu.entry_id
    #        del self.pool_menu
    #        self.zfs.rescan_pools()
    #        self.pool_menu = graphic.VerticalMenu(self.window, self.zfs.get_pools(), 1, 2, 1)

    def _draw(self):
        """Main draw function"""
        self.window.erase()
        self.window.border()
        self.window.noutrefresh()
        self.time_graph.draw()
        self.zpool_io_win.draw()
        self.pool_menu.draw()
        self.selection_menu.draw()
        self.time_graph_pio_menu.draw()
        self.time_graph_lio_menu.draw()
        self.time_graph_lat_menu.draw()
        self.refresh()

    def set_time_graph_source(self):
        """Change source of data for graph on pool,stats_type or specific stat change"""
        common_source = self.zfs.zpools[self.pool_menu.selected()].pool_io.history
        source = common_source.physical_io_stats[self.time_graph_pio_menu.selected()]
        if self.selection_menu.selected() == "IO-logical":
            source = common_source.physical_io_stats[self.time_graph_lio_menu.selected()]
        if self.selection_menu.selected() == "latency":
            source = common_source.latency_stats[self.time_graph_lat_menu.selected()]
        self.time_graph.change_source(source)

    def handle_key(self, char):
        """Handle pressed key"""
        if char == curses.KEY_DOWN:
            self.pool_menu.move_right()
            self.set_time_graph_source()
        if char == curses.KEY_UP:
            self.pool_menu.move_left()
            self.set_time_graph_source()
        if char == curses.KEY_NPAGE:
            for item in self.get_selected_elements():
                item.scroll_down()
        if char == curses.KEY_PPAGE:
            for item in self.get_selected_elements():
                item.scroll_up()
        if chr(char) == "h":
            self.selection_menu.move_left()
            self.set_time_menu_visibility()
            self.set_time_graph_source()
            self.set_correct_covert_funct()
            self.zpool_io_win.reset_autoscroll()
        if chr(char) == "l":
            self.selection_menu.move_right()
            self.set_time_menu_visibility()
            self.set_time_graph_source()
            self.set_correct_covert_funct()
            self.zpool_io_win.reset_autoscroll()
        if char == 72:
            self.active_menu.move_left()
            self.set_time_graph_source()
            self.set_correct_covert_funct()
        if char == 76:
            self.active_menu.move_right()
            self.set_time_graph_source()
            self.set_correct_covert_funct()
        #        if chr(char) == '+':
        #            self.time_graph.zoom_in()
        #        if chr(char) == '-':
        #            self.time_graph.zoom_out()
        self.draw()
