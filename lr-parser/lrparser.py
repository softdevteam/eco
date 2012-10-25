import sys
sys.path.append("../")

from gparser import Parser, Nonterminal, Terminal, Epsilon
from syntaxtable import SyntaxTable, FinishSymbol, Reduce, Goto, Accept, Shift
from stategraph import StateGraph
from constants import LR0, LR1, LALR
from astree import AST, Node

class LRParser(object):

    def __init__(self, grammar, lr_type=LR0):
        parser = Parser(grammar)
        parser.parse()

        self.graph = StateGraph(parser.start_symbol, parser.rules, lr_type)
        self.graph.build()

        if lr_type == LALR:
            self.graph.convert_lalr()

        self.syntaxtable = SyntaxTable(lr_type)
        self.syntaxtable.build(self.graph)

        self.stack = []
        self.ast_stack = []

    def check(self, _input):
        self.reset()

        l = []
        # XXX need an additional lexer to do this right
        for i in _input.split(" "):
            l.append(Terminal(i))
        l.append(FinishSymbol())
        _input = l

        self.stack.append(FinishSymbol())
        self.stack.append(0)

        i = 0
        while i < len(_input):
            c = _input[i]
            state_id = self.stack[-1]
            element = self.syntaxtable.lookup(state_id, c)
            if element is None:
                return False
            if isinstance(element, Shift):
                self.stack.append(c)
                self.stack.append(element.action)
                i += 1
            if isinstance(element, Reduce):
                #self.add_to_ast(element)
                for x in range(2*element.amount()):
                    self.stack.pop()
                state_id = self.stack[-1]
                self.stack.append(element.action.left)
                element = self.syntaxtable.lookup(state_id, element.action.left)
                assert isinstance(element, Goto)
                self.stack.append(element.action)

            if isinstance(element, Accept):
                return True

    def add_to_ast(self, element):
        l = []
        # action = Production
        for e in element.action.right:
            if isinstance(e, Nonterminal):
                l.append(self.ast_stack.pop())
            if isinstance(e, Terminal):
                l.append(Node(e, []))
        l.reverse()
        n = Node(element.action.left, l)
        self.ast_stack.append(n)

    def get_ast(self):
        return AST(self.ast_stack[0])

    def reset(self):
        self.stack = []
        self.ast_stack = []
