class Production(object):

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __eq__(self, other):
        return self.left == other.left and self.right == other.right

    def __hash__(self):
        # XXX: this is not safe
        s = "%s|%s" % (self.left, self.right)
        return hash(s)

    def __repr__(self):
        return "Production(%s, %s)" % (self.left, self.right)
