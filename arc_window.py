"""Module for arc window"""

import curses

import graphic
import app_window
import scroll_pad
import utils
import time_graph
import arc_history


class ArcBarGraph(graphic.BarGraph):
    """Bar graph for memory usage"""

    def __init__(self, zfs, values, s_r, s_c, size_r, size_c, colors=None):
        if colors is None:
            colors = {}
        self.zfs = zfs
        super().__init__(values, s_r, s_c, size_r, size_c, colors)
        self.prepare_data()

    def prepare_data(self):
        """Prepare data in bar graph format"""
        stats = self.zfs.arc.stats
        self.values = {}
        try:
            self.values["arc"] = int(stats["size"])
            self.values["system"] = int(stats["memory_all_bytes"]) - int(stats["memory_free_bytes"])
            self.values["free"] = int(stats["memory_free_bytes"])
            self.calculate_sizes()
        except KeyError:
            return

    def _draw(self):
        self.prepare_data()
        super()._draw()


class ArcWindow(app_window.AppWindow):
    """Main arc info window"""

    def __init__(self, main_screen, zfs):
        self.zfs = zfs
        super().__init__(main_screen, 3, 1)
        rows, cols = self.window.getmaxyx()
        row, col = self.window.getbegyx()

        self.arc_pad = ArcPad(row + 1, col + 2, 10, 40, rows - 7, 40, self.zfs)
        self.arc_comp_bar2 = ArcBarGraph(self.zfs, [], rows - 3, 2, 5, cols - 2)

        self.arc_time_graph = time_graph.TimeGraphMulti(
            6, col + 2 + 40, rows - 7 - 2, cols - 2 - 41, zfs.arc.arc_history.graph1_data
        )
        self.arc_time_graph.enable_x_scale(1, utils.add_second)
        self.time_graph_menu = graphic.HorizontalMenu(
            ["ARC by cache", "ARC by type"], 4, col + 2 + 40, br=curses.ACS_BTEE, bl=curses.ACS_LTEE
        )
        self.register_element(self.arc_pad)
        self.arc_pad.select()
        self.arc_time_graph.set_convert_funct(utils.convert_size)

    def resize(self, s_r, s_c, row, col):
        self.resize_window()
        row, col = self.window.getbegyx()
        rows = self.window.getmaxyx()[0]
        ###        if gui.Gui.gui_hidden:
        ###            pad_c = 1
        ###        else:
        ###            pad_c = 2
        self.arc_pad.resize(row + 1, col + 2, rows - 7, 40)
        self.draw()
        self.refresh()

    def rescan(self):
        """Rescan"""
        # todo: todo
        pass

    def print_graph_legend(self):
        """Print legend above of arc graph"""
        rows, cols = self.window.getmaxyx()
        if self.time_graph_menu.selected() == "ARC by cache":
            values = arc_history.GRAPH_1 + ["other_size"]
        else:
            values = arc_history.GRAPH_2
        i = 0
        inc = 0
        self.window.addstr(2, 2 + 40 + 30, " " * (cols - 42 - 31))
        try:
            for val in values:
                self.window.addch(
                    2,
                    2 + 40 + 31 + inc,
                    96,
                    curses.A_ALTCHARSET
                    | curses.color_pair(self.arc_time_graph.palette[i])
                    | curses.A_REVERSE,
                )
                self.window.addstr(2, 2 + 40 + 31 + inc + 2, val, self.arc_time_graph.palette[i])
                inc += len(val) + 5
                i += 1
        except curses.error:
            i = 0
            inc = 0
            self.window.addstr(2, 2 + 40 + 30, " " * (cols - 42 - 30))
            self.window.addch(2, cols - 1, curses.ACS_VLINE)
            for val in values:
                self.window.addch(
                    2,
                    2 + 40 + 31 + inc,
                    96,
                    curses.A_ALTCHARSET
                    | curses.color_pair(self.arc_time_graph.palette[i])
                    | curses.A_REVERSE,
                )
                self.window.addstr(
                    2,
                    2 + 40 + 31 + inc + 2,
                    val.replace("_size", ""),
                    self.arc_time_graph.palette[i],
                )
                inc += len(val.replace("_size", "")) + 5
                i += 1

    def _draw(self):
        self.window.border()
        self.window.noutrefresh()
        self.arc_pad.draw()
        self.arc_time_graph.draw()
        self.arc_comp_bar2.draw()
        self.time_graph_menu.draw()
        self.print_graph_legend()

        self.refresh()

    def map_menu_to_graph(self):
        """Chose correct values for legend based on arc type menu"""
        if self.time_graph_menu.selected() == "ARC by cache":
            return self.zfs.arc.arc_history.graph1_data
        return self.zfs.arc.arc_history.graph2_data

    def handle_key(self, char):
        """Handle user input"""
        if char == curses.KEY_NPAGE:
            for item in self.get_selected_elements():
                item.scroll_down()
        if char == curses.KEY_PPAGE:
            for item in self.get_selected_elements():
                item.scroll_up()
        if chr(char) == "h":
            self.time_graph_menu.move_left()
            self.arc_time_graph.change_source(self.map_menu_to_graph())
        if chr(char) == "l":
            self.time_graph_menu.move_right()
            self.arc_time_graph.change_source(self.map_menu_to_graph())
        self.draw()


class ArcPad(scroll_pad.ScrollPad):
    """Class for ARC info scrollpad"""

    def __init__(self, s_r, s_c, size_r, size_c, w_size_r, w_size_c, zfs):
        self.zfs = zfs
        super().__init__(s_r, s_c, size_r, size_c, w_size_r, w_size_c, True)
        self.draw()

    # pylint: disable=too-many-statements
    def _draw(self):
        self.window.erase()
        self.border_window.attrset(curses.color_pair(graphic.COLOR_OK))
        self.border_window.border()
        self.border_window.attrset(curses.color_pair(0))
        stats = self.zfs.arc.stats
        i = 0
        self.window.addstr(i, 1, "Arc stats:", curses.A_BOLD)
        i += 1
        shift = 25

        try:
            self.window.addstr(
                i, shift, str(round(100 * int(stats["size"]) / int(stats["c_max"]), 2)) + "%"
            )
            self.window.addstr(i, 1, "Used:")
            i += 1

            self.window.addstr(i, 1, "Actual size:")
            self.window.addstr(i, shift, utils.convert_size(int(stats["size"])))
            i += 1

            self.window.addstr(i, 1, "Target size:")
            self.window.addstr(i, shift, utils.convert_size(int(stats["c"])))
            i += 1

            self.window.addstr(i, 1, "Minimal size:")
            self.window.addstr(i, shift, utils.convert_size(int(stats["c_min"])))
            i += 1

            self.window.addstr(i, 1, "Maximal size:")
            self.window.addstr(i, shift, utils.convert_size(int(stats["c_max"])))
            i += 1

            self.window.addstr(i, 1, "MFU size:")
            self.window.addstr(i, shift, utils.convert_size(int(stats["mfu_size"])))
            i += 1

            self.window.addstr(i, 1, "MRU size:")
            self.window.addstr(i, shift, utils.convert_size(int(stats["mru_size"])))
            i += 1

            self.window.addstr(i, 1, "MFU ghost size:")
            self.window.addstr(i, shift, utils.convert_size(int(stats["mfu_ghost_size"])))
            i += 1

            self.window.addstr(i, 1, "MRU ghost size:")
            self.window.addstr(i, shift, utils.convert_size(int(stats["mru_ghost_size"])))
            i += 1

            self.window.addstr(i, 1, "Metadata size:")
            self.window.addstr(i, shift, utils.convert_size(int(stats["metadata_size"])))
            i += 1

            self.window.addstr(i, 1, "Dnode size:")
            self.window.addstr(i, shift, utils.convert_size(int(stats["dnode_size"])))
            i += 1

            self.window.addstr(i, 1, "Dbuf size:")
            self.window.addstr(i, shift, utils.convert_size(int(stats["dbuf_size"])))
            i += 1

            self.window.addstr(i, 1, "Bonus size:")
            self.window.addstr(i, shift, utils.convert_size(int(stats["bonus_size"])))
            i += 1

            self.window.addstr(i, 1, "Header size:")
            self.window.addstr(i, shift, utils.convert_size(int(stats["hdr_size"])))
            i += 1

            self.window.addstr(i, 1, "Total RAM:")
            self.window.addstr(i, shift, utils.convert_size(int(stats["memory_all_bytes"])))
            i += 1

            self.window.addstr(i, 1, "Free RAM:")
            self.window.addstr(i, shift, utils.convert_size(int(stats["memory_free_bytes"])))
            i += 1

            self.window.addstr(i, 1, "Arc compressratio:")
            self.window.addstr(
                i,
                shift,
                str(round(int(stats["uncompressed_size"]) / int(stats["compressed_size"]), 2)),
            )
            i += 1

            self.window.addstr(i, 1, "Metadata cache:")
            self.window.addstr(
                i,
                shift,
                str(round(100 * int(stats["arc_meta_used"]) / int(stats["arc_meta_limit"]), 2))
                + "%",
            )
            i += 1

            self.window.addstr(i, 1, "Dnode cache:")
            self.window.addstr(
                i,
                shift,
                str(round(100 * int(stats["dnode_size"]) / int(stats["arc_dnode_limit"]), 2)) + "%",
            )
            i += 1
        except KeyError:
            return
