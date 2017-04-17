import os, tempfile, json, subprocess

from incparser.astree import TextNode, BOS, EOS, ImageNode, FinishSymbol
from grammar_parser.gparser import Terminal, MagicTerminal, IndentationTerminal, Nonterminal

from .lspace import Text, Row, Column, Flow, Pres, Colour, ApplyStyleSheet, viewer


class EcoDocToken (object):
    """
    Token to export to LSpace via JSON
    """
    def __init__(self, text):
        self.text = text

    def __present__(self):
        return Text(self.text)


class EcoDocLine (object):
    """
    Line to export to LSpace via JSON
    """
    def __init__(self):
        self.tokens = []

    def token(self, token):
        self.tokens.append(token)

    def __present__(self):
        return Row(self.tokens)


class EcoDoc (object):
    """
    Document to export to LSpace via JSON
    """
    def __init__(self):
        self.lines = []
        self._current_line = None

    def _get_current_line(self):
        if self._current_line is None:
            self._current_line = EcoDocLine()
            self.lines.append(self._current_line)
        return self._current_line

    def new_line(self):
        if self._current_line is None:
            self._current_line = EcoDocLine()
            self._current_line.token(EcoDocToken(" "))
            self.lines.append(self._current_line)
        self._current_line = None

    def token(self, token):
        return self._get_current_line().token(token)

    def __present__(self):
        title = ApplyStyleSheet(Text('Eco Document'), text_size=20.0, text_weight='bold', text_colour=Colour(0.0, 0.3, 0.4))
        content = Column(self.lines)
        content = ApplyStyleSheet(content, text_font_family='Courier New', text_colour=Colour(0.4, 0.4, 0.4))
        return ApplyStyleSheet(Column([title, content]), column_y_spacing=20.0)


def view_in_lspace(tree_manager, lspace_root=None):
    """
    View the content of the given `TreeManager` in the LSpace eco_viewer tool

    tree_manager: a `TreeManager` instance that contains the document to render
    """
    node = tree_manager.lines[0].node # first node
    doc = EcoDoc()
    while True:
        node = node.next_term
        if isinstance(node.symbol, IndentationTerminal):
            continue
        if isinstance(node, EOS):
            lbnode = tree_manager.get_languagebox(node)
            if lbnode:
                node = lbnode
                continue
            else:
                break
        if isinstance(node.symbol, MagicTerminal):
            node = node.symbol.ast.children[0]
            continue
        if node.symbol.name == "\r":
            doc.new_line()
        else:
            doc.token(EcoDocToken(node.symbol.name))



    return viewer(doc, lspace_root=lspace_root)

