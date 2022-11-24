"""Module for pool info class"""

import curses

import graphic
import window
import scroll_pad
import utils
import zfs_lib
import gui


class PoolWindowBarGraph(graphic.BarGraph):
    """Bar graph for pool space usage"""

    def __init__(self, pool_menu, zfs, values, s_r, s_c, size_r, size_c, colors=None):
        if colors is None:
            colors = {}
        self.menu = pool_menu
        self.zfs = zfs
        self.last_pool = self.zfs.zpools[self.menu.selected()]
        super().__init__(values, s_r, s_c, size_r, size_c, colors)
        self.prepare_data()

    def prepare_data(self):
        """Convert data to bar graph format"""
        self.values = {}
        self.values["used"] = int(self.last_pool.property["allocated"])
        if self.last_pool.property["checkpoint"] == "-":
            self.values["checkpoint"] = 0
        else:
            self.values["checkpoint"] = int(self.last_pool.property["checkpoint"])
        self.values["free"] = int(self.last_pool.property["free"])
        self.calculate_sizes()

    def _draw(self):
        if self.last_pool != self.zfs.zpools[self.menu.selected()]:
            self.last_pool = self.zfs.zpools[self.menu.selected()]
            self.prepare_data()
        super()._draw()


class PoolWindow(window.AppWindow):
    """Main pool IO window"""

    def __init__(self, main_screen, zfs):
        self.zfs = zfs
        super().__init__(main_screen, 3, 1)
        rows, cols = self.window.getmaxyx()
        row, col = self.window.getbegyx()

        self.pool_menu = graphic.VerticalMenu(zfs.get_pools(), row + 1, col + 2)
        self.pool_pad = PoolPad(
            row + 1,
            self.pool_menu.get_size()[1] + col + 2,
            20,
            60,
            rows - 7,
            60,
            self.zfs,
            self.pool_menu,
        )
        self.dbgmsg_pad = DbgmsgPad(
            row + 1,
            self.pool_menu.get_size()[1] + col + 2 + 60,
            60,
            155,
            (rows - 7) // 2,
            cols - (self.pool_menu.get_size()[1] + col + 2 + 60),
            self.zfs.log,
        )
        pool = self.zfs.zpools[self.pool_menu.selected()]
        self.events_pad = EventPad(
            row + (rows - 7) // 2 + 1,
            self.pool_menu.get_size()[1] + col + 2 + 60,
            60,
            155,
            (rows - 7) - (rows - 7) // 2,
            cols - (self.pool_menu.get_size()[1] + col + 2 + 60),
            pool.event_log.logs,
        )
        self.usage_bar = PoolWindowBarGraph(self.pool_menu, self.zfs, [], rows - 6, 2, 5, cols - 2)

        self.register_element(self.pool_pad)
        self.register_element(self.dbgmsg_pad)
        self.register_element(self.events_pad)
        self.pool_pad.select()

        self.draw()

    def resize(self, s_r, s_c, row, col):
        """Resize window"""
        self.resize_window()
        row, col = self.window.getbegyx()
        rows, cols = self.window.getmaxyx()
        self.pool_menu.resize()
        if gui.Gui.gui_hidden:
            pad_c = 1
        else:
            pad_c = 2
        self.pool_pad.resize(row + 1, self.pool_menu.get_size()[1] + col + 2, rows - 7, 60)
        self.dbgmsg_pad.resize(
            row + 1,
            self.pool_menu.get_size()[1] + col + 2 + 60,
            (rows - 7) // 2,
            cols - (self.pool_menu.get_size()[1] + 3 + 60),
        )
        self.usage_bar.resize(rows - 6 + self.window.getbegyx()[0], pad_c, 5, cols - 2)
        self.pool_menu.move_window(row + 1, col + 2)

        self.events_pad.resize(
            row + (rows - 7) // 2 + 1,
            self.pool_menu.get_size()[1] + col + 2 + 60,
            (rows - 7) - (rows - 7) // 2,
            cols - (self.pool_menu.get_size()[1] + 3 + 60),
        )
        self.usage_bar.window.noutrefresh()
        self.draw()
        self.refresh()

    def rescan(self):
        """Rescan"""
        self.zfs.rescan_pools()
        self.pool_menu.update_menu(self.zfs.get_pools())
        self.resize(0, 0, 0, 0)

    def _draw(self):
        self.window.border()
        self.window.noutrefresh()
        self.pool_menu.draw()
        self.pool_pad.draw()
        self.dbgmsg_pad.draw()
        self.events_pad.draw()
        self.usage_bar.draw()
        self.refresh()

    def handle_key(self, char):
        """Handle user input"""
        if char == curses.KEY_DOWN:
            self.pool_menu.move_right()
            pool = self.zfs.zpools[self.pool_menu.selected()]
            self.events_pad.change_queue(pool.event_log.logs)
        if char == curses.KEY_NPAGE:
            for item in self.get_selected_elements():
                item.scroll_down()
        if char == curses.KEY_PPAGE:
            for item in self.get_selected_elements():
                item.scroll_up()
        if char == curses.KEY_UP:
            self.pool_menu.move_left()
            pool = self.zfs.zpools[self.pool_menu.selected()]
            self.events_pad.change_queue(pool.event_log.logs)
        self.draw()


class DbgmsgPad(scroll_pad.ScrollPad):
    """Scrollpad printing data from queue"""

    def __init__(self, s_r, s_c, size_r, size_c, w_size_r, w_size_c, queue):
        self.queue = queue
        super().__init__(s_r, s_c, w_size_r, w_size_c, w_size_r, w_size_c, True)
        self.draw()

    def change_queue(self, queue):
        """Change input queue"""
        self.queue = queue

    def _draw(self):
        self.window.erase()
        i = 0
        record = 0
        for line in list(self.queue):
            record += 1
            data = line[10:]
            self.add_line(i, 0, line[:8])
            for sub_line in utils.split_on_words(data, self.window.getmaxyx()[1] - 11):
                i += self.add_line(i, 9, sub_line)
            if record > 10:
                return


class EventPad(scroll_pad.ScrollPad):
    """Specialized pad for printing event log"""

    def __init__(self, s_r, s_c, size_r, size_c, w_size_r, w_size_c, queue):
        self.queue = queue
        super().__init__(s_r, s_c, 30, size_c, w_size_r, w_size_c)
        self.draw()

    def change_queue(self, queue):
        """Change input queue"""
        self.queue = queue

    def _draw(self):
        self.window.erase()
        i = 0
        rows = self.window.getmaxyx()[0]
        for record in self.queue:
            for line in record.rows:
                if i < rows - 1:
                    self.window.addstr(i, 0, line)
                try:
                    self.window.addstr(i, 0, line)
                except curses.error:
                    break
                i += 1


class PoolPad(scroll_pad.ScrollPad):
    """Scroll pad for pool info"""

    def __init__(self, s_r, s_c, size_r, size_c, w_size_r, w_size_c, zfs, Menu):
        self.menu = Menu
        self.zfs = zfs
        super().__init__(s_r, s_c, size_r, size_c, w_size_r, w_size_c, True)
        self.draw()

    # pylint: disable=too-many-branches,too-many-statements
    def _draw(self):
        pool = self.zfs.zpools[self.menu.selected()]
        self.window.erase()
        i = 0
        self.window.addstr(i, 1, "Properties:", curses.A_BOLD)
        i += 1
        shift = 20
        self.window.addstr(i, 1, "Health:")
        if pool.property["health"] == "ONLINE":
            color = curses.color_pair(graphic.COLOR_OK)
        else:
            color = curses.color_pair(graphic.COLOR_ERR)
        self.window.addstr(i, shift, pool.property["health"], color)
        i += 1

        self.window.addstr(i, 1, "Size:")
        self.window.addstr(i, shift, utils.convert_size(int(pool.property["size"])))
        i += 1

        self.window.addstr(i, 1, "Allocated:")
        self.window.addstr(i, shift, utils.convert_size(int(pool.property["allocated"])))
        i += 1

        self.window.addstr(i, 1, "Free:")
        self.window.addstr(i, shift, utils.convert_size(int(pool.property["free"])))
        i += 1

        self.window.addstr(i, 1, "Capacity:")
        if int(pool.property["capacity"]) < zfs_lib.CAPACITY_LIMIT_WARN:
            color = curses.color_pair(graphic.COLOR_OK)
        else:
            if int(pool.property["capacity"]) < zfs_lib.CAPACITY_LIMIT_ERR:
                color = curses.color_pair(graphic.COLOR_WARN)
            else:
                color = curses.color_pair(graphic.COLOR_ERR)
        self.window.addstr(i, shift, str(pool.property["capacity"]) + "%", color)
        i += 1

        self.window.addstr(i, 1, "Fragmentation:")
        if int(pool.property["fragmentation"]) < zfs_lib.FRAGMENTATION_LIMIT_WARN:
            color = curses.color_pair(graphic.COLOR_OK)
        else:
            if int(pool.property["fragmentation"]) < zfs_lib.FRAGMENTATION_LIMIT_ERR:
                color = curses.color_pair(graphic.COLOR_WARN)
            else:
                color = curses.color_pair(graphic.COLOR_ERR)
        self.window.addstr(i, shift, str(pool.property["fragmentation"]) + "%", color)
        i += 1

        self.window.addstr(i, 1, "Freeing:")
        if int(pool.property["freeing"]) < zfs_lib.FREEING_LIMIT:
            color = curses.color_pair(graphic.COLOR_OK)
        else:
            color = curses.color_pair(graphic.COLOR_WARN)
        self.window.addstr(i, shift, utils.convert_size(int(pool.property["freeing"])), color)
        i += 1

        self.window.addstr(i, 1, "Autotrim:")
        self.window.addstr(i, shift, str(pool.property["autotrim"]), color)
        i += 1

        self.window.addstr(i, 1, "Readonly:")
        if pool.property["readonly"] == "off":
            color = curses.color_pair(graphic.COLOR_OK)
        else:
            color = curses.color_pair(graphic.COLOR_ERR)
        self.window.addstr(i, shift, str(pool.property["readonly"]), color)
        i += 1

        self.window.addstr(i, 1, "Dedupratio:")
        self.window.addstr(i, shift, pool.property["dedupratio"])
        i += 1

        self.window.addstr(i, 1, "Metaslabs:")
        self.window.addstr(i, shift, pool.property["metaslabs"])
        i += 1

        self.window.addstr(i, 1, "Checkpoint:")
        if pool.property["checkpoint"] == "-":
            self.window.addstr(i, shift, str(pool.property["checkpoint"]))
        else:
            self.window.addstr(i, shift, utils.convert_size(int(pool.property["checkpoint"])))
        i += 2

        self.window.addstr(i, 1, "Metaslab fragmentation histogram:", curses.A_BOLD)
        i += 1
        for line in pool.frag_hist:
            inc = self.add_line(i, 1, line)
            i += inc
