# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from typing import Dict, Generator, Tuple

import os
from os import path as op

import re
import fnmatch

from .re import (
    tag_parse,
    tokenize,
    magic_check,
    special_match,
)


def tag_glob(pathname, entities=None, dironly=False) -> Generator[Tuple[str, Dict], None, None]:
    """
    adapted from cpython glob
    """
    dirname, basename = op.split(pathname)
    if not dirname:
        # print(repr(dirname), repr(basename))
        if _isrecursive(basename):
            dir_generator = _rlistdir(dirname, dironly)
        else:
            dir_generator = _iterdir(dirname, dironly)
        for dirname in dir_generator:
            yield (dirname, dict())
        return
    if dirname != pathname and has_magic(dirname):
        dirs = tag_glob(dirname, entities, dironly=True)
    else:
        dirs = [(dirname, dict())]
    for dirname, dirtagdict in dirs:
        # print("40", repr(dirname), repr(dirtagdict))
        for name, tagdict in _tag_glob_in_dir(dirname, basename, entities, dironly, dirtagdict):
            yield (op.join(dirname, name), _combine_tagdict(dirtagdict, tagdict))


def _combine_tagdict(a, b) -> Dict:
    z = b.copy()
    for k, v in a.items():
        if k in z:
            assert v == z[k]
        else:
            z[k] = v
    return z


def _tag_glob_in_dir(dirname, basename, entities, dironly, parenttagdict):
    """
    adapted from cpython glob
    only basename can contain magic
    """
    # print("60", repr(dirname), repr(basename), repr(entities), repr(parenttagdict))
    assert not has_magic(dirname)
    match = _translate(basename, entities, parenttagdict)
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


def _validate_re(s):
    try:
        re.compile(s)
        return True
    except Exception:
        pass
    return False


def _translate(pat, entities, parenttagdict):
    res = ""

    tokens = tokenize.split(pat)

    entities_in_res = set()

    for token in tokens:
        if len(token) == 0:
            continue

        matchobj = tag_parse.fullmatch(token)
        if matchobj is not None:

            tag_name = matchobj.group("tag_name")
            if entities is None or tag_name in entities:
                filter_type = matchobj.group("filter_type")
                filter_str = matchobj.group("filter")

                if tag_name in parenttagdict:
                    s = parenttagdict[tag_name]
                    if s.endswith("/"):
                        s = s[:-1]
                    res += re.escape(s)
                    # TODO warning that filter is ignored
                    continue

                enre = None
                if filter_str is not None:
                    if filter_type == ":":
                        enre = filter_str.replace("\\{", "{").replace("\\}", "}")  # regex syntax
                    elif filter_type == "=":  # glob syntax
                        enre = fnmatch.translate(filter_str)
                        enre = special_match.sub("", enre)  # remove control codes

                if enre is None or not _validate_re(enre):
                    enre = r"[^/]+"

                if tag_name not in entities_in_res:
                    res += r"(?P<%s>%s)" % (tag_name, enre)
                    entities_in_res.add(tag_name)
                else:
                    res += r"(?P=%s)" % tag_name
            else:
                res += re.escape(token)

        else:
            fnre = fnmatch.translate(token)
            fnre = special_match.sub("", fnre)
            fnre = fnre.replace(".*", "[^/]*")
            res += fnre

    res += "/?"

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
                        entry_name = entry.name
                        if entry.is_dir():
                            entry_name = op.join(entry_name, "")
                        if not _ishidden(entry_name):
                            yield entry_name
                except OSError:
                    pass
    except OSError:
        return


def _rlistdir(dirname, dironly):
    """
    adapted from cpython glob
    """
    names = list(_iterdir(dirname, dironly))
    for x in names:
        path = op.join(dirname, x) if dirname else x
        yield path
        # print("176", repr(dirname), repr(path))
        yield from _rlistdir(path, dironly)


def has_magic(s):
    return magic_check.search(s) is not None


def _isrecursive(pattern):
    return pattern == "**"


def _ishidden(path):
    """
    adapted from cpython glob
    """
    return path[0] == "."
