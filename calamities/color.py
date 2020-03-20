# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""
import curses


class Color:
    def __init__(self):
        curses.init_pair(1, -1, -1)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_WHITE)
        curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_WHITE)
        curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_WHITE)
        curses.init_pair(6, curses.COLOR_RED, curses.COLOR_WHITE)
        curses.init_pair(7, curses.COLOR_CYAN, curses.COLOR_WHITE)

        self.default = curses.color_pair(1)
        self.black = curses.color_pair(2)
        self.blue = curses.color_pair(3)
        self.green = curses.color_pair(4)
        self.magenta = curses.color_pair(5)
        self.red = curses.color_pair(6)

        self.white = curses.color_pair(2) | curses.A_REVERSE

        self.idefault = curses.color_pair(1) | curses.A_REVERSE

        self.iblue = curses.color_pair(3) | curses.A_REVERSE
        self.igreen = curses.color_pair(4) | curses.A_REVERSE
        self.imagenta = curses.color_pair(5) | curses.A_REVERSE
        self.ired = curses.color_pair(6) | curses.A_REVERSE
        self.icyan = curses.color_pair(7) | curses.A_REVERSE

        self.palette = [self.ired, self.igreen,
                        self.imagenta, self.icyan]

    def from_string(self, str):
        if str == "blue":
            return self.iblue
        elif str == "green":
            return self.igreen
        elif str == "magenta":
            return self.imagenta
        elif str == "red":
            return self.ired
        elif str == "cyan":
            return self.icyan
        else:
            return self.default
