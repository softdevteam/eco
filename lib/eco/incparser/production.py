class Production(object):

    def __init__(self, left, right):
        self.left = left
        self.right = right
        self._hash = None

    def __eq__(self, other):
        return self.left == other.left and self.right == other.right

    def __hash__(self):
        if self._hash is None:
            # XXX: this is not safe
            s = "%s|%s" % (self.left, self.right)
            self._hash = hash(s)
        return self._hash

    def __repr__(self):
        return "Production(%s, %s)" % (self.left, self.right)
