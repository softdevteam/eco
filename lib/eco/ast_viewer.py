# Copyright (c) 2012--2014 King's College London
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

"""Program for quick viewing the AST of a given program using a given annotated grammar"""

from viewer import Viewer
from grammars.grammars import python275_annotated
from treemanager import TreeManager
from incparser.incparser import IncParser
from inclexer.inclexer import IncrementalLexer
from incparser.astree import BOS, EOS

grammar = python275_annotated
whitespace = True

lexer = IncrementalLexer(grammar.priorities)
parser = IncParser(grammar.grammar, 1, whitespace)
parser.init_ast()
ast = parser.previous_version
treemanager = TreeManager()
treemanager.add_parser(parser, lexer, grammar.name)
treemanager.set_font_test(7, 17) # hard coded. PyQt segfaults in test suite

inputstring = """import abc.xyz as efg
from x import z

class Test:
    def x():
        if x == 1:
            z = 3 + 4 * 5
        elif x == 2:
            for x in range(2,10):
                print x
        else:
            z = 4
        return 1 if a==b else 2"""

treemanager.import_file(inputstring)

viewer = Viewer("pydot")
viewer.get_tree_image(treemanager.get_mainparser().previous_version.parent, [], whitespace, ast=True)
import os
os.system("xdg-open " + viewer.image)
