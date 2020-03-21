# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""
from ..view import CallableView
from ..keyboard import Key
from ..text import Text, TextElement, TextElementCollection


class SingleChoiceInputView(CallableView):
    def __init__(
        self,
        options,
        label=None,
        cur_index=None,
        isVertical=False,
        addBrackets=True,
        showSelectionAfterExit=True,
        renderfun=None,
        colorfun=None,
        **kwargs,
    ):
        super(SingleChoiceInputView, self).__init__(**kwargs)
        self.isVertical = isVertical
        self.addBrackets = addBrackets
        self.showSelectionAfterExit = showSelectionAfterExit

        self.cur_index = cur_index

        self.label = label
        self.options = None
        self.set_options(options)

        self.maxStrLength = 0
        self.clearBeforeDrawSize = 0
        self.offset = 0
        self.renderfun = renderfun
        self.colorfun = colorfun

    def set_options(self, newoptions):
        self.offset = 0
        for i in range(len(newoptions)):
            if not isinstance(newoptions[i], Text):
                newoptions[i] = TextElement(newoptions[i])
        if self.options is not None:
            self.clearBeforeDrawSize = len(self.options)
        self.options = newoptions
        if self.cur_index is not None and self.cur_index > len(newoptions):
            self.cur_index = 0

    def _is_ok(self):
        return True

    def _before_call(self):
        if self.cur_index is None:
            self.cur_index = 0
        arrows = "← →"
        if self.isVertical:
            arrows = "↑ ↓"
        self._setStatusBar(
            "  ".join(["[↵] Ok", f"[{arrows}] Change selection", "[ctrl-c] Cancel"])
        )

    def _handleKey(self, c):
        if c == Key.Break:
            self.cur_index = None
            self.update()
            self.isActive = False
        elif c == Key.Return:
            if self._is_ok():
                self.isActive = False
        elif (self.isVertical and c == Key.Up) or (
            not self.isVertical and c == Key.Left
        ):
            self.cur_index = max(0, self.cur_index - 1)
            self.update()
        elif (self.isVertical and c == Key.Down) or (
            not self.isVertical and c == Key.Right
        ):
            self.cur_index = min(len(self.options) - 1, self.cur_index + 1)
            self.update()
        elif isinstance(c, Key):
            pass
        else:
            pass

    def _getViewWidth(self):
        return self.maxStrLength

    def _getOutput(self):
        if self.cur_index is not None:
            return str(self.options[self.cur_index])

    def _drawAt_horizontal(self, y):
        y = self.layout.offset(self)
        x = 0
        if self.label is not None:
            self.layout.window.addstr(y, x, self.label, self.color)
            x += self.columnWidth
            x += 1
        for i, option in enumerate(self.options):
            color = self.color
            if i == self.cur_index:
                if self.isActive:
                    color = self.emphasisColor
                elif self.showSelectionAfterExit:
                    color = self.highlightColor
            if self.addBrackets:
                self.layout.window.addstr(y, x, "[", color)
                x += 1
            nchr = option.drawAt(y, x, self.layout, color, renderfun=self.renderfun)
            x += nchr
            if self.addBrackets:
                self.layout.window.addstr(y, x, "]", color)
                x += 1
            x += 1
        return 1

    def _draw_text(self, y, text, color):
        nchr = text.drawAt(y, 0, self.layout, color)
        nothing = " " * (self.maxStrLength - nchr)
        self.layout.window.addstr(y, nchr, nothing, self.layout.color.default)
        return nchr

    def _draw_option(self, i, y):
        option = self.options[i]
        color = self.color
        overridecolor = False
        if self.cur_index is not None:
            if i == self.cur_index and self.isActive:
                color = self.emphasisColor
                overridecolor = True
            elif i == self.cur_index and self.showSelectionAfterExit:
                color = self.highlightColor
            elif self.colorfun is not None:
                color = self.colorfun(option)
        x = 0
        if self.addBrackets:
            self.layout.window.addstr(y, x, "[", color)
            x += 1
        nchr = option.drawAt(
            y,
            x,
            self.layout,
            color,
            overridecolor=overridecolor,
            renderfun=self.renderfun,
        )
        x += nchr
        if self.addBrackets:
            self.layout.window.addstr(y, x, "]", color)
            x += 1
        nothing = " " * (self.maxStrLength - nchr)
        self.layout.window.addstr(y, nchr, nothing, self.layout.color.default)
        return nchr

    def _drawAt_vertical(self, y):
        my, mx = self.layout.getLayoutSize()
        maxSize = my // 2

        size = 0

        if self.clearBeforeDrawSize > 0:
            if self.clearBeforeDrawSize > maxSize:
                self.clearBeforeDrawSize = maxSize
            nothing = " " * self._getViewWidth()
            for i in range(self.clearBeforeDrawSize):
                self.layout.window.addstr(y + i, 0, nothing, self.layout.color.default)
            self.clearBeforeDrawSize = 0

        def _calc_layout():
            correctedMaxSize = maxSize
            haveMoreAtFront = False
            if self.offset > 0:
                haveMoreAtFront = True
                correctedMaxSize -= 1
            haveMoreAtEnd = False
            if len(self.options) - self.offset > maxSize:
                haveMoreAtEnd = True
                correctedMaxSize -= 1
            return haveMoreAtFront, haveMoreAtEnd, correctedMaxSize

        haveMoreAtFront, haveMoreAtEnd, correctedMaxSize = _calc_layout()
        if self.cur_index is not None:
            prev_offset = -1
            while prev_offset != self.offset:
                prev_offset = self.offset
                if self.cur_index < self.offset:
                    self.offset = self.cur_index
                elif self.cur_index >= self.offset + correctedMaxSize:
                    self.offset = self.cur_index - correctedMaxSize + 1
                if self.offset == 1:
                    self.offset = 2
                (haveMoreAtFront, haveMoreAtEnd, correctedMaxSize) = _calc_layout()

        if haveMoreAtFront:
            entry = TextElement(f"-- {self.offset} more --", self.layout.color.default)
            nchr = self._draw_text(y + size, entry, self.color)
            if nchr > self.maxStrLength:
                self.maxStrLength = nchr
            size += 1

        upper = self.offset + correctedMaxSize
        if upper > len(self.options):
            upper = len(self.options)
        for i in range(self.offset, upper):
            nchr = self._draw_option(i, y + size)
            if nchr > self.maxStrLength:
                self.maxStrLength = nchr
            size += 1

        if haveMoreAtEnd:
            n = len(self.options) - (self.offset + correctedMaxSize)
            entry = TextElement(f"-- {n} more --", self.layout.color.default)
            nchr = self._draw_text(y + size, entry, self.color)
            if nchr > self.maxStrLength:
                self.maxStrLength = nchr
            size += 1

        return size

    def drawAt(self, y):
        if self.isVertical:
            return self._drawAt_vertical(y)
        else:
            return self._drawAt_horizontal(y)


class MultipleChoiceInputView(SingleChoiceInputView):
    def __init__(self, options, checked=[], isVertical=False, **kwargs):
        super(MultipleChoiceInputView, self).__init__(
            options,
            isVertical=isVertical,
            addBrackets=False,
            showSelectionAfterExit=False,
            renderfun=self._render_option,
            colorfun=self._color_option,
            **kwargs,
        )
        self.checked = {str(k): (str(k) in checked) for k in self.options}

    def _before_call(self):
        if self.cur_index is None:
            self.cur_index = 0
        arrows = "← →"
        if self.isVertical:
            arrows = "↑ ↓"
        self._setStatusBar(
            "  ".join(
                [
                    "[↵] Ok",
                    "[space] Toggle checked/unchecked",
                    f"[{arrows}] Change selection",
                    "[ctrl-c] Cancel",
                ]
            )
        )

    def _handleKey(self, c):
        if c == ord(" "):
            if self.cur_index is not None:
                optionStr = str(self.options[self.cur_index])
                self.checked[optionStr] = not self.checked[optionStr]
                self.update()
        else:
            super(MultipleChoiceInputView, self)._handleKey(c)

    def _getOutput(self):
        return self.checked

    def _render_option(self, optionStr):
        status = " "
        if self.checked[optionStr]:
            status = "*"
        return f"[{status}] {optionStr}"

    def _color_option(self, option):
        if self.checked[str(option)]:
            return self.highlightColor
        return self.color


class MultiSingleChoiceInputView(SingleChoiceInputView):
    def __init__(self, options, values, addBrackets=True, **kwargs):
        super(MultiSingleChoiceInputView, self).__init__(
            options,
            isVertical=True,
            addBrackets=False,
            showSelectionAfterExit=False,
            **kwargs,
        )
        self.selectedIndices = None
        self.optionWidth = max(len(option) for option in options)

        for i in range(len(values)):
            if not isinstance(values[i], Text):
                values[i] = TextElement(values[i])
        if addBrackets:
            for i in range(len(values)):
                if isinstance(values[i], TextElement):
                    values[i].value = f"[{values[i].value}]"
                elif isinstance(values[i], TextElementCollection):
                    values[i].textElements[
                        0
                    ].value = f"[{values[i].textElements[0].value}"
                    values[i].textElements[
                        -1
                    ].value = f"{values[i].textElements[-1].value}]"
                else:
                    raise NotImplementedError
        self.values = values

    def _before_call(self):
        super(MultiSingleChoiceInputView, self)._before_call()
        if self.selectedIndices is None:
            self.selectedIndices = [0] * len(self.values)
        actions = ["[↵] Ok", "[↑ ↓ ← →] Change selection", "[ctrl-c] Cancel"]
        self._setStatusBar("  ".join(actions))

    def _handleKey(self, c):
        if c == Key.Left:
            if self.cur_index is not None and self.selectedIndices is not None:
                self.selectedIndices[self.cur_index] = max(
                    0, self.selectedIndices[self.cur_index] - 1
                )
            self.update()
        elif c == Key.Right:
            if self.cur_index is not None and self.selectedIndices is not None:
                self.selectedIndices[self.cur_index] = min(
                    len(self.values) - 1, self.selectedIndices[self.cur_index] + 1
                )
            self.update()
        else:
            super(MultiSingleChoiceInputView, self)._handleKey(c)

    def _getOutput(self):
        if self.selectedIndices is not None:
            return {
                str(k): str(self.values[v])
                for k, v in zip(self.options, self.selectedIndices)
            }

    def _draw_option(self, i, y):
        option = self.options[i]
        x = 0
        color = self.color
        option.drawAt(y, 0, self.layout, color)
        x += self.optionWidth
        x += 1

        for j, value in enumerate(self.values):
            color = self.color
            if self.selectedIndices is not None:
                if j == self.selectedIndices[i]:
                    if (
                        self.cur_index is not None
                        and i == self.cur_index
                        and self.isActive
                    ):
                        color = self.emphasisColor
                    else:
                        color = self.highlightColor
            nchr = value.drawAt(y, x, self.layout, color)
            x += nchr
            x += 1

        return x


class MultiMultipleChoiceInputView(MultiSingleChoiceInputView):
    def __init__(self, options, values, checked=[], **kwargs):
        super(MultiSingleChoiceInputView, self).__init__(
            options,
            isVertical=True,
            addBrackets=False,
            showSelectionAfterExit=False,
            **kwargs,
        )
        self.optionWidth = max(len(option) for option in options)

        self.cur_col = None

        for i in range(len(values)):
            if not isinstance(values[i], Text):
                values[i] = TextElement(values[i])
        self.values = values
        self.checked = [
            {str(k): (str(k) in checked) for k in self.values} for _ in self.values
        ]

    def _before_call(self):
        super(MultiSingleChoiceInputView, self)._before_call()
        if self.cur_col is None:
            self.cur_col = 0
        actions = [
            "[↵] Ok",
            "[space] Toggle checked/unchecked",
            "[↑ ↓ ← →] Change selection",
            "[ctrl-c] Cancel",
        ]
        self._setStatusBar("  ".join(actions))

    def _handleKey(self, c):
        if c == Key.Left:
            if self.cur_col is not None:
                self.cur_col = max(0, self.cur_col - 1)
            self.update()
        elif c == Key.Right:
            if self.cur_col is not None:
                self.cur_col = min(len(self.values) - 1, self.cur_col + 1)
            self.update()
        elif c == ord(" "):
            if self.cur_index is not None and self.cur_col is not None:
                valueStr = str(self.values[self.cur_col])
                self.checked[self.cur_index][valueStr] = not self.checked[
                    self.cur_index
                ][valueStr]
                self.update()
        else:
            super(MultiSingleChoiceInputView, self)._handleKey(c)

    def _getOutput(self):
        return self.checked

    def _draw_option(self, i, y):
        option = self.options[i]
        x = 0
        color = self.color
        option.drawAt(y, 0, self.layout, color)
        x += self.optionWidth
        x += 1

        for j, value in enumerate(self.values):
            valueStr = str(value)
            checked = self.checked[i][valueStr]
            color = self.color
            if (
                self.cur_col is not None
                and j == self.cur_col
                and self.cur_index is not None
                and i == self.cur_index
                and self.isActive
            ):
                color = self.emphasisColor
            elif checked:
                color = self.highlightColor
            box = "[ ] "
            if checked:
                box = "[*] "
            self.layout.window.addstr(y, x, box, color)
            x += len(box)
            nchr = value.drawAt(y, x, self.layout, color)
            x += nchr
            x += 1

        return x
