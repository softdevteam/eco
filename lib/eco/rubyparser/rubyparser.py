from grammars.grammars import EcoFile
from export.jruby import JRubyExporter
from incparser.astree import AST, BOS, EOS, TextNode
from grammar_parser.gparser import Terminal, Nonterminal
from incparser.syntaxtable import FinishSymbol

import subprocess
import tempfile

lexingrules = [
        ("<ws>", "[ \t]"),
        ("<return>", "[\n\r]"),
        ("alias", "alias"),
        ("class", "class"),
        ("module", "module"),
        ("module", "module"),
        ("def", "def"),
        ("undef", "undef"),
        ("begin", "begin"),
        ("rescue", "rescue"),
        ("ensure", "ensure"),
        ("end", "end"),
        ("if", "if"),
        ("unless", "unless"),
        ("then", "then"),
        ("elseif", "elseif"),
        ("else", "else"),
        ("case", "case"),
        ("when", "when"),
        ("while", "while"),
        ("until", "until"),
        ("for", "for"),
        ("break", "break"),
        ("next", "next"),
        ("redo", "redo"),
        ("retry", "retry"),
        ("in", "in"),
        ("do", "do"),
        ("super", "super"),
        ("self", "self"),
        ("tIDENTIFIER", "[a-z_][a-zA-Z_0-9]*"),
        ("tCONSTANT", "[A-Z][a-zA-Z_0-9]*"),
        ("rest", ".")
        ]

class RubyProxy(EcoFile):

    def __init__(self):
        self.name = "Ruby"
        self.base = "Ruby"
        self.filename = ""

    def load(self):
        from inclexer.inclexer import IncrementalLexerCF
        lexer = IncrementalLexerCF()
        names = []
        regexs = []
        for n, r in lexingrules:
            names.append(n)
            regexs.append(r)
        lexer.from_name_and_regex(names, regexs)
        parser = RubyParser()
        parser.init_ast()
        return parser, lexer

    def __str__(self):
        return self.name

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

    def get_next_symbols_list(self, state=-1):
        return []

    def save_status(self, version):
        pass
