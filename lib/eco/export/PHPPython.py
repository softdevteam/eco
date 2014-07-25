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

import helper
from incparser.astree import BOS, EOS, TextNode
from grammar_parser.gparser import MagicTerminal, IndentationTerminal
import re
import logging

class PHP(helper.Generic):

    def __init__(self):
        self.nestings = []
        self.bracklvl = 0
        self.buf = []
        self.embed = []

    def language_box(self, name, node):
        if name == "<Python + PHP>":
            buf = Python().pp(node)
            if self.in_class():
                # put PHP func in here and store embed for later
                phpfunc = self.convert_py_to_php(buf)
                self.buf.append(phpfunc)

                # rename py function
                text = re.sub("def\s+([a-zA-Z_][a-zA-Z0-9_]*)",r"def py_\1", buf)
                self.embed.append(text)
            else:
                self.buf.append("embed_py_func(\"%s\");" % (_escapepy(buf)))

    def walk(self, node):
        while True:
            node = node.next_term
            sym = node.symbol
            if isinstance(node, EOS):
                break
            assert isinstance(node, TextNode)
            if isinstance(sym, MagicTerminal):
                self.language_box(sym.name, node.symbol.ast.children[0])
            elif isinstance(sym, IndentationTerminal):
                pass
            elif sym.name == "\r":
                self.text("\n")
            else:
                self.text(sym.name)

            # collect information about classes and brackets
            if sym.name == "class":
                self.nestings.append(("class", self.bracklvl))
            elif sym.name == "function":
                self.nestings.append(("function", self.bracklvl))
            elif sym.name == "{":
                self.bracklvl += 1
            elif sym.name == "}":
                self.bracklvl -= 1
                if self.nestings and self.bracklvl == self.nestings[-1][1]:
                    # release lbox functions
                    c = self.nestings.pop()
                    if c[0] == "class":
                        for e in self.embed:
                            self.buf.append("\nembed_py_func(\"%s\");" % (_escapepy(e)))
                            self.embed.pop()

    def in_class(self):
        return self.nestings and self.nestings[-1][0] == "class"

    def convert_py_to_php(self, text):
        name = re.match("def\s+([a-zA-Z_][a-zA-Z0-9_]*)", text).group(1)
        params = re.match(".*\((.*)\)\s*:", text).group(1).replace(" ", "").split(",")
        if params == [""]:
            logging.error("emebbed python function needs 'self' parameter")
        params = params[1:]
        newparams = []
        for p in params:
            if p != "":
                newparams.append("$"+p)

        if newparams:
            args = "$this, %s" % (", ".join(newparams))
        else:
            args = "$this"
        phpfunc = "function %s(%s){return py_%s(%s);}" % (name, ",".join(newparams), name, args)
        return phpfunc

class Python(helper.Generic):
    def language_box(self, name, node):
        if name == "<PHP + Python>":
            buf = PHP().pp(node)
            self.buf.append("embed_php_func(\"\"\"\n%s\n\"\"\")" % (_escape(buf)))

def _escapepy(s):
    return s.replace("\\", "\\\\").replace("\"", "\\\"").replace("'", "\\'").replace("\n", "\\n").replace("$", "\$")

def _escape(s):
    return s.replace("\\", "\\\\").replace("\"", "\\\"").replace("'", "\\'")

def export(node):
    return "<?php\n%s\n?>" % (PHP().pp(node),)
