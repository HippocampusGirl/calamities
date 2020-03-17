# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

fs_root = "/"

import os
from os import path as op
import re


def get_dir(text):
    if self.text is None:
        dir = os.curdir
    else:
        dir = op.dirname(self.text)
    if len(dir) == 0:
        dir = os.curdir


def fake_to_real_path(path):
    if op.isabs(path):
        return op.join(fs_root, path)
    return path


def real_to_fake_path(path):
    if op.isabs(path):
        if path.startswith(fs_root):
            return path[len(fs_root):]
        else:
            raise ValueError
    return path
