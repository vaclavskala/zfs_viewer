"""Main app module"""

import curses
import signal

import graphic
import zfs_lib
import gui
import pool_window
import dataset_window
import arc_window
import arc_io_window
import zpool_io_window
import dataset_io_window
import pid_io_window
import txg_window


class Program:
    """Main class representing program"""

    # pylint: disable=too-many-instance-attributes
    def __init__(self, screen):
        signal.signal(signal.SIGINT, self.signal_handler_preinit)
        self.stdscr = screen
        graphic.GraphicObject.init_colors()
        curses.curs_set(0)
        self.min_r, self.min_c = 33, 133
        self.error_screen = gui.ErrorScreen(self.stdscr, self.min_r, self.min_c)
        while not self.is_size_ok():
            self.error_screen.start()
            curses.doupdate()
            char = self.stdscr.getch()
            if char > 0 and chr(char) == "q":
                curses.ungetch("q")
                return
        curses.halfdelay(10)
        self.zfs = zfs_lib.Zfs()
        self.window_map = {}
        self.window_map["pools"] = pool_window.PoolWindow(self.stdscr, self.zfs)
        self.window_map["datasets"] = dataset_window.DatasetWindow(self.stdscr, self.zfs)
        self.window_map["arc"] = arc_window.ArcWindow(self.stdscr, self.zfs)
        self.window_map["arc_IO"] = arc_io_window.ArcIOWindow(self.stdscr, self.zfs)
        self.window_map["zpool_IO"] = zpool_io_window.ZpoolIOWindow(self.stdscr, self.zfs)
        self.window_map["dataset_IO"] = dataset_io_window.DatasetIOWindow(self.stdscr, self.zfs)
        self.window_map["txgs"] = txg_window.TxgWindow(self.stdscr, self.zfs)
        self.window_map["PID_IO"] = pid_io_window.PIDWindow(self.stdscr, self.zfs)
        self.time_window = gui.TimeWindow(self.stdscr, 1)
        self.top_menu_window = gui.TopMenuWindow(self.stdscr)
        #        self.top_menu_window.top_menu.set_graylist(['arc','arc_IO'])
        self.resize()

    def selected_window(self):
        """Return item selected by top menu"""
        return self.window_map[self.top_menu_window.top_menu.selected()]

    def is_size_ok(self):
        """Check if size of window is bigger than minimum"""
        rows, cols = self.stdscr.getmaxyx()
        if (rows >= self.min_r) and (cols >= self.min_c):
            return True
        return False

    # pylint: disable=no-self-use
    def signal_handler_preinit(self, *_):
        """When ctrl+c, send 'q' to program

        Used when app is not initialized"""
        curses.ungetch("q")

    # not needed
    def signal_handler(self, *_):
        """When app is initialized, stop time_window and send exit to app"""
        self.time_window.should_exit = True
        curses.ungetch("q")

    def resize(self):
        """Called when window is resized"""
        if self.is_size_ok():
            curses.flushinp()
            self.error_screen.stop()
            self.top_menu_window.resize(0, 0, 0, 0)
            self.time_window.resize(0, 0, 0, 0)
            for window in self.window_map.values():
                window.resize(0, 0, 0, 0)
            self.selected_window().resize(0, 0, 0, 0)

            self.stdscr.border()
            self.stdscr.noutrefresh()
            self.top_menu_window.draw()
            self.time_window.draw()
            self.time_window.refresh()
            self.selected_window().draw()
            self.selected_window().refresh()
            curses.doupdate()
        else:
            self.error_screen.start()

    def main_screen(self):
        """Main loop

        Handle input, draw and resize
        """
        while True:
            char = self.stdscr.getch()
            if char == -1:
                if self.is_size_ok():
                    self.time_window.refresh()
                    self.selected_window().draw()
                    self.selected_window().refresh()
                    curses.doupdate()
                continue
            if char == curses.KEY_RIGHT:
                self.top_menu_window.top_menu.move_right()
                self.top_menu_window.draw()
                self.selected_window().draw()
                self.selected_window().refresh()
            if char == curses.KEY_LEFT:
                self.top_menu_window.top_menu.move_left()
                self.top_menu_window.draw()
                self.selected_window().draw()
                self.selected_window().refresh()
            if char == curses.KEY_RESIZE:
                self.resize()
                self.top_menu_window.draw()
                continue
            if char == ord("\t"):
                self.selected_window().cycle_elements()
            if char == 353:
                self.selected_window().cycle_elements_bck()
            if chr(char) == "x":
                gui.Gui.hide_gui(not gui.Gui.gui_hidden)
                self.resize()
                self.stdscr.border()
                self.stdscr.noutrefresh()
                self.top_menu_window.draw()
                self.time_window.resize(0, 0, 0, 0)
            if chr(char) == "q":
                break
            if chr(char) == "r":
                # todo: rescan all windows
                self.selected_window().rescan()

            self.time_window.refresh()
            self.selected_window().handle_key(char)
            curses.doupdate()


def main_stage2(stdscr):
    """Main function"""
    program = Program(stdscr)
    program.main_screen()


# wrapper restore original terminal settings
def main():
    """Main"""
    curses.wrapper(main_stage2)


if __name__ == "__main__":
    main()
