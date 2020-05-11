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
from .text import TextInputView, common_chars
from .choice import SingleChoiceInputView
from ..text import TextElement, TextElementCollection, Text
from ..file import resolve

tag_parse = re.compile(r"{(?P<tag_name>[a-z]+)(:(?P<filter>[^}]+))?}")

_tokenize0 = re.compile(r"(\A|[^\\])({)([a-z]+)(?:(:)(.+))?(})")
_tokenize1 = re.compile(r"(\A|[^\\])({[a-z]+(?::(?:[^{}]|\\{|\\})+)?})")
_magic_check = re.compile(r"(?:\*|\?|(?:\A|[^\\]){|[^\\]})")
_recursive_check = re.compile(r"\*\*")
_special_match = re.compile(r"(\\[AbBdDsDwWZ])")
_suggestion_match = re.compile(r"({suggestion})")
_chartype_filter = re.compile(r"(\[.+\])")
_show_tag_suggestion_check = re.compile(r".*(?P<newtag>{[^}]*)\Z")
_remove_tag_remainder_match = re.compile(r"(?P<oldtag>[^{]*})")

p = inflect.engine()


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
    tokens = _tokenize1.split(pat)
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
    tokens = _tokenize1.split(pat)
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
                    if _chartype_filter.fullmatch(filter) is not None:
                        enre = f"{filter}+"  # [allowed characters] syntax
                    else:  # glob syntax
                        enre = fnmatch.translate(filter)
                        enre = _special_match.sub("", enre)
                res += r"(?P<%s>%s)" % (tag_name, enre)
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


def has_magic(s):
    return _magic_check.search(s) is not None


def _isrecursive(pattern):
    return _recursive_check.fullmatch(pattern) is not None


def _ishidden(path):
    """
    adapted from cpython glob
    """
    return path[0] == "."


class FilePatternInputView(CallableView):
    def __init__(
        self,
        entities,
        required_entities=[],
        entity_colors_list=["ired", "igreen", "imagenta", "icyan", "iyellow"],
        dironly=False,
        base_path=None,
        **kwargs,
    ):
        super(FilePatternInputView, self).__init__(**kwargs)
        self.text_input_view = TextInputView(
            base_path, tokenizefun=self._tokenize, nchr_prepend=1, messagefun=self._messagefun,
        )
        self.text_input_view.update = self.update
        self.suggestion_view = SingleChoiceInputView([], isVertical=True, addBrackets=False)
        self.suggestion_view.update = self.update

        self.message = TextElement("")
        self.message_is_dirty = False

        self.matching_files = []
        self.cur_dir = None
        self.cur_dir_files = []
        self.dironly = dironly
        self.is_ok = False

        self.entities = entities
        self.required_entities = required_entities
        self.entity_colors_list = entity_colors_list
        self.color_by_tag = None
        self.tag_suggestions = None
        self.is_suggesting_entities = False

    @property
    def text(self):
        return self.text_input_view.text

    @text.setter
    def text(self, val):
        self.text_input_view.text = val

    def show_message(self, msg):
        if isinstance(msg, Text):
            self.message = msg
        else:
            self.message = self._tokenize(msg, addBrackets=False)
        self.message_is_dirty = True

    def _suggest_entities(self):
        self.is_suggesting_entities = True
        self.suggestion_view.set_options(self.tag_suggestions)

    def _suggest_matches(self):
        self.is_suggesting_entities = False
        self.suggestion_view.set_options(self.matching_files)

    def _tokenize(self, text, addBrackets=True):
        if addBrackets:
            text = f"[{text}]"
        tokens = _tokenize0.split(text)
        tokens = [token for token in tokens if token is not None]
        retval = []
        for i, token in enumerate(tokens):
            if token == "{":
                text_elem = TextElement(token)
                color = None
                if i + 1 < len(tokens):
                    tag = tokens[i + 1]
                    if tag in self.color_by_tag:
                        color = self.color_by_tag[tag]
                if color is None:
                    color = self.highlightColor
                text_elem.color = color
                retval.append(text_elem)
            elif token == "}" and len(retval) > 0:
                retval[-1].value += token
                retval.append(TextElement(""))
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
        self.color_by_tag = {
            ent: self.layout.color.from_string(color_str)
            for ent, color_str in zip(self.entities, self.entity_colors_list)
        }
        self.tag_suggestions = [
            TextElement(f"{{{ent}}}", color=self.color_by_tag[ent]) for ent in self.entities
        ]

    def _before_call(self):
        self.text_input_view._before_call()
        self.text_input_view.isActive = True
        self._scan_files()

    def _is_ok(self):
        return self.is_ok

    def _getOutput(self):
        if self.text is not None:
            return resolve(self.text)

    def _scan_files(self):
        if self.text is not None:
            text = str(self.text)
            cur_index = self.text_input_view.cur_index
            matchobj = _show_tag_suggestion_check.match(text[:cur_index])
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
        newpathname = resolve(newpathname)
        tagglobres = tag_glob(newpathname, self.entities + ["suggestion"], self.dironly)

        new_suggestions = set()
        suggestiontempl = op.basename(newpathname)
        filepaths = []
        tagdictlist = []
        try:
            for filepath, tagdict in tagglobres:
                if "suggestion" in tagdict and len(tagdict["suggestion"]) > 0:
                    suggestionstr = _suggestion_match.sub(tagdict["suggestion"], suggestiontempl)
                    if op.isdir(filepath):
                        suggestionstr = op.join(suggestionstr, "")
                    new_suggestions.add(suggestionstr)
                elif (self.dironly and op.isdir(filepath)) or (
                    not self.dironly and op.isfile(filepath)
                ):
                    filepaths.append(filepath)
                    tagdictlist.append(tagdict)
        except ValueError:
            pass
        except AssertionError:
            return
        tagsetdict = {}
        if len(tagdictlist) > 0:
            tagsetdict = {
                k: set(dic[k] for dic in tagdictlist) for k in tagdictlist[0] if k != "suggestion"
            }

        nfile = len(filepaths)

        has_all_required_entities = all(entity in tagsetdict for entity in self.required_entities)

        if not self.message_is_dirty:
            if has_all_required_entities:
                self.message.color = self.layout.color.iblue
                self.message.value = p.inflect(f"Found {nfile} plural('file', {nfile})")

                if len(tagsetdict) > 0:
                    self.message.value += " "
                    self.message.value += "for"
                    self.message.value += " "
                    tagmessages = [
                        p.inflect(f"{len(v)} plural('{k}', {len(v)})")
                        for k, v in tagsetdict.items()
                    ]
                    self.message.value += p.join(tagmessages)
            else:
                self.message.color = self.layout.color.iblue
                self.message.value = "Missing"
                self.message.value += " "
                self.message.value += p.join(
                    [
                        f"{{{entity}}}"
                        for entity in self.required_entities
                        if entity not in tagsetdict
                    ]
                )

        self.message_is_dirty = False

        if nfile > 0 and has_all_required_entities:
            self.is_ok = True
        else:
            self.is_ok = False

        self.matching_files = [self._tokenize(s, addBrackets=False) for s in new_suggestions]
        self._suggest_matches()

    def _handleKey(self, c):
        if c == Key.Break:
            self.text = None
            self.suggestion_view.set_options([])
            self.isActive = False
        elif self.suggestion_view.isActive and self.suggestion_view.cur_index is not None:
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
                    matchobj = _show_tag_suggestion_check.match(text[:cur_index])
                    if matchobj is not None:
                        start, end = matchobj.span("newtag")
                        newtext = text[:start]
                        newtext += selection
                        self.text_input_view.cur_index = len(newtext)
                        matchobj = _remove_tag_remainder_match.match(text[cur_index:])
                        if matchobj is not None:
                            cur_index += matchobj.end("oldtag")
                        newtext += text[cur_index:]
                        self.text = newtext
                else:
                    self.text = op.join(op.dirname(text), selection)
                    self.text_input_view.cur_index = len(self.text)
                self.message_is_dirty = False
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
            cur_text = self.text
            cur_index = self.text_input_view.cur_index
            if c == Key.Down and (self.is_suggesting_entities or len(self.matching_files) > 0):
                self.suggestion_view.isActive = True
                self.text_input_view.isActive = False
                self.suggestion_view._before_call()
                self.update()
            elif c == Key.Tab and len(self.matching_files) > 0:
                cc = common_chars(self.matching_files)
                self.text = op.join(op.dirname(str(self.text)), cc)
                self.text_input_view.cur_index = len(self.text)
            elif c == Key.Return:
                if self._is_ok():
                    self.suggestion_view.set_options([])
                    self.suggestion_view.isActive = False
                    self.text_input_view.isActive = False
                    self.isActive = False
            elif self.text_input_view.isActive:
                self.text_input_view._handleKey(c)

            if (
                self.text is not None and self.text != cur_text
            ) or cur_index != self.text_input_view.cur_index:
                # was changed
                self.message_is_dirty = False
                self._scan_files()
                self.update()

    def drawAt(self, y):
        if y is not None:
            size = 0
            size += self.text_input_view.drawAt(y + size)
            size += self.suggestion_view.drawAt(y + size)
            return size
