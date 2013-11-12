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

from incparser.incparser import IncParser
from inclexer.inclexer import IncrementalLexer
from grammars.grammars import calc1, java15
from grammar_parser.plexer import PriorityLexer
from grammar_parser.gparser import Terminal, Nonterminal
from incparser.astree import TextNode, BOS, EOS, FinishSymbol

N = Nonterminal
T = Terminal

class Test_IncrementalParser:

    def compare_trees(self, original, other):
        assert len(original.children) == len(other.children)
        for i in range(len(original.children)):
            assert original.children[i].symbol == other.children[i].symbol
            if original.children[i].children != []:
                self.compare_trees(original.children[i], other.children[i])

    def make_nodes(self, elements):
        l = []
        for e in elements:
            l.append(TextNode(e))
        return l

    def insert_text(self, ast, pos, text):
        node = ast.parent.children[0]
        cnt = 0
        while cnt <= pos:
            node = node.next_term
            cnt += len(node.symbol.name)
        node.symbol.name = text + node.symbol.name
        return node

class Test_CalcParser(Test_IncrementalParser):

    def setup_class(cls):
        cls.lexer = IncrementalLexer(calc1.priorities)
        cls.parser = IncParser(calc1.grammar, 1, True)
        cls.parser.init_ast()
        cls.ast = cls.parser.previous_version

    def test_simple(self):
        bos = self.ast.parent.children[0]
        new = TextNode(Terminal("1+2"))
        bos.insert_after(new)
        self.lexer.relex(new)
        assert self.parser.inc_parse([]) == True
        assert self.ast.parent.symbol == Nonterminal("Root")
        assert isinstance(self.ast.parent.children[0], BOS)
        assert isinstance(self.ast.parent.children[-1], EOS)
        bos = self.ast.parent.children[0]

        root = TextNode(Nonterminal("Root"))
        bos = BOS(Terminal(""))
        eos = EOS(FinishSymbol())
        Start = TextNode(Nonterminal("Startrule"))
        root.set_children([bos, Start, eos])
        E1 = TextNode(Nonterminal("E"))
        Start.set_children([TextNode(N("WS")), E1])

        E1.set_children(self.make_nodes([N("E"), T("+"), N("WS"), N("T")]))

        E2 = E1.children[0]
        E2.set_children(self.make_nodes([N("T")]))
        T1 = E2.children[0]
        T1.set_children(self.make_nodes([N("P")]))
        P1 = T1.children[0]
        P1.set_children(self.make_nodes([T("1"), N("WS")]))

        T2 = E1.children[3]
        T2.set_children(self.make_nodes([N("P")]))

        P2 = T2.children[0]
        P2.set_children(self.make_nodes([T("2"), N("WS")]))

        self.compare_trees(self.ast.parent, root)

class Test_JavaParser(Test_IncrementalParser):

    def setup_class(cls):
        cls.lexer = IncrementalLexer(java15.priorities)
        cls.parser = IncParser(java15.grammar, 1, True)
        cls.parser.init_ast()
        cls.ast = cls.parser.previous_version

    def test_java(self):
        bos = self.ast.parent.children[0]
        new = TextNode(Terminal("class Test {}"))
        bos.insert_after(new)
        self.lexer.relex(new)
        self.lexer.relex(new)
        assert self.parser.inc_parse([]) == True

        node = self.insert_text(self.ast, 12, "public static void main(String[] args){}")
        self.lexer.relex(node)
        assert self.parser.inc_parse([]) == True
        result = """Nonterminal('Root')
    Terminal('''')
    Nonterminal('Startrule')
        Nonterminal('WS')
        Nonterminal('goal')
            Nonterminal('compilation_unit')
                Nonterminal('package_declaration_opt')
                Nonterminal('import_declarations_opt')
                Nonterminal('type_declarations_opt')
                    Nonterminal('type_declarations')
                        Nonterminal('type_declaration')
                            Nonterminal('class_declaration')
                                Nonterminal('modifiers_opt')
                                Terminal(''class'')
                                Nonterminal('WS')
                                    Terminal('' '')
                                    Nonterminal('WS')
                                Terminal(''Test'')
                                Nonterminal('WS')
                                    Terminal('' '')
                                    Nonterminal('WS')
                                Nonterminal('type_parameters_opt')
                                Nonterminal('super_opt')
                                Nonterminal('interfaces_opt')
                                Nonterminal('class_body')
                                    Terminal(''{'')
                                    Nonterminal('WS')
                                    Nonterminal('class_body_declarations_opt')
                                        Nonterminal('class_body_declarations')
                                            Nonterminal('class_body_declaration')
                                                Nonterminal('class_member_declaration')
                                                    Nonterminal('method_declaration')
                                                        Nonterminal('method_header')
                                                            Nonterminal('modifiers_opt')
                                                                Nonterminal('modifiers')
                                                                    Nonterminal('modifiers')
                                                                        Nonterminal('modifier')
                                                                            Terminal(''public'')
                                                                            Nonterminal('WS')
                                                                                Terminal('' '')
                                                                                Nonterminal('WS')
                                                                    Nonterminal('modifier')
                                                                        Terminal(''static'')
                                                                        Nonterminal('WS')
                                                                            Terminal('' '')
                                                                            Nonterminal('WS')
                                                            Terminal(''void'')
                                                            Nonterminal('WS')
                                                                Terminal('' '')
                                                                Nonterminal('WS')
                                                            Nonterminal('method_declarator')
                                                                Terminal(''main'')
                                                                Nonterminal('WS')
                                                                Terminal(''('')
                                                                Nonterminal('WS')
                                                                Nonterminal('formal_parameter_list_opt')
                                                                    Nonterminal('formal_parameter_list')
                                                                        Nonterminal('formal_parameter')
                                                                            Nonterminal('type')
                                                                                Nonterminal('reference_type')
                                                                                    Nonterminal('array_type')
                                                                                        Nonterminal('name')
                                                                                            Nonterminal('simple_name')
                                                                                                Terminal(''String'')
                                                                                                Nonterminal('WS')
                                                                                        Nonterminal('dims')
                                                                                            Terminal(''['')
                                                                                            Nonterminal('WS')
                                                                                            Terminal('']'')
                                                                                            Nonterminal('WS')
                                                                                                Terminal('' '')
                                                                                                Nonterminal('WS')
                                                                            Nonterminal('variable_declarator_id')
                                                                                Terminal(''args'')
                                                                                Nonterminal('WS')
                                                                Terminal('')'')
                                                                Nonterminal('WS')
                                                            Nonterminal('throws_opt')
                                                        Nonterminal('method_body')
                                                            Nonterminal('block')
                                                                Terminal(''{'')
                                                                Nonterminal('WS')
                                                                Nonterminal('block_statements_opt')
                                                                Terminal(''}'')
                                                                Nonterminal('WS')
                                    Terminal(''}'')
                                    Nonterminal('WS')
    $"""
        assert result == self.ast.cprint()
