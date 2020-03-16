# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""
import curses
import curses.ascii
import enum
import queue


class Key(enum.Enum):
    Break = "break"
    Return = "return"
    Up = "up"
    Down = "down"
    Left = "left"
    Right = "right"
    Backspace = "backspace"
    Delete = "delete"


class Keyboard:
    def __init__(self):
        self.queue = queue.SimpleQueue()
        self.state = ""

    def __call__(self, c):
        if c == curses.ascii.ETX or c == curses.ascii.EOT:  # ctrl-c or ctrl-d
            self.queue.put_nowait(Key.Break)
        elif c == curses.ascii.NL or c == curses.ascii.CR:
            self.queue.put_nowait(Key.Return)
        elif c == curses.KEY_UP:
            self.queue.put_nowait(Key.Up)
        elif c == curses.KEY_DOWN:
            self.queue.put_nowait(Key.Down)
        elif c == curses.KEY_LEFT:
            self.queue.put_nowait(Key.Left)
        elif c == curses.KEY_RIGHT:
            self.queue.put_nowait(Key.Right)
        elif c == curses.ascii.DEL or c == curses.ascii.BS:
            self.queue.put_nowait(Key.Backspace)
        elif c == curses.KEY_DC:
            self.queue.put_nowait(Key.Delete)
        elif c == curses.ascii.ESC:
            self.state = "^["
        elif self.state == "^[" and c == ord("["):
            self.state = "^[["
        elif self.state == "^[[" and c == ord("3"):
            self.state = "^[[3"
        elif self.state == "^[[3" and c == ord("~"):
            self.state = ""
            self.queue.put_nowait(Key.Delete)
        elif curses.ascii.isprint(c):
            self.queue.put_nowait(c)