# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""


class Text:
    def __len__(self):
        raise NotImplementedError

    def __str__(self):
        raise NotImplementedError

    def __iter__(self):
        raise NotImplementedError

    def __lt__(self, other):
        return str(self) < str(other)

    def __eq__(self, other):
        return str(self) == str(other)

    def drawAt(self, y, x, layout, color=None):
        raise NotImplementedError


class TextElement(Text):
    def __init__(self, value, color=None):
        self.color = color
        self.value = value

    def __len__(self):
        return len(self.value)

    def __str__(self):
        return self.value

    def __iter__(self):
        for c in self.value:
            yield c, self.color

    def drawAt(self, y, x, layout, color=None, overridecolor=False, renderfun=None):
        if y is None or x is None or layout is None:
            return
        if self.color is not None and not overridecolor:
            color = self.color
        elif color is None:
            color = layout.color.default
        if isinstance(color, str):
            color = layout.color.from_string(color)
        value = self.value
        if renderfun is not None:
            value = renderfun(value)
        layout.window.addstr(y, x, value, color)
        return len(value)


class TextElementCollection(Text):
    def __init__(self, textElements=[]):
        self.textElements = textElements

    def __len__(self):
        return sum(len(el) for el in self.textElements)

    def __str__(self):
        ret = ""
        for el in self.textElements:
            ret += str(el)
        return ret

    def __iter__(self):
        for el in self.textElements:
            for tup in el:
                yield tup

    def drawAt(self, y, x, layout, color=None, overridecolor=False, renderfun=None):
        size = 0
        for el in self.textElements:
            el.drawAt(y, x + size, layout, color, overridecolor, renderfun)
            size += len(el)
        return size
