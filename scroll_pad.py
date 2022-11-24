"""Window with ability to scroll"""

import abc
import curses
import math

import meta_selectable
import graphic


# pylint: disable=too-many-instance-attributes
class ScrollPad(graphic.Hideable, meta_selectable.MetaSelectable):
    """Window with ability to scroll"""

    def __init__(self, s_r, s_c, size_r, size_c, w_size_r, w_size_c, autogrow=False):
        self.s_r = s_r
        self.s_c = s_c
        self.view_r, self.view_c = 0, 0
        self.w_size_r, self.w_size_c = w_size_r, w_size_c
        self.size_r = max(size_r, w_size_r - 2)
        self.size_c = max(size_c, w_size_c - 2)
        self.autogrow = autogrow
        self.border_window = curses.newwin(w_size_r, w_size_c, s_r, s_c)
        self.window = curses.newpad(self.size_r, self.size_c)
        super().__init__()
        meta_selectable.MetaSelectable.__init__(self)

    def add_line_int(self, row, col, payload, format_type=curses.A_NORMAL):
        """Add line to window to specified row and col"""
        if row + math.ceil(len(payload) / self.w_size_c) + 1 >= self.size_r and self.autogrow:
            self.resize_pad(row + math.ceil(len(payload) / self.w_size_c) + 2, self.size_c)
        for count in range(0, math.ceil(len(payload) / (self.w_size_c - 2))):
            try:
                self.window.addstr(
                    row,
                    col,
                    payload[
                        count
                        * (self.w_size_c - 2) : min((count + 1) * (self.w_size_c - 2), len(payload))
                    ],
                    format_type,
                )
                row += 1
            except curses.error:
                return count + 1
        return math.ceil(len(payload) / (self.w_size_c - 2))

    def add_line(self, row, col, payload, format_type=curses.A_NORMAL):
        """Add line to window to specified position"""
        # if write from start of line or payload will fit to rest of line
        if (col == 0) or (len(payload) < self.w_size_c - col):
            return self.add_line_int(row, col, payload, format_type)
        shift = 0
        shift += self.add_line_int(row, col, payload[0 : self.w_size_c - col - 2], format_type)
        shift += self.add_line_int(row + 1, 0, payload[self.w_size_c - col - 2 :], format_type)
        return shift

    def add_ch(self, row, col, payload, format_type=curses.A_NORMAL):
        """Check if line is avaliable and print char"""
        self.add_line(row, col, " ", format_type)
        self.window.addch(row, col, payload, format_type)

    def resize_pad(self, size_r, size_c):
        """Resize virtual size of scrollpad"""
        self.window.resize(size_r, size_c)
        self.size_r = size_r

    def reset_autoscroll(self):
        """Shrink virtual size to physical window size"""
        if self.autogrow:
            self.resize_pad(self.w_size_r, self.w_size_c)

    # pylint: disable=duplicate-code
    def resize(self, s_r, s_c, w_size_r, w_size_c):
        """Resize scrollpad"""
        self.s_r = s_r
        self.s_c = s_c
        self.w_size_r = w_size_r
        self.w_size_c = w_size_c
        self.border_window.erase()
        if self.autogrow:
            self.resize_pad(self.w_size_r, self.w_size_c)

        try:
            self.border_window.mvwin(s_r, s_c)
            self.border_window.resize(w_size_r, w_size_c)
        except curses.error:
            pass
        else:
            return

        try:
            self.border_window.resize(w_size_r, w_size_c)
            self.border_window.mvwin(s_r, s_c)
        except curses.error:
            return

    def draw_scroll_indicator(self):
        """Indicator of position within scrollpad"""
        start = round((self.w_size_r - 1) * self.view_r // self.size_r) + 1
        size = round(self.w_size_r * self.w_size_r // self.size_r)

        if self.view_r > self.size_r - self.w_size_r:
            start = self.w_size_r - size - 1
            self.border_window.addch(
                self.w_size_r - 1,
                0,
                77,
                curses.color_pair(102) | curses.A_ALTCHARSET | curses.A_REVERSE,
            )

        if self.view_r == 0:
            self.border_window.addch(
                0, 0, 76, curses.color_pair(102) | curses.A_ALTCHARSET | curses.A_REVERSE
            )

        for i in range(start, start + size):
            try:
                self.border_window.addch(
                    i, 0, 88, curses.color_pair(102) | curses.A_ALTCHARSET | curses.A_REVERSE
                )
            except curses.error:
                pass

        if self.view_r >= self.size_r - self.w_size_r:
            start = self.w_size_r - size - 1
            self.border_window.addch(
                self.w_size_r - 1,
                0,
                77,
                curses.color_pair(102) | curses.A_ALTCHARSET | curses.A_REVERSE,
            )

        if self.view_r == 0:
            self.border_window.addch(
                0, 0, 76, curses.color_pair(102) | curses.A_ALTCHARSET | curses.A_REVERSE
            )

    @abc.abstractmethod
    def _draw(self):
        pass

    def refresh(self):
        """Refresh border window and visible part of main window"""
        self.border_window.noutrefresh()
        try:
            # can fail on window resize
            self.window.noutrefresh(
                self.view_r,
                self.view_c,
                self.s_r + 1,
                self.s_c + 1,
                self.s_r + self.w_size_r - 2,
                self.s_c + self.w_size_c - 2,
            )
        except curses.error:
            return

    def scroll_down(self):
        """Scroll down in scrollpad"""
        # full scroll
        if self.view_r <= self.size_r - 2 * self.w_size_r:
            self.view_r += self.w_size_r - 2
            return
        # scroll only to end
        if self.view_r < self.size_r - self.w_size_r:
            self.view_r = self.size_r - self.w_size_r

    def scroll_up(self):
        """Scroll up in scrollpad"""
        # full scroll
        if self.view_r >= self.w_size_r:
            self.view_r -= self.w_size_r + 2
            return
        # scroll to start of window
        if self.view_r < self.w_size_r:
            self.view_r = 0

    def draw(self):
        """Draw scrollpad"""
        if self.is_visible():
            self._draw()
            if self.is_selected():
                self.border_window.attrset(curses.color_pair(graphic.COLOR_OK))
            self.border_window.border()
            self.border_window.attrset(curses.color_pair(0))
            self.draw_scroll_indicator()
            self.refresh()

    def get_size(self):
        """Return size of window"""
        return self.border_window.getmaxyx()

    def get_pos(self):
        """Return position of top left corner"""
        return self.border_window.getbegyx()
