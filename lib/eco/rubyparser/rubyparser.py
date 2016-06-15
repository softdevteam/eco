from export.jruby import JRubyExporter
from incparser.astree import AST, BOS, EOS, TextNode
from grammar_parser.gparser import Terminal, Nonterminal
from incparser.syntaxtable import FinishSymbol

import subprocess
import tempfile

class RubyLexer(object):
    def relex(self, node):
        return True

    def is_indentation_based(self):
        return False

class LineDummy(object):
    def __init__(self, node):
        self.node = node

class DummyTM(object):
    def __init__(self, node):
        self.lines = [LineDummy(node)]

class RubyParser(object):
    def __init__(self):
        self.previous_version = None
        self.error_node = None
        self.graph = None
        self.last_status = True
        self.whitespaces = True

    def init_ast(self, magic_parent = None):
        bos = BOS(Terminal(""), 0, [])
        eos = EOS(FinishSymbol(), 0, [])
        bos.magic_parent = magic_parent
        eos.magic_parent = magic_parent
        bos.next_term = eos
        eos.prev_term = bos
        root = TextNode(Nonterminal("Root"), 0, [bos, eos])
        self.previous_version = AST(root)

    def _find_node(self, lineno, charno):
        node = self.previous_version.parent.children[0]
        current_line = 1
        current_charno = 0
        while True:
            node = node.next_term
            if isinstance(node, EOS):
                return node
            if node.lookup == "<return>":
                current_line += 1
                current_charno = 0
                continue
            current_charno += len(node.symbol.name)
            if current_line == lineno and current_charno >= charno:
                return node

    def inc_parse(self, line_indents = [], reparse=False):
        self.last_status = True
        self.error_node = None
        exporter = JRubyExporter(DummyTM(self.previous_version.parent.children[0]))
        f = tempfile.mkstemp(suffix=".rb")
        exporter.export(path=f[1])
        proc = subprocess.Popen(["ruby-parse", f[1]],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        stdout, _ = proc.communicate()
        for line in stdout.split('\n'):
            if line.startswith('warning:'):
                continue
            if line.startswith(f[1]):
                tokens = line.split(':')
                self.error_node = self._find_node(int(tokens[1]), int(tokens[2]))
                self.last_status = False
                return

    def reparse(self):
        self.inc_parse()

    def save_status(self, version):
        pass
