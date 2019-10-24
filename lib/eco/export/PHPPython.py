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

from . import helper
from incparser.astree import BOS, EOS, TextNode
from grammar_parser.gparser import MagicTerminal, IndentationTerminal
import re
import logging

class PHP(helper.Generic):

    def __init__(self, source=None):
        self.nestings = []
        self.variable_assignment = False
        self.bracklvl = 0
        self.buf = []
        self.embed = []
        self.used_funcs = set()
        self.lineno = 0
        self.source = source

    def language_box(self, name, node):
        if name == "<Python + PHP>":
            python = Python(self.source, self.lineno)
            buf = python.pp(node)

            if self.in_class():
                classname = self.get_classname()
                self.embed.append((classname, buf, self.lineno))
                for i in range(buf.count("\n")):
                    self.buf.append("\n")
            elif self.in_function():
                # $foo = compile_py_func(...)
                if self.variable_assignment:
                    self.buf.append("compile_py_func(\"%s\", \"%s\", %s);" % (_escapepy(buf), self.source, self.lineno))
                # compile_py_func(...)
                else:
                    name = re.match("(@.*\s)?def\s+([a-zA-Z_][a-zA-Z0-9_]*)", buf).group(2)
                    pyname = self.get_unused_name(name)
                    phpfunc = self.convert_py_to_php(buf, pyname, inclass = False)

                    # rename py function
                    text = re.sub("def\s+([a-zA-Z_][a-zA-Z0-9_]*)",r"def %s" % (pyname), buf, count = 1)
                    self.buf.append("\n$%s = compile_py_func(\"%s\", \"%s\", %s);" % (pyname, _escapepy(text), self.source, self.lineno))
                    self.buf.append("\n");
                    self.buf.append(phpfunc)
            else: # outside of a function we can use compile_py_func_global
                if self.variable_assignment:
                    self.buf.append("compile_py_func(\"%s\", \"%s\", %s);" % (_escapepy(buf), self.source, self.lineno))
                else:
                    self.buf.append("compile_py_func_global(\"%s\", \"%s\", %s);" % (_escapepy(buf), self.source, self.lineno))
                    newlines = buf.count("\n")
                    for i in range(newlines):
                        self.buf.append("\n")
            self.lineno += python.lineno - 1
        elif name == "<Python expression>":
            buf = PythonExpr().pp(node)
            self.buf.append("call_user_func(compile_py_func(\"f = lambda: %s;\"))" % (_escapepy(buf)))

    def walk(self, node):
        while True:
            if node.lookup == "<return>":
                self.lineno += 1
            node = node.next_term
            sym = node.symbol
            if isinstance(node, EOS):
                break
            assert isinstance(node, TextNode)
            if isinstance(sym, MagicTerminal):
                if node.parent.parent.symbol.name == "expr_without_variable":
                    self.variable_assignment = True
                self.language_box(sym.name, node.symbol.ast.children[0])
                self.variable_assignment = False
            elif isinstance(sym, IndentationTerminal):
                pass
            elif sym.name == "\r":
                self.text("\n")
            else:
                self.text(sym.name)

            # collect information about classes and brackets
            if sym.name == "class":
                tmp = node
                while tmp.lookup != "T_STRING":
                    tmp = tmp.next_term
                classname = tmp.symbol.name
                self.nestings.append(("class", self.bracklvl, classname))
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
                        self.embed.reverse()
                        while self.embed != []:
                            classname, func, lineno = self.embed.pop()
                            self.buf.append("compile_py_meth(\"%s\", \"%s\", \"%s\", %s);" % (classname, _escapepy(func), self.source, lineno))

    def in_class(self):
        return self.nestings and self.nestings[-1][0] == "class"

    def in_function(self):
        return self.nestings and self.nestings[-1][0] == "function"

    def get_classname(self):
        try:
            return self.nestings[-1][2]
        except Exception:
            return None

    def convert_py_to_php(self, text, pyname, inclass=True):
        name = re.match("(@.*\s)?def\s+([a-zA-Z_][a-zA-Z0-9_]*)", text).group(2)
        params = re.match("(@.*\s)?.*\((.*)\)\s*:", text).group(2).replace(" ", "").split(",")
        if params == [""] and inclass:
            logging.error("emebbed python function needs 'self' parameter")
        if inclass:
            params = params[1:] # delete self
        newparams = []
        for p in params:
            if p != "":
                newparams.append("$"+p)

        if newparams:
            args = "$this, %s" % (", ".join(newparams))
        else:
            args = "$this"
        if not inclass:
            args = args[6:] # remove $this if function is not within a class
        # create clean args without default values
        cleanargs = []
        for c in args.split(","):
            # delete everything from "="
            pos = c.find("=")
            if pos > 0:
                cleanargs.append(c[:pos])
            else:
                cleanargs.append(c)
        cleanargs = ",".join(cleanargs)

        paramstring = ", ".join(newparams)
        phpfunc = "function %s(%s){\n    global $%s;\n    return $%s(%s);\n}" % (name, paramstring, pyname, pyname, cleanargs)
        return phpfunc

    def get_unused_name(self, name):
        newname = "__pyhyp__" + name
        i = 1
        while newname in self.used_funcs:
            newname = "__pyhyp__" + name + str(i)
            i += 1
        self.used_funcs.add(newname)
        return newname

class Python(helper.Generic):
    def language_box(self, name, node):
        if name == "<PHP + Python>":
            php = PHP()
            buf = php.pp(node)
            self.buf.append("compile_php_func(\"\"\"%s\"\"\", \"%s\", %s)" % (_escape(buf), self.source, self.lineno + self.parent_ln - 1))
            self.lineno += php.lineno

class PythonExpr(Python):
    pass

def _escapepy(s):
    return s.replace("\\", "\\\\").replace("\"", "\\\"").replace("'", "\\'").replace("\n", "\\n").replace("$", "\$")

def _escape(s):
    return s.replace("\\", "\\\\").replace("\"", "\\\"").replace("'", "\\'")

def export(node, source=None):
    return "<?php{ %s\n}?>" % (PHP(source).pp(node),)
