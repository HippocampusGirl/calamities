# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from os import path as op

import re
import fnmatch

from .re import (
    tag_parse,
    tokenize,
    magic_check,
    recursive_check,
    special_match,
    chartype_filter,
)


def tag_glob(pathname, entities=None, dironly=False):
    """
    adapted from cpython glob
    """
    dirname, basename = op.split(pathname)
    if not dirname:
        if _isrecursive(basename):
            yield from _rlistdir(dirname, dironly)
        else:
            yield from _iterdir(dirname, dironly)
        return
    if dirname != pathname and has_magic(dirname):
        dirs = tag_glob(dirname, entities, dironly=True)
    else:
        dirs = [(dirname, {})]
    for dirname, dirtagdict in dirs:
        for name, tagdict in _tag_glob_in_dir(dirname, basename, entities, dironly):
            yield (op.join(dirname, name), _combine_tagdict(dirtagdict, tagdict))


def _combine_tagdict(a, b):
    z = b.copy()
    for k, v in a.items():
        if k in z:
            assert v == z[k]
        else:
            z[k] = v
    return z


def _tag_glob_in_dir(dirname, basename, entities, dironly):
    """
    adapted from cpython glob
    only basename can contain magic
    """
    assert not has_magic(dirname)
    match = _translate(basename, entities)
    for x in _iterdir(dirname, dironly):
        matchobj = match(x)
        if matchobj is not None:
            yield x, matchobj.groupdict()


def get_entities_in_path(pat):
    res = []
    tokens = tokenize.split(pat)
    for token in tokens:
        if len(token) == 0:
            continue
        matchobj = tag_parse.fullmatch(token)
        if matchobj is not None:
            tag_name = matchobj.group("tag_name")
            res.append(tag_name)
    return res


def _translate(pat, entities):
    res = ""
    tokens = tokenize.split(pat)
    for token in tokens:
        if len(token) == 0:
            continue
        matchobj = tag_parse.fullmatch(token)
        if matchobj is not None:
            tag_name = matchobj.group("tag_name")
            if entities is None or tag_name in entities:
                enre = r".*"
                filter = matchobj.group("filter")
                if filter is not None:
                    if chartype_filter.fullmatch(filter) is not None:
                        enre = f"{filter}+"  # [allowed characters] syntax
                    else:  # glob syntax
                        enre = fnmatch.translate(filter)
                        enre = special_match.sub("", enre)
                res += r"(?P<%s>%s)" % (tag_name, enre)
            else:
                res += re.escape(token)
        else:
            fnre = fnmatch.translate(token)
            fnre = special_match.sub("", fnre)
            res += fnre
    return re.compile(res).fullmatch


def _iterdir(dirname, dironly):
    """
    adapted from cpython glob
    """
    if not dirname:
        dirname = os.curdir
    try:
        with os.scandir(dirname) as it:
            for entry in it:
                try:
                    if not dironly or entry.is_dir():
                        if not _ishidden(entry.name):
                            yield entry.name
                except OSError:
                    pass
    except OSError:
        return


def _rlistdir(dirname, dironly):
    """
    adapted from cpython glob
    """
    yield dirname
    for x in _iterdir(dirname, dironly):
        path = op.join(dirname, x) if dirname else x
        for y in _rlistdir(path, dironly):
            yield op.join(x, y)


def has_magic(s):
    return magic_check.search(s) is not None


def _isrecursive(pattern):
    return recursive_check.fullmatch(pattern) is not None


def _ishidden(path):
    """
    adapted from cpython glob
    """
    return path[0] == "."
