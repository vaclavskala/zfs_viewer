"""Basic class for curses windows"""

import abc
import curses

import graphic
import gui

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


class AppWindow(Window):
    """Class for AppWindow

    AppWindow is full screen window selected by top menu
    """

    def __init__(self, main_screen, pad_x, pad_y):
        self.__main_screen = main_screen
        rows, cols = main_screen.getmaxyx()
        self.__pad_x, self.__pad_y = pad_x, pad_y
        self.selectable_elements = []
        self.element_counter = 0
        super().__init__(
            self.__pad_x, self.__pad_y, rows - self.__pad_x - 1, cols - self.__pad_y - 1
        )

    @abc.abstractmethod
    def resize(self, s_r, s_c, row, col):
        pass

    @abc.abstractmethod
    def _draw(self):
        pass

    @abc.abstractmethod
    def rescan(self):
        """Rescan function

        If window need to rescan some sources
        """
        pass

    def register_element(self, element):
        """Register tab scrollable element"""
        self.selectable_elements.append(element)

    def _select_all(self):
        """Select all elements"""
        for element in self.selectable_elements:
            element.select()

    def _unselect_all(self):
        """Unselect all elements"""
        for element in self.selectable_elements:
            element.unselect()

    def cycle_elements(self):
        """Unselect actual element and select new element"""
        self._unselect_all()
        self.element_counter += 1
        if self.element_counter >= len(self.selectable_elements):
            self.element_counter = -1
            self._select_all()
        else:
            self.selectable_elements[self.element_counter].select()

    def cycle_elements_bck(self):
        """Unselect actual element and select new element"""
        self._unselect_all()
        self.element_counter -= 1
        if self.element_counter < 0:
            self.element_counter = len(self.selectable_elements)
            self._select_all()
        else:
            self.selectable_elements[self.element_counter].select()

    def get_selected_elements(self):
        """Return list of selected elements"""
        if self.element_counter >= 0 and self.element_counter < len(self.selectable_elements):
            return [self.selectable_elements[self.element_counter]]
        if self.element_counter == -1:
            return self.selectable_elements
        return []

    def resize_window(self):
        """Resize window"""
        self.window.erase()
        rows, cols = self.__main_screen.getmaxyx()
        if gui.Gui.gui_hidden:
            self.window.mvwin(0, 0)
            self.window.resize(rows, cols)
        else:
            self.window.resize(rows - self.__pad_x - 1, cols - self.__pad_y - 1)
            self.window.mvwin(self.__pad_x, self.__pad_y)
        self.window.border()
        self.refresh()
