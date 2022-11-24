"""Module for row graph"""

import curses
import graphic
import color

palette = (
    color.COLOR_BCK_RED,
    color.COLOR_BCK_BLUE,
    color.COLOR_BCK_GREEN,
    color.COLOR_BCK_YELLOW,
    color.COLOR_BCK_CYAN,
    color.COLOR_BCK_MAGENTA,
)

# pylint: disable=too-many-instance-attributes
class RowGraph(graphic.GraphicObject):
    """Class for row graph"""

    def __init__(self, s_r, s_c, size_r, size_c, print_zeroes=False):
        self.window = curses.newwin(size_r, size_c, s_r, s_c)
        self.s_r = s_r
        self.s_c = s_c
        self.size_r = size_r
        self.size_c = size_c
        self.max_key = 0
        self.max_value = 0
        self.values = {}
        self.print_zeroes = print_zeroes
        self.sorted_values = []
        self.row_string = " " * 100
        super().__init__(self.window, s_r, s_c)

    def set_values(self, values):
        """Sat values from which make graph"""
        self.sorted_values = sorted(values.items(), key=lambda kv: kv[1], reverse=True)
        self.max_key = 0
        self.max_value = 0
        for item in self.sorted_values:
            if len(item[0]) > self.max_key:
                self.max_key = len(item[0])
            if item[1] > self.max_value:
                self.max_value = item[1]

    def _draw(self):
        cols = self.window.getmaxyx()[1]
        if self.max_key > cols // 3:
            self.draw_small()
        else:
            self.draw_big()

    def draw_big(self):
        """If is enough space to print key outside of graph bar"""
        self.window.erase()
        self.window.border()
        rows, cols = self.window.getmaxyx()
        i = 1
        color_index = 0
        for item in self.sorted_values:
            col = (cols - self.max_key - 2 - 2) * item[1] // self.max_value
            if col > 0:
                self.window.addstr(i, 1, item[0] + ":")
                self.window.addstr(
                    i,
                    self.max_key + 2 + 1,
                    self.row_string[0:col],
                    curses.color_pair(palette[color_index]),
                )
                if len(str(item[1])) < col:
                    self.window.addstr(
                        i,
                        self.max_key + 3 + col - len(str(item[1])),
                        str(item[1]),
                        curses.color_pair(palette[color_index]),
                    )
            if self.print_zeroes and col == 0:
                self.window.addstr(i, 1, item[0] + ":")
            i += 1
            color_index = (color_index + 1) % len(palette)
            if i > (rows - 2):
                break
        self.window.noutrefresh()

    def draw_small(self):
        """I dont know"""
        # todo: wtf
        self.draw_big()

    def resize(self, s_r, s_c, row, col):
        """Resize row graph"""
        try:
            self.window.mvwin(s_r, s_c)
            self.window.resize(row, col)
        except curses.error:
            self.window.resize(row, col)
            self.window.mvwin(s_r, s_c)
