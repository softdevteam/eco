# Copyright (c) 2012--2014 King's College London
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

from grammar_parser.gparser import Parser, Nonterminal, Terminal,MagicTerminal, Epsilon, IndentationTerminal, AnySymbol
from syntaxtable import SyntaxTable, FinishSymbol, Reduce, Goto, Accept, Shift
from stategraph import StateGraph
from constants import LR0, LR1, LALR
from astree import AST, TextNode, BOS, EOS

import logging

Node = TextNode


def printc(text, color):
    print("\033[%sm%s\033[0m" % (color, text))

class IncParser(object):

    def __init__(self, grammar=None, lr_type=LR0, whitespaces=False, startsymbol=None):

        if grammar:
            logging.debug("Parsing Grammar")
            parser = Parser(grammar, whitespaces)
            parser.parse()

            filename = "".join([os.path.dirname(__file__), "/../pickle/", str(hash(grammar) ^ hash(whitespaces)), ".pcl"])
            try:
                logging.debug("Try to unpickle former stategraph")
                f = open(filename, "r")
                start = time.time()
                self.graph = pickle.load(f)
                end = time.time()
                logging.debug("unpickling done in %s", end-start)
            except IOError:
                logging.debug("could not unpickle old graph")
                logging.debug("Creating Stategraph")
                self.graph = StateGraph(parser.start_symbol, parser.rules, lr_type)
                logging.debug("Building Stategraph")
                self.graph.build()
                logging.debug("Pickling")
                pickle.dump(self.graph, open(filename, "w"))

            if lr_type == LALR:
                self.graph.convert_lalr()

            logging.debug("Creating Syntaxtable")
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
        self.whitespaces = whitespaces
        self.anycount = {}
        self.anycounter = 0
        self.status_by_version = {}
        self.errornode_by_version = {}

        self.indent_stack = None
        self.indentation_based = False

        self.previous_version = None
        logging.debug("Incemental parser done")

    def from_dict(self, rules, startsymbol, lr_type, whitespaces, pickle_id, precedences):
        self.graph = None
        self.syntaxtable = None
        if pickle_id:
            filename = "".join([os.path.dirname(__file__), "/../pickle/", str(pickle_id ^ hash(whitespaces)), ".pcl"])
            try:
                f = open(filename, "r")
                self.syntaxtable = pickle.load(f)
            except IOError:
                pass
        if self.syntaxtable is None:
            self.graph = StateGraph(startsymbol, rules, lr_type)
            self.graph.build()
            self.syntaxtable = SyntaxTable(lr_type)
            self.syntaxtable.build(self.graph, precedences)
            if pickle_id:
                pickle.dump(self.syntaxtable, open(filename, "w"))

        self.whitespaces = whitespaces

    def init_ast(self, magic_parent=None):
        bos = BOS(Terminal(""), 0, [])
        eos = EOS(FinishSymbol(), 0, [])
        bos.magic_parent = magic_parent
        eos.magic_parent = magic_parent
        bos.next_term = eos
        eos.prev_term = bos
        root = Node(Nonterminal("Root"), 0, [bos, eos])
        self.previous_version = AST(root)
        root.save(0)
        bos.save(0)
        eos.save(0)

    def reparse(self):
        self.inc_parse([], True)

    def inc_parse(self, line_indents=[], reparse=False):
        print("============ new parse ===============")
        logging.debug("============ NEW INCREMENTAL PARSE ================= ")
        self.error_node = None
        self.stack = []
        self.undo = []
        self.current_state = 0
        self.stack.append(Node(FinishSymbol(), 0, []))
        self.stack[0].indent = [0]
        bos = self.previous_version.parent.children[0]
        la = self.pop_lookahead(bos)
        self.loopcount = 0
        self.anycount = {}
        self.anycounter = 0

        USE_OPT = False

        # for now ALWAYS delete the indentationtokens before EOS
        eos = self.previous_version.parent.children[-1]
        d = eos.prev_term
        while isinstance(d.symbol, IndentationTerminal):
            d.parent.remove_child(d, False)
            d = d.prev_term

        while(True):
            logging.debug("\x1b[35mProcessing\x1b[0m %s %s %s %s", la, la.changed, id(la), la.indent)
            self.loopcount += 1
            if isinstance(la.symbol, Terminal) or isinstance(la.symbol, FinishSymbol) or la.symbol == Epsilon():
                if la.changed:#self.has_changed(la):
                    assert False # with prelexing you should never end up here!
                else:
                    lookup_symbol = self.get_lookup(la)
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
                if la.changed or reparse:
                    la.changed = False
                    self.undo.append((la, 'changed', True))
                    la = self.left_breakdown(la)
                else:
                    if USE_OPT:
                        goto = self.syntaxtable.lookup(self.current_state, la.symbol)
                        if goto: # can we shift this Nonterminal in the current state?
                            logging.debug("OPTShift: %s in state %s -> %s", la.symbol, self.current_state, goto)
                            follow_id = goto.action
                            self.stack.append(la)
                            la.state = follow_id #XXX this fixed goto error (i should think about storing the states on the stack instead of inside the elements)
                            self.current_state = follow_id
                            logging.debug("USE_OPT: set state to %s", self.current_state)
                            la = self.pop_lookahead(la)
                            self.validating = True
                            continue
                        else:
                            #XXX can be made faster by providing more information in syntax tables
                            first_term = la.find_first_terminal()

                            lookup_symbol = self.get_lookup(first_term)
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
                            logging.debug("\x1b[37mis shiftable\x1b[0m")
                            self.stack.append(la)
                            self.current_state = la.state
                            self.right_breakdown()
                            la = self.pop_lookahead(la)
                        else:
                            la = self.left_breakdown(la)
        logging.debug("============ INCREMENTAL PARSE END ================= ")

    def parse_anysymbol(self):
        symbol = AnySymbol()
        result = self.syntaxtable.lookup(self.current_state, symbol)
        if not result:
            symbol = AnySymbol("@ncr")
            result = self.syntaxtable.lookup(self.current_state, symbol)
        return result, symbol

    def is_valid(self, symbol):
        print("valid:", symbol, self.syntaxtable.lookup(self.current_state, symbol))
        return self.syntaxtable.lookup(self.current_state, symbol)

    def parse_terminal(self, la, lookup_symbol):
        # try parsing ANYSYMBOL
        element = self.syntaxtable.lookup(self.current_state, lookup_symbol)

        if not isinstance(la.symbol, FinishSymbol):
            if self.process_any(la):
                return self.pop_lookahead(la)
        elif self.indentation_based:
            # check if indenttokens are correct, if not update
            last = list(self.get_last_indent(la))
            needed = []
            if not isinstance(la.prev_term, BOS) and (self.is_valid(Terminal("DEDENT")) or self.is_valid(Terminal("NEWLINE"))):
                needed.append(IndentationTerminal("NEWLINE"))
                while 0 < last[-1]:
                    last.pop()
                    needed.append(IndentationTerminal("DEDENT"))

            there = []
            n = la.prev_term
            while isinstance(n.symbol, IndentationTerminal):
                there.insert(0, n.symbol)
                n = n.prev_term

            print(needed)
            print(there)
            if needed == there or len(needed) < len(there):
                # needed can be smaller than there, after we added tokens in a
                # previous step (reduce). After reducing to startrule nothing
                # is needed anymore, but the tokens are still there
                printc("ALL IS WELL", 37)
            else:
                printc("UPDATING", 37)
                # update
                print("    tried parsing $ but dedent not finished")
                # finish dedentation
                n = la.prev_term
               #while isinstance(n.symbol, IndentationTerminal):
               #    print("    removing", n)
               #    n.parent.remove_child(n, False)
               #    n = n.prev_term
               #    self.stack.pop()
               #self.current_state = self.stack[-1].state
                i = 0
                last_added = la
                for node in needed:
                    if len(there) > i and there[i] == node:
                        print("    skip", node)
                    else:
                        self.silent_insert(la.prev_term, Node(node))
                    i += 1
                return self.pop_lookahead(n)

        logging.debug("\x1b[34mparse_terminal\x1b[0m: %s in %s -> %s", lookup_symbol, self.current_state, element)
        if isinstance(element, Accept):
            #XXX change parse so that stack is [bos, startsymbol, eos]
            bos = self.previous_version.parent.children[0]
            eos = self.previous_version.parent.children[-1]
            self.previous_version.parent.set_children([bos, self.stack[1], eos])
            logging.debug("loopcount: %s", self.loopcount)
            logging.debug ("\x1b[32mAccept\x1b[0m")
            return "Accept"
        elif isinstance(element, Shift):
            self.validating = False
            self.shift(la, element)
            return self.pop_lookahead(la)

        elif isinstance(element, Reduce):
            logging.debug("\x1b[33mReduce\x1b[0m: %s -> %s", la, element)
            self.reduce(element)
            return self.parse_terminal(la, lookup_symbol)
        elif element is None:
            if self.validating:
                logging.debug("Was validating: Right breakdown and return to normal")
                logging.debug("Before breakdown: %s", self.stack[-1])
                self.right_breakdown()
                logging.debug("After breakdown: %s", self.stack[-1])
                self.validating = False
            else:
                return self.do_undo(la)

    def is_logical_line(self, node):
        # check if line is logical (i.e. doesn't only consist of whitespaces,
        # comments, etc)
        if node.symbol.name == "\r" and node.prev_term.symbol.name == "\\":
            return False
        node = node.next_term
        while True:
            if isinstance(node, EOS):
                return False
            if node.parent.symbol.name in ["multiline_string", "single_string", "comment"]:
                return False
            if node.lookup == "<return>": # reached next line
                return False
            if node.lookup == "<ws>":
                node = node.next_term
                continue
            if  isinstance(node.symbol, IndentationTerminal):
                node = node.next_term
                continue
            # if we are here, we reached a normal node
            return True

    def parse_whitespace(self, la):
        #XXX indentation logic here
        if la.lookup == "<return>":
            if isinstance(la.next_term, EOS):
                n = la
                while isinstance(n.symbol, IndentationTerminal):
                    print("       remove eos indent", n)
                    n.parent.remove_child(n, False)
                    n = n.prev_term
            else:
                n = la.next_term
                while isinstance(n.symbol, IndentationTerminal):
                    print("       remove indent")
                    n.parent.remove_child(n, False)
                    n = n.next_term

            # XXX only remove if not logical, otherwise try to update tokens instead of renewing them
            if not self.is_logical_line(la):
                return

            if n.lookup == "<ws>":
                ws = len(n.symbol.name)
            else:
                ws = 0

            last = list(self.get_last_indent(la))
            print("       last", last)
            if ws > last[-1]:
                self.silent_insert(la, Node(IndentationTerminal("INDENT")))
                self.silent_insert(la, Node(IndentationTerminal("NEWLINE")))
                la.indent = last + [ws]
                print("       set indent", la, la.indent)
            elif ws < last[-1]:
                while ws < last[-1]:
                    last.pop()
                    print("       add dedent")
                    self.silent_insert(la, Node(IndentationTerminal("DEDENT")))
                self.silent_insert(la, Node(IndentationTerminal("NEWLINE")))
                la.indent = list(last)
                if ws != last[-1]:
                    print("UNBALANCED", last)
                    # XXX in future, just ERROR here
                    self.silent_insert(la, Node(IndentationTerminal("UNBALANCED")))
            else:
                print("NEWLINE", last)
                self.silent_insert(la, Node(IndentationTerminal("NEWLINE")))
                la.indent = list(last)

    def silent_insert(self, la, newnode):
        print("       \x1b[36mINSERT\x1b[0m", newnode, id(newnode))
        newnode.right = la.right
        newnode.next_term = la.next_term
        newnode.left = la
        newnode.prev_term = la
        newnode.parent = la.parent

        if newnode.right:
            self.undo.append((newnode.right, "left", newnode.right.left))
            newnode.right.left = newnode
        self.undo.append((newnode.next_term, "prev_term", newnode.next_term.prev_term))
        newnode.next_term.prev_term = newnode

        self.undo.append((la, "right", la.right))
        la.right = newnode
        self.undo.append((la, "next_term", la.next_term))
        la.next_term = newnode

    def parse_indent(self, la):
        lookup = self.get_lookup(la)
        element = self.syntaxtable.lookup(self.current_state, lookup)
        print("NOPUSH:", lookup, element)
        if isinstance(element, Shift):
            self.stack[-1].state = element.action
            self.current_state = element.action
        elif isinstance(element, Reduce):
            self.reduce(element)
            self.parse_indent(la)
        print("DONE")

    def get_last_indent(self, la):
        # XXX not the most performant solution as it iterates over all elements
        # on the stack until one has it's indent level set, which will be
        # either a return terminal or a Nonterminal with a return somewhere in
        # its subtrees
        for n in reversed(self.stack):
            if n.indent and n is not la:
                return n.indent

    def set_total_indent(self, node):
        l = []
        if node.children:
            for c in node.children:
                if c.indent:
                    l = c.indent
        if l:
            node.indent = l

    def get_lookup(self, la):
        if la.lookup != "":
            lookup_symbol = Terminal(la.lookup)
        else:
            lookup_symbol = la.symbol
        if isinstance(lookup_symbol, IndentationTerminal):
            #XXX hack: change parsing table to accept IndentationTerminals
            lookup_symbol = Terminal(lookup_symbol.name)
        return lookup_symbol

    def do_undo(self, la):
        while len(self.undo) > 0:
            node, attribute, value = self.undo.pop(-1)
            setattr(node, attribute, value)
        self.error_node = la
        logging.debug ("\x1b[31mError\x1b[0m: %s %s %s", la, la.prev_term, la.next_term)
        logging.debug("loopcount: %s", self.loopcount)
        return "Error"

    def reduce(self, element):
        # Reduces elements from the stack to a Nonterminal subtree.  special:
        # COMMENT subtrees that are found on the stack during reduction are
        # added "silently" to the subtree (they don't count to the amount of
        # symbols of the reduction)
        children = []
        i = 0
        while i < element.amount():
            c = self.stack.pop()
            # apply folding information from grammar to tree nodes
            fold = element.action.right[element.amount()-i-1].folding
            c.symbol.folding = fold
            children.insert(0, c)
            if c.symbol.name != "~COMMENT~":
                i += 1
            if self.anycount.has_key(c):
                for _ in range(self.anycount[c]):
                    c = self.stack.pop()
                    children.insert(0,c)
        if self.stack[-1].symbol.name == "~COMMENT~":
            c = self.stack.pop()
            children.insert(0, c)

        logging.debug("   Element on stack: %s(%s)", self.stack[-1].symbol, self.stack[-1].state)
        self.current_state = self.stack[-1].state #XXX don't store on nodes, but on stack
        logging.debug("   Reduce: set state to %s (%s)", self.current_state, self.stack[-1].symbol)

        goto = self.syntaxtable.lookup(self.current_state, element.action.left)
        if goto is None:
            raise Exception("Reduction error on %s in state %s: goto is None" % (element, self.current_state))
        assert goto != None

        # save childrens parents state
        for c in children:
            self.undo.append((c, 'parent', c.parent))
            self.undo.append((c, 'left', c.left))
            self.undo.append((c, 'right', c.right))

        new_node = Node(element.action.left.copy(), goto.action, children)
        self.set_total_indent(new_node)
        logging.debug("   Add %s to stack and goto state %s", new_node.symbol, new_node.state)
        self.stack.append(new_node)
        self.current_state = new_node.state # = goto.action
        logging.debug("Reduce: set state to %s (%s)", self.current_state, new_node.symbol)
        if getattr(element.action.annotation, "interpret", None):
            # eco grammar annotations
            self.interpret_annotation(new_node, element.action)
        else:
            # johnstone annotations
            self.add_alternate_version(new_node, element.action)

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
        node = self.stack.pop() # optimistically shifted Nonterminal
        # after the breakdown, we need to properly shift the left over terminal
        # using the (correct) current state from before the optimistic shift of
        # it's parent tree
        self.current_state = self.stack[-1].state
        logging.debug("right breakdown(%s): set state to %s", node.symbol.name, self.current_state)
        while(isinstance(node.symbol, Nonterminal)):
            for c in node.children:
                if not self.process_any(c): # in breakdown we also have to take care of ANYSYMBOLs
                    self.shift(c, rb=True)
                c = c.right
            node = self.stack.pop()
            # after undoing an optimistic shift (through pop) we need to revert
            # back to the state before the shift (which can be found on the top
            # of the stack after the "pop"
            if isinstance(node.symbol, FinishSymbol):
                # if we reached the end of the stack, reset to state 0 and push
                # FinishSymbol pack onto the stack
                self.current_state = 0
                self.stack.append(node)
                return
            else:
                logging.debug("right breakdown else: set state to %s", self.stack[-1].state)
                self.current_state = self.stack[-1].state
        if not self.process_any(node):
            self.shift(node, rb=True) # pushes previously popped terminal back on stack

    def shift(self, la, element=None, rb=False):
        if not element:
            lookup_symbol = self.get_lookup(la)
            element = self.syntaxtable.lookup(self.current_state, lookup_symbol)
        logging.debug("\x1b[32m" + "%sShift(%s)" + "\x1b[0m" + ": %s -> %s", "rb" if rb else "", self.current_state, la, element)
        la.state = element.action
        self.stack.append(la)
        self.current_state = la.state

        if not la.lookup == "<ws>":
            # last_shift_state is used to predict next symbol
            # whitespace destroys correct behaviour
            self.last_shift_state = element.action

        if self.indentation_based and not rb:
            return self.parse_whitespace(la)

    def process_any(self, la):
        result, symbol = self.parse_anysymbol()
        if result:
            # ANYSYMBOL with finishing symbol
            r_finish = self.syntaxtable.lookup(result.action, self.get_lookup(la))
            if isinstance(r_finish, Shift):
                self.end_any(la, result)
                return False
            # ANY without finishing symbol
            elif symbol.name == "@ncr" and (la.lookup == "<return>" or la.symbol == IndentationTerminal("NEWLINE") or isinstance(la, EOS)):
                self.end_any(la, result, symbol.name)
                return False
            else:
                self.push_any(la)
                return True

    def push_any(self, la):
        logging.debug("AnySymbol: push %s" % (la))
        la.state = self.current_state # this node is now part of this comment state (needed to unvalidating)
        self.stack.append(la)
        self.anycounter += 1

    def end_any(self, la, result, mode="@"):
        logging.debug("AnySymbol: end %s (%s)" % (la, mode))
        self.current_state = result.action # switch to state after ANY and continue parsing normally
        logging.debug("AnySymbol: set state to %s", self.current_state)
        if mode == "@ncr":
            self.anycount[self.stack[-1]] = self.anycounter # store amount of pushed elements on last symbol
        else:
            self.anycount[la] = self.anycounter # store amount of pushed elements on last symbol
        self.anycounter = 0

    def pop_lookahead(self, la):
        org = la
        while(la.right_sibling() is None):
            la = la.parent
        logging.debug("pop_lookahead(%s): %s", org.symbol, la.right_sibling().symbol)
        return la.right_sibling()

    def shiftable(self, la):
        if self.syntaxtable.lookup(self.current_state, la.symbol):
            return True
        return False

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

    def get_ast(self):
        bos = Node(Terminal("bos"), 0, [])
        eos = Node(FinishSymbol(), 0, [])
        root = Node(Nonterminal("Root"), 0, [bos, self.ast_stack[0], eos])
        return AST(root)

    def get_next_possible_symbols(self, state_id):
        l = set()
        for (state, symbol) in self.syntaxtable.table.keys():
            if state == state_id:
                l.add(symbol)
        return l

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

    def load_status(self, version):
        try:
            self.last_status = self.status_by_version[version]
        except KeyError:
            logging.warning("Could not find status for version %s", version)
        try:
            self.error_node = self.errornode_by_version[version]
        except KeyError:
            logging.warning("Could not find errornode for version %s", version)

    def save_status(self, version):
        self.status_by_version[version] = self.last_status
        self.errornode_by_version[version] = self.error_node
