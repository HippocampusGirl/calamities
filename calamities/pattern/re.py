# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import re


tag_parse = re.compile(r"{(?P<tag_name>[a-z]+)(:(?P<filter>[^}]+))?}")

tokenize = re.compile(r"(\A|[^\\])({[a-z]+(?::(?:[^{}]|\\{|\\})+)?})")

magic_check = re.compile(r"(?:\*|\?|(?:\A|[^\\]){|[^\\]})")

recursive_check = re.compile(r"\*\*")

special_match = re.compile(r"(\\[AbBdDsDwWZ])")

suggestion_match = re.compile(r"({suggestion})")

chartype_filter = re.compile(r"(\[.+\])")

show_tag_suggestion_check = re.compile(r".*(?P<newtag>{[^}]*)\Z")

remove_tag_remainder_match = re.compile(r"(?P<oldtag>[^{]*})")
