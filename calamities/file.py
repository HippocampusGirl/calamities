# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from os import path as op

from .config import config


def get_dir(text):
    if text is None:
        dir = os.curdir
    else:
        dir = op.dirname(text)
    if len(dir) == 0:
        dir = os.curdir
    return dir


def resolve(path):
    abspath = op.abspath(path)
    if abspath.startswith(config.fs_root):
        return abspath
    return op.normpath(config.fs_root + abspath)
