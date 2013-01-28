import sys
sys.path.append("../")

import re
from gparser import Nonterminal, Terminal

class AST(object):
    def __init__(self, parent):
        self.parent = parent
        self.progress = 0

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

class Node(object):
    def __init__(self, symbol, state, children):
        self.symbol = symbol
        self.children = children
        self.state = state
        self.parent = None
        for c in self.children:
            c.parent = self

    def mark_changed(self):
        node = self
        #node.changed = True
        while node.parent:
            node = node.parent
            node.changed = True

    def set_children(self, children):
        self.children = children
        for c in self.children:
            c.parent = self

    def remove_child(self, child):
        for i in xrange(len(self.children)):
            if self.children[i] is child:
                self.children.pop(i)
                return

    def replace_children(self, la, children):
        i = 0
        children.reverse()
        for c in self.children:
            if c is la:
                self.children.pop(i)
                for newchild in children:
                    self.children.insert(i, newchild)
                    newchild.parent = self
                return i
            i += 1

    def insert_before_node(self, node, newnode):
        i = 0
        for c in self.children:
            if c is node:
                self.children.insert(i, newnode)
                newnode.parent = self
                newnode.mark_changed()
                return
            i += 1

    def insert_after_node(self, node, newnode):
        i = 0
        for c in self.children:
            if c is node:
                self.children.insert(i+1, newnode)
                newnode.parent = self
                newnode.mark_changed()
                return
            i += 1

    def right_sibling(self):
        if not self.parent:
            return None
        siblings = self.parent.children
        last = None
        for i in range(len(siblings)-1, -1, -1):
            if siblings[i] is self:
                return last
            else:
                last = siblings[i]

    def left_sibling(self):
        siblings = self.parent.children
        last = None
        for i in range(len(siblings)):
            if siblings[i] is self:
                return last
            else:
                last = siblings[i]

    def next_terminal(self):
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

    def previous_terminal(self):
        node = self
        while node.left_sibling() is None:
            node = node.parent
            print(node)

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

    def __eq__(self, other):
        if isinstance(other, Node):
            return other.symbol == self.symbol and other.state == self.state and other.children == self.children
        return False

import string
lowercase = set(list(string.ascii_lowercase))
uppercase = set(list(string.ascii_uppercase))
digits = set(list(string.digits))

class TextNode(Node):
    def __init__(self, symbol, state, children, pos=-1):
        Node.__init__(self, symbol, state, children)
        self.pos = pos
        self.position = 0
        self.changed = False
        self.seen = 0
        self.deleted = False

        self.regex = ""
        self.text = ""
        self.lookup = ""
        self.priority = 999999 # XXX change to maxint later or reverse priority

    def matches(self, text):
        if self.symbol.name == "":
            return True
        old = self.symbol.name
        new = text

        m = re.match("^" + self.regex + "$", new)
        if m:
            return True
        return False

    def char_in_regex(self, c):
        if c in self.regex:
            #XXX be carefull to not accidentially match chars with non-escaped regex chars like ., [, etc
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
        self.symbol = Terminal(text)
        self.mark_changed()

    def insert(self, char, pos):
        #XXX change type of name to list for all symbols
        l = list(self.symbol.name)
        internal_pos = pos - self.position
        l.insert(internal_pos-1, char)
        self.change_text("".join(l))

    def delete(self, pos):
        self.backspace(pos)

    def backspace(self, pos):
        print("delete", self, "Pos:", pos,  "selfpos", self.position)
        l = list(self.symbol.name)
        if len(l) == 1: # if node going to be empty: delete
            #XXX merge remaining nodes here
            #left = self.previous_terminal()
            #right = self.next_terminal()
            #newtext = left.symbol.name + right.symbol.name
            #if left.matches(newtext):
            #    left.change_text(newtext)
            #    right.mark_changed()
            #    right.parent.children.remove(right)
            #print("Merge", left, right)
            # don't delete right now since we need to find repairnodes first
            #if isinstance(self.symbol, Terminal):
            #    self.mark_changed()
            #    self.parent.children.remove(self)
            #    self.deleted = True
            self.change_text("")
        else:
            internal_pos = pos - self.position
            l.pop(pos)
            print(l)
            self.change_text("".join(l))

    def __repr__(self):
        return "%s(%s, %s, %s, %s)" % (self.__class__.__name__, self.symbol, self.state, self.children, self.lookup)

class SpecialTextNode(TextNode):
    def backspace(self, pos):
        return

class BOS(SpecialTextNode):
    pass

class EOS(SpecialTextNode):
    pass
