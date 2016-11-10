# Copyright (c) 2013--2014 King's College London
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

from grammar_parser.gparser import IndentationTerminal
from incparser.astree import TextNode

class IndentationManager:

    def __init__(self, root):
        self.bos = root.children[0]
        self.eos = root.children[-1]
        self.whitespaces = {}
        self.indentation = {}
        self.changed = False

    def repair(self, node):
        self.changed = False
        """Repair indentation in the line given by node."""
        bol = self.get_line_start(node)
        # if line is not logical, skip ahead to next logical line
        if not self.is_logical_line(bol):
            self.remove_indentation_nodes(bol) # remove previous indentation
            bol = self.next_line(bol)
            if bol is None:
                bol = self.prev_line(self.eos)
            else:
                while True:
                    if bol is None:
                        return False # nothing has been changed
                    if self.is_logical_line(bol):
                        break
                    bol = self.next_line(bol)

        before = self.get_whitespace(bol)
        self.calculate_indentation(bol)
        self.fix_tokens(bol)
        after = self.get_whitespace(bol)

        # update following lines that dependant
        search_threshold = min(before, after)

        current_indent = self.get_indentation(bol)
        current_ws = self.count_whitespace(bol)
        bol = self.next_line(bol)
        while bol is not None:
            ws = self.count_whitespace(bol)
            if ws is None and bol.prev_term and bol.prev_term.symbol.name != "\\":
                bol = self.next_line(bol)
                continue
            if ws > current_ws:
                self.indentation[bol] = current_indent + 1
            if ws == current_ws:
                self.indentation[bol] = current_indent
            if ws < current_ws:
                self.calculate_indentation(bol)

            self.fix_tokens(bol)

            if self.get_whitespace(bol) <= search_threshold:
                # repair everything up to the line that has smaller indentation/whitespace
                # than the changed line
                break

            current_ws = ws
            current_indent = self.get_indentation(bol)
            bol = self.next_line(bol)
        return self.changed

    def repair_full(self):
        self.whitespaces = {}
        self.indentation = {}
        bol = self.bos
        while bol is not None:
            self.calculate_indentation(bol)
            self.fix_tokens(bol)
            bol = self.next_line(bol)

    def calculate_indentation(self, bol):
        """Scans whitespaces in previous lines and sets the indentation of the
        line given by bol accordingly."""
        # calculate indentation by scanning previous lines
        ws = self.count_whitespace(bol)
        temp = bol
        found_smaller = False
        while bol is not self.bos:
            bol = self.prev_line(bol)
            if not self.is_logical_line(bol):
                continue
            prev_ws = self.count_whitespace(bol)
            if ws < prev_ws:
                found_smaller = True
                continue
            if ws == prev_ws:
                self.indentation[temp] = self.get_indentation(bol)
                return
            if ws > prev_ws:
                if not found_smaller:
                    self.indentation[temp] = self.get_indentation(bol) + 1
                return

    def fix_tokens(self, bol):#XXX redundant (remove and add import method that fixes each line)
        """Update (add/remove) indentation tokens."""
        new_tokens = []
        temp = bol
        if bol is self.bos:
            this_ws = self.count_whitespace(bol)
            self.indentation[bol] = this_ws
        elif self.is_logical_line(bol):
            this_ws = self.count_whitespace(bol)
            self.whitespaces[bol] = this_ws
            bol = self.prev_line(bol)
            while bol is not self.bos and not self.is_logical_line(bol):
                bol = self.prev_line(bol)
            prev_ws = self.count_whitespace(bol)

            if prev_ws == this_ws:
                self.indentation[temp] = self.get_indentation(bol) # this is only needed when calling fix_tokens separately (e.g. import)
                new_tokens.append(self.create_token("newline"))
            elif prev_ws < this_ws:
                self.indentation[temp] = self.get_indentation(bol) + 1
                new_tokens.append(self.create_token("indent"))
                new_tokens.append(self.create_token("newline"))
            elif prev_ws > this_ws:
                this_indent = self.find_indentation(temp)
                if this_indent is None:
                    new_tokens.append(self.create_token("unbalanced"))
                else:
                    self.indentation[temp] = this_indent
                    prev_indent = self.get_indentation(bol)
                    indent_diff = prev_indent - this_indent
                    for i in range(indent_diff):
                        new_tokens.append(self.create_token("dedent"))
                    new_tokens.append(self.create_token("newline"))

        self.apply_nodes(new_tokens, temp)

    def apply_nodes(self, new, bol):
        """Insert generated indentation tokens into the token stream if they
        differ from current tokens"""
        # test if indent nodes have changed
        changed = self.indentation_nodes_changed(bol, new)
        if changed:
            self.changed = True
            # remove old indentation nodes
            self.remove_indentation_nodes(bol)
            # and insert new ones
            for node in new:
                bol.insert_after(node)

        # generate last lines dedent
        if self.next_line(bol) is None: # this is the last line
            node = self.eos.prev_term
            while isinstance(node.symbol, IndentationTerminal):
                node = node.prev_term

            # if line is not logical, find previous logical
            while not self.is_logical_line(bol) and bol is not self.bos:
                bol = self.prev_line(bol)

            # generate correct amount of dedentation nodes
            this_indent = self.get_indentation(bol)
            if this_indent is None:
                # this happens when there's only one line and that line is not
                # logical
                return

            new = []
            for i in range(this_indent):
                new.append(self.create_token("dedent"))
            new.append(self.create_token("newline"))

            changed = self.indentation_nodes_changed(node, new)
            if changed:
                self.changed = True
                # remove old indentation nodes
                self.remove_indentation_nodes(node)
                # and insert new ones
                for n in new:
                    node.insert_after(n)

    def indentation_nodes_changed(self, bol, nodes):
        """Compares indentation tokens in a line with new tokens to find out
        whether the line needs to be updated"""
        previous_nodes = []
        node = bol.next_term
        while isinstance(node.symbol, IndentationTerminal):
            previous_nodes.append(node)
            node = node.next_term

        previous_nodes.reverse()
        if len(previous_nodes) != len(nodes):
            return True
        for i in range(len(nodes)):
            if nodes[i].symbol != previous_nodes[i].symbol:
                return True
        return False

    def remove_indentation_nodes(self, bol):
        if bol is None:
            return
        node = bol.next_term
        while isinstance(node.symbol, IndentationTerminal):
            node.parent.remove_child(node)
            node = node.next_term
        return node

    def find_indentation(self, bol):
        # indentation level
        this_ws = self.count_whitespace(bol)
        while not bol is self.bos:
            bol = self.prev_line(bol)
            prev_ws = self.count_whitespace(bol)
            if prev_ws is None:
                continue
            if prev_ws == this_ws:
                return self.get_indentation(bol)
            if prev_ws < this_ws:
                return None
        return None

    def create_token(self, name):
        if name == "newline":
            return TextNode(IndentationTerminal("NEWLINE"))
        if name == "indent":
            return TextNode(IndentationTerminal("INDENT"))
        if name == "dedent":
            return TextNode(IndentationTerminal("DEDENT"))
        if name == "unbalanced":
            return TextNode(IndentationTerminal("UNBALANCED"))

    def count_whitespace(self, bol):
        # indentation whitespaces
        if not self.is_logical_line(bol):
            return None

        node = bol.next_term     # get first node in line

        while isinstance(node.symbol, IndentationTerminal):
            node = node.next_term # skip indent nodes

        if node.lookup == "<ws>":
            return len(node.symbol.name)

        return 0

    def get_whitespace(self, bol):
        try:
            return self.whitespaces[bol]
        except KeyError:
            return 0

    def get_indentation(self, bol):
        try:
            return self.indentation[bol]
        except KeyError:
            return 0

    def prev_line(self, node):
        node = node.prev_term
        while True:
            if node.lookup == "<return>":
                return node
            if node is self.bos:
                return node
            node = node.prev_term

    def next_line(self, node):
        node = node.next_term
        while True:
            if node.lookup == "<return>":
                return node
            if node is self.eos:
                return None
            node = node.next_term

    def get_line_start(self, node):
        while True:
            if node.lookup == "<return>":
                break
            if node is self.bos:
                break
            node = node.prev_term
        return node

    def is_logical_line(self, node):
        # check if line is logical (i.e. doesn't only consist of whitespaces,
        # comments, etc)
        if node.symbol.name == "\r" and node.prev_term.symbol.name == "\\":
            return False
        node = node.next_term
        while True:
            if node is self.eos:
                return False
            if node.lookup == "hash": # reached next line
                print("hash means not logical")
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
