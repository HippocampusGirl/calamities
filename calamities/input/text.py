# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

import numpy as np

from ..view import CallableView
from ..keyboard import Key
from ..text import TextElement
from .choice import SingleChoiceInputView


def _tokenize(text):
    return TextElement(f"[{text}]")


class TextInputView(CallableView):
    def __init__(
        self,
        text=None,
        isokfun=None,
        messagefun=None,
        tokenizefun=None,
        nchr_prepend=0,
        **kwargs,
    ):
        super(TextInputView, self).__init__(**kwargs)
        self.text = text
        self.previousLength = None
        self.cur_index = 0

        self.isokfun = isokfun
        if self.isokfun is None:
            self.isokfun = self._is_ok

        self.messagefun = messagefun

        self.tokenizefun = tokenizefun
        self.nchr_prepend = nchr_prepend
        if self.tokenizefun is None:
            self.tokenizefun = _tokenize
            self.nchr_prepend = 1

    def _before_call(self):
        if self.text is None:
            self.text = ""
        self._setStatusBar(
            "  ".join(["[↵] Ok", "[← →] Move cursor", "[ctrl-c] Cancel"])
        )

    def _is_ok(self):
        return True

    def _handleKey(self, c):
        if c == Key.Break:
            self.text = None
            self.isActive = False
        elif c == Key.Return:
            if self._is_ok():
                self.isActive = False
        elif c == Key.Left:
            self.cur_index = max(0, self.cur_index - 1)
            self.update()
        elif c == Key.Right:
            self.cur_index = min(len(self.text), self.cur_index + 1)
            self.update()
        elif c == Key.Backspace:
            if self.cur_index > 0:
                self.text = (
                    self.text[: self.cur_index - 1] + self.text[self.cur_index :]
                )
                self.cur_index -= 1
                self.update()
        elif c == Key.Delete:
            if self.cur_index < len(self.text):
                self.text = (
                    self.text[: self.cur_index] + self.text[self.cur_index + 1 :]
                )
                self.update()
        elif isinstance(c, Key):
            pass
        else:
            self.text = (
                self.text[: self.cur_index] + chr(c) + self.text[self.cur_index :]
            )
            self.cur_index += 1
            self.update()

    def _getOutput(self):
        return self.text

    def drawAt(self, y, x=0):
        curLength = None
        if self.text is not None:
            text = self.tokenizefun(self.text)
            curLength = len(text)
            for c, color in text:
                if color is None:
                    color = self.color
                if (
                    self.isActive
                    and self.cur_index is not None
                    and x == self.cur_index + self.nchr_prepend
                ):
                    color = self.emphasisColor
                self.layout.window.addch(y, x, c, color)
                x += 1

        if self.previousLength is not None:
            for i in range(x, self.previousLength + 1):
                self.layout.window.addch(y, i, " ", self.layout.color.default)

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
    def __init__(
        self, number=0, min=-np.inf, max=np.inf, **kwargs,
    ):
        super(NumberInputView, self).__init__(text=str(number), **kwargs)
        self.min = min
        self.max = max

    def _is_ok(self):
        try:
            number = float(self.text)
            return self.min <= number <= self.max
        except ValueError:
            return False

    def _handleKey(self, c):
        if isinstance(c, Key) or chr(c) in "0123456789.e":
            super(NumberInputView, self)._handleKey(c)

    def _getOutput(self):
        return float(self.text)


class MultiTextInputView(SingleChoiceInputView):
    text_input_type = TextInputView

    def __init__(self, options, textlist=None, **kwargs):
        super(MultiTextInputView, self).__init__(
            options,
            isVertical=True,
            addBrackets=False,
            showSelectionAfterExit=False,
            **kwargs,
        )
        self.selectedIndices = None
        self.optionWidth = max(len(option) for option in options)

        if textlist is None:
            textlist = [None] * len(options)
        kwargs = dict(nchr_prepend=self.optionWidth + 1 + 1, tokenizefun=_tokenize)
        self.children = [
            self.text_input_type(**kwargs)
            if text is None
            else self.text_input_type(text, **kwargs)
            for text in textlist
        ]

    def setup(self):
        super(MultiTextInputView, self).setup()
        for child in self.children:
            child.layout = self.layout
            child.setup()

    def _before_call(self):
        super(MultiTextInputView, self)._before_call()
        actions = [
            "[↵] Ok",
            "[← →] Move cursor",
            "[↑ ↓] Change selection",
            "[ctrl-c] Cancel",
        ]
        self._setStatusBar("  ".join(actions))
        for child in self.children:
            child._before_call()
        self.children[self.cur_index].isActive = True

    def _handleKey(self, c):
        if (
            c == Key.Left
            or c == Key.Right
            or c == Key.Backspace
            or c == Key.Delete
            or not isinstance(c, Key)
        ):
            if self.cur_index is not None:
                self.children[self.cur_index]._handleKey(c)
            self.update()
        else:
            prev_index = self.cur_index
            super(MultiTextInputView, self)._handleKey(c)
            if self.cur_index is not None and prev_index != self.cur_index:
                self.children[prev_index].isActive = False
                self.children[self.cur_index].isActive = True
            elif self.cur_index is None or not self.isActive:
                self.children[prev_index].isActive = False

    def _is_ok(self):
        return all(child._is_ok() for child in self.children)

    def _getOutput(self):
        return {
            str(option): str(child.text)
            for option, child in zip(self.options, self.children)
        }

    def _draw_option(self, i, y):
        option = self.options[i]
        x = 0
        color = self.color
        if self.cur_index is not None and i == self.cur_index and self.isActive:
            color = self.emphasisColor
        option.drawAt(y, x, self.layout, color)
        x += self.optionWidth
        x += 1

        self.children[i].drawAt(y, x)

        return x


class MultiNumberInputView(MultiTextInputView):
    text_input_type = NumberInputView
