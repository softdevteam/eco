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

class Production(object):

    def __init__(self, left, right, annotation=None, prec=None):
        self.left = left
        self.right = right
        self.annotation = annotation
        self.prec = prec
        self._hash = None
        self.inserts = {}

    def __eq__(self, other):
        return self.left == other.left and self.right == other.right

    def __hash__(self):
        if self._hash is None:
            # XXX: this is not safe
            s = "%s|%s" % (self.left, self.right)
            self._hash = hash(s)
        return self._hash

    def __repr__(self):
        l = []
        for e in self.right:
            l.append(e.name)
        return "%s ::= %s {%s}" % (self.left.name if self.left else "None", " ".join(l), self.annotation)
        #return "Production(%s, %s)" % (self.left, self.right)
