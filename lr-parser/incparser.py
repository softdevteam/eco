import sys
sys.path.append("../")

from gparser import Parser, Nonterminal, Terminal, Epsilon
from syntaxtable import SyntaxTable, FinishSymbol, Reduce, Goto, Accept, Shift
from stategraph import StateGraph
from constants import LR0, LR1, LALR
from astree import AST, Node

class IncParser(object):

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

        self.previous_version = None

    def inc_parse(self, _input):
        if not self.previous_version:
            result = self.check(_input)
            self.previous_version = self.get_ast()
            return result

        _inputiter = iter(_input)

        self.stack = []
        self.current_state = 0
        bos = self.previous_version.parent.children[0]
        la = self.pop_lookahead(bos)

        while(True):
            print(la, "\n-------")
            if isinstance(la.symbol, Terminal) or isinstance(la.symbol, FinishSymbol):
                print("terminal")
                if self.has_changed(la):
                    pass # XXX relex
                else:
                    element = self.syntaxtable.lookup(self.current_state, la.symbol)
                    if isinstance(element, Accept):
                        return True
                    elif isinstance(element, Shift):
                        self.stack.append(la)
                        self.stack.append(element.action)
                        self.current_state = element.action
                        la = self.pop_lookahead(la)
                    elif isinstance(element, Reduce):
                        children = []
                        for i in range(element.amount()):
                            children.append(self.stack.pop())
                        self.current_state = self.stack[-1]

                        self.stack.append(Node(element.action.left, children))
                        goto = self.syntaxtable.lookup(self.current_state, element.action.left)
                        self.stack.append(goto.action)
                    elif action is None:
                        return False
            else: # Nonterminal
                print("nonterminal")
                if self.has_changed(la):
                    la = self.left_breakdown(la)
                else:
                    # perform reductions
                    next_terminal = next(_inputiter)
                    a = self.syntaxtable.lookup(self.current_state, next_terminal)
                    if isinstance(a, Reduce):
                        #perform
                        pass
                    if self.shiftable(la):
                        goto = self.syntaxtable.lookup(self.current_state, la.symbol)
                        self.stack.append(la)
                        self.right_breakdown()
                        la = self.pop_lookahead(la)

    def right_breakdown(self):
        node = self.stack.pop()
        while(isinstance(node, Nonterminal)):
            for c in node.children:
                self.shift(c)
            node = self.stack.pop()
        self.shift(node)

    def shift(self, la):
        self.stack.append(la)
        self.current_state = la.state

    def pop_lookahead(self, la):
        while(la.right_sibling() is None):
            la = la.parent
        return la.right_sibling()

    def shiftable(self, la):
        if self.graph.follow(self.current_state, la.symbol):
            return True
        return False

    def has_changed(self, node):
        # XXX fill with content
        return False

    def check(self, _input):
        self.reset()

        l = []
        # XXX need an additional lexer to do this right
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
                # add shifted terminal to ast stack
                self.ast_stack.append(Node(c, element.action, []))

            if isinstance(element, Reduce):
                for x in range(2*element.amount()):
                    self.stack.pop()
                state_id = self.stack[-1]
                self.stack.append(element.action.left)

                goto = self.syntaxtable.lookup(state_id, element.action.left)
                assert isinstance(goto, Goto)
                self.stack.append(goto.action)

                # add Nonterminal after Goto (setting nodes on ast_stack as
                # children)
                self.reduce_ast(element, goto.action)

            if isinstance(element, Accept):
                return True

    def reduce_ast(self, element, state):
        l = []
        # action = Production
        for e in element.action.right:
            l.append(self.ast_stack.pop())
        l.reverse()
        n = Node(element.action.left, state, l)
        self.ast_stack.append(n)

    def get_ast(self):
        bos = Node("bos", 0, [])
        eos = Node(FinishSymbol(), 0, [])
        root = Node("Root", 0, [bos, self.ast_stack[0], eos])
        return AST(root)

    def reset(self):
        self.stack = []
        self.ast_stack = []
