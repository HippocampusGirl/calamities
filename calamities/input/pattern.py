# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""
import os
from os import path as op

import inflect

from ..keyboard import Key
from ..view import CallableView
from .text import TextInputView, common_chars
from .choice import SingleChoiceInputView
from ..text import TextElement, TextElementCollection, Text
from ..file import resolve
from ..pattern import (
    tag_glob,
    tag_parse,
    tokenize,
    suggestion_match,
    show_tag_suggestion_check,
    remove_tag_remainder_match,
)

p = inflect.engine()


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
            base_path,
            tokenizefun=self._tokenize,
            nchr_prepend=1,
            messagefun=self._messagefun,
            forbidden_chars="'\"'",
            maxlen=256,
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
        tokens = tokenize.split(text)
        tokens = [token for token in tokens if token is not None]
        retval = []
        for token in tokens:
            text_elem = TextElement(token)
            matchobj = tag_parse.fullmatch(token)
            if matchobj is not None:
                tag_name = matchobj.group("tag_name")
                color = self.highlightColor
                if tag_name in self.color_by_tag:
                    color = self.color_by_tag[tag_name]
                text_elem.color = color
            retval.append(text_elem)
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
            path = str(self.text).strip()
            return resolve(path)

    def _scan_files(self):
        if self.text is not None:
            text = str(self.text).strip()
            cur_index = self.text_input_view.cur_index
            matchobj = show_tag_suggestion_check.match(text[:cur_index])
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
                    suggestionstr = suggestion_match.sub(tagdict["suggestion"], suggestiontempl)
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
            if nfile == 0:
                self.message.value = ""
            elif has_all_required_entities:
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
                    matchobj = show_tag_suggestion_check.match(text[:cur_index])
                    if matchobj is not None:
                        start, end = matchobj.span("newtag")
                        newtext = text[:start]
                        newtext += selection
                        self.text_input_view.cur_index = len(newtext)
                        matchobj = remove_tag_remainder_match.match(text[cur_index:])
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
            else:
                if not self.text_input_view.isActive:
                    self.suggestion_view.isActive = False
                    self.text_input_view.isActive = True
                    self.text_input_view._before_call()
                    self.update()
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

            if self.text_input_view._viewWidth > self._viewWidth:
                self._viewWidth = self.text_input_view._viewWidth
            if self.suggestion_view._viewWidth > self._viewWidth:
                self._viewWidth = self.suggestion_view._viewWidth

            return size
