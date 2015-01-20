# Copyright (c) 2014 King's College London
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
from grammar_parser.gparser import MagicTerminal, Terminal, Nonterminal

class ATerms:

    def to_term(self, node):
        if node is None:
            return
        from grammar_parser.bootstrap import AstNode, ListNode
        if isinstance(node, AstNode):
            return self.process_astnode(node)
        elif isinstance(node, ListNode):
            return self.process_listnode(node)
        elif isinstance(node.symbol, Nonterminal):
            return self.process_nonterm(node)
        elif isinstance(node.symbol, Terminal):
            return self.process_term(node)

    def process_astnode(self, node):
        s = []
        s.append(node.name)
        s.append("(")
        s.append(self.collect_children(node.children.values()))
        s.append(")")
        return "".join(s)

    def collect_children(self, children):
        s = []
        for c in children:
            t = self.to_term(c)
            if t:
                s.append(self.to_term(c))
        return ", ".join(s)

    def process_listnode(self, node):
        s = []
        s.append("[")
        s.append(self.collect_children(node.children))
        s.append("]")
        return "".join(s)

    def process_nonterm(self, node):
        from grammar_parser.bootstrap import AstNode, ListNode
        if not isinstance(node, AstNode) and not isinstance(node, ListNode) and node.alternate:
            return self.to_term(node.alternate)
        s = []
        s.append(node.symbol.name)
        s.append("(")
        children = []
        for c in node.children:
            text = self.to_term(c)
            if text:
                children.append(text)
        s.append(", ".join(children))
        s.append(")")
        return "".join(s)

    def process_term(self, node):
        s = []
        s.append(node.lookup)
        s.append("(\"")
        s.append(repr(node.symbol.name))
        s.append("\")")
        return "".join(s)

def export(start):
    return ATerms().to_term(start)
