# Copyright (c) 2013--2014 King's College London
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

from inclexer.inclexer import IncrementalLexer, StringWrapper
from incparser.astree import AST
from grammars.grammars import calc
from incparser.astree import TextNode, BOS, EOS, MultiTextNode
from grammar_parser.gparser import Terminal, Nonterminal, MagicTerminal

import pytest
from cflexer.lexer import LexingError

class Test_IncrementalLexer:

    def setup_class(cls):
        cls.x = 15

    def lex(self, text):
        return self.lexer.lex(text)

    def relex(self, node):
        self.lexer.relex(node)

def mk_multitextnode(l):
    mt = MultiTextNode()
    mt.set_children([TextNode(x) for x in l])
    return mt

class Test_CalcLexer(Test_IncrementalLexer):

    def setup_class(cls):
        _, cls.lexer = calc.load()

    def test_lex(self):
        tokens = self.lex("1 + 2 * 3")
        expected = []
        expected.append(("1", "INT"))
        expected.append((" ", "<ws>"))
        expected.append(("+", "plus"))
        expected.append((" ", "<ws>"))
        expected.append(("2", "INT"))
        expected.append((" ", "<ws>"))
        expected.append(("*", "mul"))
        expected.append((" ", "<ws>"))
        expected.append(("3", "INT"))
        assert tokens == expected

    def test_lex2(self):
        tokens = self.lex("+2")
        expected = []
        expected.append(("+", "plus"))
        expected.append(("2", "INT"))
        assert tokens == expected

    def test_lex_no_valid_token(self):
        pytest.raises(LexingError, self.lex, "abc") # shouldn't loop forever

    def test_token_iter(self):
        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        new = TextNode(Terminal("1+2*3"))
        bos.insert_after(new)

        from inclexer.inclexer import StringWrapper
        sw = StringWrapper(new, new)
        next_token = self.lexer.lexer.get_token_iter(sw)
        assert next_token() == ("1", "INT", 1, [TextNode(Terminal("1+2*3"))])
        assert next_token() == ("+", "plus", 0, [TextNode(Terminal("1+2*3"))])
        assert next_token() == ("2", "INT", 1, [TextNode(Terminal("1+2*3"))])
        assert next_token() == ("*", "mul", 1, [TextNode(Terminal("1+2*3"))])
        assert next_token() == ("3", "INT", 1, [TextNode(Terminal("1+2*3"))])

    def test_token_iter2(self):
        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        new = TextNode(Terminal("12"))
        new2 = TextNode(Terminal("34"))
        bos.insert_after(new)
        new.insert_after(new2)

        from inclexer.inclexer import StringWrapper
        sw = StringWrapper(new, new)
        next_token = self.lexer.lexer.get_token_iter(sw)
        assert next_token() == ("1234", "INT", 1, [TextNode(Terminal("12")), TextNode(Terminal("34"))])

    def test_token_iter_lbox(self):
        lexer = IncrementalLexer("""
"[0-9]+":INT
"\x80":LBOX
        """)
        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        new = TextNode(Terminal("12"))
        new2 = TextNode(MagicTerminal("<SQL>"))
        new3 = TextNode(Terminal("34"))
        bos.insert_after(new)
        new.insert_after(new2)
        new2.insert_after(new3)

        from inclexer.inclexer import StringWrapper
        sw = StringWrapper(new, new)
        next_token = lexer.lexer.get_token_iter(sw) 
        assert next_token() == ("12", "INT", 1, [TextNode(Terminal("12"))])
        assert next_token() == ("\x80", "LBOX", 0, [TextNode(MagicTerminal("<SQL>"))])
        assert next_token() == ("34", "INT", 1, [TextNode(Terminal("34"))])

    def test_relex(self):
        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        new = TextNode(Terminal("1 + 2 * 3"))
        bos.insert_after(new)
        self.relex(new)
        assert ast.parent.symbol == Nonterminal("Root")
        assert isinstance(ast.parent.children[0], BOS)
        assert isinstance(ast.parent.children[-1], EOS)
        node = bos.next_term; assert node.symbol == Terminal("1"); assert node.lookahead == 1
        node = node.next_term; assert node.symbol == Terminal(" "); assert node.lookahead == 1
        node = node.next_term; assert node.symbol == Terminal("+"); assert node.lookahead == 0
        node = node.next_term; assert node.symbol == Terminal(" ")
        node = node.next_term; assert node.symbol == Terminal("2")
        node = node.next_term; assert node.symbol == Terminal(" ")
        node = node.next_term; assert node.symbol == Terminal("*")
        node = node.next_term; assert node.symbol == Terminal(" ")
        node = node.next_term; assert node.symbol == Terminal("3")
        node = node.next_term; assert isinstance(node, EOS)

    def test_relex4(self):
        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        new1 = TextNode(Terminal("1"))
        new2 = TextNode(Terminal("2"))
        new3 = TextNode(Terminal("+"))
        new4 = TextNode(Terminal("3+4"))
        new5 = TextNode(Terminal("+4"))
        new6 = TextNode(Terminal("5"))
        bos.insert_after(new1)
        new1.insert_after(new2)
        new2.insert_after(new3)
        new3.insert_after(new4)
        new4.insert_after(new5)
        new5.insert_after(new6)
        self.relex(new1)
        assert ast.parent.symbol == Nonterminal("Root")
        assert isinstance(ast.parent.children[0], BOS)
        assert isinstance(ast.parent.children[-1], EOS)
        node = bos.next_term; assert node.symbol == Terminal("12")
        node = node.next_term; assert node.symbol == Terminal("+")
        node = node.next_term; assert node.symbol == Terminal("3")
        node = node.next_term; assert node.symbol == Terminal("+")
        node = node.next_term; assert node.symbol == Terminal("4")
        node = node.next_term; assert node.symbol == Terminal("+")
        node = node.next_term; assert node.symbol == Terminal("45")
        node = node.next_term; assert isinstance(node, EOS)

    def test_relex_stop(self):
        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        new = TextNode(Terminal("1+2"))
        old1 = TextNode(Terminal("*"))
        old2 = TextNode(Terminal("3"))
        old2.lookup = "INT"
        bos.insert_after(new)
        new.insert_after(old1)
        old1.insert_after(old2)
        self.relex(new)
        assert ast.parent.symbol == Nonterminal("Root")
        assert isinstance(ast.parent.children[0], BOS)
        assert isinstance(ast.parent.children[-1], EOS)
        node = bos.next_term; assert node.symbol == Terminal("1")
        node = node.next_term; assert node.symbol == Terminal("+")
        node = node.next_term; assert node.symbol == Terminal("2")
        node = node.next_term; assert node.symbol == Terminal("*")
        node = node.next_term; assert node.symbol == Terminal("3")
        node = node.next_term; assert isinstance(node, EOS)

    def test_relex_update_insert(self):
        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        new1 = TextNode(Terminal("1"))
        new2 = TextNode(Terminal("2"))
        new3 = TextNode(Terminal("+3"))
        bos.insert_after(new1)
        new1.insert_after(new2)
        new2.insert_after(new3)
        self.relex(new1)
        
        twelve = bos.next_term
        assert twelve.symbol == Terminal("12")
        assert twelve is new1
        assert new2.deleted is True

        plus = twelve.next_term
        assert plus.symbol == Terminal("+")
        assert plus is new3

        assert plus.next_term.symbol == Terminal("3")


    def test_relex2(self):
        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        new = TextNode(Terminal("1"))
        bos.insert_after(new)
        self.relex(new)
        node = bos.next_term; assert node.symbol == Terminal("1")

        new.symbol.name = "1+"
        self.relex(new)
        node = bos.next_term; assert node.symbol == Terminal("1")
        node = node.next_term; assert node.symbol == Terminal("+")

        node.symbol.name = "+2"
        self.relex(node)
        node = bos.next_term; assert node.symbol == Terminal("1")
        node = node.next_term; assert node.symbol == Terminal("+")
        node = node.next_term; assert node.symbol == Terminal("2")

    def test_relex3(self):
        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        new1 = TextNode(Terminal("1+2"))
        new2 = TextNode(Terminal("345"))
        new3 = TextNode(Terminal("6+"))
        new4 = TextNode(Terminal("789")) # this should never be touched
        new4.lookup = "INT"
        new5 = TextNode(Terminal("+")) # this should never be touched
        new5.lookup = "plus"
        bos.insert_after(new1)
        new1.insert_after(new2)
        new2.insert_after(new3)
        new3.insert_after(new4)
        new4.insert_after(new5)
        self.relex(new1)
        assert ast.parent.symbol == Nonterminal("Root")
        assert isinstance(ast.parent.children[0], BOS)
        assert isinstance(ast.parent.children[-1], EOS)
        node = bos.next_term; assert node.symbol == Terminal("1")
        node = node.next_term; assert node.symbol == Terminal("+")
        node = node.next_term; assert node.symbol == Terminal("23456")
        node = node.next_term; assert node.symbol == Terminal("+")
        # check that 789 hasn't been relexed
        assert node.next_term is new4
        assert node.next_term.symbol is new4.symbol

    def test_relex_newline(self):
        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        new1 = TextNode(Terminal("1+2\r3+4"))
        bos.insert_after(new1)
        self.relex(new1)
        assert ast.parent.symbol == Nonterminal("Root")
        assert isinstance(ast.parent.children[0], BOS)
        assert isinstance(ast.parent.children[-1], EOS)
        node = bos.next_term; assert node.symbol == Terminal("1")
        node = node.next_term; assert node.symbol == Terminal("+")
        node = node.next_term; assert node.symbol == Terminal("2")
        node = node.next_term; assert node.symbol == Terminal("\r")
        node = node.next_term; assert node.symbol == Terminal("3")
        node = node.next_term; assert node.symbol == Terminal("+")
        node = node.next_term; assert node.symbol == Terminal("4")

    def test_relex_return(self):
        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        text = TextNode(Terminal("123\r"))
        bos.insert_after(text)
        self.relex(text)

        last_return = eos.prev_term
        assert last_return.symbol.name == "\r"
        assert last_return.lookup == "<return>"

        new_number = TextNode(Terminal("3"))
        last_return.insert_after(new_number)
        self.relex(new_number)

        new = TextNode(Terminal("\r"))
        last_return.insert_after(new)
        self.relex(new)
        assert new.symbol == Terminal("\r")
        assert new.lookup == "<return>"

    def test_backwards_lexing(self):
        lexer = IncrementalLexer("""
"::=":doublecolon
"=":equal
":":singlecolon
        """)
        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        text = TextNode(Terminal(":"))
        bos.insert_after(text)
        lexer.relex(text)

        assert bos.next_term.symbol.name == ":"
        assert bos.next_term.lookup == "singlecolon"
        assert text.lookahead == 1

        text.symbol.name = "::"
        lexer.relex(text)

        assert text.lookahead == 2
        text2 = text.next_term
        assert text2.lookback == 1

        assert bos.next_term.symbol.name == ":"
        assert bos.next_term.next_term.symbol.name == ":"

        text2.symbol.name = ":="
        lexer.relex(text2)

        assert bos.next_term.symbol.name == "::="
        assert isinstance(bos.next_term.next_term, EOS)

    def test_lookahead(self):
        lexer = IncrementalLexer("""
"aaa":aaa
"a":a
"b":b
        """)
        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        text = TextNode(Terminal("baab"))
        bos.insert_after(text)
        lexer.relex(text)
        assert ast.parent.children[1].symbol.name == "b"
        assert ast.parent.children[2].symbol.name == "a"
        assert ast.parent.children[3].symbol.name == "a"
        assert ast.parent.children[4].symbol.name == "b"
        ast.parent.children[1].symbol = None
        ast.parent.children[3].symbol.name = "aa"
        lexer.relex(ast.parent.children[3])

        assert ast.parent.children[2].symbol.name == "aaa"
        assert ast.parent.children[3].symbol.name == "b"

    def test_stringwrapper(self):
        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        text1 = TextNode(Terminal("abc"))
        text2 = TextNode(Terminal("+"))
        text3 = TextNode(Terminal("1"))
        text4 = TextNode(Terminal("*"))
        text5 = TextNode(Terminal("3456"))
        bos.insert_after(text1)
        text1.insert_after(text2)
        text2.insert_after(text3)
        text3.insert_after(text4)
        text4.insert_after(text5)

        wrapper = StringWrapper(text1, text1)
        assert wrapper[0] == "a"
        assert wrapper[2] == "c"
        assert wrapper[3] == "+"
        assert wrapper[4] == "1"
        assert wrapper[5] == "*"
        assert wrapper[6] == "3"
        assert wrapper[9] == "6"

        s = "abc+1*3456"
        for i in range(len(s)):
            for j in range(len(s)):
                assert wrapper[i:j] == s[i:j]
                print(i,j,wrapper[i:j])

    def test_multitoken_normal_to_multi(self):
        lexer = IncrementalLexer("""
"\"[a-z\r\x80]*\"":str
        """)

        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        text = TextNode(Terminal("\"abc\rdef\""))
        bos.insert_after(text)
        lexer.relex(text)
        assert bos.next_term.lookup == "str"
        assert bos.next_term == mk_multitextnode([Terminal("\"abc"), Terminal("\r"), Terminal("def\"")])
        assert bos.next_term.children[0] is text
        assert bos.next_term.next_term is eos

    def test_normal_to_multi_and_normal(self):
        lexer = IncrementalLexer("""
"\"[a-z\r\x80]*\"":str
"[a-z]+":var
        """)

        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        text = TextNode(Terminal("\"abc\rdef\""))
        bos.insert_after(text)
        lexer.relex(text)
        assert bos.next_term.lookup == "str"
        assert bos.next_term == mk_multitextnode([Terminal("\"abc"), Terminal("\r"), Terminal("def\"")])

        bos.next_term.children[2].symbol.name = "de\"f"
        lexer.relex(bos.next_term)

        assert bos.next_term == mk_multitextnode([Terminal("\"abc"), Terminal("\r"), Terminal("de\"")])
        assert bos.next_term.next_term == TextNode(Terminal("f"))

    def test_normal_to_normal_and_multi(self):
        lexer = IncrementalLexer("""
"\"[a-z\r\x80]*\"":str
"[a-z]+":var
        """)

        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        text = TextNode(Terminal("\"abc\rdef\""))
        bos.insert_after(text)
        lexer.relex(text)
        assert bos.next_term.lookup == "str"
        assert bos.next_term == mk_multitextnode([Terminal("\"abc"), Terminal("\r"), Terminal("def\"")])

        bos.next_term.children[0].symbol.name = "ab\"c"
        lexer.relex(bos.next_term)

        assert bos.next_term == TextNode(Terminal("ab"))
        assert bos.next_term.next_term == mk_multitextnode([Terminal("\"c"), Terminal("\r"), Terminal("def\"")])

    def test_multitoken_multi_to_normal(self):
        lexer = IncrementalLexer("""
"\"[a-z\r\x80]*\"":str
        """)

        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        text = mk_multitextnode([Terminal("\"abc"), Terminal("def\"")])
        bos.insert_after(text)
        lexer.relex(text)
        assert bos.next_term.lookup == "str"
        assert bos.next_term.symbol.name == "\"abcdef\""
        assert bos.next_term.next_term is eos

    def test_multitoken_multi_to_multi(self):
        lexer = IncrementalLexer("""
"\"[a-z\r\x80]*\"":str
        """)

        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        text = mk_multitextnode([Terminal("\"abc"), Terminal("\r"), Terminal("a"), Terminal("def\"")])
        bos.insert_after(text)
        lexer.relex(text)
        assert bos.next_term.lookup == "str"
        assert bos.next_term == mk_multitextnode([Terminal("\"abc"), Terminal("\r"), Terminal("adef\"")])
        assert bos.next_term is text
        assert bos.next_term.next_term is eos

    def test_multi_to_multi_and_normal1(self):
        lexer = IncrementalLexer("""
"\"[a-z\r\x80]*\"":str
"[a-z]+":var
        """)

        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        text = mk_multitextnode([Terminal("\"abc"), Terminal("\r"), Terminal("de\"f")])
        bos.insert_after(text)
        lexer.relex(text)
        assert bos.next_term.lookup == "str"
        assert bos.next_term == mk_multitextnode([Terminal("\"abc"), Terminal("\r"), Terminal("de\"")])
        assert bos.next_term is text
        assert bos.next_term.next_term.symbol.name == "f"
        assert bos.next_term.next_term.next_term is eos

    def test_multi_to_multi_and_normal2(self):
        lexer = IncrementalLexer("""
"\"[a-z\r\x80]*\"":str
"[a-z]+":var
        """)

        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        text = mk_multitextnode([Terminal("ab\"c"), Terminal("\r"), Terminal("def\"")])
        bos.insert_after(text)
        lexer.relex(text)
        assert bos.next_term.symbol.name == "ab"
        assert bos.next_term.next_term.lookup == "str"
        assert bos.next_term.next_term == mk_multitextnode([Terminal("\"c"), Terminal("\r"), Terminal("def\"")])
        assert bos.next_term.next_term is text
        assert bos.next_term.next_term.next_term is eos

    def test_normal_and_multi_to_normal_and_multi(self):
        lexer = IncrementalLexer("""
"\"[a-z\r\x80]*\"":str
"[a-z]+":var
        """)

        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        n1 = TextNode(Terminal("ab"))
        n2 = mk_multitextnode([Terminal("cd\"e"), Terminal("\r"), Terminal("fg\"")])
        bos.insert_after(n1)
        n1.insert_after(n2)
        lexer.relex(n1)
        assert bos.next_term.symbol.name == "abcd"
        assert bos.next_term is n1
        assert bos.next_term.next_term.lookup == "str"
        assert bos.next_term.next_term == mk_multitextnode([Terminal("\"e"), Terminal("\r"), Terminal("fg\"")])
        assert bos.next_term.next_term is n2
        assert bos.next_term.next_term.next_term is eos

    def test_normal_and_multi_to_multi(self):
        lexer = IncrementalLexer("""
"\"[a-z\r\x80]*\"":str
"[a-z]+":var
        """)

        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        n1 = TextNode(Terminal("\"abc"))
        n2 = mk_multitextnode([Terminal("def"), Terminal("\r"), Terminal("gh\"")])
        bos.insert_after(n1)
        n1.insert_after(n2)
        lexer.relex(n1)
        assert bos.next_term == mk_multitextnode([Terminal("\"abcdef"), Terminal("\r"), Terminal("gh\"")])
        assert bos.next_term.next_term is eos

    def test_normal_and_multi_to_multi2(self):
        lexer = IncrementalLexer("""
"\"[a-z\r\x80]*\"":str
"[a-z]+":var
        """)

        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        n1 = TextNode(Terminal("\"abc"))
        n2 = TextNode(Terminal("\r"))
        n3 = mk_multitextnode([Terminal("def"), Terminal("\r"), Terminal("gh\"")])
        bos.insert_after(n1)
        n1.insert_after(n2)
        n2.insert_after(n3)
        lexer.relex(n1)
        assert bos.next_term == mk_multitextnode([Terminal("\"abc"), Terminal("\r"), Terminal("def"), Terminal("\r"), Terminal("gh\"")])
        assert bos.next_term.next_term is eos

    def test_normal_and_multi_to_multi3(self):
        lexer = IncrementalLexer("""
"\"[a-z\r\x80]*\"":str
"[a-z]+":var
        """)

        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        n1 = TextNode(Terminal("\"abc\r"))
        n2 = mk_multitextnode([Terminal("def"), Terminal("\r"), Terminal("gh\"")])
        bos.insert_after(n1)
        n1.insert_after(n2)
        lexer.relex(n1)
        assert bos.next_term == mk_multitextnode([Terminal("\"abc"), Terminal("\r"), Terminal("def"), Terminal("\r"), Terminal("gh\"")])
        assert bos.next_term.next_term is eos

    def test_normal_and_multi_to_multi4(self):
        lexer = IncrementalLexer("""
"\"[a-z\r\x80]*\"":str
"[a-z]+":var
        """)

        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        n1 = mk_multitextnode([Terminal("\"abc"), Terminal("\r"), Terminal("def")])
        n2 = TextNode(Terminal("gh\""))
        bos.insert_after(n1)
        n1.insert_after(n2)
        lexer.relex(n1)
        assert bos.next_term == mk_multitextnode([Terminal("\"abc"), Terminal("\r"), Terminal("defgh\"")])
        assert bos.next_term.next_term is eos

    def test_multix2_to_multi(self):
        lexer = IncrementalLexer("""
"\"[a-z\r\x80]*\"":str
"[a-z]+":var
        """)

        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        n1 = mk_multitextnode([Terminal("\"ab"), Terminal("\r"), Terminal("cd")])
        n2 = mk_multitextnode([Terminal("ef"), Terminal("\r"), Terminal("gh\"")])
        bos.insert_after(n1)
        n1.insert_after(n2)
        lexer.relex(n1)
        assert bos.next_term == mk_multitextnode([Terminal("\"ab"), Terminal("\r"), Terminal("cdef"), Terminal("\r"), Terminal("gh\"")])
        assert bos.next_term.next_term is eos

    def test_multi_to_multix2(self):
        lexer = IncrementalLexer("""
"\"[a-zA-Z\r\x80]*\"":str
"[a-z]+":var
        """)

        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        n1 = mk_multitextnode([Terminal("\"ab"), Terminal("\r"), Terminal("cd\"\"ef"), Terminal("\r"), Terminal("gXh\"")])
        bos.insert_after(n1)
        lexer.relex(n1)
        assert bos.next_term == mk_multitextnode([Terminal("\"ab"), Terminal("\r"), Terminal("cd\"")])
        assert bos.next_term.next_term == mk_multitextnode([Terminal("\"ef"), Terminal("\r"), Terminal("gXh\"")])
        assert bos.next_term.next_term.next_term is eos

    def test_multi_to_multi_normal_multi(self):
        lexer = IncrementalLexer("""
"\"[a-z\r\x80]*\"":str
"[a-z]+":var
        """)

        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        n1 = mk_multitextnode([Terminal("\"ab"), Terminal("\r"), Terminal("cd\"xy\"ef"), Terminal("\r"), Terminal("gaaaah\"")])
        bos.insert_after(n1)
        lexer.relex(n1)
        assert bos.next_term == mk_multitextnode([Terminal("\"ab"), Terminal("\r"), Terminal("cd\"")])
        assert bos.next_term.next_term.symbol == Terminal("xy")
        assert bos.next_term.next_term.next_term == mk_multitextnode([Terminal("\"ef"), Terminal("\r"), Terminal("gaaaah\"")])
        assert bos.next_term.next_term.next_term.next_term is eos

    def test_multitoken_reuse1(self):
        lexer = IncrementalLexer("""
"\"[a-z\r\x80]*\"":str
        """)

        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        text = TextNode(Terminal("\"abc\rdef\""))
        bos.insert_after(text)
        lexer.relex(text)
        assert bos.next_term.lookup == "str"
        assert bos.next_term == mk_multitextnode([Terminal("\"abc"), Terminal("\r"), Terminal("def\"")])
        assert bos.next_term.children[0] is text

        bos.next_term.children[2].symbol.name = "de\rf\"" # insert another newline
        child0 = bos.next_term.children[0]
        child1 = bos.next_term.children[1]
        child2 = bos.next_term.children[2]

        mt = bos.next_term

        lexer.relex(bos.next_term)
        assert bos.next_term == mk_multitextnode([Terminal("\"abc"), Terminal("\r"), Terminal("de"), Terminal("\r"), Terminal("f\"")])
        # test if nodes within a MultiTextNode are reused
        assert bos.next_term.children[0] is child0
        assert bos.next_term.children[1] is child1
        assert bos.next_term.children[2] is child2

        child3 = bos.next_term.children[3]
        child4 = bos.next_term.children[4]

        assert child0.prev_term is None
        assert child0.next_term is child1
        assert child1.prev_term is child0
        assert child1.next_term is child2
        assert child2.prev_term is child1
        assert child2.next_term is child3
        assert child3.prev_term is child2
        assert child3.next_term is child4
        assert child4.prev_term is child3
        assert child4.next_term is None

        assert bos.next_term is mt # reused the MultiTextNode

    def test_multitoken_reuse2(self):
        lexer = IncrementalLexer("""
"\"[a-z\r\x80]*\"":str
        """)

        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        text = TextNode(Terminal("\"abc\rdef\""))
        bos.insert_after(text)
        lexer.relex(text)
        assert bos.next_term.lookup == "str"
        assert bos.next_term == mk_multitextnode([Terminal("\"abc"), Terminal("\r"), Terminal("def\"")])

        bos.next_term.children[0].symbol.name = "\"ab\rc" # insert another newline
        child_abc = bos.next_term.children[0]
        child_r1 = bos.next_term.children[1]
        child_def = bos.next_term.children[2]

        lexer.relex(bos.next_term)
        assert bos.next_term == mk_multitextnode([Terminal("\"ab"), Terminal("\r"), Terminal("c"), Terminal("\r"), Terminal("def\"")])
        assert bos.next_term.children[0] is child_abc
        assert bos.next_term.children[3] is child_r1
        assert bos.next_term.children[4] is child_def

        child_r2 = bos.next_term.children[1]
        child_c = bos.next_term.children[2]

        assert child_abc.prev_term is None
        assert child_abc.next_term is child_r2
        assert child_r2.prev_term is child_abc
        assert child_r2.next_term is child_c
        assert child_c.prev_term is child_r2
        assert child_c.next_term is child_r1
        assert child_r1.prev_term is child_c
        assert child_r1.next_term is child_def
        assert child_def.prev_term is child_r1
        assert child_def.next_term is None

    def test_multitoken_relex_merge(self):
        lexer = IncrementalLexer("""
"\"[a-z\r\x80]*\"":str
        """)

        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        text = TextNode(Terminal("\"abc\rde\rf\""))
        bos.insert_after(text)
        lexer.relex(text)
        assert bos.next_term.lookup == "str"
        assert bos.next_term == mk_multitextnode([Terminal("\"abc"), Terminal("\r"), Terminal("de"), Terminal("\r"), Terminal("f\"")])

        bos.next_term.children.pop(3) # remove a newline
        child0 = bos.next_term.children[0]
        child1 = bos.next_term.children[1]
        child2 = bos.next_term.children[2]

        lexer.relex(bos.next_term)
        assert bos.next_term == mk_multitextnode([Terminal("\"abc"), Terminal("\r"), Terminal("def\"")])
        assert bos.next_term.children[0] is child0
        assert bos.next_term.children[1] is child1
        assert bos.next_term.children[2] is child2

    def test_multitoken_real_lbox(self):
        lexer = IncrementalLexer("""
"\"[a-z\r\x80]*\"":str
        """)

        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        text1 = TextNode(Terminal("\"abc"))
        lbox  = TextNode(MagicTerminal("<SQL>"))
        text2 = TextNode(Terminal("def\""))
        bos.insert_after(text1)
        text1.insert_after(lbox)
        lbox.insert_after(text2)
        lexer.relex(text1)
        assert bos.next_term.lookup == "str"
        assert bos.next_term == mk_multitextnode([Terminal("\"abc"), MagicTerminal("<SQL>"), Terminal("def\"")])

    def test_multitoken_real_lbox_multiple(self):
        lexer = IncrementalLexer("""
"\"[a-z\r\x80]*\"":str
        """)

        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        n1 = TextNode(Terminal("\"abc"))
        n2  = TextNode(MagicTerminal("<SQL>"))
        n3 = TextNode(Terminal("def"))
        n4  = TextNode(MagicTerminal("<Calc>"))
        n5 = TextNode(Terminal("ghi\""))
        bos.insert_after(n1)
        n1.insert_after(n2)
        n2.insert_after(n3)
        n3.insert_after(n4)
        n4.insert_after(n5)
        lexer.relex(n1)
        assert bos.next_term.lookup == "str"
        assert bos.next_term == mk_multitextnode([Terminal("\"abc"), MagicTerminal("<SQL>"), Terminal("def"), MagicTerminal("<Calc>"), Terminal("ghi\"")])

    def test_multitoken_real_lbox_cut_off_string(self):
        lexer = IncrementalLexer("""
"\"[a-z\r\x80]*\"":str
"[a-z]+":var
        """)

        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        text1 = TextNode(Terminal("\"abc"))
        lbox  = TextNode(MagicTerminal("<SQL>"))
        text2 = TextNode(Terminal("d\"ef\""))
        bos.insert_after(text1)
        text1.insert_after(lbox)
        lbox.insert_after(text2)
        pytest.raises(LexingError, lexer.relex, text1)
        text2.symbol.name = "d\"ef"
        lexer.relex(text1)
        assert bos.next_term.lookup == "str"
        assert bos.next_term == mk_multitextnode([Terminal("\"abc"), MagicTerminal("<SQL>"), Terminal("d\"")])
        assert bos.next_term.next_term.symbol.name == "ef"

    def test_multitoken_real_lbox_relex(self):
        lexer = IncrementalLexer("""
"\"[a-z\r\x80]*\"":str
        """)

        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        text1 = TextNode(Terminal("\"abc"))
        lbox  = TextNode(MagicTerminal("<SQL>"))
        text2 = TextNode(Terminal("def\""))
        bos.insert_after(text1)
        text1.insert_after(lbox)
        lbox.insert_after(text2)
        lexer.relex(text1)
        assert bos.next_term.lookup == "str"
        assert bos.next_term == mk_multitextnode([Terminal("\"abc"), MagicTerminal("<SQL>"), Terminal("def\"")])

        bos.next_term.children[0].symbol.name = "\"ab\rc"
        lexer.relex(bos.next_term)

        assert bos.next_term == mk_multitextnode([Terminal("\"ab"), Terminal("\r"), Terminal("c"), MagicTerminal("<SQL>"), Terminal("def\"")])

    def test_multitoken_real_lbox_relex_cut_off_string(self):
        lexer = IncrementalLexer("""
"\"[a-z\r\x80]*\"":str
"[a-z]+":var
        """)

        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        text1 = TextNode(Terminal("\"abc"))
        lbox  = TextNode(MagicTerminal("<SQL>"))
        text2 = TextNode(Terminal("def\""))
        bos.insert_after(text1)
        text1.insert_after(lbox)
        lbox.insert_after(text2)
        lexer.relex(text1)
        assert bos.next_term.lookup == "str"
        assert bos.next_term == mk_multitextnode([Terminal("\"abc"), MagicTerminal("<SQL>"), Terminal("def\"")])
        assert bos.next_term.lookahead == 0

        bos.next_term.children[2].symbol.name = "d\"ef\""
        pytest.raises(LexingError, lexer.relex, bos.next_term)

        bos.next_term.children[2].symbol.name = "d\"ef"
        lexer.relex(bos.next_term)

        assert bos.next_term == mk_multitextnode([Terminal("\"abc"), MagicTerminal("<SQL>"), Terminal("d\"")])
        assert bos.next_term.next_term.symbol.name == "ef"

    def test_bug_two_newlines_delete_one(self):
        lexer = IncrementalLexer("""
"\"[a-z\r\x80]*\"":str
"[0-1]+":INT
"\+":plus
        """)

        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        text1 = TextNode(Terminal("1+\"abc\""))
        bos.insert_after(text1)
        lexer.relex(text1)
        assert bos.next_term == TextNode(Terminal("1"))
        assert bos.next_term.next_term == TextNode(Terminal("+"))
        assert bos.next_term.next_term.next_term == TextNode(Terminal("\"abc\""))

        s = bos.next_term.next_term.next_term
        s.symbol.name = "\"a\rb\rc\""

        lexer.relex(s)
        assert bos.next_term.next_term.next_term == mk_multitextnode([Terminal("\"a"), Terminal("\r"), Terminal("b"), Terminal("\r"), Terminal("c\"")])

        bos.next_term.next_term.next_term.children[3].symbol.name = ""
        assert bos.next_term.next_term.next_term == mk_multitextnode([Terminal("\"a"), Terminal("\r"), Terminal("b"), Terminal(""), Terminal("c\"")])

        lexer.relex(bos.next_term.next_term.next_term)
        assert bos.next_term.next_term.next_term == mk_multitextnode([Terminal("\"a"), Terminal("\r"), Terminal("bc\"")])

    def test_lexer_returns_nodes(self):
        lexer = IncrementalLexer("""
"\"[a-z\r\x80]*\"":str
        """)

        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        text1 = TextNode(Terminal("\"abc"))
        lbox  = TextNode(MagicTerminal("<SQL>"))
        text2 = TextNode(Terminal("def\""))
        bos.insert_after(text1)
        text1.insert_after(lbox)
        lbox.insert_after(text2)
        lexer.relex(text1)
        assert bos.next_term.lookup == "str"
        assert bos.next_term == mk_multitextnode([Terminal("\"abc"), MagicTerminal("<SQL>"), Terminal("def\"")])
        assert bos.next_term.lookahead == 0

    def test_multitoken_relex_to_normal(self):
        lexer = IncrementalLexer("""
"\"[a-z\r\x80]*\"":str
"[0-9]+":INT
"\x80":LBOX
        """)

        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        text1 = mk_multitextnode([Terminal("123"), MagicTerminal("<SQL>")])
        bos.insert_after(text1)
        lexer.relex(text1)
        assert bos.next_term.lookup == "INT"
        assert bos.next_term.symbol == Terminal("123")
        assert bos.next_term.lookahead == 1
        assert bos.next_term.next_term.symbol == MagicTerminal("<SQL>")
        assert bos.next_term.next_term.lookup == "LBOX"
        assert bos.next_term.lookahead == 1

    def test_relex_altered_string(self):
        lexer = IncrementalLexer("""
"\"[a-z\r\x80]*\"":str
"[0-9]+":INT
"\+":PLUS
"\x80":LBOX
        """)

        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        text1 = TextNode(Terminal("123+\"\""))
        bos.insert_after(text1)
        lexer.relex(text1)
        assert bos.next_term.symbol == Terminal("123")
        assert bos.next_term.lookup == "INT"
        assert bos.next_term.lookahead == 1
        assert bos.next_term.next_term.symbol == Terminal("+")
        assert bos.next_term.next_term.lookup == "PLUS"
        assert bos.next_term.next_term.lookahead == 0
        assert bos.next_term.next_term.next_term.symbol == Terminal("\"\"")
        assert bos.next_term.next_term.next_term.lookup == "str"
        assert bos.next_term.next_term.next_term.lookahead == 0

        string = bos.next_term.next_term.next_term
        string.symbol.name = "\"abc\""
        lexer.relex(string)

    def test_relex_altered_string(self):
        lexer = IncrementalLexer("""
"#[a-z\r\x80]*":comment
"[0-9]+":INT
"\+":PLUS
"\x80":LBOX
        """)

        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        text1 = TextNode(Terminal("1+"))
        text2 = TextNode(Terminal("#abc"))
        text3 = TextNode(MagicTerminal("<SQL>"))
        bos.insert_after(text1)
        text1.insert_after(text2)
        text2.insert_after(text3)
        lexer.relex(text1)
        assert bos.next_term.symbol == Terminal("1")
        assert bos.next_term.next_term.symbol == Terminal("+")
        assert bos.next_term.next_term.next_term == mk_multitextnode([Terminal("#abc"), MagicTerminal("<SQL>")])

    def test_triplequotes1(self):
        lexer = IncrementalLexer("""
"\"\"\"[^\"]*\"\"\"":triplestring
"\"[^\"]*\"":string
"[a-z]+":var
        """)

        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        text1 = TextNode(Terminal("\"\"\""))
        text2 = TextNode(Terminal("abc"))
        text3 = TextNode(Terminal("\"\"\""))
        bos.insert_after(text1)
        text1.insert_after(text2)
        text2.insert_after(text3)
        lexer.relex(text1)
        assert bos.next_term.symbol == Terminal("\"\"\"abc\"\"\"")
        assert bos.next_term.lookup == "triplestring"

        bos.next_term.symbol.name = "\"\"\"ab\"\"\"c\"\"\""
        pytest.raises(LexingError, lexer.relex, bos.next_term)

        bos.next_term.symbol.name = "\"\"\"ab\"\"\"c\"\""
        lexer.relex(bos.next_term)
