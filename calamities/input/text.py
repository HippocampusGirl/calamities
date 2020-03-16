# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""
from ..view import CallableView
from ..keyboard import Key
from ..text import (
    TextElement
)


class TextInputView(CallableView):
    def __init__(self, text=None,
                 isokfun=None,
                 messagefun=None,
                 tokenizefun=None, nchr_prepend=0,
                 **kwargs):
        super(TextInputView, self).__init__(**kwargs)
        self.text = text
        self.previousLength = None
        self.cur_index = 0

        self.isokfun = isokfun
        if self.isokfun is None:
            self.isokfun = self._isOk

        self.messagefun = messagefun

        self.tokenizefun = tokenizefun
        self.nchr_prepend = nchr_prepend
        if self.tokenizefun is None:
            self.tokenizefun = self._tokenize
            self.nchr_prepend = 1

    def _before_call(self):
        if self.text is None:
            self.text = ""
        self._setStatusBar("  ".join([
            u"[↵] Ok",
            u"[← →] Move cursor",
            u"[ctrl-c] Cancel"
        ]))

    def _isOk(self):
        return True

    def _tokenize(self, text):
        return TextElement(f"[{text}]")

    def _handleKey(self, c):
        if c == Key.Break:
            self.text = None
            self.isActive = False
        elif c == Key.Return:
            if self._isOk():
                self.isActive = False
        elif c == Key.Left:
            self.cur_index = max(0, self.cur_index - 1)
            self.update()
        elif c == Key.Right:
            self.cur_index = \
                min(len(self.text), self.cur_index + 1)
            self.update()
        elif c == Key.Backspace:
            if self.cur_index > 0:
                self.text = (
                    self.text[:self.cur_index - 1] +
                    self.text[self.cur_index:]
                )
                self.cur_index -= 1
                self.update()
        elif c == Key.Delete:
            if self.cur_index < len(self.text):
                self.text = (
                    self.text[:self.cur_index] +
                    self.text[self.cur_index + 1:]
                )
                self.update()
        elif isinstance(c, Key):
            pass
        else:
            self.text = (
                self.text[:self.cur_index] +
                chr(c) +
                self.text[self.cur_index:]
            )
            self.cur_index += 1
            self.update()

    def _getOutput(self):
        return self.text

    def drawAt(self, y):
        x = 0
        curLength = None
        if self.text is not None:
            text = self.tokenizefun(self.text)
            curLength = len(text)
            for c, color in text:
                if color is None:
                    color = self.color
                if self.isActive and \
                        self.cur_index is not None and \
                        x == self.cur_index+self.nchr_prepend:
                    color = self.emphasisColor
                self.layout.window.addch(y, x, c, color)
                x += 1

        if self.previousLength is not None:
            for i in range(x, self.previousLength+1):
                self.layout.window.addch(
                    y, i, " ", self.layout.color.default)

        if self.messagefun is not None:
            message = self.messagefun()
            x += 1
            x += message.drawAt(y, x, self.layout)

        if curLength is not None:
            self.previousLength = x

        if x > self._viewWidth:
            self._viewWidth = x

        return 1


class NumberInputView(TextInputView):
    def _isOk(self):
        try:
            float(self.text)
            return True
        except ValueError:
            return False
