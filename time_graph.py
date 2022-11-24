"""Module for time series graph"""

import curses
import graphic
import utils
import color

# pylint: disable=too-many-instance-attributes
class TimeGraph(graphic.GraphicObject):
    """Class for time graph"""

    def __init__(self, s_r, s_c, size_r, size_c, values, zoom=1):
        self.window = curses.newwin(size_r, size_c, s_r, s_c)
        self.size_r = size_r
        self.size_c = size_c
        self.window.border()
        self.values = values
        self.zoom = zoom
        self.size = size_c - 2
        self.target = 0
        self.target_char = "_"
        self.print_scale = False
        self.x_scale = False
        self.scale_shift = 2
        self.function = utils.cat
        self.x_scale_funct = utils.cat
        self.x_scale_coef = 0
        super().__init__(self.window, s_r, s_c)

    def set_convert_funct(self, function):
        """Function to convert max_value to string"""
        self.function = function

    def change_source(self, source):
        """Change graph source"""
        self.values = source

    def set_target(self, value):
        """Highlight target values"""
        self.target = value

    def resize(self, s_r, s_c, size_r, size_c):
        """Resize time graph"""
        self.size = size_c - 2
        self.size_r = size_r
        self.size_c = size_c
        try:
            self.window.mvwin(s_r, s_c)
            self.window.resize(size_r, size_c)
        except curses.error:
            pass
        else:
            return

        try:
            self.window.resize(size_r, size_c)
            self.window.mvwin(s_r, s_c)
        except curses.error:
            return

        self.window.erase()

    def enable_x_scale(self, scale_coef, funct=utils.cat):
        """Enable to show x scale legend"""
        self.x_scale = True
        self.x_scale_funct = funct
        self.x_scale_coef = scale_coef
        self.scale_shift = 4

    def print_x_info(self, length, scale_reservation):
        """Print descriptions on x scale"""
        self.window.addstr(
            self.size_r - 2,
            scale_reservation + 1,
            self.x_scale_funct(str(-length * self.x_scale_coef)),
        )
        self.window.addstr(
            self.size_r - 2,
            scale_reservation + (self.size_c - scale_reservation) // 2,
            self.x_scale_funct(str(-length * self.x_scale_coef // 2)),
        )
        self.window.addstr(
            self.size_r - 2, self.size_c - 1 - len(self.x_scale_funct("0")), self.x_scale_funct("0")
        )

    def print_x_scale(self):
        """Print x scale line"""
        self.window.hline(self.size_r - 3, 1, curses.ACS_HLINE, self.size_c - 2)

    def get_max(self, values):
        """Get max_value in input queue"""
        __max = 0
        for item in values:
            if int(item) > __max:
                __max = int(item)
        __max = max(__max, self.target)
        return __max

    def zoom_in(self):
        """Zoom graph"""
        if self.zoom < 3:
            self.zoom += 1

    def zoom_out(self):
        """Zoom out graph"""
        if self.zoom > 1:
            self.zoom -= 1

    def zoom_data(self):
        """Zoom data according to zoom"""
        tmp_values = list(self.values)
        values = tmp_values[len(tmp_values) - self.size_c : len(tmp_values)]
        return values

    def draw_column(self, height, col):
        """Draw graph column"""
        if height != self.size_r - self.scale_shift:
            for i in range(height + 1, self.size_r + 1 - self.scale_shift):
                try:
                    self.window.addstr(i, col, " ", curses.color_pair(100))
                except curses.error:
                    continue
        else:
            self.window.addch(self.size_r - self.scale_shift, col, "_")

    def empty_column(self, col):
        """Draw empty column"""
        for i in range(1, self.size_r - self.scale_shift):
            self.window.addstr(i, col, " ")

    def process_data(self, values, max_value, scale_reservation):
        """Process all source and print colums"""
        col = self.size_c - 2
        values.reverse()
        for item in values:
            row = self.size_r - (item * (self.size_r - 1 - self.scale_shift) / max_value) + 0
            if int(item) >= 0:
                self.draw_column(int(row) - self.scale_shift, col)
            col -= 1
            if col <= scale_reservation:
                break

    # pylint: disable=too-many-nested-blocks
    def _draw(self):
        self.window.erase()
        self.window.border()
        self.window.noutrefresh()
        values = self.zoom_data()
        max_value = self.get_max(values)

        scale_reservation = len(str(self.function(max_value))) + 2

        try:
            self.window.addch(0, scale_reservation, curses.ACS_TTEE)
            self.window.vline(
                1, scale_reservation, curses.ACS_VLINE, self.size_r - 2, curses.color_pair(0)
            )
            self.window.addch(self.size_r - 1, scale_reservation, curses.ACS_BTEE)
        except curses.error:
            pass

        if max_value <= 0:
            self.window.noutrefresh()
            return

        if self.target > 0:
            target_row = self.size_r - (self.target * (self.size_r - 3) / max_value) + 0
            self.window.hline(
                int(target_row) - 1,
                self.s_c + scale_reservation,
                curses.ACS_HLINE,
                self.size_c - 4 - scale_reservation,
                curses.color_pair(2),
            )

        self.process_data(values, max_value, scale_reservation)
        target_row = self.size_r - (self.target * (self.size_r - 3) / max_value) + 0

        self.window.addstr(
            1, scale_reservation - len(str(self.function(max_value))), str(self.function(max_value))
        )
        self.window.addstr(
            1 + (self.size_r - self.scale_shift) // 2,
            scale_reservation - len(str(self.function(max_value // 2))),
            str(self.function(max_value // 2)),
        )
        self.window.addstr(
            self.size_r - self.scale_shift,
            scale_reservation - len(str(self.function(0))),
            str(self.function(0)),
        )
        if self.target:
            self.window.addstr(
                int(target_row) - 1,
                scale_reservation - len(str(self.function(self.target))),
                str(self.function(self.target)),
                curses.color_pair(2),
            )

        if self.x_scale:
            self.print_x_scale()
            self.print_x_info(len(values), scale_reservation)
            self.window.addch(self.size_r - 3, scale_reservation, 110, curses.A_ALTCHARSET)
        self.window.noutrefresh()


class TimeGraphMulti(TimeGraph):
    """Class for time graph"""

    def __init__(self, s_r, s_c, size_r, size_c, values, zoom=1):
        self.palette = (
            color.COLOR_BCK_RED,
            color.COLOR_BCK_BLUE,
            color.COLOR_BCK_GREEN,
            color.COLOR_BCK_YELLOW,
            color.COLOR_BCK_CYAN,
            color.COLOR_BCK_MAGENTA,
        )
        super().__init__(s_r, s_c, size_r, size_c, values, zoom)

    def get_max(self, values):
        """Get max_value in input queue"""
        max_val = 0
        for item in values:
            val_sum = 0
            for val in item:
                val_sum += int(val)
            if val_sum > max_val:
                max_val = val_sum
        max_val = max(max_val, self.target)
        return max_val

    def draw_column(self, height, col, col_color, inc=0):
        """Draw graph column"""
        for i in range(0, height):
            try:
                self.window.addstr(self.size_r - self.scale_shift - i - inc, col, " ", col_color)
            except curses.error:
                continue

    def process_data(self, values, max_value, scale_reservation):
        col = self.size_c - 2
        values.reverse()
        for item in values:
            inc = 0
            i = 0
            for val in item:
                row = (val * (self.size_r - self.scale_shift) / max_value) + 0
                if int(val) >= 0:
                    self.draw_column(int(row) + 0, col, curses.color_pair(self.palette[i]), inc)
                    inc += int(row) + 0
                i += 1

            col -= 1
            if col <= scale_reservation:
                break
