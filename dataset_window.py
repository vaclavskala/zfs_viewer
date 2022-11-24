"""Module for dataset info window"""

import curses
import datetime

import graphic
import window
import scroll_pad
import utils
import gui


class DatasetWindowBarGraph(graphic.BarGraph):
    """Bar graph for dataset space usage"""

    def __init__(self, pool_menu, zfs, values, s_r, s_c, size_r, size_c, colors=None):
        if colors is None:
            colors = {}
        self.menu = pool_menu
        self.zfs = zfs
        self.last_dataset = self.zfs.dataset_by_name(self.menu.selected())
        super().__init__(values, s_r, s_c, size_r, size_c, colors)
        self.prepare_data()

    def prepare_data(self):
        """Prepare data for bar graph format"""
        self.values = {}
        self.values["usedbydataset"] = int(self.last_dataset.property["usedbydataset"])
        self.values["usedbysnapshots"] = int(self.last_dataset.property["usedbysnapshots"])
        self.values["usedbychildren"] = int(self.last_dataset.property["usedbychildren"])
        self.values["usedbyrefreservation"] = int(
            self.last_dataset.property["usedbyrefreservation"]
        )
        self.calculate_sizes()

    def _draw(self):
        if self.last_dataset != self.zfs.dataset_by_name(self.menu.selected()):
            self.last_dataset = self.zfs.dataset_by_name(self.menu.selected())
            self.prepare_data()
        super()._draw()


class DatasetWindow(window.AppWindow):
    """Main dataset info window"""

    def __init__(self, main_screen, zfs):
        self.zfs = zfs
        super().__init__(main_screen, 3, 1)
        rows, cols = self.window.getmaxyx()
        row, col = self.window.getbegyx()
        self.dataset_menu = graphic.VerticalMenu(
            zfs.get_datasets(), row + 1, col + 2, 0, 0, cols // 4
        )
        half_screen = (cols - self.dataset_menu.get_size()[1] + col + 2) // 2
        self.dataset_pad = DatasetPad(
            row + 1,
            self.dataset_menu.get_size()[1] + col + 2,
            28,
            60,
            rows - 7,
            half_screen,
            self.zfs,
            self.dataset_menu,
        )
        self.snapshot_menu = graphic.HorizontalMenu(
            ["Snapshots", "Holds"],
            row + 1,
            self.dataset_pad.get_pos()[1] + self.dataset_pad.get_size()[1] - 3,
            br=curses.ACS_BTEE,
            bl=curses.ACS_LTEE,
        )

        self.snapshot_pad = SnapshotPad(
            row + 3,
            self.dataset_pad.get_pos()[1] + self.dataset_pad.get_size()[1],
            20,
            70,
            rows - 7,
            cols - col - 50 - self.dataset_menu.get_size()[1] - 2,
            self.zfs,
            self.dataset_menu,
            self.snapshot_menu,
        )
        self.usage_bar = DatasetWindowBarGraph(
            self.dataset_menu,
            self.zfs,
            [],
            rows - 6,
            3 + self.dataset_menu.get_size()[1],
            5,
            cols - 3 - self.dataset_menu.get_size()[1],
        )

        self.set_snapshot_menu_graylist()
        self.register_element(self.dataset_pad)
        self.register_element(self.snapshot_pad)
        self.dataset_pad.select()
        self.draw()

    def resize(self, s_r, s_c, row, col):
        """Resize window"""
        self.resize_window()
        row, col = self.window.getbegyx()
        rows, cols = self.window.getmaxyx()
        self.dataset_menu.set_max_size(rows - 7)
        self.dataset_menu.resize()
        if gui.Gui.gui_hidden:
            pad_c = 1
        else:
            pad_c = 2
        half_screen = min((cols - (self.dataset_menu.get_size()[1] + col + 2)) // 2, 60)

        half_screen2 = cols - half_screen - self.dataset_menu.get_size()[1] - col - 4 + pad_c

        self.dataset_menu.move_window(row + 1, col + 2)
        self.dataset_pad.resize(
            row + 1, self.dataset_menu.get_size()[1] + col + 2, rows - 7, half_screen
        )
        self.snapshot_pad.resize(
            row + 3,
            self.dataset_pad.get_pos()[1] + self.dataset_pad.get_size()[1],
            rows - 7 - 2,
            half_screen2,
        )
        try:
            self.usage_bar.resize(
                rows - 6 + self.window.getbegyx()[0], pad_c, 5, cols - 2 - pad_c * 0
            )
        except curses.error:
            self.usage_bar.resize(
                rows - 6 + self.window.getbegyx()[0], pad_c, 5, cols - 2 - pad_c * 0
            )

        self.snapshot_menu.move_window(
            row + 1, self.dataset_pad.get_pos()[1] + self.dataset_pad.get_size()[1]
        )
        self.usage_bar.window.noutrefresh()
        self.draw()
        self.refresh()

    def rescan(self):
        """rescan datasets"""
        # todo: update menu
        del self.dataset_menu
        self.zfs.rescan_datasets()
        self.dataset_menu = graphic.VerticalMenu(self.window, self.zfs.get_datasets(), 4, 2, 1)

    def _draw(self):
        self.window.border()
        self.window.noutrefresh()
        self.dataset_menu.draw()
        self.snapshot_pad.draw()
        self.usage_bar.draw()
        self.snapshot_menu.draw()
        self.window.noutrefresh()
        self.dataset_pad.draw()
        self.refresh()

    def set_snapshot_menu_graylist(self):
        """If dataset has any holds on snapshots"""
        dataset = self.zfs.dataset_by_name(self.dataset_menu.selected())
        if dataset.has_holds:
            self.snapshot_menu.set_graylist("")
        else:
            self.snapshot_menu.set_graylist("Holds")

    def handle_key(self, char):
        """Handle user input"""
        if char == curses.KEY_DOWN:
            self.dataset_menu.move_right()
            self.set_snapshot_menu_graylist()
        if char == curses.KEY_UP:
            self.dataset_menu.move_left()
            self.set_snapshot_menu_graylist()
        if char == curses.KEY_NPAGE:
            for item in self.get_selected_elements():
                item.scroll_down()
        if char == curses.KEY_PPAGE:
            for item in self.get_selected_elements():
                item.scroll_up()
        if chr(char) == "h":
            self.snapshot_menu.move_left()
        if chr(char) == "l":
            self.snapshot_menu.move_right()
        self.draw()


class DatasetPad(scroll_pad.ScrollPad):
    """Dataset info scroll pad"""

    def __init__(self, s_r, s_c, size_r, size_c, w_size_r, w_size_c, zfs, Menu):
        self.menu = Menu
        self.zfs = zfs
        super().__init__(s_r, s_c, size_r, size_c, w_size_r, w_size_c, True)
        self.draw()

    def _draw(self):
        self.window.erase()
        self.border_window.attrset(curses.color_pair(graphic.COLOR_OK))
        self.border_window.border()
        self.border_window.attrset(curses.color_pair(0))

        dataset = self.zfs.dataset_by_name(self.menu.selected())

        i = 0
        self.window.addstr(i, 1, "Properties:", curses.A_BOLD)
        i += 1

        pad = 25

        for dataset_property in [
            "used",
            "referenced",
            "available",
            "usedbysnapshots",
            "quota",
            "refquota",
            "usedbydataset",
            "usedbychildren",
            "usedbyrefreservation",
            "recordsize",
        ]:
            self.window.addstr(i, 1, dataset_property.capitalize() + ":")
            self.window.addstr(i, pad, utils.convert_size(dataset.property[dataset_property]))
            i += 1

        for dataset_property in dataset.property.keys():
            if dataset_property not in [
                "used",
                "referenced",
                "available",
                "usedbysnapshots",
                "quota",
                "refquota",
                "recordsize",
                "usedbychildren",
                "usedbyrefreservation",
                "usedbydataset",
            ]:
                self.window.addstr(i, 1, dataset_property.capitalize() + ":")
                i += self.add_line(i, pad, dataset.property[dataset_property])


class SnapshotPad(scroll_pad.ScrollPad):
    """ScrollPad for snapshots"""

    def __init__(self, s_r, s_c, size_r, size_c, w_size_r, w_size_c, zfs, Menu, Section_menu):
        self.menu = Menu
        self.section_menu = Section_menu
        self.zfs = zfs
        super().__init__(s_r, s_c, size_r, size_c, w_size_r, w_size_c, True)
        self.draw()

    # pylint: disable=too-many-branches
    def _draw(self):
        self.window.erase()
        self.border_window.attrset(curses.color_pair(graphic.COLOR_OK))
        self.border_window.border()
        self.border_window.attrset(curses.color_pair(0))

        dataset = self.zfs.dataset_by_name(self.menu.selected())

        if self.section_menu.selected() == "Snapshots":
            snap_name_len = 0

            for key in dataset.snapshot:
                if len(dataset.snapshot[key].short_name) > snap_name_len:
                    snap_name_len = len(dataset.snapshot[key].short_name)

            if snap_name_len > self.w_size_c - 17 - 6 - 8:
                snap_name_len = self.w_size_c - 17 - 6 - 8
            else:
                snap_name_len -= 2

            snap_name_len = max(snap_name_len, 5)

            i = 0
            self.window.addstr(i, 1, "name:", curses.A_BOLD)
            self.window.addstr(i, 2 + snap_name_len, "time:", curses.A_BOLD)
            self.window.addstr(i, 2 + snap_name_len + 19, "size:", curses.A_BOLD)
            i += 1

            for key in dataset.snapshot:
                if len(dataset.snapshot[key].short_name) > snap_name_len:
                    self.add_line(
                        i, 1, "@" + dataset.snapshot[key].short_name[0 : snap_name_len - 2]
                    )
                else:
                    self.add_line(i, 1, "@" + dataset.snapshot[key].short_name)
                self.window.addstr(i, 2 + snap_name_len, dataset.snapshot[key].creation_human)
                self.window.addstr(
                    i, 2 + snap_name_len + 19, utils.convert_size(dataset.snapshot[key].size)
                )
                i += 1

        if self.section_menu.selected() == "Holds":
            hold_name_len = 0
            snap_name_len = 0
            for key in dataset.snapshot:
                for key2 in dataset.snapshot[key].holds:
                    if len(key2) > hold_name_len:
                        hold_name_len = len(key2)
                    if len(key) > snap_name_len:
                        snap_name_len = len(key)

            snap_name_len = min(snap_name_len, 6)
            hold_name_len = min(hold_name_len, 6)

            i = 0
            self.window.addstr(i, 1, "name:", curses.A_BOLD)
            self.window.addstr(i, hold_name_len + 4, "snap:", curses.A_BOLD)
            self.window.addstr(i, hold_name_len + snap_name_len + 12, "time:", curses.A_BOLD)
            i += 1

            for key in dataset.snapshot:
                for key2 in dataset.snapshot[key].holds:
                    hold = dataset.snapshot[key].holds[key2]
                    self.window.addstr(i, 1, key2)
                    self.window.addstr(i, hold_name_len + 4, key)
                    self.window.addstr(
                        i,
                        hold_name_len + snap_name_len + 12,
                        datetime.datetime.fromtimestamp(hold).strftime("%b %d %H:%M %Y"),
                    )
                    i += 1
