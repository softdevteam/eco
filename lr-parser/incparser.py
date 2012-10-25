import sys
sys.path.append("../")

from gparser import Parser, Nonterminal, Terminal, Epsilon
from syntaxtable import SyntaxTable, FinishSymbol, Reduce, Goto, Accept, Shift
from stategraph import StateGraph
from constants import LR0, LR1, LALR
from astree import AST, TextNode

Node = TextNode

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
        self.all_changes = []

        self.previous_version = None

    def init_ast(self):
        bos = Node(Terminal("bos"), 0, [])
        eos = Node(FinishSymbol(), 0, [])
        empty = Node(Terminal(""), 0,  [], 0)
        root = Node(Nonterminal("Root"), 0, [bos, empty, eos])
        self.previous_version = AST(root)

    def inc_parse(self):
        self.stack = []
        self.current_state = 0
        self.stack.append(Node(FinishSymbol(), 0, []))
        bos = self.previous_version.parent.children[0]
        la = self.pop_lookahead(bos)

        while(True):
            print("STACK:", self.stack)
            print("NODE:", la)
            print("CURRENT STATE", self.current_state)
            if isinstance(la.symbol, Terminal) or isinstance(la.symbol, FinishSymbol) or la.symbol == Epsilon():
                print("terminal")
                if la.changed:#self.has_changed(la):
                    print("relex")
                    text = la.symbol.name
                    tokens = text.split(" ")
                    children = []
                    for t in tokens:
                        children.append(Node(Terminal("\"%s\"" % (t,)), -1, []))
                    pos = la.parent.replace_children(la, children)
                    #self.all_changes.remove(la)
                    #la.changed = False
                    self.previous_version.pprint()
                    la = la.parent.children[pos]
                else:
                    element = self.syntaxtable.lookup(self.current_state, la.symbol)
                    if isinstance(element, Accept):
                        print("Accept")
                        self.stack[1].pprint()
                        #XXX change parse so that stack is [bos, startsymbol, eos]
                        bos = self.previous_version.parent.children[0]
                        eos = self.previous_version.parent.children[-1]
                        self.previous_version.parent.children = [bos, self.stack[1], eos]
                        return True
                    elif isinstance(element, Shift):
                        print("Shift")
                        la.state = element.action
                        self.stack.append(la)
                        self.current_state = element.action
                        la = self.pop_lookahead(la)
                    elif isinstance(element, Reduce):
                        print("Reduce", element.action)
                        children = []
                        for i in range(element.amount()):
                            children.insert(0, self.stack.pop())
                        self.current_state = self.stack[-1].state
                        print("Stack[-1]", self.stack[-1])

                        goto = self.syntaxtable.lookup(self.current_state, element.action.left)
                        new_node = Node(element.action.left, goto.action, children)
                        self.stack.append(new_node)
                        self.current_state = new_node.state
                    elif element is None:
                        print("ERROR")
                        return False
            else: # Nonterminal
                print("nonterminal")
                if self.has_changed(la):
                    print("has changed")
                    la = self.left_breakdown(la)
                else:
                    print("has not changed")
                    # perform reductions
                    #next_terminal = next(_inputiter)
                    #a = self.syntaxtable.lookup(self.current_state, next_terminal)
                    #if isinstance(a, Reduce):
                    #    print("REDUCE")
                        #perform
                    #    pass
                    if self.shiftable(la):
                        print("SHIFTABLE")
                        self.shift(la)
                        self.right_breakdown()
                        print("STACK after shift:", self.stack)
                        la = self.pop_lookahead(la)
                    else:
                        la = self.left_breakdown(la)
            print("---------------")

    def inc_parse_old(self, _input):
        if not self.previous_version:
            result = self.check(_input)
            self.previous_version = self.get_ast()
            return result

        self.all_changes = []
        _input = self.prepare_input(_input)
        self.find_changes(iter(_input))
        _inputiter = iter(_input)

        self.stack = []
        self.current_state = 0
        self.stack.append(Node(FinishSymbol(), 0, []))
        bos = self.previous_version.parent.children[0]
        la = self.pop_lookahead(bos)

        while(True):
            print("STACK:", self.stack)
            print("NODE:", la)
            print("CURRENT STATE", self.current_state)
            if isinstance(la.symbol, Terminal) or isinstance(la.symbol, FinishSymbol) or la.symbol == Epsilon():
                print("terminal")
                if self.has_changed(la):
                    print("relex")
                    #self.relex(la) # XXX relex
                    #XXX also adjust state
                    next_terminal = next(_inputiter)
                    print("NEXTTERMINAL", next_terminal)
                    la.symbol = next_terminal
                    self.all_changes.remove(la)
                else:
                    element = self.syntaxtable.lookup(self.current_state, la.symbol)
                    if isinstance(element, Accept):
                        return True
                    elif isinstance(element, Shift):
                        print("Shift")
                        self.stack.append(la)
                        la.state = element.action
                        self.current_state = element.action
                        la = self.pop_lookahead(la)
                    elif isinstance(element, Reduce):
                        print("Reduce", element.action)
                        children = []
                        for i in range(element.amount()):
                            children.insert(0, self.stack.pop())
                        self.current_state = self.stack[-1].state
                        print("Stack[-1]", self.stack[-1])

                        goto = self.syntaxtable.lookup(self.current_state, element.action.left)
                        new_node = Node(element.action.left, goto.action, children)
                        self.stack.append(new_node)
                        self.current_state = new_node.state
                    elif element is None:
                        print("ERROR")
                        return False
            else: # Nonterminal
                print("nonterminal")
                if self.has_changed(la):
                    print("has changed")
                    la = self.left_breakdown(la)
                else:
                    print("has not changed")
                    # perform reductions
                    next_terminal = next(_inputiter)
                    a = self.syntaxtable.lookup(self.current_state, next_terminal)
                    if isinstance(a, Reduce):
                        print("REDUCE")
                        #perform
                        pass
                    if self.shiftable(la):
                        print("SHIFTABLE")
                        self.shift(la)
                        self.right_breakdown()
                        print("STACK after shift:", self.stack)
                        la = self.pop_lookahead(la)
                    else:
                        la = self.left_breakdown(la)
            print("---------------")

    def left_breakdown(self, la):
        if len(la.children) > 0:
            return la.children[0]
        else:
            return self.pop_lookahead(la)

    def right_breakdown(self):
        node = self.stack.pop()
        while(isinstance(node.symbol, Nonterminal)):
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

    def find_changes(self, inputiter):
        # XXX later we'll work on the ast the whole time
        # so nodes are marked as changed while typing
        print("-------- find changes -----")
        changed = []
        ast = self.previous_version
        nodes = [ast.parent]
        while nodes != []:
            node = nodes.pop()
            if isinstance(node.symbol, Terminal) or isinstance(node.symbol, Epsilon):
                i = next(inputiter)
                if i != node.symbol:
                    print("changed", node, "to", i)
                    temp = node
                    changed.append(temp)
                    while(temp.parent is not None):
                        changed.append(temp.parent)
                        temp = temp.parent
            nodes.extend(list(reversed(node.children)))
        self.all_changes = changed
        print("---------------------------")

    def has_changed(self, node):
        return node in self.all_changes

    def prepare_input(self, _input):
        l = []
        # XXX need an additional lexer to do this right
        if _input != "":
            for i in _input.split(" "):
                l.append(Terminal("\"" + i + "\""))
        l.append(FinishSymbol())
        return l

    def check(self, _input):
        self.reset()

        _input = self.prepare_input(_input)

        self.stack.append(FinishSymbol())
        self.stack.append(0)

        i = 0
        while i < len(_input):
            c = _input[i]
            state_id = self.stack[-1]
            element = self.syntaxtable.lookup(state_id, c)

            print(element)
            print(state_id)
            print(c)
            if element is None:
                return False

            if isinstance(element, Shift):
                print("shift")
                self.stack.append(c)
                self.stack.append(element.action)
                i += 1
                # add shifted terminal to ast stack
                self.ast_stack.append(Node(c, element.action, []))

            if isinstance(element, Reduce):
                print("reduce")
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
            if e == Epsilon():
                l.append(Node(Epsilon(), 0, []))
            else:
                l.append(self.ast_stack.pop())
        l.reverse()
        n = Node(element.action.left, state, l)
        self.ast_stack.append(n)

    def get_ast(self):
        bos = Node(Terminal("bos"), 0, [])
        eos = Node(FinishSymbol(), 0, [])
        root = Node(Nonterminal("Root"), 0, [bos, self.ast_stack[0], eos])
        return AST(root)

    def reset(self):
        self.stack = []
        self.ast_stack = []
        self.all_changes = []
