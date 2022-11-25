"""Basic class for curses windows"""

import abc
import curses

import graphic

# pylint: disable=duplicate-code


class Window(graphic.Hideable):
    """Class representing window on screen"""

    # pylint: disable=duplicate-code
    def __init__(self, s_r, s_c, size_r, size_c):
        self.window = curses.newwin(size_r, size_c, s_r, s_c)
        self.s_r = s_r
        self.s_c = s_c
        self.size_r = size_r
        self.size_c = size_c
        super().__init__()
        self.need_redraw = False

    @abc.abstractmethod
    def resize(self, s_r, s_c, row, col):
        """All windows must implement resize function

        Called when screen resized.
        """
        pass

    @abc.abstractmethod
    def _draw(self):
        """All windows must implement _draw function

        Called by draw function when object is not hidden
        """
        pass

    def refresh(self):
        """Refresh window"""
        self.window.noutrefresh()

    def handle_key(self, char):
        """Handle input keys

        When window need key input, it can reimplement this function
        """
        pass

    def draw(self):
        """Call internal draw if object is visible"""
        if self.is_visible():
            self._draw()

    def get_size(self):
        """Return size of window"""
        return self.window.getmaxyx()

    def get_pos(self):
        """Return top left corner of window"""
        return self.window.getbegyx()
