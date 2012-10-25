import sys
sys.path.append("../")

from gparser import Nonterminal

class AST(object):
    def __init__(self, parent):
        self.parent = parent

    def find_node_at_pos(self, pos):
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


    def set_children(self, children):
        self.children = children
        for c in self.children:
            c.parent = self

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

    def right_sibling(self):
        print("right_sibling", self)
        siblings = self.parent.children
        last = None
        for i in range(len(siblings)-1, -1, -1):
            if siblings[i] is self:
                return last
            else:
                last = siblings[i]

    def __repr__(self):
        return "Node(%s, %s, %s)" % (self.symbol, self.state, self.children)

    def pprint(self, indent=0):
        print(" "*indent, self.symbol, ":", self.state, "(", id(self), ")")
        indent += 4
        for c in self.children:
            c.pprint(indent)

    def __eq__(self, other):
        if isinstance(other, Node):
            return other.symbol == self.symbol and other.state == self.state and other.children == self.children
        return False

class TextNode(Node):
    def __init__(self, symbol, state, children, pos=-1):
        Node.__init__(self, symbol, state, children)
        self.pos = pos
        self.changed = False

    def change_pos(self, i):
        self.pos += i

    def change_text(self, text):
        self.symbol.name = text

    def insert(self, char, pos):
        #XXX change type of name to list for all symbols
        l = list(self.symbol.name)
        internal_pos = pos - self.pos
        l.insert(internal_pos-1, char)
        self.symbol.name = "".join(l)

    def delete(self, pos):
        l = list(self.symbol.name)
        internal_pos = pos - self.pos
        l.pop(internal_pos)
        self.symbol.name = "".join(l)

    def __repr__(self):
        return "TextNode(%s, %s, %s, %s)" % (self.symbol, self.state, self.children, self.pos)

