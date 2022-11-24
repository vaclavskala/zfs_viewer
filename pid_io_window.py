"""Window for showing pool reads by PID"""

import curses

import graphic
import window
import scroll_pad
import utils
import gui
import row_graph
import reads_stats_history


class PIDWindowBarGraph(graphic.BarGraph):
    """Bar graph for reads flags"""

    def __init__(self, dataset_menu, zfs, values, s_r, s_c, size_r, size_c, colors=None):
        if colors is None:
            colors = {}
        self.menu = dataset_menu
        self.zfs = zfs
        self.last_uid = 0
        super().__init__(values, s_r, s_c, size_r, size_c, colors)
        self.prepare_data()

    def prepare_data(self):
        """Convert data to bar graph format"""
        self.values = {}
        self.flags_name_map = {}
        self.flags_name_map["A"] = "ASYNC"
        self.flags_name_map["P"] = "PREFETCH"
        self.flags_name_map["C"] = "CACHED"
        self.flags_name_map["Z"] = "ZFETCH"
        self.flags_name_map["S"] = "SEND"

        try:
            stats = self.zfs.zpools["pool1"].read_stats.dataset_stats["pool1"].flags_stats
        except KeyError:
            stats = {}
        #    "SYNC"          : 1 << 0,
        #    "ASYNC"         : 1 << 1,
        #    "PREFETCH"      : 1 << 2,
        #    "CACHED"        : 1 << 3,
        #    "ZFETCH"        : 1 << 5,
        #    "SEND_PREFETCH" : 1 << 6

        #    "S" : 1 << 0,
        #    "A" : 1 << 1,
        #    "P" : 1 << 2,
        #    "C" : 1 << 3,
        #    "Z" : 1 << 5,
        #    "S" : 1 << 6

        for key in stats:
            try:
                self.values[self.flags_name_map[key]] = stats[key]
            except KeyError:
                continue
        self.calculate_sizes()

    def _draw(self):
        """Main draw function"""
        # todo zfs_utils
        try:
            if self.last_uid < int(
                self.zfs.zpools[self.menu.selected().split("/")[0]].read_stats.history.queue[0].uid
            ):
                self.last_uid = int(self.zfs.zpools["pool1"].read_stats.history.queue[0].uid)
                self.prepare_data()
        except IndexError:
            pass
        super()._draw()


class PIDRowGraph(row_graph.RowGraph):
    """Row graph for graph pid by reads"""

    def __init__(self, s_r, s_c, size_r, size_c, zfs, menu):
        self.s_r = s_r
        self.s_c = s_c
        self.size_r = size_r
        self.size_c = size_c
        self.zfs = zfs
        self.menu = menu
        super().__init__(s_r, s_c, size_r, size_c)

    def prepare_data(self):
        """Prepare data for row graph format"""
        dataset = self.zfs.dataset_by_name(self.menu.selected())
        pool = dataset.name.split("/")[0]
        try:
            source = self.zfs.zpools[pool].read_stats.dataset_stats[dataset.name].pid_stats
        except KeyError:
            source = {}
        out = {}
        for key in source:
            process_name = self.zfs.zpools[pool].read_stats.pid_map[key]
            out[process_name + " (" + key + ")"] = source[key]
        self.set_values(out)


class PIDDatasetRowGraph(row_graph.RowGraph):
    """Row graph for showing datasets by reads count"""

    def __init__(self, s_r, s_c, size_r, size_c, zfs):
        self.s_r = s_r
        self.s_c = s_c
        self.size_r = size_r
        self.size_c = size_c
        self.zfs = zfs
        super().__init__(s_r, s_c, size_r, size_c)

    def prepare_data(self):
        """Convert data to row graph format"""
        out = {}
        for pool in self.zfs.get_pools():
            for dataset in self.zfs.zpools[pool].read_stats.dataset_stats:
                if pool != dataset:
                    try:
                        out[dataset] = self.zfs.zpools[pool].read_stats.dataset_stats[dataset].count
                    except KeyError:
                        continue
        self.set_values(out)


class PIDWindow(window.AppWindow):
    """Main app window for PID tab"""

    def __init__(self, main_screen, zfs):
        self.zfs = zfs
        super().__init__(main_screen, 3, 1)
        rows, cols = self.window.getmaxyx()
        row, col = self.window.getbegyx()
        self.dataset_menu = graphic.VerticalMenu(zfs.get_datasets(), 4, 2, 0, 0, cols // 4)
        self.pid_small_window = PIDSmallWindow(
            row + 1,
            self.dataset_menu.get_size()[1] + col + 2,
            rows - 7,
            (cols - self.dataset_menu.get_size()[1]) // 2,
            self.zfs,
            self.dataset_menu,
        )
        self.pid_row_graph = PIDRowGraph(
            row + 3,
            self.pid_small_window.s_c + self.pid_small_window.w_size_c,
            (rows - 2) // 2 - 2,
            cols - (self.pid_small_window.s_c + self.pid_small_window.w_size_c),
            self.zfs,
            self.dataset_menu,
        )
        self.pid_stats_window = PIDStatsWindow(
            self.pid_row_graph.window.getbegyx()[0] - 3,
            self.pid_row_graph.window.getbegyx()[1] + 1,
            3,
            cols - self.pid_row_graph.window.getbegyx()[1] - 2,
            self.zfs,
            self.dataset_menu,
        )
        self.dataset_row_graph = PIDDatasetRowGraph(
            self.pid_row_graph.window.getbegyx()[0] + self.pid_row_graph.window.getmaxyx()[0],
            self.pid_row_graph.window.getbegyx()[1],
            (rows - 2) // 2,
            cols - self.pid_row_graph.window.getbegyx()[1],
            zfs,
        )
        self.flags_bar = PIDWindowBarGraph(
            self.dataset_menu,
            self.zfs,
            [],
            rows - 3,
            2,
            5,
            cols - 3 - self.pid_stats_window.window.getmaxyx()[1] - 1,
        )
        self.pid_row_graph.prepare_data()
        self.register_element(self.pid_small_window)
        self.pid_small_window.select()
        self.draw()

    def resize(self, s_r, s_c, row, col):
        """Resize objects on window resize"""
        self.window.erase()
        self.resize_window()
        row, col = self.window.getbegyx()
        rows, cols = self.window.getmaxyx()
        self.dataset_menu.set_max_size(rows - 7)
        self.dataset_menu.resize()
        if gui.Gui.gui_hidden:
            pad_c = 1
        else:
            pad_c = 2
        self.dataset_menu.move_window(row + 1, col + 1)
        rows, cols = self.window.getmaxyx()
        row, col = self.window.getbegyx()

        self.pid_small_window.resize(
            row + 1,
            self.dataset_menu.get_size()[1] + col + 2,
            rows - 7,
            (cols - self.dataset_menu.get_size()[1]) // 2,
        )
        self.pid_row_graph.resize(
            row + 3,
            self.pid_small_window.s_c + self.pid_small_window.w_size_c,
            (rows - 2) // 2 - 2,
            cols - (self.pid_small_window.s_c + self.pid_small_window.w_size_c),
        )
        self.pid_stats_window.resize(
            self.pid_row_graph.window.getbegyx()[0] - 3,
            self.pid_row_graph.window.getbegyx()[1] + 1,
            3,
            cols - self.pid_row_graph.window.getbegyx()[1] - 2,
        )
        self.dataset_row_graph.resize(
            self.pid_row_graph.window.getbegyx()[0] + self.pid_row_graph.window.getmaxyx()[0],
            self.pid_row_graph.window.getbegyx()[1],
            rows - 4 - self.pid_row_graph.window.getmaxyx()[0],
            cols - self.pid_row_graph.window.getbegyx()[1],
        )

        self.flags_bar.resize(
            rows - 6 + self.window.getbegyx()[0],
            pad_c,
            5,
            cols - 3 - self.pid_stats_window.window.getmaxyx()[1] + 1 - pad_c,
        )
        self.flags_bar.window.noutrefresh()

        self.draw()
        self.refresh()

    def rescan(self):
        """Rescan"""
        # todo
        del self.dataset_menu
        self.zfs.rescan_datasets()
        self.dataset_menu = graphic.VerticalMenu(self.window, self.zfs.get_datasets(), 4, 2, 1)

    def _draw(self):
        self.window.border()
        self.window.noutrefresh()
        self.pid_row_graph.prepare_data()
        self.dataset_menu.draw()
        self.pid_small_window.draw()
        self.pid_row_graph.draw()
        self.pid_stats_window.draw()
        self.dataset_row_graph.prepare_data()
        self.dataset_row_graph.draw()
        self.flags_bar.draw()

        self.refresh()

    def handle_key(self, char):
        """Handle user input"""
        if char == curses.KEY_DOWN:
            self.dataset_menu.move_right()
        if char == curses.KEY_UP:
            self.dataset_menu.move_left()
        if char == curses.KEY_NPAGE:
            for item in self.get_selected_elements():
                item.scroll_down()
        if char == curses.KEY_PPAGE:
            for item in self.get_selected_elements():
                item.scroll_up()
        self.draw()


class PIDStatsWindow(window.Window):
    """Subwindow showing stats about reads file"""

    def __init__(self, s_r, s_c, size_r, size_c, zfs, Menu):
        self.menu = Menu
        self.zfs = zfs
        super().__init__(s_r, s_c, size_r, size_c)
        self.draw()

    def _draw(self):
        dataset = self.zfs.dataset_by_name(self.menu.selected())
        pool = dataset.name.split("/")[0]

        self.window.erase()

        _, cols = self.window.getmaxyx()

        if cols > 60:
            text1 = "Sample count: "
            text2 = "Time window: "
            text3 = "Arc included: "
        else:
            text1 = "Samples: "
            text2 = "Window: "
            text3 = "Arc: "

        try:
            dist = (
                cols
                - len(
                    text1 + str(self.zfs.zpools[pool].read_stats.dataset_stats[dataset.name].count)
                )
                - len(
                    text2
                    + str(utils.convert_time_ns(self.zfs.zpools[pool].read_stats.data_time_window))
                )
                - len(text3 + "n")
                - 2
            ) // 2
            self.window.addstr(
                1,
                2,
                text1 + str(self.zfs.zpools[pool].read_stats.dataset_stats[dataset.name].count),
                curses.A_BOLD,
            )
            col = (
                len(text1 + str(self.zfs.zpools[pool].read_stats.dataset_stats[dataset.name].count))
                + dist
            )
        except (KeyError, IndexError):
            dist = (
                cols
                - len(text1 + "0")
                - len(
                    text2
                    + str(utils.convert_time_ns(self.zfs.zpools[pool].read_stats.data_time_window))
                )
                - len(text3 + "n")
                - 2
            ) // 2
            self.window.addstr(1, 2, text1 + "0", curses.A_BOLD)
            col = len(text1) + dist
        try:
            self.window.addstr(
                1,
                col,
                text2
                + str(utils.convert_time_ns(self.zfs.zpools[pool].read_stats.data_time_window)),
                curses.A_BOLD,
            )
            col = cols - len(text3 + "n") - 2
        except (KeyError, IndexError):
            pass
        try:
            self.window.addstr(
                1, col, text3 + utils.bool_to_str(self.zfs.zfs_reads_arc()), curses.A_BOLD
            )
        except KeyError:
            pass
        self.window.border(0, 0, 0, 0, curses.ACS_TTEE, curses.ACS_TTEE)
        self.refresh()

    def resize(self, s_r, s_c, row, col):
        """Resize"""
        try:
            self.window.mvwin(s_r, s_c)
            self.window.resize(row, col)
        except curses.error:
            self.window.resize(row, col)
            self.window.mvwin(s_r, s_c)

    def rescan(self):
        """Rescan"""
        pass


class PIDSmallWindow(scroll_pad.ScrollPad):
    """Subwindow showing list of reads by dataset"""

    def __init__(self, s_r, s_c, size_r, size_c, zfs, Menu):
        self.menu = Menu
        self.zfs = zfs
        super().__init__(s_r, s_c, reads_stats_history.MAX_RECORDS, 200, size_r, size_c)
        self.draw()

    def print_header(self, separation):
        """Print window header"""
        col = separation[0]
        self.window.addstr(0, col, "UID", curses.A_BOLD)
        col += separation[1]
        if separation[2] > 0:
            self.window.addstr(0, col, "dataset", curses.A_BOLD)
            col += separation[2]
        self.window.addstr(0, col, "object", curses.A_BOLD)
        col += separation[3]
        self.window.addstr(0, col, "flags", curses.A_BOLD)
        col += separation[4]
        self.window.addstr(0, col, "PID", curses.A_BOLD)
        col += separation[5]
        self.window.addstr(0, col, "process", curses.A_BOLD)

    def print_data(self):
        """Print data"""
        dataset = self.zfs.dataset_by_name(self.menu.selected())
        pool = dataset.name.split("/")[0]
        i = 1

        max_dataset_length = 0
        max_processname_legth = 0
        for record in list(self.zfs.zpools[pool].read_stats.history.queue):
            if dataset.name in (record.dataset_name, pool):
                if len(record.dataset_name) > max_dataset_length:
                    max_dataset_length = len(record.dataset_name)
                if len(record.process) > max_processname_legth:
                    max_processname_legth = len(record.process)

        separation = [1, 12, 0, 10, 7, 10]
        if (
            dataset.name == pool
            and self.w_size_c > sum(separation) + max_processname_legth + max_dataset_length + 4
        ):
            separation[2] = max_dataset_length + 3

        self.print_header(separation)

        for record in list(self.zfs.zpools[pool].read_stats.history.queue):
            if dataset.name in (record.dataset_name, pool):
                col = separation[0]
                try:
                    self.window.addstr(i, col, record.uid)
                except curses.error:
                    break
                col += separation[1]

                if dataset.name == pool and separation[2] > 0:
                    self.window.addstr(i, col, record.dataset_name)
                    col += separation[2]

                self.window.addstr(i, col, record.object_id)
                col += separation[3]

                self.window.addstr(i, col, ",".join(map(str, record.flags)))
                col += separation[4]

                self.window.addstr(i, col, record.pid)
                col += separation[5]

                self.window.addstr(i, col, record.process)
                i += 1

    def _draw(self):
        self.window.erase()
        self.print_data()
        self.refresh()
