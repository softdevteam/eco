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

from __future__ import print_function

try:
    import cPickle as pickle
except:
    import pickle

import time, os

from grammar_parser.gparser import Parser, Nonterminal, Terminal,MagicTerminal, Epsilon, IndentationTerminal
from syntaxtable import SyntaxTable, FinishSymbol, Reduce, Goto, Accept, Shift
from stategraph import StateGraph
from constants import LR0, LR1, LALR
from astree import AST, TextNode, BOS, EOS

Node = TextNode

# deactivate parser output for now
def noprint(*args, **kwargs):
    pass

class IncParser(object):

    def __init__(self, grammar=None, lr_type=LR0, whitespaces=False, startsymbol=None):

        if grammar:
            print("Parsing Grammar")
            parser = Parser(grammar, whitespaces)
            parser.parse()

            filename = "".join([os.path.dirname(__file__), "/../pickle/", str(hash(grammar) ^ hash(whitespaces)), ".pcl"])
            try:
                print("Try to unpickle former stategraph")
                f = open(filename, "r")
                start = time.time()
                self.graph = pickle.load(f)
                end = time.time()
                print("unpickling done in", end-start)
            except IOError:
                print("could not unpickle old graph")
                print("Creating Stategraph")
                self.graph = StateGraph(parser.start_symbol, parser.rules, lr_type)
                print("Building Stategraph")
                self.graph.build()
                print("Pickling")
                pickle.dump(self.graph, open(filename, "w"))

            if lr_type == LALR:
                self.graph.convert_lalr()

            print("Creating Syntaxtable")
            self.syntaxtable = SyntaxTable(lr_type)
            self.syntaxtable.build(self.graph)

        self.stack = []
        self.ast_stack = []
        self.all_changes = []
        self.undo = []
        self.last_shift_state = 0
        self.validating = False
        self.last_status = False
        self.error_node = None

        self.previous_version = None
        print("Incemental parser done")

    def from_dict(self, rules, startsymbol, lr_type, whitespaces):
        self.graph = StateGraph(startsymbol, rules, lr_type)
        self.graph.build()

        self.syntaxtable = SyntaxTable(lr_type)
        self.syntaxtable.build(self.graph)

    def init_ast(self, magic_parent=None):
        bos = BOS(Terminal(""), 0, [])
        eos = EOS(FinishSymbol(), 0, [])
        bos.magic_parent = magic_parent
        eos.magic_parent = magic_parent
        bos.next_term = eos
        eos.prev_term = bos
        root = Node(Nonterminal("Root"), 0, [bos, eos])
        self.previous_version = AST(root)

    def inc_parse(self, line_indents=[]):
        print("============ NEW INCREMENTAL PARSE ================= ")
        self.error_node = None
        self.stack = []
        self.undo = []
        self.current_state = 0
        self.stack.append(Node(FinishSymbol(), 0, []))
        bos = self.previous_version.parent.children[0]
        la = self.pop_lookahead(bos)
        self.loopcount = 0

        USE_OPT = True

        while(True):
            self.loopcount += 1
            if isinstance(la.symbol, Terminal) or isinstance(la.symbol, FinishSymbol) or la.symbol == Epsilon():
                if la.changed:#self.has_changed(la):
                    assert False # with prelexing you should never end up here!
                else:
                    if la.lookup != "":
                        lookup_symbol = Terminal(la.lookup)
                    else:
                        lookup_symbol = la.symbol

                    result = self.parse_terminal(la, lookup_symbol)
                    if result == "Accept":
                        self.last_status = True
                        return True
                    elif result == "Error":
                        self.last_status = False
                        return False
                    elif result != None:
                        la = result

            else: # Nonterminal
                if la.changed:
                    la.changed = False
                    self.undo.append((la, 'changed', True))
                    la = self.left_breakdown(la)
                else:
                    if USE_OPT:
                        follow_id = self.graph.follow(self.current_state, la.symbol)
                        if follow_id: # can we shift this Nonterminal in the current state?
                            self.stack.append(la)
                            la.state = follow_id #XXX this fixed goto error (i should think about storing the states on the stack instead of inside the elements)
                            self.current_state = follow_id
                            la = self.pop_lookahead(la)
                            self.validating = True
                            continue
                        else:
                            first_term = la.find_first_terminal()
                            if first_term.lookup != "":
                                lookup_symbol = Terminal(first_term.lookup)
                            else:
                                lookup_symbol = first_term.symbol
                            element = self.syntaxtable.lookup(self.current_state, lookup_symbol)
                            if isinstance(element, Reduce):
                                self.reduce(element)
                            else:
                                la = self.left_breakdown(la)
                    else:
                    # PARSER WITHOUT OPTIMISATION
                        if la.lookup != "":
                            lookup_symbol = Terminal(la.lookup)
                        else:
                            lookup_symbol = la.symbol
                        element = self.syntaxtable.lookup(self.current_state, lookup_symbol)

                        if self.shiftable(la):
                            self.shift(la)
                            self.right_breakdown()
                            la = self.pop_lookahead(la)
                        else:
                            la = self.left_breakdown(la)
        print("============ INCREMENTAL PARSE END ================= ")

    def parse_terminal(self, la, lookup_symbol):
        #print("Parsing terminal", la)
        if isinstance(lookup_symbol, IndentationTerminal):
            #XXX hack: change parsing table to accept IndentationTerminals
            lookup_symbol = Terminal(lookup_symbol.name)
        element = self.syntaxtable.lookup(self.current_state, lookup_symbol)
        if isinstance(element, Accept):
            #XXX change parse so that stack is [bos, startsymbol, eos]
            bos = self.previous_version.parent.children[0]
            eos = self.previous_version.parent.children[-1]
            self.previous_version.parent.set_children([bos, self.stack[1], eos])
            print("loopcount", self.loopcount)
            print ("Accept")
            return "Accept"
        elif isinstance(element, Shift):
            print("Shift", la)
            # removing this makes "Valid tokens" correct, should not be needed
            # for incremental parser
            #self.undo.append((la, "state", la.state))
            la.state = element.action
            self.stack.append(la)
            self.current_state = element.action
            if not la.lookup == "<ws>":
                # last_shift_state is used to predict next symbol
                # whitespace destroys correct behaviour
                self.last_shift_state = element.action
            return self.pop_lookahead(la)

        elif isinstance(element, Reduce):
            #print("Reducing")
            self.reduce(element)
            return self.parse_terminal(la, lookup_symbol)
        elif element is None:
            if self.validating:
                self.right_breakdown()
                self.validating = False
            else:
                # undo all changes
                while len(self.undo) > 0:
                    node, attribute, value = self.undo.pop(-1)
                    setattr(node, attribute, value)
                self.error_node = la
                print ("Error", la, la.prev_term, la.next_term)
                print("loopcount", self.loopcount)
                return "Error"

    def reduce(self, element):
        children = []
        for i in range(element.amount()):
            c = self.stack.pop()
            # apply folding information from grammar to tree nodes
            fold = element.action.right[element.amount()-i-1].folding
            c.symbol.folding = fold
            children.insert(0, c)
        self.current_state = self.stack[-1].state #XXX

        goto = self.syntaxtable.lookup(self.current_state, element.action.left)
        assert goto != None

        # save childrens parents state
        for c in children:
            self.undo.append((c, 'parent', c.parent))
            self.undo.append((c, 'left', c.left))
            self.undo.append((c, 'right', c.right))

        new_node = Node(element.action.left.copy(), goto.action, children)
        self.stack.append(new_node)
        self.current_state = new_node.state
        self.interpret_annotation(new_node, element.action)
        #self.add_alternate_version(new_node, element.action)

    def interpret_annotation(self, node, production):
        annotation = production.annotation
        if annotation:
            astnode = annotation.interpret(node)
            node.alternate = astnode

    def add_alternate_version(self, node, production):
        # add alternate (folded) versions for nodes to the tree
        alternate = TextNode(node.symbol.__class__(node.symbol.name), node.state, [])
        alternate.children = []
        teared = []
        for i in range(len(node.children)):
            if production.inserts.has_key(i):
                # insert teared nodes at right position
                value = production.inserts[i]
                for t in teared:
                    if t.symbol.name == value.name:
                        alternate.children.append(t)
            c = node.children[i]
            if c.symbol.folding == "^^^":
                c.symbol.folding = None
                teared.append(c)
                continue
            elif c.symbol.folding == "^^":
                while c.alternate is not None:
                    c = c.alternate
                alternate.symbol = c.symbol
                for child in c.children:
                    alternate.children.append(child)
            elif c.symbol.folding == "^":
                while c.alternate is not None:
                    c = c.alternate
                for child in c.children:
                    alternate.children.append(child)
            else:
                alternate.children.append(c)
        node.alternate = alternate

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
                l.append(Terminal(i))
        l.append(FinishSymbol())
        return l

   #def reduce_ast(self, element, state):
   #    l = []
   #    # action = Production
   #    for e in element.action.right:
   #        if e == Epsilon():
   #            l.append(Node(Epsilon(), 0, []))
   #        else:
   #            l.append(self.ast_stack.pop())
   #    l.reverse()
   #    n = Node(element.action.left, state, l)
   #    self.ast_stack.append(n)

    def get_ast(self):
        bos = Node(Terminal("bos"), 0, [])
        eos = Node(FinishSymbol(), 0, [])
        root = Node(Nonterminal("Root"), 0, [bos, self.ast_stack[0], eos])
        return AST(root)

    def get_next_possible_symbols(self, state_id):
        stateset = self.graph.state_sets[state_id]
        lookahead = set()
        for state in stateset.elements:
            if state.isfinal():
                lookahead = lookahead | stateset.lookaheads[state]
            else:
                s = state.next_symbol()
                if isinstance(s, Terminal):
                    lookahead.add(s)

        return lookahead

    def get_next_symbols_list(self, state = -1):
        if state == -1:
            state = self.last_shift_state
        lookahead = self.get_next_possible_symbols(state)

        s = []
        for symbol in lookahead:
            s.append(symbol.name)
        return s

    def get_next_symbols_string(self, state = -1):
        l = self.get_next_symbols_list(state)
        return ", ".join(l)

    def get_expected_symbols(self, state_id):
        #XXX if state of a symbol is nullable, return next symbol as well
        #XXX if at end of state, find state we came from (reduce, stack) and get next symbols from there
        if state_id != -1:
            stateset = self.graph.state_sets[state_id]
            symbols = stateset.get_next_symbols_no_ws()
            return symbols
        return []


    def reset(self):
        self.stack = []
        self.ast_stack = []
        self.all_changes = []
        self.undo = []
        self.last_shift_state = 0
        self.validating = False
        self.last_status = False
        self.error_node = None
        self.previous_version = None
        self.init_ast()
