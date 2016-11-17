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

from grammar_parser.gparser import Parser, Nonterminal, Terminal, Epsilon, IndentationTerminal
from syntaxtable import SyntaxTable, FinishSymbol, Reduce, Accept, Shift
from stategraph import StateGraph
from constants import LR0, LALR
from astree import AST, TextNode, BOS, EOS
from ip_plugins.plugin import PluginManager
from error_recovery import RecoveryManager

import logging

Node = TextNode


def printc(text, color):
    print("\033[%sm%s\033[0m" % (color, text))

def printline(start):
    start = start.next_term
    l = []
    while True:
        l.append(start.symbol.name)
        if start.lookup == "<return>" or isinstance(start, EOS):
            break
        start = start.next_term
    return "".join(l)

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
        self.last_shift_state = 0
        self.validating = False
        self.last_status = False
        self.error_node = None
        self.whitespaces = whitespaces
        self.status_by_version = {}
        self.errornode_by_version = {}
        self.indentation_based = False

        self.previous_version = None
        self.prev_version = 0

        self.ooc = None


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

    def inc_parse(self, line_indents=[], needs_reparse=False, state=0, stack = []):
        logging.debug("============ NEW INCREMENTAL PARSE ================= ")
        logging.debug("= starting in state %s ", state)
        self.validating = False
        self.error_node = None
        self.reused_nodes = set()
        self.current_state = state
        bos = self.previous_version.parent.children[0]
        eos = self.previous_version.parent.children[-1]
        if not stack:
            self.stack = [eos]
        else:
            self.stack = stack
        eos.state = 0
        self.loopcount = 0
        self.needs_reparse = needs_reparse
        self.error_nodes = []
        if self.ooc:
            rmroot = self.ooc[1]
        else:
            rmroot = self.previous_version.parent
        self.rm = RecoveryManager(self.prev_version, rmroot, self.stack, self.syntaxtable)

        USE_OPT = True


        la = self.pop_lookahead(bos)
        while(True):
            logging.debug("\x1b[35mProcessing\x1b[0m %s %s %s %s", la, la.changed, id(la), la.indent)
            self.loopcount += 1



            # Abort condition for out-of-context analysis. If we reached the state of the
            # node that is being analyses and the lookahead matches the nodes
            # lookahead from the previous parse, we are done
            if self.ooc:
                logging.debug("ooc %s", self.ooc)
                logging.debug("la %s", la)
                logging.debug("cs %s", self.current_state)
                if la is self.ooc[0] and self.current_state == self.ooc[1].state:
                    logging.debug("HELAU")
                    self.last_status = True
                    return True

            if isinstance(la.symbol, Terminal) or isinstance(la.symbol, FinishSymbol) or la.symbol == Epsilon():
                if la.changed and False: #XXX not needed once we introduce errors
                    assert False # with prelexing you should never end up here!
                else:
                    lookup_symbol = self.get_lookup(la)
                    result = self.parse_terminal(la, lookup_symbol)
                    if result == "Accept":
                        # With error recovery we can end up in the accepting
                        # state despite errors occuring during the parse.
                        if len(self.error_nodes) == 0:
                            self.last_status = True
                            return True
                        self.last_status = False
                        return False
                    elif result == "Error":
                        self.last_status = False
                        return False
                    elif result != None:
                        la = result

            else: # Nonterminal
                #iso_and_changed = la.isolated and self.surrounding_context_changed(la)
                if la.has_changes() or needs_reparse or la.has_errors():# or iso_and_changed:
                    #la.changed = False # as all nonterminals that have changed are being rebuild, there is no need to change this flag (this also solves problems with comments)
                    la = self.left_breakdown(la)
                else:
                    if USE_OPT:
                        goto = self.syntaxtable.lookup(self.current_state, la.symbol)
                        if goto: # can we shift this Nonterminal in the current state?
                            logging.debug("OPTShift: %s in state %s -> %s", la.symbol, self.current_state, goto)
                            follow_id = goto.action
                            self.stack.append(la)
                            la.state = follow_id #XXX this fixed goto error (I should think about storing the states on the stack instead of inside the elements)
                            self.current_state = follow_id
                            logging.debug("USE_OPT: set state to %s", self.current_state)
                            if la.isolated:
                                # When skipping previously isolated subtrees,
                                # traverse their children to find the error
                                # nodes and report them back to the editor.
                                self.find_nested_error(la)
                            la = self.pop_lookahead(la)
                            self.validating = True
                            continue
                        else:
                            #XXX can be made faster by providing more information in syntax tables
                            first_term = la.find_first_terminal(self.prev_version)

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

    def parse_terminal(self, la, lookup_symbol):
        element = None
        if la.deleted:
            # Nodes are no longer removed from the tree. Instead "deleted" nodes
            # are skipped during parsing so they won't end up in the next parse
            # tree. This allows to revert deleted nodes on undo.
            la = self.pop_lookahead(la)
            return la
        # XXX if temporary EOS symbol, check lookup
        #        if accept: return accept
        #        if nothing: try normal EOS instead (e.g. to reduce things)
        
        if isinstance(la, EOS):
            # This is needed so we can finish single line comments at the end of
            # the file
            element = self.syntaxtable.lookup(self.current_state, Terminal("<eos>"))
            if isinstance(element, Shift):
                self.current_state = element.action
                return la
        if element is None:
            element = self.syntaxtable.lookup(self.current_state, lookup_symbol)
        logging.debug("\x1b[34mparse_terminal\x1b[0m: %s in %s -> %s", lookup_symbol, self.current_state, element)
        if isinstance(element, Accept):
            #XXX change parse so that stack is [bos, startsymbol, eos]
            bos = self.previous_version.parent.children[0]
            eos = self.previous_version.parent.children[-1]

            bos.changed = False
            eos.changed = False
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
            return la #self.parse_terminal(la, lookup_symbol)
        elif element is None:
            if self.validating:
                logging.debug("Was validating: Right breakdown and return to normal")
                logging.debug("Before breakdown: %s", self.stack[-1])
                self.right_breakdown()
                logging.debug("After breakdown: %s", self.stack[-1])
                self.validating = False
            else:
                self.error_nodes.append(la)
                self.error_node = la
                if False:# and self.rm.recover(la):
                    # recovered, continue parsing
                    self.refine(self.rm.iso_node, self.rm.iso_offset, self.rm.error_offset)
                    self.current_state = self.rm.new_state
                    self.rm.iso_node.isolated = True
                    self.stack.append(self.rm.iso_node)
                    logging.debug("Recovered. Continue after %s", self.rm.iso_node)
                    return self.pop_lookahead(self.rm.iso_node)
                # Couldn't find a subtree to recover. Recovering the whole tree.
                logging.debug ("\x1b[31mError\x1b[0m: %s %s %s", la, la.prev_term, la.next_term)
                logging.debug("loopcount: %s", self.loopcount)
                self.isolate(self.previous_version.parent) #XXX isolate middle child instead?
                return "Error"

    def get_lookup(self, la):
        if la.lookup != "":
            lookup_symbol = Terminal(la.lookup)
        else:
            lookup_symbol = la.symbol
        if isinstance(lookup_symbol, IndentationTerminal):
            #XXX hack: change parsing table to accept IndentationTerminals
            lookup_symbol = Terminal(lookup_symbol.name)
        return lookup_symbol

    def isolate(self, node):
        if node.has_changes():# or node.has_errors():
            node.load(self.prev_version)
            if node.nested_changes:
                node.nested_errors = True
            if node.changed:
                node.local_error = True
            for c in node.children:
                self.isolate(c)

    def refine(self, node, offset, error_offset):
        # for all children that come after the detection offset, we need
        # to analyse them using the normal incparser
        print("Refine", node, offset, error_offset)
        node.load(self.prev_version)
        node.local_error = node.nested_errors = False
        for c in node.children:
            if offset > error_offset:
                self.out_of_context_analysis(c)
            else:
                self.isolate(c)
            offset += c.textlength()
            # XXX don't undo valid changes in nodes that don't contain the
            # error node. needs retainablity check

    def out_of_context_analysis(self, node):
        logging.debug("Attempting out of context analysis on %s", node)
        print("Attempting out of context analysis on %s", node)

        if self.indentation_based:
            # XXX update succeeeding whitespace in outer tree
            #     update indent attr of isolated tree so remaining outer tree
            #     can be parsed correctly
            logging.debug("    Failed: OOC not working with indentation atm")
            return

        if not node.children:
            logging.debug("    Failed: Node has no children")
            return

        if not node.has_changes():
            logging.debug("    Failed: Node has no changes")
            return

        #XXX lookahead can't have changes either

        temp_parser = IncParser()
        temp_parser.syntaxtable = self.syntaxtable
        temp_parser.prev_version = self.prev_version

        oldname = node.symbol.name
        oldleft = node.left
        oldright = node.right
        oldparent = node.parent

        temp_bos = BOS(Terminal(""), 0, [])
        temp_eos = self.pop_lookahead(node)

        eos_parent = temp_eos.parent
        eos_left = temp_eos.left
        eos_right = temp_eos.right

        logging.debug("    TempEOS: %s", temp_eos)
        temp_root = Node(Nonterminal("TempRoot"), 0, [temp_bos, node, temp_eos])
        temp_bos.next_term = node
        temp_bos.state = oldleft.state
        temp_bos.save(node.version)
        temp_parser.previous_version = AST(temp_root)
        temp_parser.ooc = (temp_eos, node)
        dummy_stack_eos = EOS(Terminal(""), oldleft.state, [])
        try:
            temp_parser.inc_parse(state=oldleft.state, stack=[dummy_stack_eos])
        except IndexError:
            temp_parser.last_status == False

        temp_eos.parent = eos_parent
        temp_eos.left = eos_left
        temp_eos.right = eos_right

        if temp_parser.last_status == False:
              # isolate
              logging.debug("OOC analysis of %s failed", node)
              self.isolate(node) # XXX actually need to call refine here
              node.isolated = True
              return

        newnode = temp_parser.stack[-1]

        if newnode.symbol.name != oldname:
            logging.debug("OOC analysis resulted in different symbol")
            # not is not the same: revert all changes!
            self.isolate(node)
            return

        if newnode is not node:
            logging.debug("OOC analysis resulted in different node but same symbol")
            i = oldparent.children.index(node)
            oldparent.children[i] = newnode
            newnode.parent = oldparent
            newnode.left = oldleft
            if oldleft:
                oldleft.right = newnode
            newnode.right = oldright
            if oldright:
                oldright.left = newnode
            newnode.mark_changed()
            return

        logging.debug("Subtree resulted in the same parse as before", newnode, node)
        node.parent = oldparent
        node.left = oldleft
        node.right = oldright

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
            i += 1

        logging.debug("   Element on stack: %s(%s)", self.stack[-1].symbol, self.stack[-1].state)
        self.current_state = self.stack[-1].state #XXX don't store on nodes, but on stack
        logging.debug("   Reduce: set state to %s (%s)", self.current_state, self.stack[-1].symbol)

        goto = self.syntaxtable.lookup(self.current_state, element.action.left)
        if goto is None:
            raise Exception("Reduction error on %s in state %s: goto is None" % (element, self.current_state))
        assert goto != None

        # save childrens parents state
        for c in children:
            c.local_error = False
            c.nested_errors = False
            if not c.new:
                # just marking changed is not enough. If we encounter an error
                # during reduction the path from the root down to this node is
                # incomplete and thus can't be reverted/isolate properly
                c.mark_changed()

        reuse_parent = self.ambig_reuse_check(element.action.left, children)
        if not self.needs_reparse and reuse_parent:
            new_node = reuse_parent
            new_node.changed = False
            new_node.isolated = False
            new_node.set_children(children)
            new_node.state = goto.action # XXX need to save state using hisotry service
            new_node.mark_changed()
        else:
            new_node = Node(element.action.left.copy(), goto.action, children)
        new_node.refresh_textlen()
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

    def ambig_reuse_check(self, prod, children):
        if children:
            for c in children:
                if c.parent and not c.new: # not a new node
                    old_parent = c.get_attr('parent', self.prev_version)
                    if old_parent.symbol == prod and old_parent not in self.reused_nodes:
                        self.reused_nodes.add(old_parent)
                        return old_parent
        return None

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
                # insert tiered nodes at right position
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
            # This bit of code is necessary to avoid a bug that occurs with the
            # default Wagner implementation if we isolate a subtree and
            # optimistically shift an empty Nonterminal, and then run into an
            # error. The verifying parts of the incremental parser then try to
            # undo wrong optimistic shifts by breaking them down to their most
            # right terminal. Since the optimistic shift happened on an empty
            # Nonterminal, the algorithm tries to break down the isolated
            # subtree to the left of it. Since this subtree contains an error in
            # form of an unshiftable terminal, the algorithm fails and throws an
            # exception. The following code fixes this by ignoring already
            # isolated subtrees.
            if node.isolated:
                self.stack.append(node)
                self.current_state = node.state
                return
            for c in node.children:
                self.shift(c, rb=True)
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


    def pop_lookahead(self, la):
        while(self.right_sibling(la) is None):
            la = la.get_attr("parent", self.prev_version)
        return self.right_sibling(la)

    def right_sibling(self, node):
        return node.right_sibling(self.prev_version)

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

    def find_nested_error(self, node):
        """Given an isolated node, finds the first local error node contained in
        it."""
        for c in node.children:
            # if node.isolated: find nested_error
            if c.nested_errors:
                if self.find_nested_error(c):
                    return c
            if c.local_error:
                self.error_nodes.append(c)
                return c
        return None

    def surrounding_context_changed(self, node):
        # find isolation trees last terminal
        print("surroduning", node)
        while isinstance(node, Nonterminal):
            if node.children:
                node = node.children[-1]
                continue
            else:
                # find left sibling
                while not node.left:
                    node = node.parent
                continue
        # found terminal
        if node.next_term.changed:
            return True
        
        if node.next_term is not node.get_attr("next_term", self.prev_version):
            return True
