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
from grammar_parser.gparser import Nonterminal, Terminal, IndentationTerminal
from .syntaxtable import FinishSymbol

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
        if children is None:
            children = []
        self.set_children(children)
        self.log = {}
        self.max_version = None
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

    def mark_changed(self):
        if self.changed or self.nested_changes:
            # this has already been marked
            self.changed = True
            return
        node = self
        self.changed = True
        while True:
            if not node.parent:
                break
            if node.parent.has_changes():
                node.parent.nested_changes = True
                break
            node = node.parent
            node.nested_changes = True

    def set_children(self, children):
        self.children = children
        last = None
        for c in children:
            c.parent = self
            c.left = last
            if last is not None:
                last.right = c
            last = c
        if last is not None:
            last.right = None # last child has no right sibling
            #XXX need to save this?

    def update_siblings(self):
        for i in range(len(self.parent.children)):
            c = self.parent.children[i]
            if c is self:
                if i > 0:
                    c.left = self.parent.children[i-1]
                else:
                    c.left = None
                if i < len(self.parent.children) - 1:
                    c.right = self.parent.children[i+1]
                else:
                    c.right = None
                break

    def save(self, version):
        # XXX version set, e.g. set(0,1,5,6,9) that contains all versions in
        # which this node has been saved. this way we can easily check if a
        # the node has changes in that version and quickly get the closest
        # versions to it if not
        self.log[("children", version)] = list(self.children)
        self.log[("parent", version)] = self.parent
        self.log[("left", version)] = self.left
        self.log[("right", version)] = self.right
        self.log[("next_term", version)] = self.next_term
        self.log[("prev_term", version)] = self.prev_term
        self.log[("deleted", version)] = self.deleted
        self.log[("indent", version)] = self.indent
        self.log[("changed", version)] = self.changed
        self.log[("nested_changes", version)] = self.nested_changes
        self.log[("nested_errors", version)] = self.nested_errors
        self.log[("local_error", version)] = self.local_error
        self.log[("textlen", version)] = self.textlen
        self.log[("position", version)] = self.position
        self.log[("isolated", version)] = self.isolated
        self.log[("version", version)] = version
        if self.new:
            self.log[("new", version)] = True
            self.new = False
        # XXX save lookback
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
                self.changed = self.log[("changed", version)]
                self.nested_changes = self.log[("nested_changes", version)]
                self.local_error = self.log[("local_error", version)]
                self.nested_errors = self.log[("nested_errors", version)]
                self.textlen = self.log[("textlen", version)]
                self.position = self.log[("position", version)]
                self.isolated = self.log[("isolated", version)]
                self.version = version
                return
            version -= 1

    def delete_version(self, version):
        if not ("parent", version) in self.log:
            return
        assert version <= self.max_version
        for attr in ["parent", "children", "left", "right", "next_term", "prev_term", "deleted", "indent",\
                "changed", "nested_changes", "local_error", "nested_errors", "symbol.name", "lookup", "version"]:
            if (attr, version) in self.log:
                self.log.pop((attr, version))
        # reset max_version
        new_max = version - 1
        while not ("parent", new_max) in self.log:
            if new_max == 0:
                break
            new_max -= 1
        self.max_version = new_max

    def get_attr(self, attr, version):
        if version is None:
            return getattr(self, attr)
        if self.max_version and version > self.max_version:
            return self.log[(attr, self.max_version)]
        while version >= 0:
            try:
                return self.log[(attr, version)]
            except KeyError:
                version -= 1
        raise AttributeError("Attribute %s for version %s not found." % (attr, version))

    def remove_child(self, child, remove=False):
        for i in range(len(self.children)):
            if self.children[i] is child:
                removed_child = child
                removed_child.deleted = True
                child.prev_term.next_term = child.next_term
                child.prev_term.mark_changed()
                child.next_term.prev_term = child.prev_term
                child.next_term.mark_changed()
                child.mark_changed()
                self.mark_changed()
                if remove:
                    self.children.pop(i)
                    if removed_child.left:
                        removed_child.left.right = removed_child.right
                        removed_child.left.changed = True
                    if removed_child.right:
                        removed_child.right.left = removed_child.left
                        removed_child.right.changed = True
                return

    def insert_after(self, node):
        self.parent.insert_after_node(self, node)

    def remove(self, remove=False):
        self.parent.remove_child(self, remove)

    def replace(self, node):
        # XXX non optimal version
        self.insert_after(node)
        self.remove()

    def ismultichild(self):
        return isinstance(self.parent, MultiTextNode)

    def ismultinode(self):
        return type(self) is MultiTextNode

    def insert_after_node(self, node, newnode):
        i = 0
        for c in self.children:
            if c is node:
                self.children.insert(i+1, newnode)
                self.mark_changed()
                newnode.parent = self
                newnode.mark_changed()
                # update siblings
                newnode.left = c
                newnode.right = c.right
                c.right = newnode
                c.changed = True
                if newnode.right:
                    newnode.right.left = newnode
                    newnode.right.changed = True
                # update terminal pointers
                newnode.prev_term = node
                node.next_term.prev_term = newnode
                node.next_term.mark_changed()
                newnode.next_term = node.next_term
                node.next_term = newnode
                newnode.magic_parent = node.magic_parent
                return
            i += 1
        assert False

    def right_sibling(self, version=None):
        if version:
            return self.get_attr("right", version)
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

    def find_first_terminal(self, version):
        node = self
        while isinstance(node.symbol, Nonterminal):
            if node.get_attr("children", version) == []:
                while node.right_sibling(version) is None:
                    node = node.get_attr("parent", version)
                node = node.right_sibling(version)
            else:
                node = node.get_attr("children", version)[0]
        while node.deleted:
            node = node.get_attr("next_term", version)
        return node

    def next_terminal(self, skip_indent=False):
        n = self.next_term
        if not n:
            if type(self.parent) is MultiTextNode:
                return self.parent.next_term
        if type(n) is MultiTextNode:
            return n.children[0]
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
        if not n:
            if type(self.parent) is MultiTextNode:
                return self.parent.prev_term
        if type(n) is MultiTextNode:
            return n.children[-1]
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
    __slots__ = ["autobox", "tbd", "name", "log", "max_version", "version", "position", "changed", "exists", "isolated", "textlen", "local_error", "nested_errors", "nested_changes", "new", "deleted", "image", "image_src", "plain_mode", "alternate", "lookahead", "lookback", "lookup", "parent_lbox", "magic_backpointer", "indent"]
    def __init__(self, symbol, state=-1, children=None, pos=-1, lookahead=0):
        if children is None:
            children = []
        Node.__init__(self, symbol, state, children)
        self.position = 0
        self.changed = False #XXX should maybe be True by default
        self.new = True
        self.nested_changes = False
        self.local_error = False
        self.nested_errors = False
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
        self.textlen = -1
        self.isolated = None
        self.lookback = -1
        self.exists = False
        self.name = None
        self.tbd = False
        self.autobox = None

    def get_magicterminal(self):
        try:
            return self.magic_backpointer
        except AttributeError:
            return None

    def get_root(self, version=None):
        if version:
            last = self
            node = self.get_attr("parent", version)
            while node is not None:
                last = node
                node = node.get_attr("parent", version)
            return last
        else:
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
        self.mark_changed()
        # Remove their lookup values to make sure the parser fails if these
        # can't be relexed properly
        if type(self.parent) is MultiTextNode:
            self.parent.lookup = ""
        else:
            self.lookup = ""

    def save(self, version):
        Node.save(self, version)
        self.log[("symbol.name", version)] = self.symbol.name
        self.log[("lookup", version)] = self.lookup
        self.max_version = version

    def load(self, version):
        Node.load(self, version)
        while version >= 0:
            if ("parent", version) in self.log:
                self.lookup = self.log[("lookup", version)]
                break
            version -= 1

        if not isinstance(self.symbol, Terminal):
            return
        text = self.get_text(version)
        if text:
            self.symbol.name = text
        else:
            pass

    def is_new(self, version):
        return ("new", version) in self.log

    def textlength(self, version = None):
        if version is not None:
            return self.get_attr("textlen", version)
        return self.textlen

    def calc_textlength(self):
        if self.children:
            self.textlen = sum([c.textlen for c in self.children])
        elif self.deleted or isinstance(self.symbol, FinishSymbol) or isinstance(self, BOS) or isinstance(self.symbol, Nonterminal):
            self.textlen = 0
        else:
            self.textlen = len(self.symbol.name)

    def has_unsaved_changes(self):
        if self.changed != self.log[("changed", self.version)]:
            return True
        if self.nested_changes != self.log[("nested_changes", self.version)]:
            return True
        return False

    def has_changes(self, version = None):
        if version:
            return self.get_attr("changed", version) or self.get_attr("nested_changes", version)
        return self.changed or self.nested_changes

    def has_errors(self):
        return self.nested_errors or self.local_error

    def get_text(self, version):
        while version >= 0:
            if ("symbol.name", version) in self.log:
                return self.log[("symbol.name", version)]
            version -= 1
        return self.symbol.name

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

class MultiTextNode(TextNode):
    def __init__(self):
        TextNode.__init__(self, Terminal("<Multinode>"))

    def insert_at_beginning(self, node):
        self.children.insert(0, node)
        node.parent = self

    def update_children(self):
        for i in range(len(self.children)):
            c = self.children[i]
            if i == 0:
                c.left = None
                c.prev_term = None
            else:
                c.left = c.prev_term = self.children[i-1]
            if i < len(self.children) - 1:
                c.right = c.next_term = self.children[i+1]
            else:
                c.right = None
                c.next_term = None

    def insert_after_node(self, node, newnode):
        for i in range(len(self.children)):
            if self.children[i] is node:
                self.children.insert(i+1, newnode)
                newnode.parent = self
                self.update_neighbors(i+1)
                return

    def remove_child(self, child, version=None):
        for i in range(len(self.children)):
            if self.children[i] is child:
                self.children.pop(i)
                if i > 0:
                    self.update_neighbors(i-1)
                elif i < len(self.children):
                    self.update_neighbors(i)
                return

    def update_neighbors(self, i):
        self.children[i].next_term = None
        self.children[i].prev_term = None
        self.children[i].left = None
        self.children[i].right = None
        if i > 0:
            self.children[i-1].next_term = self.children[i]
            self.children[i-1].right = self.children[i]
            self.children[i].prev_term = self.children[i-1]
            self.children[i].left = self.children[i-1]
        if i+1 < len(self.children):
            self.children[i].next_term = self.children[i+1]
            self.children[i].right = self.children[i+1]
            self.children[i+1].prev_term = self.children[i]
            self.children[i+1].left = self.children[i]

    def isempty(self):
        return self.children == []

    def __repr__(self):
        return "MultiTextNode(%s)" % self.children

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
