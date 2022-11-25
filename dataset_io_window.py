"""Module for dataset IO window"""

import curses

import graphic
import app_window
import scroll_pad
import utils
import gui
import dataset_io
import time_graph
import dataset_history


class DatasetIOWindow(app_window.AppWindow):
    """Main dataset IO window"""

    def __init__(self, main_screen, zfs):
        self.zfs = zfs
        super().__init__(main_screen, 3, 1)
        rows, cols = self.window.getmaxyx()
        row, col = self.window.getbegyx()

        datasets = []
        for pool in self.zfs.zpools.values():
            for dataset in pool.datasets.values():
                if dataset.property["mounted"] == "yes":
                    datasets += [dataset.name]

        self.dataset_menu = graphic.VerticalMenu(datasets, row + 1, col + 1, 0, 0, cols // 4)
        self.dataset_io_pad = DatasetIOPad(
            row + 1,
            self.dataset_menu.get_size()[1] + col + 2,
            5,
            110,
            (rows - 1) // 2,
            cols - col - self.dataset_menu.get_size()[1] - 2,
            self.zfs,
            self.dataset_menu,
        )
        self.time_graph = time_graph.TimeGraph(
            row + rows // 2 + 2,
            col + 1,
            rows // 2 - 2,
            cols - 2,
            self.zfs.dataset_by_name(datasets[0]).io.history.stats["reads"],
        )
        self.time_graph_menu = graphic.HorizontalMenu(
            dataset_history.IO_STATS,
            row + rows // 2 - 3,
            col,
            br=curses.ACS_BTEE,
            bl=curses.ACS_LTEE,
        )

        self.menu_convert_map = {
            "c_total": utils.convert_count,
            "reads": utils.convert_count,
            "writes": utils.convert_count,
            "nread": utils.convert_size,
            "b_total": utils.convert_size,
            "nwritten": utils.convert_size,
            "nunlinks": utils.convert_count,
            "nunlinked": utils.convert_count,
        }
        self.set_correct_covert_funct()
        self.draw()

    def set_correct_covert_funct(self):
        """What function to use to convert values"""
        try:
            funct = self.menu_convert_map[self.time_graph_menu.selected()]
        except KeyError:
            funct = utils.cat
        self.time_graph.set_convert_funct(funct)

    def resize(self, s_r, s_c, row, col):
        """Resize window"""
        self.resize_window()
        row, col = self.window.getbegyx()
        rows, cols = self.window.getmaxyx()
        self.dataset_menu.set_max_size(5)
        self.dataset_menu.resize()
        if gui.Gui.gui_hidden:
            pad_c = 1
        else:
            pad_c = 2
        self.dataset_io_pad.resize(
            row + 1,
            self.dataset_menu.get_size()[1] + col + 2,
            (rows - row) // 2,
            cols - col - self.dataset_menu.get_size()[1] + pad_c - 4,
        )
        self.time_graph_menu.move_window(row + rows - rows // 2 + 1 - pad_c, col + 1)
        self.time_graph.resize(
            row + rows - (rows // 2) - pad_c + 3, col + 1, rows - (rows - row) // 2 - 4, cols - 2
        )
        self.dataset_menu.move_window(row + 1, col + 1)
        self.dataset_menu.set_max_size((rows - row) // 2)
        self.dataset_menu.resize()

        self.draw()
        self.refresh()

    def rescan(self):
        """Rescan"""
        # todo: ?
        del self.dataset_menu
        self.zfs.rescan_datasets()
        self.dataset_menu = graphic.VerticalMenu(self.window, self.zfs.get_datasets(), 4, 2, 1)

    def _draw(self):
        self.window.border()
        self.window.noutrefresh()
        self.dataset_menu.draw()
        self.dataset_io_pad.draw()
        self.time_graph.draw()
        self.time_graph_menu.draw()
        self.refresh()

    def handle_key(self, char):
        """Handle user input"""
        if char == curses.KEY_DOWN:
            self.dataset_menu.move_right()
            self.time_graph.change_source(
                self.zfs.dataset_by_name(self.dataset_menu.selected()).io.history.stats[
                    self.time_graph_menu.selected()
                ]
            )
        if char == curses.KEY_UP:
            self.dataset_menu.move_left()
            self.time_graph.change_source(
                self.zfs.dataset_by_name(self.dataset_menu.selected()).io.history.stats[
                    self.time_graph_menu.selected()
                ]
            )
        if chr(char) == "h":
            self.time_graph_menu.move_left()
            self.set_correct_covert_funct()
            self.time_graph.change_source(
                self.zfs.dataset_by_name(self.dataset_menu.selected()).io.history.stats[
                    self.time_graph_menu.selected()
                ]
            )
        if chr(char) == "l":
            self.time_graph_menu.move_right()
            self.set_correct_covert_funct()
            self.time_graph.change_source(
                self.zfs.dataset_by_name(self.dataset_menu.selected()).io.history.stats[
                    self.time_graph_menu.selected()
                ]
            )
        self.draw()


class DatasetIOPad(scroll_pad.ScrollPad):
    """Dataset IO subwindow"""

    def __init__(self, s_r, s_c, size_r, size_c, w_size_r, w_size_c, zfs, Menu):
        self.menu = Menu
        self.zfs = zfs
        super().__init__(s_r, s_c, size_r, size_c, w_size_r, w_size_c, True)
        self.draw()

    def print_header(self, row, col, shift, block_separator):
        """Print table header"""
        self.window.addstr(row, col + shift * 2 - len("count") // 2 - 2, "count")
        self.window.addstr(
            row, col + shift * 3 + block_separator + shift - len("bandwith") // 2 - 2, "bandwidth"
        )
        self.window.addstr(
            row, col + shift * 6 + 2 * block_separator + shift - len("count") // 2, "count"
        )
        self.window.addstr(row + 1, col + shift * 0, "read")
        self.window.addstr(row + 1, col + shift * 1, "write")
        self.window.addstr(row + 1, col + shift * 2, "total")
        self.window.addstr(row + 1, col + shift * 3 + block_separator, "read")
        self.window.addstr(row + 1, col + shift * 4 + block_separator, "write")
        self.window.addstr(row + 1, col + shift * 5 + block_separator, "total")
        self.window.addstr(row + 1, col + shift * 6 + 2 * block_separator, "del")
        self.window.addstr(row + 1, col + shift * 7 + 2 * block_separator, "fin_del")
        self.window.addstr(row + 1, col + shift * 8 + 2 * block_separator, "del_queue")

    # pylint: disable=too-many-branches,too-many-nested-blocks
    def _draw(self):
        self.window.erase()
        self.border_window.attrset(curses.color_pair(graphic.COLOR_OK))
        self.border_window.border()
        self.border_window.attrset(curses.color_pair(0))

        shift = 8
        block_separator = 0

        if self.w_size_c > 44 + shift * (9 + 2):
            block_separator = shift

        self.print_header(0, 40, shift, block_separator)

        print_grey = True
        if (self.w_size_r - 2) < len(self.zfs.get_datasets()):
            print_grey = False

        i = 2
        for pool in self.zfs.zpools.values():
            for dataset in pool.datasets.values():
                if dataset.io.valid == 1:
                    if self.menu.selected() == dataset.name:
                        attr = curses.color_pair(graphic.COLOR_OK)
                    else:
                        attr = curses.A_NORMAL
                    self.add_line(i, 1, dataset.name, attr)
                    j = 0
                    for key in ["reads", "writes", "c_total"]:
                        self.add_line(
                            i, 40 + shift * j, utils.convert_count(dataset.io.stats[key]), attr
                        )
                        j += 1
                    for key in ["nread", "nwritten", "b_total"]:
                        self.add_line(
                            i,
                            40 + shift * j + block_separator * 1,
                            utils.convert_size(dataset.io.stats[key]),
                            attr,
                        )
                        j += 1
                    for key in ["nunlinks", "nunlinked", "del_queue"]:
                        self.add_line(
                            i,
                            40 + shift * j + block_separator * 2,
                            utils.convert_count(dataset.io.stats[key]),
                            attr,
                        )
                        j += 1
                    i += 1
                else:
                    if print_grey:
                        self.add_line(i, 1, dataset.name, curses.A_DIM)
                        j = 0
                        separator = 0
                        for key in dataset_io.IO_STATS:
                            if j > 2:
                                separator = block_separator
                            if j > 5:
                                separator = 2 * block_separator
                            self.add_line(i, 40 + shift * j + separator, "-", curses.A_DIM)
                            j += 1
                        i += 1
