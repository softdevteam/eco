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

from grammar_parser.bootstrap import BootstrapParser, AstNode, LookupExpr, ListExpr, AddExpr, ListNode, ReferenceExpr, Foreach
from grammar_parser.gparser import Nonterminal, Terminal, Epsilon

class Test_Parser(object):

    def test_simple(self):
        grammar = """
X ::= A "b"
    | C;

A ::= "a";
C ::= "c";

%%

a:"a"
b:"b"
c:"c"
"""
        bp = BootstrapParser()
        bp.parse(grammar)
        assert bp.start_symbol == Nonterminal("X")
        assert bp.rules[Nonterminal("X")].symbol == Nonterminal("X")
        assert bp.rules[Nonterminal("X")].alternatives == [[Nonterminal("A"), Terminal("b")], [Nonterminal("C")]]
        assert bp.rules[Nonterminal("A")].alternatives == [[Terminal("a")]]
        assert bp.rules[Nonterminal("C")].alternatives == [[Terminal("c")]]

    def test_empty_alternative(self):
        grammar = """
A ::= "a"
    | ;

%%

a:"a"
"""
        bp = BootstrapParser()
        bp.parse(grammar)
        assert bp.start_symbol == Nonterminal("A")
        assert bp.rules[Nonterminal("A")].alternatives == [[Terminal("a")], []]

class Test_Lexer(object):

    def test_simple(self):
        grammar = """
X ::= "x";

%%

a:"a"
b:"b"
c:"c"
"""
        bp = BootstrapParser()
        bp.parse(grammar)
        assert bp.lrules[0] == ("a", "a")
        assert bp.lrules[1] == ("b", "b")
        assert bp.lrules[2] == ("c", "c")

    def test_simple(self):
        grammar = """
X ::= "x";

%%

numbers:"[0-9]+"
text:"[a-z][a-z]*"
escaped:"abc\\\"escaped"
"""
        bp = BootstrapParser()
        bp.parse(grammar)
        assert bp.lrules[0] == ("numbers", "[0-9]+")
        assert bp.lrules[1] == ("text", "[a-z][a-z]*")
        assert bp.lrules[2] == ("escaped", "abc\\\"escaped")

class Test_Annotations(object):

    def test_annotations(self):
        grammar = """
X ::= "x" {Node(child=#0)};
Y ::= "y" {[#0,#3]};
Z ::= "z" {#1+#2};
A ::= "a" {Node2(child=#0, child2=[#1,#3], child3=#3+[#4])};

%%

x:"x"
"""
        bp = BootstrapParser()
        bp.parse(grammar)
        assert bp.rules[Nonterminal("X")].annotations == [AstNode("Node", {"child":LookupExpr(0)})]
        assert bp.rules[Nonterminal("Y")].annotations == [ListExpr([LookupExpr(0), LookupExpr(3)])]
        assert bp.rules[Nonterminal("Z")].annotations == [AddExpr(LookupExpr(1), LookupExpr(2))]
        assert bp.rules[Nonterminal("A")].annotations == [AstNode("Node2", {'child': LookupExpr(0), 'child2':ListExpr([LookupExpr(1), LookupExpr(3)]), 'child3':AddExpr(LookupExpr(3), ListExpr([LookupExpr(4)]))})]

    def test_alternatives(self):
        grammar = """
X ::= "x" {Node(child=#0)}
    | "y" "z" {#1};

%%

x:"x"
"""
        bp = BootstrapParser()
        bp.parse(grammar)
        assert bp.rules[Nonterminal("X")].annotations == [AstNode("Node", {"child":LookupExpr(0)}), LookupExpr(1)]

    def test_annotations_extension(self):
        grammar = """
X ::= "x" {foreach(#2) X(name=item.x)}
    ;

%%

x:"x"
"""
        bp = BootstrapParser()
        bp.parse(grammar)
        assert bp.rules[Nonterminal("X")].annotations == [Foreach("foreach", LookupExpr(2), AstNode("X", {"name": ReferenceExpr("item", "x")}))]

    def test_lookup_reference(self):
        grammar = """
X ::= "x" {X(name=#0.x)}
    ;

%%

x:"x"
"""
        bp = BootstrapParser()
        bp.parse(grammar)
        assert bp.rules[Nonterminal("X")].annotations == [AstNode("X", {"name": LookupExpr(0, "x")})]

import py
from treemanager import TreeManager
from incparser.incparser import IncParser
class Test_Bootstrapping(object):

    def test_error(self):
        bootstrap = BootstrapParser()
        test_grammar = """S ::= A {If(child1=#1, child2=[#3, #4]}; %% a:\"a\""""
        with py.test.raises(Exception):
            bootstrap.parse(test_grammar)

    def test_simple(self):
        bootstrap = BootstrapParser()
        test_grammar = """S ::= A {If(child1=#1, child2=[#3, #4])}; A ::= \"a\"; %% a:\"a\""""
        bootstrap.parse(test_grammar)

    def test_bootstrapping1(self):
        bootstrap = BootstrapParser(lr_type=1, whitespaces=False)
        test_grammar = 'S ::= "abc"; %% abc:\"abc\"'
        bootstrap.parse(test_grammar)
        self.treemanager = TreeManager()
        self.treemanager.add_parser(bootstrap.incparser, bootstrap.inclexer, "")
        self.treemanager.set_font_test(7, 17)
        self.treemanager.key_normal("a")
        assert bootstrap.incparser.last_status == False
        self.treemanager.key_normal("b")
        assert bootstrap.incparser.last_status == False
        self.treemanager.key_normal("c")
        assert bootstrap.incparser.last_status == True

    def test_calculator(self):
        calc = """
            E ::= T             {#0}
                | E "plus" T    {Plus(arg1=#0,arg2=#2)}
                ;
            T ::= P             {#0}
                | T "mul" P     {Mul(arg1=#0,arg2=#2)}
                ;
            P ::= "INT"         {#0}
                ;
        %%

            INT:"[0-9]+"
            plus:"\+"
            mul:"\*"
            <ws>:"[ \\t]+"
            <return>:"[\\n\\r]"
        """
        bootstrap = BootstrapParser(lr_type=1, whitespaces=False)
        bootstrap.parse(calc)
        self.treemanager = TreeManager()
        self.treemanager.add_parser(bootstrap.incparser, bootstrap.inclexer, "")
        self.treemanager.set_font_test(7, 17)
        self.treemanager.key_normal("1")
        assert bootstrap.incparser.last_status == True
        self.treemanager.key_normal("+")
        assert bootstrap.incparser.last_status == False
        self.treemanager.key_normal("2")
        assert bootstrap.incparser.last_status == True
        self.treemanager.key_normal("*")
        assert bootstrap.incparser.last_status == False
        self.treemanager.key_normal("3")
        assert bootstrap.incparser.last_status == True

        # test ast generation
        root = bootstrap.incparser.previous_version.parent
        assert root.symbol.name == "Root"
        assert root.children[1].symbol.name == "E"
        E = root.children[1]
        assert isinstance(E.alternate, AstNode)
        assert E.alternate.name == "Plus"
        plus = E.alternate
        assert plus.children['arg1'].symbol.name == "1"
        mul = plus.children['arg2']
        assert isinstance(mul, AstNode)
        assert mul.name == "Mul"
        assert mul.children['arg1'].symbol.name == "2"
        assert mul.children['arg2'].symbol.name == "3"


    def test_foreach(self):
        grammar = """
X ::= items {foreach(#0) Field(b=item.x)}
    ;

items ::= items "comma" item    {#0 + [#2]}
        | item                  {[#0]}
        ;

item ::= "a" {Var(x=#0)}
       | "b" {Var(x=#0)}
        ;

%%

a:"a"
b:"b"
comma:","

"""
        bootstrap = BootstrapParser(lr_type=1, whitespaces=False)
        bootstrap.parse(grammar)
        self.treemanager = TreeManager()
        self.treemanager.add_parser(bootstrap.incparser, bootstrap.inclexer, "")
        self.treemanager.set_font_test(7, 17)
        self.treemanager.key_normal("a")
        assert bootstrap.incparser.last_status == True
        self.treemanager.key_normal(",")
        assert bootstrap.incparser.last_status == False
        self.treemanager.key_normal("b")
        assert bootstrap.incparser.last_status == True

        # test ast generation
        root = bootstrap.incparser.previous_version.parent
        assert root.symbol.name == "Root"
        assert root.children[1].symbol.name == "X"
        E = root.children[1]
        assert isinstance(E.alternate, ListNode)
        assert isinstance(E.alternate.children[0], AstNode)
        assert isinstance(E.alternate.children[1], AstNode)
        assert E.alternate.children[0].name == "Field"
        assert E.alternate.children[1].name == "Field"
        assert E.alternate.children[0].children['b'].symbol.name == "a"
        assert E.alternate.children[1].children['b'].symbol.name == "b"

    def test_lookup_reference(self):
        grammar = """
X ::= item {#0.x}
    ;

item ::= "a" {Var(x=#0)}
       | "b" {Var(x=#0)}
        ;

%%

a:"a"
b:"b"
comma:","

"""
        bootstrap = BootstrapParser(lr_type=1, whitespaces=False)
        bootstrap.parse(grammar)
        self.treemanager = TreeManager()
        self.treemanager.add_parser(bootstrap.incparser, bootstrap.inclexer, "")
        self.treemanager.set_font_test(7, 17)
        self.treemanager.key_normal("a")
        assert bootstrap.incparser.last_status == True

        # test ast generation
        root = bootstrap.incparser.previous_version.parent
        assert root.symbol.name == "Root"
        assert root.children[1].symbol.name == "X"
        E = root.children[1]
        assert E.alternate.symbol.name == "a"

