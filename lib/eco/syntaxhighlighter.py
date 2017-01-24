# Copyright (c) 2013--2014 King's College London
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

from PyQt4.Qt import QPalette
from PyQt4.QtCore import QSettings
from grammar_parser.gparser import MultiTerminal

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

    gb_colors = {
        "red": "#FB4934",
        "green": "#B8BB26",
        "yellow": "#FABD2F",
        "blue": "#83A598",
        "purple": "#A791B6",
        "cyan": "#8EC07C",
        "grey": "#A89984",
    }
    keyword_colors = {}
    keyword_style = {}
    parent_colors = {}

    def __init__(self, palette):
        self.palette = palette
        settings = QSettings("softdev", "Eco")
        theme = settings.value("app_theme", "Light (Default)")
        if theme == "Gruvbox":
            self.colors = self.gb_colors

    def get_color(self, node):
        if isinstance(node.symbol.name, list):
            if node.lookup in self.keyword_colors:
                color = self.keyword_colors[node.lookup]
            else:
                color = "default"
            return self.colors[color]
        parent = node.parent
       #if parent:
       #    while parent.symbol.name.startswith("*match_until"):
       #        parent = parent.parent
        if parent and type(parent.symbol) is MultiTerminal:
            return self.get_color(parent)
        if parent and parent.symbol.name in self.parent_colors:
            color = self.parent_colors[parent.symbol.name]
        elif node.symbol.name in self.keyword_colors:
            color = self.keyword_colors[node.symbol.name]
        elif node.lookup in self.keyword_colors:
            color = self.keyword_colors[node.lookup]
        else:
            color = "default"

        if color == "default":
            hexcode = self.palette.color(QPalette.Text)
        else:
            hexcode = self.colors[color]
        return hexcode

    def get_default_color(self):
        return self.palette.color(QPalette.Text)

    def get_style(self, node):
        if not isinstance(node.symbol.name, list) and node.symbol.name in self.keyword_style:
            return self.keyword_style[node.symbol.name]
        elif node.lookup in self.keyword_style:
            return self.keyword_style[node.lookup]
        return "normal"

class PythonHighlighter(SyntaxHighlighter):
    keyword_colors = {
        "import": "red",
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
        "HEX": "cyan",
        "OCTAL": "cyan",
        "BINARY": "cyan",
        "STRING": "cyan",
        "range":"blue",
        "list":"blue",
        "set":"blue",
        "dict":"blue",
        "len":"blue",
        "reversed":"blue",
        "isinstance":"blue",
        "print":"blue",
        "True":"blue",
        "False":"blue",
    }

    parent_colors = {
        "slcomment": "grey",
        "single_string": "cyan",
        "multiline_string": "cyan"
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

class JavaScriptHighlighter(SyntaxHighlighter):
    keyword_colors = {
        "var": "yellow",
        "while": "red",
        "for": "red",
        "if": "red",
        "else": "red",
        "typeof": "red",
        "return": "red",
        "break": "red",
        "delete": "red",
        "function": "cyan",
        "float": "purple",
        "hex": "purple",
        "octal": "purple",
        "binary": "purple",
        "true": "purple",
        "false": "purple",
    }

    parent_colors = {
        "single_string": "cyan",
        "slcomment": "grey",
        "mlcomment": "grey"
    }

class SqlHighlighter(SyntaxHighlighter):
    keyword_colors = {
        "SELECT": "yellow",
        "FROM": "yellow",
        "WHERE": "yellow",
        "JOIN": "yellow",
        "INNER": "yellow",
        "OUTER": "yellow",
        "NATURAL": "yellow",
        "LEFT": "yellow",
        "RIGHT": "yellow",
        "ON": "yellow",
        "BETWEEN": "yellow",
        "INT_LITERAL": "red",
        "STRING_LITERAL": "cyan",
        # "IDENTIFIER": "blue",
        "QUOTED_IDENTIFIER": "purple",
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
        "NUMBER": "red",
        "%": "red",
        "true":"blue",
        "false":"blue"
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

class HtmlHighlighter(SyntaxHighlighter):
    keyword_colors = {
        "<html": "blue",
        "<head": "blue",
        "<body": "blue",
        "<table": "blue",
        "<tr": "blue",
        "<td": "blue",
        "<span": "blue",
        "<img": "blue",
        "<a": "blue",
        "<h1": "blue",
        "<h2": "blue",
        "<title": "blue",
        "<": "blue",
        ">": "blue",
        "</html>": "blue",
        "</head>": "blue",
        "</body>": "blue",
        "</table>": "blue",
        "</tr>": "blue",
        "</td>": "blue",
        "</span>": "blue",
        "</img>": "blue",
        "</a>": "blue",
        "</h1>": "blue",
        "</h2>": "blue",
        "</title>": "blue",
        "TEXT": "default",
        "STRING": "red",
        "NUMBER": "red",
        "COMMENT": "grey",
    }

class PhpHighlighter(SyntaxHighlighter):
    keyword_colors = {
        "T_CLASS": "green",
        "T_NAMESPACE": "green",
        "T_FUNCTION": "green",
        "T_STRING": "blue",
        "T_RETURN": "green"
    }
    keyword_style = {
        "static": "italic",
        "void": "bold",
        "int": "bold"
    }

    parent_colors = {
        "string": "cyan",
        "slcomment": "grey",
        "mlcomment": "grey"
    }

class SLHighlighter(SyntaxHighlighter):
    keyword_colors = {
        "id": "green",
        "numericLiteral": "purple",
        "stringLiteral": "blue",
        "function": "red",
        "while": "red",
        "if": "red",
        "else": "red",
        "return": "red",
        "break": "red",
        "continue": "red",
    }

    parent_colors = {
        "comment": "grey"
    }

class RubyHighlighter(SyntaxHighlighter):
    keyword_colors = {
        "alias": "blue",
        "class": "blue",
        "module": "blue",
        "def": "blue",
        "undef": "blue",
        "begin": "blue",
        "rescue": "blue",
        "ensure": "blue",
        "end": "blue",
        "if": "blue",
        "unless": "blue",
        "then": "blue",
        "elseif": "blue",
        "else": "blue",
        "case": "blue",
        "when": "blue",
        "while": "blue",
        "until": "blue",
        "for": "blue",
        "break": "blue",
        "next": "blue",
        "redo": "blue",
        "retry": "blue",
        "in": "blue",
        "do": "blue",
        "super": "blue",
        "self": "blue",
        "tIDENTIFIER": "yellow",
        "tCONSTANT": "green",
    }
    parent_colors = {
        "comment": "grey"
    }

def get_highlighter(parent, palette):
    if parent == "Java":
        return JavaHighlighter(palette)
    if parent == "JavaScript":
        return JavaScriptHighlighter(palette)
    if parent == "Python" or parent=="IPython":
        return PythonHighlighter(palette)
    if parent == "Sql":
        return SqlHighlighter(palette)
    if parent == "Prolog":
        return PrologHighlighter(palette)
    if parent == "Grammar":
        return GrammarHighlighter(palette)
    if parent == "Scoping":
        return ScopingrulesHighlighter(palette)
    if parent == "Html":
        return HtmlHighlighter(palette)
    if parent == "Php":
        return PhpHighlighter(palette)
    if parent == "SimpleLanguage":
        return SLHighlighter(palette)
    if parent == "Ruby":
        return RubyHighlighter(palette)
    return SyntaxHighlighter(palette)
