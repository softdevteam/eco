from incparser.astree import AST, BOS, EOS, TextNode
from grammar_parser.gparser import Terminal, Nonterminal
from incparser.syntaxtable import FinishSymbol

class RubyLexer(object):
    def relex(self, node):
        return True

    def is_indentation_based(self):
        return False

class RubyParser(object):
    def __init__(self):
        self.previous_version = None
        self.error_node = None
        self.graph = None
        self.last_status = True

    def init_ast(self, magic_parent = None):
        bos = BOS(Terminal(""), 0, [])
        eos = EOS(FinishSymbol(), 0, [])
        bos.magic_parent = magic_parent
        eos.magic_parent = magic_parent
        bos.next_term = eos
        eos.prev_term = bos
        root = TextNode(Nonterminal("Root"), 0, [bos, eos])
        self.previous_version = AST(root)

    def inc_parse(self, line_indents = [], reparse=False):
        # XXX replace root with result of jruby parse
        pass

    def save_status(self, version):
        pass
