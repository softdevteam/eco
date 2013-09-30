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

from incparser.lrparser import LRParser
from incparser.constants import LR0, LR1, LALR

grammar = """
    S ::= "a" B "d"
    B ::= "b"
        | C
    C ::= "c"
"""

import pytest
pytest.skip("deprecated")

def test_input():
    lrp = LRParser(grammar)
    assert lrp.check("a b d") == True
    assert lrp.check("a c d") == True
    assert lrp.check("a a d") == False

def test_input2():
    lrp = LRParser(grammar, 1)
    assert lrp.check("a b d") == True
    assert lrp.check("a c d") == True
    assert lrp.check("a a d") == False

def test_calc1():
    grammar = """
        E ::= P
            | E "+" P
        P ::= "1" | "2"
    """
    lrp = LRParser(grammar, 0)
    assert lrp.check("1") == True
    assert lrp.check("1 + 2") == True
    print("NOW WITH LR(1)")
    lrp = LRParser(grammar, 1)
    assert lrp.check("1 + 2") == True

def test_calc2():
    grammar = """
        E ::= T
            | E "+" T
        T ::= P
            | T "*" P
        P ::= "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9"
    """
    lrp = LRParser(grammar, 0)
    assert lrp.check("1 + 2") == True
    assert lrp.check("1 + 2 * 3") == True
    assert lrp.check("1 * 2 * 3 + 4") == True

    lrp = LRParser(grammar, 1)
    assert lrp.check("1 + 2") == True
    assert lrp.check("1 + 2 * 3") == True
    assert lrp.check("1 * 2 * 3 + 4") == True

def test_epsilon():
    grammar = """
        S ::= "b" A "d"
        A ::= "c"
            |
    """
    lrp = LRParser(grammar, 1)
    assert lrp.check("b c d") == True
    assert lrp.check("b d") == True

def test_epsilon2():
    grammar = """
        S ::= A B "c"
        A ::= "a"
        B ::= "b"
            |
    """
    lrp = LRParser(grammar, LR0)
    assert lrp.check("a b c") == True
    assert lrp.check("a c") == True
    assert lrp.check("a b b") == False

    lrp = LRParser(grammar, LALR)
    assert lrp.check("a b c") == True
    assert lrp.check("a c") == True
    assert lrp.check("a b b") == False

def test_recursion():
    grammar = """
        S ::= "b" S
            |
    """

    lrp = LRParser(grammar, LR0)
    assert lrp.check("b b b b b b b b b b b") == True
    assert lrp.check("b b") == True
    assert lrp.check("b") == True
    assert lrp.check("") == False

    lrp = LRParser(grammar, LALR)
    assert lrp.check("b b b b b b b b b b b") == True
    assert lrp.check("b b") == True
    assert lrp.check("b") == True
    assert lrp.check("") == False

def test_recursion2():
    grammar = """
        S ::= "b" A
        A ::= S
            |
    """
    lrp = LRParser(grammar, LR0)
    assert lrp.check("b b b b b b b b b b b") == True
    assert lrp.check("b b") == True
    assert lrp.check("b") == True
    assert lrp.check("") == False

    lrp = LRParser(grammar, LALR)
    assert lrp.check("b b b b b b b b b b b") == True
    assert lrp.check("b b") == True
    assert lrp.check("b") == True
    assert lrp.check("") == False

def notest_small_language():
    grammar = """
        program ::= ws class program

        ws ::= ws ws_char
                     |
        ws_char ::= "\n" | "\t" | "\r"

        id ::= id_char id
             |

        id_char ::= "a"|"b"|"c"|"d"|"e"|"f"|"g"|"h"|"i"|"j"|"k"|"l"|"m"|"n"|"o"|"p"|"q"|"r"|"s"|"t"|"u"|"v"|"w"|"x"|"y"|"z"
                  |

        class ::= "class" ws id ws "{" functions "}"
        functions ::= ws function ws functions
                    |
        function ::= "function" ws id ws "{" func_body "}"
        func_body ::= ws
    """

    lrp = LRParser(grammar, LR0)
    assert lrp.check("""class test { function hello { } }""") == True

    lrp = LRParser(grammar, LALR)
    assert lrp.check("""
        class test {
            function hello {
            }
        }
    """) == True

