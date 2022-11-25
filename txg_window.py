"""Class for txg window"""

import curses

import graphic
import window
import app_window
import time_graph
import txg_history
import utils


class TxgSmallWindow(window.Window):
    """Class for subwindow on txg window"""

    def __init__(self, s_r, s_c, size_r, size_c, zfs, pool_menu):
        self.zfs = zfs
        self.pool_menu = pool_menu
        super().__init__(s_r, s_c, size_r, size_c)

    def _draw(self):
        self.window.erase()
        dist = self.size_c // (len(txg_history.MENU_VIEW_DATA) + 1)
        col = 0
        for param in txg_history.MENU_VIEW_DATA:
            self.window.addstr(1, 2 + col * dist, param, curses.A_BOLD)
            col += 1

        col = 0
        for param in txg_history.MENU_VIEW_DATA:
            row = 2
            for key in reversed(
                self.zfs.zpools[self.pool_menu.selected()].txgs.history.stats[param]
            ):
                if row > 9:
                    attr = curses.A_DIM
                else:
                    attr = curses.A_NORMAL
                try:
                    self.window.addstr(
                        row, 2 + col * dist, txg_history.CONVERT_MAP[param](key), attr
                    )
                except KeyError:
                    self.window.addstr(row, 2 + col * dist, str(key), attr)
                row += 1
                if row > 10:
                    break
            col += 1
        self.window.border()
        self.window.noutrefresh()

    def resize(self, s_r, s_c, row, col):
        try:
            self.window.mvwin(s_r, s_c)
            self.window.resize(row, col)
        except curses.error:
            self.window.resize(row, col)
            self.window.mvwin(s_r, s_c)


class TxgWindow(app_window.AppWindow):
    """Class for main txg window"""

    def __init__(self, main_screen, zfs):
        self.zfs = zfs
        super().__init__(main_screen, 3, 1)
        self.pool_menu = graphic.VerticalMenu(zfs.get_pools(), 1, 2)
        rows, cols = self.window.getmaxyx()
        row, col = self.window.getbegyx()

        self.time_graph = time_graph.TimeGraph(
            row + 3 + 12,
            col + 1,
            rows - 16,
            cols - 2,
            self.zfs.zpools[self.pool_menu.selected()].txgs.history.stats["otime"],
        )
        self.txg_win = TxgSmallWindow(
            row + 1,
            col + 2 + self.pool_menu.get_size()[1],
            12,
            cols - 3 - self.pool_menu.get_size()[1],
            self.zfs,
            self.pool_menu,
        )

        self.menu_convert_map = {
            "ndirty": utils.convert_size,
            "reads": utils.convert_count,
            "nread": utils.convert_size,
            "total_c": utils.convert_count,
            "writes": utils.convert_count,
            "nwritten": utils.convert_size,
            "total_b": utils.convert_size,
            "otime": utils.convert_time_ns,
            "qtime": utils.convert_time_ns,
            "wtime": utils.convert_time_ns,
            "stime": utils.convert_time_ns,
        }

        self.time_graph_menu = graphic.HorizontalMenu(
            txg_history.GRAPH_VIEW_DATA, row + 13, col + 1, br=curses.ACS_BTEE, bl=curses.ACS_LTEE
        )
        self.time_graph_menu.set_pos("otime")

        self.set_correct_covert_funct()

        self.time_graph.set_target(5000000000)

    def set_correct_covert_funct(self):
        """What function to use to convert values"""
        try:
            funct = self.menu_convert_map[self.time_graph_menu.selected()]
        except KeyError:
            funct = utils.cat
        self.time_graph.set_convert_funct(funct)

    def resize(self, s_r, s_c, row, col):
        self.resize_window()
        row, col = self.window.getbegyx()
        rows, cols = self.window.getmaxyx()
        ###        if gui.Gui.gui_hidden:
        ###            pad_c = 1
        ###        else:
        ###            pad_c = 2

        self.pool_menu.move_window(row + 1, col + 1)
        self.time_graph.resize(row + 3 + 12, col + 1, rows - 16, cols - 2)
        self.txg_win.resize(
            row + 1,
            col + 2 + self.pool_menu.get_size()[1],
            12,
            cols - 3 - self.pool_menu.get_size()[1],
        )

        self.time_graph_menu.move_window(row + 13, col + 1)

        # todo: read from file
        self.time_graph.set_target(5000000000)

        self.draw()
        self.refresh()

    def rescan(self):
        pass

    def _draw(self):
        self.window.border()
        self.window.noutrefresh()
        self.pool_menu.draw()
        self.time_graph.draw()
        self.time_graph_menu.draw()
        self.txg_win.draw()
        self.refresh()

    def handle_key(self, char):
        pass
        if chr(char) == "+":
            self.time_graph.zoom_in()
        if chr(char) == "-":
            self.time_graph.zoom_out()
        if char == curses.KEY_DOWN:
            self.pool_menu.move_right()
            self.time_graph.change_source(
                self.zfs.zpools[self.pool_menu.selected()].txgs.history.stats[
                    self.time_graph_menu.selected()
                ]
            )
        if char == curses.KEY_UP:
            self.pool_menu.move_left()
            self.time_graph.change_source(
                self.zfs.zpools[self.pool_menu.selected()].txgs.history.stats[
                    self.time_graph_menu.selected()
                ]
            )
        if chr(char) == "h":
            self.time_graph_menu.move_left()
            self.time_graph.change_source(
                self.zfs.zpools[self.pool_menu.selected()].txgs.history.stats[
                    self.time_graph_menu.selected()
                ]
            )
            if self.time_graph_menu.selected() == "otime":
                self.time_graph.set_target(5000000000)
            else:
                self.time_graph.set_target(0)
            self.set_correct_covert_funct()
        if chr(char) == "l":
            self.time_graph_menu.move_right()
            self.time_graph.change_source(
                self.zfs.zpools[self.pool_menu.selected()].txgs.history.stats[
                    self.time_graph_menu.selected()
                ]
            )
            if self.time_graph_menu.selected() == "otime":
                self.time_graph.set_target(5000000000)
            else:
                self.time_graph.set_target(0)
            self.set_correct_covert_funct()

        self.draw()
