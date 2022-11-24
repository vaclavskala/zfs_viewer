"""Module for ARC IO window"""

import curses

import graphic
import window
import time_graph
import arc_history
import utils


class ArcIOSmallWindow(window.Window):
    """Class for ARC IO subwindow"""

    def __init__(self, s_r, s_c, size_r, size_c, zfs):
        self.zfs = zfs
        super().__init__(s_r, s_c, size_r, size_c)

    def _draw(self):
        self.window.erase()
        rows, cols = self.window.getmaxyx()
        dist = cols // (len(arc_history.EXPORTED_DATA) + 1)
        max_rows = rows - 2
        col = 0
        for param in ["time"] + arc_history.EXPORTED_DATA:
            self.window.addstr(1, 2 + col * dist, param, curses.A_BOLD)
            col += 1

        col = 0
        for param in ["time"] + arc_history.EXPORTED_DATA:
            row = 2
            for key in reversed(self.zfs.arc.arc_history.stats[param]):
                if row >= max_rows:
                    attr = curses.A_DIM
                else:
                    attr = curses.A_NORMAL
                if key != -1:
                    try:
                        self.window.addstr(
                            row, 2 + col * dist, arc_history.CONVERT_MAP[param](key), attr
                        )
                    except KeyError:
                        self.window.addstr(row, 2 + col * dist, str(key), attr)
                row += 1
                if row > max_rows:
                    break
            col += 1
        self.window.border()
        self.window.noutrefresh()

    def resize(self, s_r, s_c, row, col):
        """Resize window"""
        try:
            self.window.mvwin(s_r, s_c)
            self.window.resize(row, col)
        except curses.error:
            self.window.resize(row, col)
            self.window.mvwin(s_r, s_c)


class ArcIOWindow(window.AppWindow):
    """Main ARC IO window"""

    def __init__(self, main_screen, zfs):
        self.zfs = zfs
        super().__init__(main_screen, 3, 1)
        rows, cols = self.window.getmaxyx()
        row, col = self.window.getbegyx()

        self.time_graph = time_graph.TimeGraph(
            row + 12, col + 1, rows - 13, cols - 2, self.zfs.arc.arc_history.stats["hits"]
        )
        self.time_graph.enable_x_scale(1, utils.add_second)
        self.arc_io_win = ArcIOSmallWindow(row + 1, col + 1, 9, cols - 2, self.zfs)
        self.time_graph_menu = graphic.HorizontalMenu(
            arc_history.EXPORTED_DATA, row + 10, col + 1, br=curses.ACS_BTEE, bl=curses.ACS_LTEE
        )

        self.menu_convert_map = {
            "hits": utils.convert_count,
            "misses": utils.convert_count,
            "io_total": utils.convert_count,
            "size": utils.convert_size,
            "mru_size": utils.convert_size,
            "mfu_size": utils.convert_size,
            "hitrate": utils.cat,
        }

        self.set_correct_covert_funct()

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
        ###        if gui.Gui.gui_hidden:
        ###            pad_c = 1
        ###        else:
        ###            pad_c = 2
        arc_io_win_size = 9
        if rows > 45:
            arc_io_win_size = 12
        self.time_graph.resize(
            row + arc_io_win_size + 3, col + 1, rows - arc_io_win_size - 4, cols - 2
        )
        self.arc_io_win.resize(row + 1, col + 1, arc_io_win_size, cols - 2)
        self.time_graph_menu.move_window(row + arc_io_win_size + 1, col + 1)

        self.draw()
        self.refresh()

    def rescan(self):
        pass

    def _draw(self):
        self.window.border()
        self.window.noutrefresh()
        self.time_graph.draw()
        self.time_graph_menu.draw()
        self.arc_io_win.draw()
        self.refresh()

    def handle_key(self, char):
        """Handle user input"""
        if chr(char) == "+":
            self.time_graph.zoom_in()
        if chr(char) == "-":
            self.time_graph.zoom_out()
        if chr(char) == "h":
            self.time_graph_menu.move_left()
            self.time_graph.change_source(
                self.zfs.arc.arc_history.stats[self.time_graph_menu.selected()]
            )
            self.set_correct_covert_funct()
        if chr(char) == "l":
            self.time_graph_menu.move_right()
            self.time_graph.change_source(
                self.zfs.arc.arc_history.stats[self.time_graph_menu.selected()]
            )
            self.set_correct_covert_funct()
        self.draw()
