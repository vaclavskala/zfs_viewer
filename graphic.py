"""Module for basic graphic tools"""

import curses
import abc

COLOR_OK = 1
COLOR_ERR = 2
COLOR_WARN = 3
COLOR_ALERT = 4

COLOR_FG_GREEN = 1
COLOR_FG_RED = 2
COLOR_FG_YELLOW = 3
COLOR_FG_WHITE = 6
COLOR_FG_BLUE = 7
COLOR_FG_CYAN = 8

COLOR_BCK_WHITE = 100
COLOR_BCK_RED = 101
COLOR_BCK_BLUE = 102
COLOR_BCK_GREEN = 103
COLOR_BCK_YELLOW = 104
COLOR_BCK_CYAN = 105
COLOR_BCK_MAGENTA = 106


class Hideable(metaclass=abc.ABCMeta):
    """Meta class to implement object hide"""

    all_hidden = False

    def __init__(self):
        self.hidden = False

    def hide(self, status):
        """Hide object"""
        self.hidden = status

    def is_hidden(self):
        """Check if object is hidden"""
        return self.hidden or Hideable.all_hidden

    def is_visible(self):
        """Check if object is visible"""
        return not self.is_hidden()


class GraphicObject(Hideable):
    """Basic class for graphic object, save position and size"""

    color_initialized = False

    def __init__(self, window, s_r, s_c):
        assert s_r >= 0
        assert s_c >= 0
        self.s_r = s_r
        self.s_c = s_c
        self.window = window
        super().__init__()
        GraphicObject.init_colors()

    @classmethod
    def init_colors(cls):
        """Class method to init collors with first created object"""
        if not GraphicObject.color_initialized:
            curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
            curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
            curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
            curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_RED)
            curses.init_pair(5, curses.COLOR_RED, curses.COLOR_WHITE)
            curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLACK)
            curses.init_pair(7, curses.COLOR_BLUE, curses.COLOR_BLACK)
            curses.init_pair(8, curses.COLOR_CYAN, curses.COLOR_BLACK)

            curses.init_pair(100, curses.COLOR_BLACK, curses.COLOR_WHITE)
            curses.init_pair(101, curses.COLOR_BLACK, curses.COLOR_RED)
            curses.init_pair(102, curses.COLOR_BLACK, curses.COLOR_BLUE)
            curses.init_pair(103, curses.COLOR_BLACK, curses.COLOR_GREEN)
            curses.init_pair(104, curses.COLOR_BLACK, curses.COLOR_YELLOW)
            curses.init_pair(105, curses.COLOR_BLACK, curses.COLOR_CYAN)
            curses.init_pair(106, curses.COLOR_BLACK, curses.COLOR_MAGENTA)

    @abc.abstractmethod
    def _draw(self):
        pass

    def draw(self):
        """Call internal draw function if object of visible"""
        if self.is_visible():
            self._draw()


# pylint: disable=too-many-instance-attributes
class Menu(GraphicObject):
    """Parent class for menus"""

    def __init__(self, menu_entries, s_r, s_c, n_r, n_c, entry_id=0, **kwargs):
        assert n_r >= 0
        assert n_c >= 0
        assert entry_id >= -1
        self.s_r = s_r
        self.s_c = s_c
        self.max_entry_id = len(menu_entries)
        self.menu_entries = menu_entries
        self.entry_id = entry_id % self.max_entry_id
        self.size_r, self.size_c = n_r, n_c
        self.graylist = []

        self.max_size = 0
        self.shift = 0
        self.max_visible_items = len(menu_entries)

        self.window = curses.newwin(n_r, n_c, s_r, s_c)
        self.window.border()
        super().__init__(self.window, s_r, s_c)

        self.char_map = {
            "ls": 0,
            "rs": 0,
            "ts": 0,
            "bs": 0,
            "tl": 0,
            "tr": 0,
            "bl": 0,
            "br": 0,
        }
        self.char_map.update(kwargs)

    def __del__(self):
        self.window.erase()

    def _update_menu(self, n_r, n_c, menu_entries):
        """Change menu items"""
        self.max_entry_id = len(menu_entries)
        self.menu_entries = menu_entries
        self.entry_id = self.entry_id % self.max_entry_id
        self.window.resize(n_r, n_c)
        self.size_r, self.size_c = n_r, n_c
        self.window.border()

    def move_window(self, row, col):
        """Move menu window"""
        try:
            self.window.mvwin(row, col)
        except curses.error:
            return

    def selected(self):
        """Return actual selected element"""
        return self.menu_entries[self.entry_id]

    def resize(self):
        """Resize menu window"""
        # todo: is it needed?
        self.window.erase()
        self.window.noutrefresh()
        try:
            self.window.resize(self.size_r, self.size_c)
        except curses.error:
            return
        self.draw()

    def item_count(self):
        """Return menu items count"""
        return len(self.menu_entries)

    def move_down(self):
        """Scroll down in menu"""
        self.move_right()

    def move_up(self):
        """Scroll up in menu"""
        self.move_left()

    def set_pos(self, item):
        """Change selected item"""
        if item in self.menu_entries:
            if not item in self.graylist:
                self.entry_id = self.menu_entries.index(item)

    def move_right(self):
        """Scroll right in menu"""
        if self.entry_id != -1:
            self.entry_id = (self.entry_id + 1) % self.max_entry_id
            if self.entry_id == 0:
                self.shift = 0
            if self.menu_entries[self.entry_id] in self.graylist:
                self.move_right()
            if self.max_size > 0 and self.entry_id >= self.shift + self.max_visible_items:
                self.shift += 1

    def move_left(self):
        """Scroll left in menu"""
        if self.entry_id != -1:
            self.entry_id = (self.entry_id - 1 + self.max_entry_id) % self.max_entry_id
            if self.menu_entries[self.entry_id] in self.graylist:
                self.move_left()
            if self.entry_id == self.max_entry_id - 1:
                self.shift = self.max_entry_id - 1 - self.max_visible_items + 1
            if self.max_size > 0 and self.entry_id < self.shift:
                self.shift -= 1

    def get_size(self):
        """Return size of menu window"""
        return self.window.getmaxyx()

    def get_pos(self):
        """Return position of menu window"""
        return self.window.getbegyx()

    def set_graylist(self, graylist):
        """Disable some elements in menu"""
        self.graylist = graylist
        if self.menu_entries[self.entry_id] in self.graylist:
            self.move_right()

    def refresh(self):
        """Refresh window"""
        self.window.noutrefresh()

    @abc.abstractmethod
    def _draw(self):
        pass


class HorizontalMenu(Menu):
    """Menu in row"""

    def __init__(
        self, menu_entries, s_r, s_c, entry_id=0, field_separation=1, separator=" ", **kwargs
    ):
        assert field_separation >= 0
        self.separator = ""
        self.field_separation = field_separation
        for _ in range(field_separation):
            self.separator += self.separator + separator

        self.length = 0
        for item in menu_entries:
            self.length += len(item) + 1 + 2 * self.field_separation
        super().__init__(menu_entries, s_r, s_c, 3, self.length + 1, entry_id, **kwargs)

    def _draw(self):
        length = 0
        self.window.border(*self.char_map.values())
        for item in self.menu_entries:
            if self.entry_id == self.menu_entries.index(item):
                self.window.addstr(
                    1, 1 + length, self.separator + item + self.separator, curses.color_pair(1)
                )
            else:
                if item in self.graylist:
                    self.window.addstr(
                        1, 1 + length, self.separator + item + self.separator, curses.A_DIM
                    )
                else:
                    self.window.addstr(1, 1 + length, self.separator + item + self.separator)
            length += len(item) + 1 + 2 * self.field_separation
            if item != self.menu_entries[-1]:
                self.window.addch(0, length, curses.ACS_TTEE)
                self.window.addch(1, length, curses.ACS_VLINE)
                self.window.delch(2, length)
                self.window.insch(2, length, curses.ACS_BTEE)
        self.window.noutrefresh()

    def update_menu(self, menu_entries):
        """Update menu items"""
        self.length = 0
        for item in menu_entries:
            self.length += len(item) + 1 + 2 * self.field_separation
        super()._update_menu(3, self.length + 1, menu_entries)


class VerticalMenu(Menu):
    """Menu in column"""

    def __init__(self, menu_entries, s_r, s_c, entry_id=0, length=0, max_item_len=9999, **kwargs):
        # todo: length: assert and limit string length
        self.max_length = 0
        item_count = 0
        self.length = length
        self.max_item_len = max_item_len

        for item in menu_entries:
            if len(item) > self.max_length:
                self.max_length = len(item)
            item_count += 1
        if length > 0:
            self.max_length = length
        self.max_length = min(self.max_length, self.max_item_len)
        super().__init__(
            menu_entries, s_r, s_c, item_count * 2 + 1, self.max_length + 4, entry_id, **kwargs
        )

    def set_max_size(self, max_size):
        """Limit max size of menu window"""
        if max_size % 2 != 1:
            max_size = (max_size // 2) * 2 - 1
        max_size = min(max_size, len(self.menu_entries) * 2 + 1)
        self.max_size = max_size
        self.size_r = max_size + 0
        self.max_visible_items = (max_size - 1) // 2

    def _draw(self):
        self.window.erase()
        count = 0
        self.window.border(*self.char_map.values())
        for item in self.menu_entries[self.shift : self.shift + self.max_visible_items]:
            if self.entry_id == self.menu_entries.index(item):
                self.window.addstr(
                    2 * count + 1, 2, item[0 : self.max_item_len], curses.color_pair(1)
                )
            else:
                if item in self.graylist:
                    self.window.addstr(2 * count + 1, 2, item[0 : self.max_item_len], curses.A_DIM)
                else:
                    self.window.addstr(2 * count + 1, 2, item[0 : self.max_item_len])
            if item != self.menu_entries[self.shift : self.shift + self.max_visible_items][-1]:
                self.window.hline(2 * count + 2, 1, curses.ACS_HLINE, self.max_length + 2)
                self.window.addch(2 * count + 2, 0, curses.ACS_LTEE)
                self.window.addch(2 * count + 2, self.max_length + 3, curses.ACS_RTEE)
            count += 1
        if self.max_size > 0:
            if self.shift > 0:
                self.window.addch(0, (self.max_length + 2) // 2, chr(45), curses.A_ALTCHARSET)
            if self.shift + self.max_visible_items < len(self.menu_entries):
                self.window.addch(
                    self.size_r - 1, (self.max_length + 2) // 2, chr(46), curses.A_ALTCHARSET
                )
        self.window.noutrefresh()

    def update_menu(self, menu_entries):
        """Update menu entries"""
        self.max_length = 0
        item_count = 0
        for item in menu_entries:
            if len(item) > self.max_length:
                self.max_length = len(item)
            item_count += 1
        super()._update_menu(item_count * 2 + 1, self.max_length + 4, menu_entries)


class BarGraph(GraphicObject):
    """Class implementing barr graph"""

    palette = (
        COLOR_BCK_RED,
        COLOR_BCK_BLUE,
        COLOR_BCK_GREEN,
        COLOR_BCK_YELLOW,
        COLOR_BCK_CYAN,
        COLOR_BCK_MAGENTA,
    )
    # todo: add colors, rotate palete

    def __init__(self, values, s_r, s_c, size_r, size_c, colors):
        self.window = curses.newwin(size_r, size_c, s_r, s_c)
        self.window.border()
        self.values = values
        self.colors = colors
        self.draw_values = {}
        self.palette_index = 0
        self.size = size_c - 2
        self.bar_string = " " * 500
        super().__init__(self.window, s_r, s_c)

    def get_color(self, key):
        """Return color. Specified on creation or selected from avaliable"""
        try:
            color = self.colors[key]
        except KeyError:
            color = BarGraph.palette[self.palette_index]
            self.palette_index += 1
        return color

    def calculate_sizes(self):
        """Calculate bar sizes"""
        suma = 0
        self.palette_index = 0
        self.draw_values = {}
        for key in self.values:
            suma += self.values[key]

        for key in self.values:
            color = self.get_color(key)
            if self.values[key] > 0:
                self.draw_values[key] = (
                    self.size * self.values[key] / suma,
                    self.size * self.values[key] // suma,
                    color,
                )

    def resize(self, s_r, s_c, size_r, size_c):
        """Resize graph"""
        self.size = size_c - 2
        self.calculate_sizes()
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

    # pylint: disable=consider-using-dict-items
    def _draw(self):
        self.window.erase()
        self.window.border()
        i = 1.0
        j = 1
        self.window.addstr(3, j, self.bar_string[0 : self.size])
        for key in self.draw_values:
            try:
                data = self.draw_values[key]
                self.window.addstr(
                    1, round(i), self.bar_string[0 : data[1] + 1], curses.color_pair(data[2])
                )
                percent = round(100 * data[0] / self.size, 2)
                if data[1] >= len(str(percent)) + 2:
                    self.window.addstr(
                        1, int(i) + data[1] // 2, str(percent) + "%", curses.color_pair(data[2])
                    )
                i += data[0]
                self.window.addstr(3, j, key, curses.color_pair(data[2]) | curses.A_REVERSE)
                j += len(key) + 10
            except curses.error:
                continue
        self.window.addstr(2, 1, "Legend:", curses.A_BOLD)
        self.window.border()
        self.window.noutrefresh()
