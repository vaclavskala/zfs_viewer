"""Tools for program GUI"""

import abc
import time
import curses
import threading

import window
import graphic


class ErrorScreen:
    """Screen shown when size of screen is not enough"""

    def __init__(self, screen, min_r, min_c):
        self.screen = screen
        self.min_r, self.min_c = min_r, min_c
        self.text1 = "Minimal screen size is " + str(min_r) + " rows and " + str(min_c) + " columns"

    def start(self):
        """Start screen"""
        graphic.Hideable.all_hidden = True
        self.screen.clear()
        self.screen.refresh()
        self.screen.border()
        rows, cols = self.screen.getmaxyx()
        self.screen.addstr(
            rows // 2, (cols - len(self.text1)) // 2, self.text1, curses.color_pair(4)
        )
        text2 = "Actual size is " + str(rows) + " rows and " + str(cols) + " columns"
        self.screen.addstr(rows // 2 + 1, (cols - len(text2)) // 2, text2, curses.color_pair(4))

    def stop(self):
        """Stop screen"""
        self.screen.clear()
        self.screen.refresh()
        graphic.Hideable.all_hidden = False


class Gui(window.Window):
    """Meta class. Source for other app classes"""

    gui_hidden = False

    @classmethod
    def hide_gui(cls, status):
        """Hide all gui elements"""
        Gui.gui_hidden = status

    @abc.abstractmethod
    def resize(self, s_r, s_c, row, col):
        pass

    @abc.abstractmethod
    def _draw(self):
        pass

    def is_hidden(self):
        return self.hidden or Gui.gui_hidden or graphic.Hideable.all_hidden


class TopMenuWindow(Gui):
    """Top menu window for selecting tabs/windows"""

    def __init__(self, main_screen):
        _, cols = main_screen.getmaxyx()
        super().__init__(0, 0, 3, cols - 30)
        self.top_menu = graphic.HorizontalMenu(
            ("pools", "datasets", "arc", "arc_IO", "zpool_IO", "dataset_IO", "PID_IO", "txgs"),
            0,
            0,
            tr=curses.ACS_TTEE,
            bl=curses.ACS_LTEE,
        )
        self.window.resize(3, self.top_menu.length + 1)

    def resize(self, s_r, s_c, row, col):
        self.draw()

    def _draw(self):
        self.top_menu.draw()
        self.refresh()


class TimeWindow(Gui):
    """Top right window for showing actual time"""

    def __init__(self, main_screen, period):
        self.should_exit = False
        self.__main_screen = main_screen
        self.__period = period
        _, cols = main_screen.getmaxyx()
        self.__text_len = len(time.strftime("%c", time.localtime()))
        super().__init__(0, cols - self.__text_len - 4, 3, self.__text_len + 4)
        # for argument count consistency
        self.resize(0, 0, 0, 0)
        threading.Thread(target=self.__timer_loop, daemon=True, name="Timer").start()

    def _draw(self):
        time_string = time.strftime("%c", time.localtime())
        self.window.addstr(1, 2, time_string)
        self.window.border()
        self.window.addch(0, 0, curses.ACS_TTEE)
        self.window.addch(0, self.__text_len + 3, curses.ACS_URCORNER)
        self.window.insch(2, self.__text_len + 3, curses.ACS_RTEE)

    def __timer_loop(self):
        while not self.should_exit:
            self.draw()
            time.sleep(self.__period)

    def resize(self, s_r, s_c, row, col):
        _, cols = self.__main_screen.getmaxyx()
        self.window.mvwin(0, cols - self.__text_len - 4)
        self.window.border()
        self.draw()
        self.refresh()
