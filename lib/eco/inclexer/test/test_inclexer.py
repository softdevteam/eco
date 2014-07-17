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
from grammars.grammars import calc1
from incparser.astree import TextNode, BOS, EOS
from grammar_parser.gparser import Terminal, Nonterminal

class Test_IncrementalLexer:

    def setup_class(cls):
        cls.x = 15

    def lex(self, text):
        return self.lexer.lex(text)

    def relex(self, node):
        self.lexer.relex(node)

class Test_CalcLexer(Test_IncrementalLexer):

    def setup_class(cls):
        cls.lexer = IncrementalLexer(calc1.priorities)

    def test_lex(self):
        tokens = self.lex("1 + 2 * 3")
        expected = []
        expected.append(("1", "INT"))
        expected.append((" ", "<ws>"))
        expected.append(("+", "+"))
        expected.append((" ", "<ws>"))
        expected.append(("2", "INT"))
        expected.append((" ", "<ws>"))
        expected.append(("*", "*"))
        expected.append((" ", "<ws>"))
        expected.append(("3", "INT"))
        assert tokens == expected

    def test_lex2(self):
        tokens = self.lex("+2")
        expected = []
        expected.append(("+", "+"))
        expected.append(("2", "INT"))
        assert tokens == expected

    def test_lex_no_valid_token(self):
        tokens = self.lex("abc") # shouldn't loop forever

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
        node = bos.next_term; assert node.symbol == Terminal("1")
        node = node.next_term; assert node.symbol == Terminal(" ")
        node = node.next_term; assert node.symbol == Terminal("+")
        node = node.next_term; assert node.symbol == Terminal(" ")
        node = node.next_term; assert node.symbol == Terminal("2")
        node = node.next_term; assert node.symbol == Terminal(" ")
        node = node.next_term; assert node.symbol == Terminal("*")
        node = node.next_term; assert node.symbol == Terminal(" ")
        node = node.next_term; assert node.symbol == Terminal("3")
        node = node.next_term; assert isinstance(node, EOS)

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
        new5 = TextNode(Terminal("+")) # this should never be touched
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

        text2 = TextNode(Terminal(":"))
        text.insert_after(text2)
        lexer.relex(text2)
        assert text2.lookahead == 1

        assert bos.next_term.symbol.name == ":"
        assert bos.next_term.next_term.symbol.name == ":"

        text3 = TextNode(Terminal("="))
        text2.insert_after(text3)
        lexer.relex(text3)

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

        wrapper = StringWrapper(text1)
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


