class AST(object):
    def __init__(self, parent):
        self.parent = parent

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

    def right_sibling(self):
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
        print(" "*indent, self.symbol, ":", self.state)
        indent += 4
        for c in self.children:
            c.pprint(indent)
