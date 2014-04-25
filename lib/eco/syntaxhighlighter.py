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

class SyntaxHighlighter(object):
    colors = {
        "green": "#859900",
        "red": "#DC322F",
        "blue": "#268BD2",
        "grey": "#839496",
        "cyan": "#2AA198",
        "yellow": "#B58900",
        "purple": "#D33682",
        "default": "#333333"
    }
    keyword_colors = {}
    keyword_style = {}

    def get_color(self, node):
        if node.symbol.name in self.keyword_colors:
            color = self.keyword_colors[node.symbol.name]
        elif node.lookup in self.keyword_colors:
            color = self.keyword_colors[node.lookup]
        else:
            color = "default"
        hexcode = self.colors[color]
        return hexcode

    def get_style(self, node):
        if node.symbol.name in self.keyword_style:
            return self.keyword_style[node.symbol.name]
        elif node.lookup in self.keyword_style:
            return self.keyword_style[node.lookup]
        return "normal"

class PythonHighlighter(SyntaxHighlighter):
    keyword_colors = {
        "class": "green",
        "def": "green",
        "for": "green",
        "while": "green",
        "return": "green",
        "yield": "green",
        "pass": "green",
        "in": "green",
        "is": "green",
        "not": "green",
        "if": "green",
        "elif": "green",
        "else": "green",
        "and": "green",
        "or": "green",
        "<ws>": "grey",
        "object": "blue",
        "NUMBER": "cyan",
        "STRING": "cyan",
        "range":"blue",
        "list":"blue",
        "set":"blue",
        "dict":"blue",
        "len":"blue",
        "reversed":"blue",
        "isinstance":"blue",
    }

class JavaHighlighter(SyntaxHighlighter):
    keyword_colors = {
        "class": "green",
        "for": "green",
        "while": "green",
        "return": "green",
        "if": "green",
        "elif": "green",
        "else": "green",
        "<ws>": "grey",
        "object": "blue",
        "import": "red",
        "public": "yellow",
        "private": "yellow",
        "static": "yellow",
        "void": "yellow",
        "int": "yellow",
        "float": "yellow",
        "BOOLEAN_LITERAL": "cyan",
        "STRING_LITERAL": "cyan",
        "INTEGER_LITERAL": "cyan",
    }
    keyword_style = {
        "static": "italic",
        "void": "bold",
        "int": "bold"
    }

class SqlHighlighter(SyntaxHighlighter):
    keyword_colors = {
        "SELECT": "yellow",
        "FROM": "purple",
        "WHERE": "purple",
        "INTNUM": "red",
        "STRING": "red",
    }

class PrologHighlighter(SyntaxHighlighter):
    keyword_colors = {
        ":-": "red",
        "!": "purple",
        "is": "green",
        "append": "green",
        "findall": "green",
        ">": "green",
        "<": "green",
        "=": "green",
        "\\+": "green",
        "NUMBER": "cyan",
        "STRING": "cyan",
        "<ws>": "grey",
    }

class GrammarHighlighter(SyntaxHighlighter):
    keyword_colors = {
        "::=": "red",
        "|": "purple",
        "nonterminal": "cyan",
        "terminal": "green",
        "<ws>": "grey",
        "#": "red",
        "NUMBER": "red"
    }

class ScopingrulesHighlighter(SyntaxHighlighter):
    keyword_colors = {
        "surrounding": "blue",
        "subsequent": "blue",
        "defines": "red",
        "scopes": "red",
        "references": "red",
        "to": "red",
        "in": "red",
    }

def get_highlighter(parent):
    if parent == "Java":
        return JavaHighlighter()
    if parent == "Python":
        return PythonHighlighter()
    if parent == "Sql":
        return SqlHighlighter()
    if parent == "Prolog":
        return PrologHighlighter()
    if parent == "Grammar":
        return GrammarHighlighter()
    if parent == "Scoping":
        return ScopingrulesHighlighter()
    return SyntaxHighlighter()
