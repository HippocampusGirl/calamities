# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""
import os
from os import path as op
import re
import fnmatch

import inflect

from ..keyboard import Key
from ..view import CallableView
from .text import TextInputView
from .choice import SingleChoiceInputView
from ..text import (
    TextElement, TextElementCollection
)

_tokenize0 = re.compile(r"([^\\])({|})")
_tokenize1 = re.compile(r"(\A|[^\\])({[a-z]+})")
_entity_parse = re.compile(r"{(?P<entity_name>[a-z]+)(:(?P<filter>.+))?}")
_magic_check = re.compile(r"([*?{}])")
_recursive_check = re.compile(r"\*\*")
_special_match = re.compile(r"(\\[AbBdDsDwWZ])")
_suggestion_match = re.compile(r"({suggestion})")
_show_entity_suggestion_check = re.compile(r".*(?P<newentity>{[^}]*)\Z")

p = inflect.engine()


def entity_glob(pathname, entities, dironly=False):
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
    if dirname != pathname and _has_magic(dirname):
        dirs = entity_glob(dirname, entities, dironly=True)
    else:
        dirs = [(dirname, {})]
    for dirname, direntitydict in dirs:
        for name, entitydict in \
                _entity_glob_in_dir(dirname, basename, entities, dironly):
            yield (
                op.join(dirname, name),
                _combine_entitydict(direntitydict, entitydict))


def _combine_entitydict(a, b):
    z = b.copy()
    for k, v in a.items():
        if k in z:
            assert v == z[k]
        else:
            z[k] = v
    return z


def _entity_glob_in_dir(dirname, basename, entities, dironly):
    """
    adapted from cpython glob
    only basename can contain magic
    """
    assert not _has_magic(dirname)
    match = _translate(basename, entities)
    for x in _iterdir(dirname, dironly):
        matchobj = match(x)
        if matchobj is not None:
            yield x, matchobj.groupdict()


def _translate(pat, entities):
    res = ""
    tokens = _tokenize1.split(pat)
    for token in tokens:
        if len(token) == 0:
            continue
        matchobj = _entity_parse.fullmatch(token)
        if matchobj is not None:
            entity_name = matchobj.group("entity_name")
            if entity_name in entities:
                enre = r".*"
                filter = matchobj.group("filter")
                if filter is not None:
                    enre = fnmatch.translate(filter)
                    enre = _special_match.sub("", enre)
                res += r"(?P<%s>%s)" % (entity_name, enre)
            else:
                res += re.escape(token)
        else:
            fnre = fnmatch.translate(token)
            fnre = _special_match.sub("", fnre)
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


def _has_magic(s):
    return _magic_check.search(s) is not None


def _isrecursive(pattern):
    return _recursive_check.fullmatch(pattern) is not None


def _ishidden(path):
    """
    adapted from cpython glob
    """
    return path[0] == "."


class FilePatternInputView(CallableView):
    def __init__(self, entities,
                 entity_colors=["red", "green", "magenta", "cyan"],
                 dironly=False,
                 base_path=None, **kwargs):
        super(FilePatternInputView, self).__init__(**kwargs)
        self.text_input_view = TextInputView(
            base_path, tokenizefun=self._tokenize, nchr_prepend=1,
            messagefun=self._messagefun)
        self.text_input_view.update = self.update
        self.suggestion_view = SingleChoiceInputView(
            [], isVertical=True, addBrackets=False)
        self.suggestion_view.update = self.update

        self.message = TextElement("")

        self.matching_files = []
        self.cur_dir = None
        self.cur_dir_files = []
        self.dironly = dironly
        self.is_ok = False

        self.entities = entities
        self.entity_colors = entity_colors
        self.color_by_entity = None
        self.entity_suggestions = None
        self.is_suggesting_entities = False

    @property
    def text(self):
        return self.text_input_view.text

    @text.setter
    def text(self, val):
        self.text_input_view.text = val

    def _suggest_entities(self):
        self.is_suggesting_entities = True
        self.suggestion_view.set_options(self.entity_suggestions)

    def _suggest_matches(self):
        self.is_suggesting_entities = False
        self.suggestion_view.set_options(self.matching_files)

    def _tokenize(self, text, addBrackets=True):
        if addBrackets:
            text = f"[{text}]"
        tokens = _tokenize0.split(text)
        entity = None
        retval = []
        for token in tokens:
            if token == "{":
                retval.append(TextElement(token))
                entity = ""
            elif token == "}" and len(retval) > 0:
                retval[-1].value += token
                if entity in self.color_by_entity:
                    retval[-1].color = self.color_by_entity[entity]
                entity = None
                retval.append(TextElement(""))
            elif entity is not None and len(retval) > 0:
                retval[-1].value += token
                entity += token
            elif len(retval) > 0:
                retval[-1].value += token
            else:
                retval.append(TextElement(token))
        return TextElementCollection(retval)

    def _messagefun(self):
        return self.message

    def setup(self):
        super(FilePatternInputView, self).setup()
        self.text_input_view.layout = self.layout
        self.text_input_view.setup()
        self.suggestion_view.layout = self.layout
        self.suggestion_view.setup()
        self.color_by_entity = {
            ent: self.layout.color.from_string(color_str)
            for ent, color_str in zip(self.entities, self.entity_colors)
        }
        self.entity_suggestions = [
            TextElement(f"{{{ent}}}", color=self.color_by_entity[ent])
            for ent in self.entities
        ]

    def _before_call(self):
        self.text_input_view._before_call()
        self.text_input_view.isActive = True
        self._scan_files()

    def _isOk(self):
        return self.is_ok

    def _getOutput(self):
        return self.text

    def _scan_files(self):
        if self.text is not None:
            text = str(self.text)
            cur_index = self.text_input_view.cur_index
            matchobj = _show_entity_suggestion_check.match(text[:cur_index])
            if matchobj is not None:
                self._suggest_entities()
                return

        if self.text is None or len(self.text) == 0:
            pathname = op.join(os.curdir, "")
        else:
            pathname = str(self.text)
            if not op.isabs(pathname):
                pathname = op.join(os.curdir, pathname)

        newpathname = pathname + "{suggestion}"
        entityglobres = entity_glob(
            newpathname, self.entities + ["suggestion"], self.dironly)

        new_suggestions = set()
        suggestiontempl = op.basename(newpathname)
        filepaths = []
        entitydictlist = []
        try:
            for filepath, entitydict in entityglobres:
                if "suggestion" in entitydict and \
                        len(entitydict["suggestion"]) > 0:
                    suggestionstr = _suggestion_match.sub(
                        entitydict["suggestion"], suggestiontempl)
                    if op.isdir(filepath):
                        suggestionstr = op.join(suggestionstr, "")
                    new_suggestions.add(suggestionstr)
                elif (self.dironly and op.isdir(filepath)) or \
                        (not self.dironly and op.isfile(filepath)):
                    filepaths.append(filepath)
                    entitydictlist.append(entitydict)
        except ValueError:
            pass
        except AssertionError:
            return
        entitysetdict = {}
        if len(entitydictlist) > 0:
            entitysetdict = {
                k: set(dic[k] for dic in entitydictlist)
                for k in entitydictlist[0] if k != "suggestion"}

        nfile = len(filepaths)

        self.message.color = self.layout.color.iblue
        self.message.value = p.inflect(
            f"Found {nfile} plural('file', {nfile})")

        if len(entitysetdict) > 0:
            self.is_ok = True
            self.message.value += " "
            self.message.value += "for"
            self.message.value += " "
            entitymessages = [
                p.inflect(f"{len(v)} plural('{k}', {len(v)})")
                for k, v in entitysetdict.items()
            ]
            self.message.value += p.join(entitymessages)
        else:
            self.is_ok = False

        self.matching_files = [
            self._tokenize(s, addBrackets=False)
            for s in new_suggestions]
        self._suggest_matches()

    def _handleKey(self, c):
        if c == Key.Break:
            self.text = None
            self.suggestion_view.set_options([])
            self.isActive = False
        elif self.suggestion_view.isActive and \
                self.suggestion_view.cur_index is not None:
            if c == Key.Up and self.suggestion_view.cur_index == 0:
                self.suggestion_view.offset = 0
                self.suggestion_view.cur_index = None
                self.suggestion_view.isActive = False
                self.text_input_view.isActive = True
                self.text_input_view._before_call()
                self.update()
            elif c == Key.Return or c == Key.Right:
                text = str(self.text)
                selection = str(self.suggestion_view._getOutput())
                if self.is_suggesting_entities:
                    cur_index = self.text_input_view.cur_index
                    matchobj = _show_entity_suggestion_check.match(
                        text[:cur_index])
                    if matchobj is not None:
                        start, end = matchobj.span("newentity")
                        self.text = text[:start] + \
                            selection + \
                            text[cur_index:]
                        self.text_input_view.cur_index = start + len(selection)
                else:
                    self.text = op.join(
                        op.dirname(text),
                        selection)
                    self.text_input_view.cur_index = len(self.text)
                self._scan_files()
                self.suggestion_view.cur_index = None
                self.suggestion_view.isActive = False
                self.text_input_view.isActive = True
                self.text_input_view._before_call()
                self.update()
            elif c == Key.Left:
                self.text = op.dirname(str(self.text))
                self._scan_files()
                self.update()
            else:
                self.suggestion_view._handleKey(c)
        else:
            if c == Key.Down and (
                    self.is_suggesting_entities or
                    len(self.matching_files) > 0):
                self.suggestion_view.isActive = True
                self.text_input_view.isActive = False
                self.suggestion_view._before_call()
                self.update()
            elif c == Key.Return:
                if self._isOk():
                    self.suggestion_view.set_options([])
                    self.suggestion_view.isActive = False
                    self.text_input_view.isActive = False
                    self.isActive = False
            elif self.text_input_view.isActive:
                cur_text = self.text
                cur_index = self.text_input_view.cur_index
                self.text_input_view._handleKey(c)
                if (self.text is not None and self.text != cur_text) or \
                        cur_index != self.text_input_view.cur_index:
                    # was changed
                    self._scan_files()
                    self.update()

    def drawAt(self, y):
        size = 0
        size += self.text_input_view.drawAt(y+size)
        size += self.suggestion_view.drawAt(y+size)
        return size