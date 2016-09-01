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

import re
from grammar_parser.gparser import Nonterminal, Terminal, IndentationTerminal, MultiTerminal
from syntaxtable import FinishSymbol

class AST(object):
    def __init__(self, parent=None):
        self.parent = parent
        self.progress = 0
        self.terminals = []

    def init(self):
        bos = BOS(Terminal(""), 0, [])
        eos = EOS(FinishSymbol(), 0, [])
        bos.next_term = eos
        eos.prev_term = bos
        root = TextNode(Nonterminal("Root"), 0, [bos, eos])
        self.parent = root

    def get_bos(self):
        return self.parent.children[0]

    def get_nodes_at_position(self, pos, a=None, b=None):
        """
        Searches all nodes that match the current cursor position in the TextField.
        As a side effect all passed nodes are updated with their position in the document.
        """
        print("================== get nodes at pos ================== ")
        progress = 0
        node = self.parent.children[0]
        while node is not None:
            node.position = progress
            progress += len(node.symbol.name)

            print("node", node)
            if pos < progress:
                return [node, None]

            if pos == progress:
                print("pos == progress")
                other = node.next_terminal()
                print("other", other)
                other.position = progress
                return [node, other]

            node = node.next_terminal()
        print ("================ end get nodes at pos ================ ")


    def get_nodes_at_position_old(self, pos, node=None, bla=0):
        print("Progress:", self.progress, "Node", node)
        if node is None:
           node = self.parent#.children[1]

        if isinstance(node.symbol, Nonterminal):
            for child in node.children:
                result = self.get_nodes_at_position(pos, child, self.progress)
                if result != []:
                    self.progress = 0
                    return result
        else:
            nodes = []
            if pos <= self.progress + len(node.symbol.name):
                nodes.append(node)

            if pos == self.progress + len(node.symbol.name):
                nodes.append(node.next_terminal())

            self.progress += len(node.symbol.name)
            return nodes

    def find_node_at_pos(self, pos, node=None): #recursive
        if node is None:
           node = self.parent.children[1]

        if isinstance(node.symbol, Nonterminal):
            for child in node.children:
                result = self.find_node_at_pos(pos, child)
                if result:
                    return result

        if node.pos + len(node.symbol.name) >= pos:
            return node


    def find_node_at_pos_iterative(self, pos): #not working
        stack = []
        stack.append(self.parent.children[1]) # skip bos
        #XXX speed things up later by having a list/dict of all terminal nodes
        while stack != []:
            e = stack.pop(0)
            if isinstance(e.symbol, Nonterminal):
                stack.extend(e.children)
                continue
            if e.pos + len(e.symbol.name) >= pos:
                return e

    def find_common_parent(self, start, end):
        start_parents = []
        start = start.parent
        while start is not None:
            start_parents.append(start)
            start = start.get_parent()

        end_parents = []
        end = end.parent
        while end is not None:
            end_parents.append(end)
            end = end.get_parent()

        for p1 in start_parents:
            for p2 in end_parents:
                if p1 is p2:
                    return p1
        return None

    def adjust_nodes_after_node(self, node, change):
        stack = []
        stack.append(self.parent.children[1]) # skip bos
        found = False
        for e in stack:
            if e is node:
                found = True
                continue
            if found:
                e.pos += change

    def pprint(self):
        self.parent.pprint()

    def cprint(self, output=[]):
        self.parent.cprint(output)
        return "\n".join(output)

class Node(object):
    __slots__ = ["symbol", "state", "parent", "left", "right", "prev_term", "next_term", "magic_parent", "children", "annotations"]
    def __init__(self, symbol, state, children):
        self.symbol = symbol
        self.state = state
        self.parent = None
        self.left = None
        self.right = None
        self.prev_term = None
        self.next_term = None
        self.magic_parent = None
        self.set_children(children)
        self.log = {}
        self.annotations = []

    def add_annotation(self, annotation):
        self.annotations.append(annotation)

    def remove_annotations_by_class(self, klass):
        for annotation in self.annotations:
            if isinstance(annotation, klass):
                self.annotations.remove(annotation)

    def has_annotation_by_class(self, klass):
        for annotation in self.annotations:
            if isinstance(annotation, klass):
                return True
        return False

    def get_annotations_with_hint(self, klass):
        matching = []
        for annotation in self.annotations:
            for hint in annotation.get_hints():
                if isinstance(hint, klass):
                    matching.append(annotation)
        return matching

    def save_ns(self, setchildren=False):
        from treemanager import TreeManager
        self.log[("ns", TreeManager.version)] = True

    def mark_changed(self):
        node = self
        while True:
            node.save_ns()
            node.version = node.version + 0.000001
            if not node.parent:
                # if language box changed we need to update the version numbers
                # in the parent parser as well
                if node.get_magicterminal():
                    node.get_magicterminal().mark_version()
                break
            if node.parent.changed is True and node.parent.has_changes() is True:
                break
            node = node.parent
            node.changed = True

    def mark_version(self):
        node = self
        while True:
            node.save_ns()
            node.version = node.version + 0.000001
            if not node.parent:
                if node.get_magicterminal():
                    node.get_magicterminal().mark_version()
                break
            if node.parent.has_changes() is True:
                break
            node = node.parent

    def set_children(self, children):
        self.children = children
        last = None
        for c in children:
            c.parent = self
            c.left = last
            if last is not None:
                last.right = c
            last = c
            c.save_ns(True)
        if last is not None:
            last.right = None # last child has no right sibling
            #XXX need to save this?

    def save(self, version):
        self.log[("children", version)] = list(self.children)
        self.log[("parent", version)] = self.parent
        self.log[("left", version)] = self.left
        self.log[("right", version)] = self.right
        self.log[("next_term", version)] = self.next_term
        self.log[("prev_term", version)] = self.prev_term
        self.log[("deleted", version)] = self.deleted
        self.log[("indent", version)] = self.indent
        self.version = version

    def load(self, version):
        while version >= 0:
            if ("parent", version) in self.log:
                self.parent = self.log[("parent", version)]
                self.children = list(self.log[("children", version)])
                self.left = self.log[("left", version)]
                self.right = self.log[("right", version)]
                self.next_term = self.log[("next_term", version)]
                self.prev_term = self.log[("prev_term", version)]
                self.deleted = self.log[("deleted", version)]
                self.indent = self.log[("indent", version)]
                self.version = version
                return
            version -= 1

    def get_attr(self, attr, version):
        if version is None:
            return self.__getattribute__(attr)
        version = int(version)
        while version >= 0:
            try:
                return self.log[(attr, version)]
            except KeyError:
                version -= 1
        raise AttributeError("Attribute %s for version %s not found." % (attr, version))

    def remove_child(self, child):
        for i in xrange(len(self.children)):
            if self.children[i] is child:
                removed_child = self.children.pop(i)
                removed_child.deleted = True
                removed_child.save_ns()
                # update siblings
                if removed_child.left:
                    removed_child.left.right = removed_child.right
                    removed_child.left.save_ns()
                if removed_child.right:
                    removed_child.right.left = removed_child.left
                    removed_child.right.save_ns()
                # update terminal pointers
                child.prev_term.next_term = child.next_term
                child.prev_term.save_ns()
                child.prev_term.mark_version()
                child.next_term.prev_term = child.prev_term
                child.next_term.save_ns()
                child.next_term.mark_version()
                self.mark_changed()
                self.changed = True
                return

    def insert_after(self, node):
        if isinstance(self.parent, MultiTerminal):
            for i in xrange(len(self.parent.name)):
                if self.parent.name[i] is self:
                    self.parent.name.insert(i+1, node)
                    node.parent = self.parent
        else:
            self.parent.insert_after_node(self, node)

    def remove(self):
        if isinstance(self.parent, MultiTerminal):
            for i in range(len(self.parent.name)):
                if self.parent.name[i] is self:
                    self.parent.name.pop(i)
                    return
        else:
            self.parent.remove_child(self)

    def replace(self, node):
        # XXX non optimal version
        self.insert_after(node)
        self.remove()

    def isempty(self):
        if isinstance(self.symbol, MultiTerminal):
            return self.symbol.name == []

    def ismultichild(self):
        return isinstance(self.parent, MultiTerminal)

    def insert_after_node(self, node, newnode):
        i = 0
        for c in self.children:
            if c is node:
                self.children.insert(i+1, newnode)
                newnode.parent = self
                newnode.mark_changed()
                # update siblings
                newnode.left = c
                newnode.right = c.right
                c.right = newnode
                c.save_ns()
                if newnode.right:
                    newnode.right.left = newnode
                    newnode.right.save_ns()
                # update terminal pointers
                newnode.prev_term = node
                node.next_term.prev_term = newnode
                node.next_term.save_ns()
                node.next_term.mark_version()
                newnode.next_term = node.next_term
                node.next_term = newnode
                newnode.magic_parent = node.magic_parent
                return
            i += 1

    def right_sibling(self):
        return self.right

    def old_right_sibling(self):
        if not self.parent:
            return None
        siblings = self.parent.children
        for i in range(len(siblings)):
            if siblings[i] is self:
                if i+1 < len(siblings):
                    print("returning right sibling", siblings[i+1], self.right)
                    return siblings[i+1]

    def left_sibling(self):
        siblings = self.parent.children
        last = None
        for i in range(len(siblings)):
            if siblings[i] is self:
                return last
            else:
                last = siblings[i]

    def find_first_terminal(self):
        node = self
        while isinstance(node.symbol, Nonterminal):
            if node.children == []:
                while node.right is None:
                    node = node.parent
                node = node.right
            else:
                node = node.children[0]
        return node

    def next_terminal(self, skip_indent=False):
        n = self.next_term
        if not n:
            if type(self.parent.symbol) is MultiTerminal:
                return self.parent.next_term
        if skip_indent:
            while n is not None and isinstance(n.symbol, IndentationTerminal):
                n = n.next_term
        return n

    def old_next_terminal(self):
        if isinstance(self, EOS):
            return None

        node = self
        while node.right_sibling() is None:
            node = node.parent

        node = node.right_sibling()

        while node.children != []:
            node = node.children[0]

        # fix for empty rules resulting in nonterminals without children
        if isinstance(node.symbol, Nonterminal):
            return node.next_terminal()

        return node

    def previous_terminal(self, skip_indent = False):
        n = self.prev_term
        if skip_indent:
            while n is not None and isinstance(n.symbol, IndentationTerminal):
                n = n.prev_term
        return n

    def old_previous_terminal(self):
        if isinstance(self, BOS):
            return None

        node = self
        while node.left_sibling() is None:
            node = node.parent

        node = node.left_sibling()

        while node.children != []:
            node = node.children[-1]

        if isinstance(node.symbol, Nonterminal):
            return node.previous_terminal()

        return node

    def get_first_terminal(self):
        node = self
        while isinstance(node.symbol, Nonterminal):
            if node.children == []:
                return node.next_terminal()
            node = node.children[0]
        return node

    def __repr__(self):
        return "Node(%s, %s, %s)" % (self.symbol, self.state, self.children)

    def pprint(self, indent=0):
        print(" "*indent, self.symbol, ":", self.state)
        indent += 4
        for c in self.children:
            c.pprint(indent)

    def cprint(self, output, indent=0):
        output.append(" "*indent + str(self.symbol))
        indent += 4
        for c in self.children:
            c.cprint(output, indent)

    def __eq__(self, other):
        if isinstance(other, Node):
            return other.symbol == self.symbol and other.state == self.state and other.children == self.children
        return False

import string
lowercase = set(list(string.ascii_lowercase))
uppercase = set(list(string.ascii_uppercase))
digits = set(list(string.digits))

class TextNode(Node):
    __slots__ = ["log", "version", "position", "changed", "deleted", "image", "image_src", "plain_mode", "alternate", "lookahead", "lookup", "parent_lbox", "magic_backpointer", "indent"]
    def __init__(self, symbol, state=-1, children=[], pos=-1, lookahead=0):
        Node.__init__(self, symbol, state, children)
        self.position = 0
        self.changed = False
        self.deleted = False
        self.image = None
        self.image_src = None
        self.plain_mode = False
        self.alternate = None
        self.lookahead = lookahead
        self.lookup = ""
        self.log = {}
        self.version = 0
        self.indent = None
        if isinstance(symbol, MultiTerminal):
            symbol.pnode = self

    def prev_terminal(self):
        if self.prev_term:
            return self.prev_term
        if type(self.parent.symbol) is MultiTerminal:
            return self.parent.prev_term

    def get_magicterminal(self):
        try:
            return self.magic_backpointer
        except AttributeError:
            return None

    def get_root(self):
        node = self
        while node.parent is not None:
            node = node.parent
        return node

    def get_parent(self):
        if self.parent:
            return self.parent
        return self.get_magicterminal()

    def matches(self, text):
        if self.symbol.name == "":
            return True
        new = text

        m = re.match("^" + self.regex + "$", new)
        if m:
            return True
        return False

    def char_in_regex(self, c):
        if c in self.regex:
            #XXX be careful to not accidentally match chars with non-escaped regex chars like ., [, etc
            return True
        if c in lowercase and re.findall("\[.*a-z.*\]", self.regex):
            return True
        if c in uppercase and re.findall("\[.*A-Z.*\]", self.regex):
            return True
        if c in digits and re.findall("\[.*0-9.*\]", self.regex):
            return True
        return False

    def change_pos(self, i):
        self.pos += i

    def change_text(self, text):
        _cls = self.symbol.__class__
        self.symbol = _cls(text)
        self.mark_version()

    def save(self, version):
        Node.save(self, version)
        self.log[("symbol.name", version)] = self.symbol.name

    def load(self, version):
        Node.load(self, version)
        if not isinstance(self.symbol, Terminal):
            return
        text = self.get_text(version)
        if text:
            self.symbol.name = text
        else:
            pass

    def has_changes(self, version=None):
        if version is None:
            from treemanager import TreeManager
            version = TreeManager.version
        return self.log.has_key(("ns", version))

    def get_text(self, version):
        while True:
            try:
                return self.log[("symbol.name", version)]
            except KeyError:
                version -= 1
                if version == -1:
                    return None
                continue

    def insert(self, char, pos):
        l = list(self.symbol.name)
        l.insert(int(pos), str(char))
        self.change_text("".join(l))

    def delete(self, pos):
        self.backspace(pos)

    def backspace(self, pos):
        l = list(self.symbol.name)
        if len(l) == 1: # if node going to be empty: delete
            #XXX merge remaining nodes here
            self.change_text("")
            return l[0]
        else:
            delchar = l.pop(int(pos))
            self.change_text("".join(l))
            return delchar

    def __repr__(self):
        return "%s(%s, %s, %s, %s)" % (self.__class__.__name__, self.symbol, self.state, len(self.children), self.lookup)

class SpecialTextNode(TextNode):
    def backspace(self, pos):
        return

class BOS(SpecialTextNode):
    pass

class EOS(SpecialTextNode):
    pass

class ImageNode(object):
    def __init__(self, node, y):
        self.node = node
        self.y = y

    def __getattr__(self, name):
        return self.node.__getattribute__(name)
