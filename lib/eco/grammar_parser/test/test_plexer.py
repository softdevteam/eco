# Copyright (c) 2012--2013 King's College London
# Created by the Software Development Team <http://soft-dev.org/>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

from grammar_parser.plexer import PriorityLexer

code = """
    "IF":KEYWORD
    "[a-zA-Z_]+":VAR
    "[0-9]+":INT
"""

import pytest

def test_plexer():
    pytest.skip("deprecated")
    plexer = PriorityLexer(code)
    assert plexer.get_priority("IF") == 0
    assert plexer.get_priority("[0-9]+") == 2

    assert plexer.get_cls("IF") == "KEYWORD"
    assert plexer.get_cls("[0-9]+") == "INT"

def test_match():
    pytest.skip("deprecated")
    plexer = PriorityLexer(code)
    assert plexer.matches("13", "INT")
    assert not plexer.matches("13a", "INT")

    assert plexer.matches("variable_", "VAR")
    assert not plexer.matches("not variable", "VAR")
