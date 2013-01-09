from time import time
class StateSet(object):

    _hashtime = 0

    def __init__(self, elements=None):
        if elements:
            self.elements = elements
        else:
            self.elements = set()

    def __len__(self):
        return len(self.elements)

    def add(self, element):
        if element not in self.elements:
            self.elements.add(element)

    def merge(self):
        # merge states that only differ in their lookahead
        # XXX this is slow
        delete = set()
        for a in self.elements:
            for b in self.elements:
                if a is not b and a.d == b.d and a.p == b.p:
                    a.lookahead |= b.lookahead
                    delete.add(b)
        self.elements.difference_update(delete)

    def __contains__(self, element):
        return element in self.elements

    def is_empty(self):
        return self.elements == []

    def get_next_symbols(self):
        symbols = set()
        for state in self.elements:
            symbol = state.next_symbol()
            if symbol:
                symbols.add(symbol)
        return symbols

    def get_next_lookahead_symbols(self):
        symbols = set()
        for lrelement in self.elements:
            symbols |= lrelement.lookahead
        return symbols

    def __eq__(self, other):
        temp = LR1Element.__eq__
        LR1Element.__eq__ = LR1Element.equal_with_la
        result = self.elements == other.elements
        LR1Element.__eq__ = temp
        return result
        #return self.equals(other, True)

    def equals(self, other, with_lookahead=True):
        if with_lookahead:
            return self.elements == other.elements

        if not isinstance(other, StateSet):
            return False
        e1 = self
        e2 = other
        #XXX why not equal only?
        #if len(e2) > len(e1):
        #    e1, e2 = e2, e1
        if len(e1) != len(e2):
            return False

        for e in e1.elements:
            if not e2.has(e, with_lookahead):
                return False
        return True

    def has(self, element, with_lookahead=True):
        for e in self.elements:
            if not with_lookahead:
                if State.__eq__(e, element):
                    return True
            else:
                if element == e:
                    return True
        return False

    def __str__(self):
        return str(self.elements)

    def __hash__(self):
        start = time()
        _hash = 0
        for element in self.elements:
            _hash ^= hash(element)
        end = time()
        StateSet._hashtime += end-start
        return _hash

class State(object):

    # backpointer only necessary for earley parser
    # lookahead only necessary for normal earley parser
    def __init__(self, production, pos, backpointer=None, lookaheadsymbol=None):
        self.p = production
        self.d = pos
        self.b = backpointer
        self.k = lookaheadsymbol
        self._hash = None

    def next_symbol(self):
        try:
            return self.p.right[self.d]
        except IndexError:
            return None

    def remaining_symbols(self):
        return self.p.right[self.d+1:]

    def isfinal(self):
        return len(self.p.right) == self.d

    def get_left(self):
        return self.p.left

    def get_lookahead(self):
        if self.d+1 >= len(self.p.right):
            return self.k
        return self.p.right[self.d+1].name

    def get_backpointer(self):
        return self.b

    def get_lookahead_raw(self):
        return self.get_lookahead().strip("\"")

    def clone(self):
        return State(self.p, self.d, self.b, self.k)

    def __repr__(self):
        return "State(%s, %s, %s, %s)" % (self.p, self.d, self.b, self.k)

    def __str__(self):
        """Displays the state in readable form as used in the Earley paper"""
        if not self.p.left:
            left = "None"
        else:
            left = self.p.left.name
        right = [x.name.strip("\"") for x in self.p.right]
        right.insert(self.d, ".")
        right = "".join(right)
        #s = "%s ::= %s %s %s" % (left, right, self.k, self.b)
        s = "%s ::= %s" % (left, right)
        return s

    def equals_str(self, s):
        return self.__str__() == s

    def __eq__(self, other):
        return self.p == other.p and self.d == other.d and self.b == other.b and self.k == other.k

    def __hash__(self):
        if self._hash is None:
            self._hash = hash(self.p) ^ hash(self.d)
        return self._hash

class LR0Element(State):

    def __init__(self, production, pos):
        State.__init__(self, production, pos, None, None)

    def __eq__(self, other):
        return self.p == other.p and self.d == other.d

    def __hash__(self):
        return hash(self.p) ^ hash(self.d)

class LR1Element(State):

    def __init__(self, production, pos, lookahead):
        State.__init__(self, production, pos, None, None)
        self.lookahead = lookahead

    def clone(self):
        return LR1Element(self.p, self.d, set(self.lookahead))

    def __eq__(self, other):
        return State.__eq__(self, other)# and self.lookahead == other.lookahead

    def equal_with_la(self, other):
        return State.__eq__(self, other) and self.lookahead == other.lookahead

    def __str__(self):
        s = State.__str__(self)
        l = []
        for t in self.lookahead:
            l.append(t.name.strip("\""))
        s += " {%s}" % (", ".join(l),)
        return s

    def __repr__(self):
        return "LR1Element(%s, %s, %s)" % (self.p, self.d, self.lookahead)
