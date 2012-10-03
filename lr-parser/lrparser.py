import sys
sys.path.append("../")

from gparser import Parser, Nonterminal, Terminal
from syntaxtable import SyntaxTable, FinishSymbol, Reduce, Goto, Accept, Shift
from stategraph import StateGraph

class LRParser(object):

    def __init__(self, grammar):
        parser = Parser(grammar)
        parser.parse()

        self.graph = StateGraph(parser.start_symbol, parser.rules)
        self.graph.build()

        self.syntaxtable = SyntaxTable()
        self.syntaxtable.build(self.graph)

        self.stack = []

    def check(self, _input):
        l = []
        for i in _input.split(" "):
            l.append(Terminal("\"" + i + "\""))
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
                for x in range(2*len(element.action.right)):
                    self.stack.pop()
                state_id = self.stack[-1]
                self.stack.append(element.action.left)
                element = self.syntaxtable.lookup(state_id, element.action.left)
                assert isinstance(element, Goto)
                self.stack.append(element.action)
            if isinstance(element, Accept):
                return True

