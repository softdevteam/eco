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

def println(node):
    l = []
    if node.symbol.name == "\r":
        node = node.next_term
    while node and node.symbol.name != "\r":
        l.append(node.symbol.name)
        node = node.next_term
    return repr("".join(l))

# NEW SIMPLIFIED ALGO
# Starting at changed line
# Update bracket counters
# If lastline is uneven, don't repair anything (need todo list)
# Fix indents:
#   remove indents (if line is not logical, ws/comment/brackets)
#   insert indents (if ws was changed)
# If logical line was changed (indents or brackets):
    # update dependent: min upto smaller line and until no more changes



class IndentationManager:

    def __init__(self, root):
        self.bos = root.children[0]
        self.eos = root.children[-1]
        self.whitespaces = {}
        self.indentation = {}
        self.parantheses = {}
        self.changed = False

    def repair(self, node):
        """Repair indentation in the line given by node."""
        self.changed = False
        bol = self.get_line_start(node)

        print "Repair", println(node)

        # update bracket info in current line
        brackets_changed = self.update_brackets(bol)
        if brackets_changed:
            # if brackets have changed, update bracket info in all dependent
            # lines
            self.apply_brackets(bol)

        # XXX Don't do anything if last line has uneven brackets, to avoid
        # removing all identation tokens in the entire file when a bracket is
        # inserted at the top. Instead put this line onto a todo list and wait
        # for the last line to become even again.

        # if line is not logical, skip ahead to next logical line
        # XXX is this necessary or does updating depdending lines already deal with this case?
       #if not self.is_logical_line(bol):
       #    self.remove_indentation_nodes(bol) # remove previous indentation
       #    bol = self.next_line(bol)
       #    if bol is None:
       #        bol = self.prev_line(self.eos)
       #    else:
       #        while True:
       #            if bol is None:
       #                return False # nothing has been changed
       #            if self.is_logical_line(bol):
       #                break
       #            bol = self.next_line(bol)

        prev_ws = self.get_whitespace(bol)
        self.update_indentation(bol)
        tokens_changed = self.fix_tokens(bol)
        curr_ws = self.get_whitespace(bol)

        if not tokens_changed and not brackets_changed:
            # We don't need to update the following lines if no indentation
            # tokens were removed/inserted in `fix_tokens(bol)`
            print("   No changes (tokens/brackets)")
            return False

        # update all dependent lines that follow
        search_threshold = min(prev_ws, curr_ws)
        current_indent = self.get_indentation(bol)
        current_ws = self.count_whitespace(bol)
        bol = self.next_line(bol)
        while bol is not None:
            ws = self.count_whitespace(bol)
            if ws is None and bol.prev_term and bol.prev_term.symbol.name != "\\":
                self.remove_indentation_nodes(bol)
                bol = self.next_line(bol)
                continue
            if ws > current_ws:
                self.indentation[bol] = current_indent + 1
            if ws == current_ws:
                self.indentation[bol] = current_indent
            if ws < current_ws:
                self.update_indentation(bol)

            changed = self.fix_tokens(bol)

            # repair dependent lines at least up to a line smaller than the
            # initally changed line. Since changed bracketing can cause changes
            # beyond this, also update succeeding lines until no more
            # indentation tokens were changed
            if self.get_whitespace(bol) <= search_threshold and not changed:
                break

            current_ws = ws
            current_indent = self.get_indentation(bol)
            bol = self.next_line(bol)

        if bol is None: # did we reach the end of the file?
            self.update_last_line()
        return self.changed

    def update_brackets(self, bol):
        if bol is self.bos:
            para = [0,0,0] # (, [, {
        else:
            prevl = self.prev_line(bol)
            para = list(self.get_para(prevl))
        before = self.get_para(bol)
        n = bol.next_term
        while n is not self.eos:
            if n.lookup == "<return>":
                break
            if n.symbol.name == "(":
                para[0] += 1
            elif n.symbol.name == ")":
                para[0] -= 1
            elif n.symbol.name == "[":
                para[1] += 1
            elif n.symbol.name == "]":
                para[1] -= 1
            elif n.symbol.name == "{":
                para[2] += 1
            elif n.symbol.name == "}":
                para[2] -= 1
            n = n.next_term
        self.parantheses[bol] = para
        if before != para:
            return True
        return False

    def apply_brackets(self, bol):
        nextl = bol
        changed = True
        while changed:
            nextl = self.next_line(nextl)
            if nextl is None:
                break
            changed = self.update_brackets(nextl)

    def get_para(self, bol):
        if bol in self.parantheses:
            return self.parantheses[bol]
        else:
            return [0,0,0]

    def repair_full(self):
        self.whitespaces = {}
        self.indentation = {}
        bol = self.bos
        while bol is not None:
            self.update_indentation(bol)
            self.fix_tokens(bol)
            bol = self.next_line(bol)

    def update_indentation(self, bol):
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

    def fix_tokens(self, bol):
        """Update indentation tokens in the line given by `bol`."""

        print "Fix tokens:"

        if not self.is_logical_line(bol):
            print "   Remove indentation"
            return self.remove_indentation_nodes(bol)

        # calculate new indentation tokens for that line
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

        # merge new tokens back into the tree, reusing existing indentation
        # tokens, if their location hasn't changed
        changed = self.merge_nodes(temp, new_tokens)
        return changed

    def update_last_line(self):
        """Update indentation tokens at the end of the file, producing dedent
        tokens for each open indentation."""
        print "Update last line"
        if True:#self.next_line(bol) is None: # this is the last line
            node = self.eos.prev_term
            while isinstance(node.symbol, IndentationTerminal):
                node = node.prev_term

            # find beginning of last line
            bol = self.eos.prev_term
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

            self.merge_nodes(node, new)

    def merge_nodes(self, bol, newnodes):
        """Insert generated indentation tokens into the token stream if they
        differ from current tokens"""
        changed = False
        previous_nodes = []
        last_node = bol
        node = bol.next_term
        while isinstance(node.symbol, IndentationTerminal):
            if not node.deleted:
                previous_nodes.append(node)
            node = node.next_term

        for i in range(len(previous_nodes)):
            if len(newnodes) > 0:
                newnode = newnodes.pop()
            else:
                # remove leftover previous_nodes
                previous_nodes[i].remove()
                changed = True
                continue

            oldnode = previous_nodes[i]
            if newnode.symbol != oldnode.symbol:
                # remove old, insert new
                oldnode.replace(newnode)
                last_node = newnode
                changed = True
            else:
                if oldnode.deleted:
                    oldnode.deleted = False
                    changed = True
                last_node = oldnode

        for n in newnodes:
            # insert remaining newnodes
            last_node.insert_after(n)
            changed = True
        return changed

    def remove_indentation_nodes(self, bol):
        if bol is None:
            return False
        changed = False
        node = bol.next_term
        while isinstance(node.symbol, IndentationTerminal):
            node.parent.remove_child(node)
            node = node.next_term
            changed = True
        return changed

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

        # if previous line has uneven parantheses, this line cannot be logical
        if node is not self.bos:
            prevl = self.prev_line(node)
            para = self.get_para(prevl)
            if para[0] > 0 or para[1] > 0 or para[2] > 0:
                return False

        if node.symbol.name == "\r":
            prev = node.prev_term
            while prev.deleted:
                prev = prev.prev_term
            if prev.symbol.name == "\\":
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
