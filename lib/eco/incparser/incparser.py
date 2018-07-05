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

from grammar_parser.gparser import Parser, Nonterminal, Terminal, Epsilon, IndentationTerminal, MagicTerminal
from syntaxtable import SyntaxTable, FinishSymbol, Reduce, Accept, Shift
from stategraph import StateGraph
from constants import LR0, LALR
from astree import AST, TextNode, BOS, EOS
from ip_plugins.plugin import PluginManager
from error_recovery import RecoveryManager
from autolboxdetector import NewAutoLboxDetector

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
        self.whitespaces = whitespaces
        self.status_by_version = {}
        self.errornodes_by_version = {}
        self.indentation_based = False

        self.previous_version = None
        self.prev_version = 0

        self.ooc = None

        self.autolboxes = None
        self.autodetector = None
        self.option_autolbox_find = False

    def is_valid_symbol(self, state, token):
        return self.syntaxtable.lookup(state, token) is not None

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

    def setup_autolbox(self, lang):
        self.autodetector = NewAutoLboxDetector(self)
        self.autodetector.preload(lang)

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
        logging.debug("============ NEW %s PARSE ================= ", "OOC" if self.ooc else "INCREMENTAL")
        logging.debug("= starting in state %s ", state)
        self.validating = False
        self.reused_nodes = set()
        self.current_state = state
        self.previous_version.parent.isolated = None
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
        self.error_pres = []
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
                logging.debug("ooc %s %s", self.ooc, id(self.ooc))
                logging.debug("la %s", la)
                logging.debug("cs %s", self.current_state)
                if la is self.ooc[0]:
                    if isinstance(la.symbol, Nonterminal):
                        # if OOC is Nonterminal, use first terminal to apply
                        # reductions
                        first_term = la.find_first_terminal(self.prev_version)
                        lookup = self.get_lookup(first_term)
                    else:
                        lookup = self.get_lookup(la)
                    while True:
                        # OOC is complete if we reached the expected state and
                        # there are no more reductions left to do
                        if self.current_state == self.ooc[2] and len(self.stack) == 2:
                            logging.debug("======= OOC parse successfull =========")
                            self.last_status = True
                            return True
                        # Otherwise apply more reductions to reach the wanted
                        # state or an error occurs
                        element = self.syntaxtable.lookup(self.current_state, lookup)
                        if not isinstance(element, Reduce):
                            logging.debug("No more reductions")
                            break
                        else:
                            self.reduce(element)
                    logging.debug("======= OOC parse failed =========")
                    self.last_status = False
                    return False

            if isinstance(la.symbol, Terminal) or isinstance(la.symbol, FinishSymbol) or la.symbol == Epsilon():
                    lookup_symbol = self.get_lookup(la)
                    result = self.parse_terminal(la, lookup_symbol)
                    if result == "Accept":
                        logging.debug("============ INCREMENTAL PARSE END (ACCEPT) ================= ")
                        # With error recovery we can end up in the accepting
                        # state despite errors occuring during the parse.
                        if len(self.error_nodes) == 0:
                            self.last_status = True
                            la.autobox = None
                            return True
                        self.last_status = False
                        return False
                    elif result == "Error":
                        logging.debug("============ INCREMENTAL PARSE END (ERROR) ================= ")
                        self.last_status = False
                        return False
                    elif result != None:
                        la = result

            else: # Nonterminal
                if la.has_changes() or needs_reparse or la.has_errors() or self.iso_context_changed(la):
                    la = self.left_breakdown(la)
                else:
                    if USE_OPT:
                        goto = self.syntaxtable.lookup(self.current_state, la.symbol)
                        # Only opt-shift if the nonterminal has children to
                        # avoid a bug in the retainability algorithm. See
                        # test/test_eco.py::Test_RetainSubtree::test_bug1
                        if goto and la.children: # can we shift this Nonterminal in the current state?
                            logging.debug("OPTShift: %s in state %s -> %s", la.symbol, self.current_state, goto)
                            follow_id = goto.action
                            self.stack.append(la)
                            la.deleted = False
                            la.state = follow_id #XXX this fixed goto error (I should think about storing the states on the stack instead of inside the elements)
                            la.exists = True
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
                                logging.debug("OPT Reduce: %s", element)
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

    def parse_terminal(self, la, lookup_symbol):
        """Lookup the current lookahead symbol in the syntax table and apply the received action."""
        element = None
        if la.deleted:
            # Nodes are no longer removed from the tree. Instead "deleted" nodes
            # are skipped during parsing so they won't end up in the next parse
            # tree. This allows to revert deleted nodes on undo.
            la.exists = False
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
            self.previous_version.parent.changed = True
            logging.debug("loopcount: %s", self.loopcount)
            logging.debug ("\x1b[32mAccept\x1b[0m")
            return "Accept"
        elif isinstance(element, Shift):
            self.validating = False
            self.shift(la, element)
            la.local_error = la.nested_errors = False
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
                if self.autodetector and self.option_autolbox_find and self.autodetector.detect_lbox(la):
                    pass # we can immediately apply the language box here in the future
                self.error_nodes.append(la)
                if self.rm.recover(la):
                    # recovered, continue parsing
                    self.refine(self.rm.iso_node, self.rm.iso_offset, self.rm.error_offset)
                    self.current_state = self.rm.new_state
                    self.rm.iso_node.isolated = la
                    self.rm.iso_node.deleted = False
                    self.stack.append(self.rm.iso_node)
                    logging.debug("Recovered. Continue after %s", self.rm.iso_node)
                    return self.pop_lookahead(self.rm.iso_node)
                logging.debug("Couldn't find a subtree to recover. Recovering the whole tree.")
                logging.debug("\x1b[31mError\x1b[0m: %s %s %s", la, la.prev_term, la.next_term)
                logging.debug("loopcount: %s", self.loopcount)

                error_offset = self.rm.offset(la, self.rm.previous_version)
                iso_node = self.previous_version.parent
                self.refine(iso_node, 0, error_offset)
                iso_node.isolated = la
                return "Error"

    def get_lookup(self, la):
        """Get the lookup symbol of a node. If no such lookup symbol exists use the nodes symbol instead."""
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

    def discard_changes(self, node):
        if node.has_changes():
            node.load(self.prev_version)
            node.exists = True
            if node.nested_changes:
                node.nested_errors = True
            if node.changed:
                node.local_error = True
                self.compute_presention(node)

    def compute_presention(self, node):
        if type(node.symbol) is not Terminal:
            # Don't show errors for indentation tokens
            return
        try:
            prev_name = node.get_attr("symbol.name", self.reference_version)
        except AttributeError:
            return
        if prev_name != node.symbol.name:
            self.error_pres.append((node, prev_name))

    def refine(self, node, offset, error_offset):
        # for all children that come after the detection offset, we need
        # to analyse them using the normal incparser
        logging.debug("    Refine %s Offset: %s Error Offset: %s", node, offset, error_offset)
        retain_set = set()
        self.pass1(node, offset, error_offset, retain_set, offset)
        node.load(self.prev_version)
        node.exists = True
        node.set_children(node.children) # reset sibling pointers
        node.local_error = node.nested_errors = False
        self.pass2(node, offset, error_offset, retain_set)

    def pass1 (self, node, offset, error_offset, retain_set, poffset):
        if offset > error_offset:
            # We don't have to check any other children
            # that come after the error node
            return
        for child in node.get_attr("children", self.prev_version):
            if offset + child.textlength() <= error_offset:
                self.find_retainable_subtrees(child, retain_set, poffset)
            else:
                self.pass1(child, offset, error_offset, retain_set, poffset)
            offset += child.textlength()
            poffset += child.textlength(self.prev_version) # calculate the current position on the fly

    def pass2(self, node, offset, error_offset, retain_set):
        for c in node.children:
            if self.ooc and c is self.ooc[0]:
                logging.debug("    Don't refine TempEOS nodes")
                return
            if offset > error_offset:
                # XXX check if following terminal requires analysis
                self.out_of_context_analysis(c)
            elif offset + c.textlength() <= error_offset:
                self.retain_or_discard(c, node, retain_set)
            else:
                assert offset <= error_offset
                assert offset + c.textlength() > error_offset
                self.discard_changes(c)
                self.pass2(c, offset, error_offset, retain_set)
            offset += c.textlength()

    def find_retainable_subtrees(self, node, retain_set, poffset):
        if self.is_retainable_subtree(node, poffset):
            retain_set.add(node)
            return
        for child in node.get_attr("children", self.prev_version):
            self.find_retainable_subtrees(child, retain_set, poffset)
            poffset += child.textlength(self.prev_version)

    def is_retainable_subtree(self, node, poffset):
        if type(node.symbol) is Terminal:
            # Don't retain terminals so we can be show them as errors
            return False
        if node.new:
            return False

        if not node.exists:
            return False

        if not node.nested_changes:
            # Even though retaining an unchanged node doesn't revert any changes
            # it avoids having to inspect the children
            return True

        # This is equivalent to Wagner's `same_pos` function.
        if node.textlength(self.prev_version) == node.textlength() and \
                poffset == node.position:
            return True

        return False


    def retain_or_discard(self, node, parent, retain_set):
        if node in retain_set:
            retain_set.remove(node)
            logging.debug("    Retaining %s (%s). Set parent to %s (%s) (%s)", node, id(node), parent, id(parent), "SAME" if parent is node.parent else "DIFF")
            # Might have been assigned to a different parent in current version
            # that was removed during refinement. This makes sure this node is
            # assigned to the right parent. See test_eco.py:Test_RetainSubtree
            if node.parent is not parent:
                node.parent.mark_changed()
                node.parent = parent
            # Also need to update siblings as they might have been changed by
            # the parser before nodes parent was reset
            node.update_siblings()
            if node.has_changes():
                parent.mark_changed()
            return
        self.discard_changes(node)
        for c in node.children:
            self.retain_or_discard(c, node, retain_set)
        node.set_children(node.children) # reset links between children

    def out_of_context_analysis(self, node):
        logging.debug("    Attempting out of context analysis on %s (%s)", node, id(node))

        if not node.children:
            logging.debug("    Failed: Node has no children")
            self.isolate(node)
            return

        if not node.has_changes():
            if node.has_errors():
                self.find_nested_error(node)
            logging.debug("    Failed: Node has no changes")
            return

        # check if subtree is followed by terminal requiring analysis
        # (includes deleted terminals)
        follow = self.next_terminal(node)
        if follow.deleted: # or follow.changed:
            # XXX This should also include `follow.changed`, but since currently nodes
            # are marked as changed even if just their siblings or next_terms
            # are updated, this would fail for most out-of-context analyses
            logging.debug("   Failed: Surrounding context has changed")
            self.isolate(node)
            return

        temp_parser = IncParser()
        temp_parser.syntaxtable = self.syntaxtable
        temp_parser.prev_version = self.prev_version
        temp_parser.reference_version = self.reference_version
        temp_parser.lang = self.lang

        oldname = node.symbol.name
        oldleft = node.left
        oldright = node.right
        oldparent = node.parent

        saved_left = node.get_attr("left", self.prev_version)
        saved_right = node.get_attr("right", self.prev_version)
        saved_parent = node.get_attr("parent", self.prev_version)

        temp_bos = BOS(Terminal(""), 0, [])
        temp_eos = self.pop_lookahead(node)
        while isinstance(temp_eos.symbol, Terminal) and temp_eos.deleted:
            # We can't use a deleted node as a temporary EOS since the deleted
            # note can pass the temp EOS reduction check but is then immediately
            # skipped by parse_terminal. This causes the parser to continue
            # parsing past the temp_eos resulting in faulty sub parse trees.
            temp_eos = self.pop_lookahead(temp_eos)

        eos_parent = temp_eos.parent
        eos_left = temp_eos.left
        eos_right = temp_eos.right
        # During out-of-context analysis we need to calculate offsets of
        # isolation nodes. Without this change we would calculate the offset
        # within the original parse tree and not the offset within the temporary
        # parse tree
        node.log[("left", self.prev_version)] = temp_bos
        node.log[("right", self.prev_version)] = temp_eos

        logging.debug("    TempEOS: %s", temp_eos)
        temp_root = Node(Nonterminal("TempRoot"), 0, [temp_bos, node, temp_eos])
        node.log[("parent", self.prev_version)] = temp_root
        temp_root.save(self.prev_version)
        temp_bos.next_term = node
        temp_bos.state = oldleft.state
        temp_bos.save(node.version)
        temp_parser.previous_version = AST(temp_root)
        temp_parser.ooc = (temp_eos, node, node.state)
        temp_parser.root = temp_root
        dummy_stack_eos = EOS(Terminal(""), oldleft.state, [])
        try:
            temp_parser.inc_parse(state=oldleft.state, stack=[dummy_stack_eos])
        except IndexError:
            temp_parser.last_status = False

        temp_eos.parent = eos_parent
        temp_eos.left = eos_left
        temp_eos.right = eos_right

        # pass on errors to the outer parser
        self.error_nodes.extend(temp_parser.error_nodes)
        self.error_pres.extend(temp_parser.error_pres)
        if temp_parser.last_status == False:
              # isolate
              logging.debug("OOC analysis of %s failed. Error on %s.", node, temp_parser.error_nodes)
              node.log[("left", self.prev_version)] = saved_left
              node.log[("right", self.prev_version)] = saved_right
              node.log[("parent", self.prev_version)] = saved_parent
              self.isolate(node) # revert changes done during OOC
              if temp_parser.previous_version.parent.isolated:
                  # if during OOC parsing error recovery isolated the entire
                  # tree (due to not finding an appropriate isolation node) we
                  # need to move the isolation reference over to the actual node
                  # being reparsed as the root is thrown away after this
                  node.isolated = temp_parser.previous_version.parent.isolated
              return

        newnode = temp_parser.stack[-1]

        if newnode.symbol.name != oldname:
            logging.debug("OOC analysis resulted in different symbol: %s", newnode.symbol.name)
            # node is not the same: revert all changes!
            node.log[("left", self.prev_version)] = saved_left
            node.log[("right", self.prev_version)] = saved_right
            node.log[("parent", self.prev_version)] = saved_parent
            self.isolate(node)
            return

        if newnode is not node:
            node.log[("left", self.prev_version)] = saved_left
            node.log[("right", self.prev_version)] = saved_right
            node.log[("parent", self.prev_version)] = saved_parent
            logging.debug("OOC analysis resulted in different node but same symbol: %s", newnode.symbol.name)
            assert len(temp_parser.stack) == 2 # should only contain [EOS, node]
            i = oldparent.children.index(node)
            oldparent.children[i] = newnode
            newnode.parent = oldparent
            newnode.left = oldleft
            if oldleft:
                oldleft.right = newnode
                oldleft.mark_changed()
            newnode.right = oldright
            if oldright:
                oldright.left = newnode
                oldright.mark_changed()
            newnode.mark_changed() # why did I remove this?
            return

        logging.debug("Subtree resulted in the same parse as before %s %s", newnode, node)
        assert len(temp_parser.stack) == 2 # should only contain [EOS, node]
        node.parent = oldparent
        node.left = oldleft
        node.right = oldright
        node.log[("left", self.prev_version)] = saved_left
        node.log[("right", self.prev_version)] = saved_right
        node.log[("parent", self.prev_version)] = saved_parent

    def reduce(self, element):
        """Reduce elements on the stack to a non-terminal."""

        children = []
        i = 0
        while i < element.amount():
            c = self.stack.pop()
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
        has_errors = False
        for c in children:
            if c.has_errors() or c.isolated:
                has_errors = True
            if not c.new:
                # just marking changed is not enough. If we encounter an error
                # during reduction the path from the root down to this node is
                # incomplete and thus can't be reverted/isolate properly
                c.mark_changed()

        reuse_parent = self.ambig_reuse_check(element.action.left, children)
        if not self.needs_reparse and reuse_parent:
            logging.debug("   Reusing parent: %s (%s)", reuse_parent, id(reuse_parent))
            new_node = reuse_parent
            new_node.changed = False
            new_node.deleted = False
            new_node.isolated = None
            new_node.local_error = False
            new_node.set_children(children)
            new_node.state = goto.action # XXX need to save state using hisotry service
            new_node.mark_changed()
        else:
            new_node = Node(element.action.left.copy(), goto.action, children)
            logging.debug("   No reuse parent. Make new %s (%s)", new_node, id(new_node))
        new_node.nested_errors = has_errors
        new_node.calc_textlength()
        new_node.position = self.stack[-1].position + self.stack[-1].textlen
        logging.debug("   Add %s to stack and goto state %s", new_node.symbol, new_node.state)
        self.stack.append(new_node)
        new_node.exists = True
        self.current_state = new_node.state # = goto.action
        logging.debug("Reduce: set state to %s (%s)", self.current_state, new_node.symbol)
        if getattr(element.action.annotation, "interpret", None):
            # eco grammar annotations
            self.interpret_annotation(new_node, element.action)

    def ambig_reuse_check(self, prod, children):
        if children:
            for c in children:
                if c.parent and not c.new: # not a new node
                    old_parent = c.get_attr('parent', self.prev_version)
                    if old_parent.symbol == prod and old_parent not in self.reused_nodes:
                        if len(old_parent.get_attr("children", self.prev_version)) > 1:
                            # if node is the only child, reuse is unambiguous so
                            # we don't need to remember we've reused this node
                            # (which allows us to reuse it after error recovery)
                            self.reused_nodes.add(old_parent)
                        return old_parent
        return None

    def top_down_reuse(self):
        main = self.previous_version.parent
        self.top_down_traversal(main)

    def top_down_traversal(self, node):
        if node.changed and not node.new:
            self.reuse_isomorphic_structure(node)
        elif node.nested_changes or node.new:
            for c in node.children:
                self.top_down_traversal(c)

    def reuse_isomorphic_structure(self, node):
        for i in range(len(node.children)):
            current_child = node.children[i]
            try:
                previous_child = node.get_attr("children", self.prev_version)[i]
            except IndexError:
                self.top_down_traversal(current_child)
                continue
            if current_child.new and not previous_child.exists and \
                current_child.symbol.name == previous_child.get_attr("symbol.name", self.prev_version):
                    self.replace_child(node, i, current_child, previous_child)
                    self.reuse_isomorphic_structure(previous_child)
            elif current_child.nested_changes or current_child.new:
                self.top_down_traversal(current_child)

    def replace_child(self, parent, i, current, previous):
        if isinstance(current.symbol, Terminal):
            # Newly inserted terminals have already been saved to the history
            # (previous_version) before we reach this. Reusing terminals
            # here would thus give no memory benefit as the old terminal can't
            # be garbage collected
            return
        parent.children[i] = previous
        previous.parent = parent # in case previous was moved before being deleted
        previous.children = list(current.children)
        for c in current.children:
            c.parent = previous
        previous.symbol.name = current.symbol.name
        previous.changed = False
        previous.deleted = False
        previous.isolated = False
        previous.local_error = False
        previous.state = current.state
        previous.mark_changed()
        previous.calc_textlength()
        previous.position = current.position
        previous.exists = True
        previous.nested_errors = current.nested_errors
        previous.right = current.right
        previous.left = current.left
        previous.alternate = current.alternate
        if previous.right:
            previous.right.left = previous
        if previous.left:
            previous.left.right = previous

        if isinstance(current.symbol, Terminal):
            previous.lookup = current.lookup
            previous.prev_term = current.prev_term
            previous.next_term = current.next_term
            previous.prev_term.next_term = previous
            previous.next_term.prev_term = previous

    def interpret_annotation(self, node, production):
        annotation = production.annotation
        if annotation:
            astnode = annotation.interpret(node)
            if not self.is_reusable_astnode(node.alternate, astnode):
                node.alternate = astnode

    def is_reusable_astnode(self, old, new):
        from grammar_parser.bootstrap import AstNode
        if type(old) is not AstNode or type(new) is not AstNode:
            return False
        if old.name != new.name:
            return False
        for key in old.children:
            if old.children.get(key) is not new.children.get(key):
                return False
        return True

    def left_breakdown(self, la):
        la.exists = False
        if len(la.children) > 0:
            return la.children[0]
        else:
            return self.pop_lookahead(la)

    def right_breakdown(self):
        node = self.stack.pop() # optimistically shifted Nonterminal
        node.exists = False
        # after the breakdown, we need to properly shift the left over terminal
        # using the (correct) current state from before the optimistic shift of
        # it's parent tree
        self.current_state = self.stack[-1].state
        logging.debug("right breakdown(%s): set state to %s", node.symbol.name, self.current_state)
        while(isinstance(node.symbol, Nonterminal)):
            # Right_breakdown reverts wrong optimistic shifts including
            # subsequent reductions. These reductions may contain nodes that
            # have been reused. Reverting the reduction also means we need to
            # undo the reusing of that node to free it up for future reusing.
            self.reused_nodes.discard(node)
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
                node.exists = True
                self.stack.append(node)
                self.current_state = node.state
                return
            for c in node.children:
                self.shift(c, rb=True)
            node = self.stack.pop()
            node.exists = False
            # after undoing an optimistic shift (through pop) we need to revert
            # back to the state before the shift (which can be found on the top
            # of the stack after the "pop"
            if isinstance(node.symbol, FinishSymbol):
                # if we reached the end of the stack, reset to state 0 and push
                # FinishSymbol pack onto the stack
                self.current_state = 0
                self.stack.append(node)
                node.exists = True
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
        la.exists = True
        la.position = self.stack[-1].position + self.stack[-1].textlen
        la.autobox = None
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
        self.previous_version = None
        self.init_ast()

    def load_status(self, version):
        try:
            self.last_status = self.status_by_version[version]
        except KeyError:
            logging.warning("Could not find status for version %s", version)
        try:
            self.error_nodes = list(self.errornodes_by_version[version])
        except KeyError:
            logging.warning("Could not find errornodes for version %s", version)

    def save_status(self, version):
        self.status_by_version[version] = self.last_status
        self.errornodes_by_version[version] = list(self.error_nodes)

    def find_nested_error(self, node):
        """Find errors within isolated subtrees."""
        self.compute_presention(node)
        if node.isolated:
            self.error_nodes.append(node.isolated)
        elif not node.nested_errors:
            return
        for c in node.children:
            self.find_nested_error(c)

    def iso_context_changed(self, node):
        # Currently catches more cases than neccessary. Could be made more
        # accurate by finding the next terminal reachable from node (including
        # deleted ones)
        if not node.isolated:
            return False
        la = self.pop_lookahead(node)
        return la.has_changes()

    def next_terminal(self, node):
        n = self.pop_lookahead(node)
        while type(n.symbol) is Nonterminal:
            children = n.get_attr("children", self.prev_version)
            if len(children) > 0:
                n = children[0]
            else:
                n = self.pop_lookahead(n)
        return n

    def has_autolbox(self, node):
        result = []
        if self.autolboxes:
            for (s, e, l) in self.autolboxes:
                if node is s:
                    result.append((s, e, l))
        return result

    def has_errors(self, root):
        start = root.children[1]
        if start.nested_errors:
            return True
        return False
