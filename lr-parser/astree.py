class AST(object):
    def __init__(self, parent):
        self.parent = parent

    def pprint(self):
        self.parent.pprint()

class Node(object):
    def __init__(self, symbol, children):
        self.symbol = symbol
        self.children = children

    def pprint(self, indent=0):
        print(" "*indent, self.symbol)
        indent += 4
        for c in self.children:
            c.pprint(indent)
