# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import curses

curses.setupterm()  # noqa

from .app import App
from .keyboard import Key, Keyboard
from .view import View, TextView, GiantTextView, SpacerView
from .input import (
    TextInputView,
    NumberInputView,
    MultiTextInputView,
    MultiNumberInputView,
    SingleChoiceInputView,
    MultipleChoiceInputView,
    MultiSingleChoiceInputView,
    MultiMultipleChoiceInputView,
    FileInputView,
    DirectoryInputView,
    FilePatternInputView,
    tag_glob,
    has_magic,
    get_entities_in_path,
)
from .layout import Layout

__all__ = [
    App,
    Key,
    Keyboard,
    View,
    TextView,
    GiantTextView,
    SpacerView,
    TextInputView,
    NumberInputView,
    MultiTextInputView,
    MultiNumberInputView,
    SingleChoiceInputView,
    MultipleChoiceInputView,
    MultiSingleChoiceInputView,
    MultiMultipleChoiceInputView,
    FileInputView,
    DirectoryInputView,
    FilePatternInputView,
    tag_glob,
    has_magic,
    get_entities_in_path,
    Layout,
]
