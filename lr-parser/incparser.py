from __future__ import print_function

import sys
sys.path.append("../")

try:
    import cPickle as pickle
except:
    import pickle

import time

from gparser import Parser, Nonterminal, Terminal,MagicTerminal, Epsilon
from syntaxtable import SyntaxTable, FinishSymbol, Reduce, Goto, Accept, Shift
from stategraph import StateGraph
from constants import LR0, LR1, LALR
from astree import AST, TextNode, BOS, EOS

Node = TextNode

# deactivate parser output for now
def print(*args, **kwargs):
    pass

class IncParser(object):

    def __init__(self, grammar, lr_type=LR0, whitespaces=False):
        print("Parsing Grammar")
        parser = Parser(grammar, whitespaces)
        parser.parse()

        filename = "".join([str(hash(grammar) ^ hash(whitespaces)), ".pcl"])
        try:
            #raise IOError
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

        self.previous_version = None
        print("Incemental parser done")

    def init_ast(self):
        bos = BOS(Terminal(""), 0, [])
        eos = EOS(FinishSymbol(), 0, [])
        empty = Node(Terminal(""), 0,  [], 0)
        empty.priority -= 1
        root = Node(Nonterminal("Root"), 0, [bos, eos])
        self.previous_version = AST(root)

    def inc_parse(self):
        print("============ NEW INCREMENTAL PARSE ================= ")
        self.stack = []
        self.undo = []
        self.current_state = 0
        self.stack.append(Node(FinishSymbol(), 0, []))
        bos = self.previous_version.parent.children[0]
        la = self.pop_lookahead(bos)

        while(True):
            #la.seen += 1
            print("--------------------")
            #print("STACK:", self.stack)
            print("NODE:", la, "regex", la.regex, "lookup", la.lookup)
            print("CURRENT STATE", self.current_state)
            if isinstance(la.symbol, Terminal) or isinstance(la.symbol, FinishSymbol) or la.symbol == Epsilon():
                if la.changed:#self.has_changed(la):
                    assert False # with prelexing you should never end up here!
                    # scannerless
                    print("-------------SCANNERLESS-----------------")
                    options = self.get_next_possible_symbols(self.current_state)
                    print("options", options)
                    print("la", la)
                    #XXX find longest match !!!
                    longest_match = ""
                    for o in options:
                        if la.symbol.name == o.name:
                            la.changed = False
                            longest_match = ""
                            print("exact match")
                            break
                        elif la.symbol.name.startswith(o.name):
                            if o.name > longest_match:
                                longest_match = o.name

                    if longest_match == "": # no match found
                        la.changed = False # continue without changing node
                    else:
                        print("found", longest_match)
                        newnode = Node(Terminal(longest_match), -1, [], la.pos)
                        la.parent.insert_before_node(la, newnode)
                        la.pos = la.pos + len(longest_match)
                        la.symbol.name = la.symbol.name[len(longest_match):]
                        la = newnode
                        #la.changed = False
                    # if none found: lexing error -> undo
                    print("--------------- END ----------------------")
                    # scannerless end
                    #print("relex")
                    #text = la.symbol.name
                    #oldpos = la.pos
                    #tokens = text.split(" ")
                    #children = []
                    #for t in tokens:
                    #    children.append(Node(Terminal(t), -1, [], oldpos))
                    #    oldpos += len(t)
                    #    oldpos += 1 # add whitespace
                    #pos = la.parent.replace_children(la, children)
                    ##self.all_changes.remove(la)
                    #la.changed = False
                    #la = la.parent.children[pos]
                else:
                    # ignore spaces
                    #if la.lookup == "WS":
                    #    self.stack.append(la)
                    #    la = self.pop_lookahead(la)
                    #    continue
                    if la.lookup != "":
                        lookup_symbol = Terminal(la.lookup)
                    else:
                        lookup_symbol = la.symbol
                    print("LOOKUPSYMBOL", lookup_symbol)
                    element = self.syntaxtable.lookup(self.current_state, lookup_symbol)
                    if isinstance(element, Accept):
                        print("Accept")
                        #XXX change parse so that stack is [bos, startsymbol, eos]
                        bos = self.previous_version.parent.children[0]
                        eos = self.previous_version.parent.children[-1]
                        self.previous_version.parent.set_children([bos, self.stack[1], eos])
                        return True
                    elif isinstance(element, Shift):
                        print("Shift")
                        la.state = element.action
                        self.stack.append(la)
                        self.current_state = element.action
                        if not la.lookup == "<ws>":
                            # last_shift_state is used to predict next symbol
                            # whitespace destroys correct behaviour
                            self.last_shift_state = element.action
                        la = self.pop_lookahead(la)

                    elif isinstance(element, Reduce):
                        print("Reduce", element.action)
                        children = []
                        for i in range(element.amount()):
                            children.insert(0, self.stack.pop())
                        self.current_state = self.stack[-1].state
                        print("Stack[-1]", self.stack[-1])

                        goto = self.syntaxtable.lookup(self.current_state, element.action.left)

                        # save childrens parents state
                        for c in children:
                            self.undo.append((c, 'parent', c.parent))

                        new_node = Node(element.action.left, goto.action, children)
                        self.stack.append(new_node)
                        self.current_state = new_node.state
                    elif element is None:
                        print("ERROR")
                        if self.validating:
                            print("VALIDATING")
                            self.right_breakdown()
                            self.validating = False
                        else:
                            # undo all changes
                            while len(self.undo) > 0:
                                node, attribute, value = self.undo.pop(0)
                                setattr(node, attribute, value)
                            return False
            else: # Nonterminal
                print("nonterminal")
                #if(la.symbol.name == "WS"):
                #    la = self.pop_lookahead(la)
                #    continue
                if la.changed:#self.has_changed(la):
                    la.changed = False
                    print("has changed")
                    self.undo.append((la, 'changed', True))
                    la = self.left_breakdown(la)
                else:
                    print("has not changed")
                    # get first terminal in subtree (further opt: add this information to syntax table)
                   #t = la.get_first_terminal()
                   #if t:
                   #    print(t)
                   #    if t.lookup != "":
                   #        lookup_symbol = Terminal(t.lookup)
                   #    else:
                   #        lookup_symbol = t.symbol
                   #    element = self.syntaxtable.lookup(self.current_state, lookup_symbol)
                   #else:
                   #    element = self.syntaxtable.lookup(self.current_state, la.symbol)
                   #print(element)
                   # THIS IS THE RIGHT STUFF
                   # ------
                   #follow_id = self.graph.follow(self.current_state, la.symbol)
                   #if follow_id: # can we shift this Nonterminal in the current state?
                   #    print("shift this shit")
                   #    self.stack.append(la)
                   #    self.current_state = follow_id
                   #    #self.stack.append(la)
                   #    #goto = self.syntaxtable.lookup(self.current_state, la.symbol)
                   #    #self.current_state = goto.action
                   #    la = self.pop_lookahead(la)
                   #    self.validating = True
                   #    continue
                   #else:
                   #    la = self.left_breakdown(la)
                   # -------
                    #elif isinstance(element, Reduce):
                    #    print("reduce this shit")
                    #else:
                    #    print("error?")
                    # perform reductions
                    #next_terminal = next(_inputiter)
                    #a = self.syntaxtable.lookup(self.current_state, next_terminal)
                    #if isinstance(a, Reduce):
                    #    print("REDUCE")
                        #perform
                    #    pass
                    # perform all reductions
                    # PARSER WITHOUT OPTIMISATION
                    t = la.next_terminal()
                    if la.lookup != "":
                        lookup_symbol = Terminal(t.lookup)
                    else:
                        lookup_symbol = t.symbol
                    element = self.syntaxtable.lookup(self.current_state, lookup_symbol)
                    print("PERFORM ALL THE REDUCTIONS", element)

                    if self.shiftable(la):
                        print("SHIFTABLE")
                        self.shift(la)
                        self.right_breakdown()
                        #print("STACK after shift:", self.stack)
                        la = self.pop_lookahead(la)
                    else:
                        la = self.left_breakdown(la)
            print("---------------")
        print("============ INCREMENTAL PARSE END ================= ")

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
        print("pop_lookahead", la)
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

    def get_next_possible_symbols(self, state_id):
        stateset = self.graph.state_sets[state_id]
        lookahead = set()
        for state in stateset.elements:
            if state.isfinal():
                lookahead = lookahead | state.lookahead
            else:
                s = state.next_symbol()
                if isinstance(s, Terminal):
                    lookahead.add(s)

        return lookahead

    def get_next_symbols_string(self):

        lookahead = self.get_next_possible_symbols(self.last_shift_state)

        s = []
        for symbol in lookahead:
            s.append(symbol.name)
        return ", ".join(s)

    def reset(self):
        self.stack = []
        self.ast_stack = []
        self.all_changes = []
