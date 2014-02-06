from grammars.grammars import eco_grammar as grammar
from treemanager import TreeManager
from incparser.incparser import IncParser
from inclexer.inclexer import IncrementalLexer, IncrementalLexerCF
from incparser.astree import BOS, EOS

from grammar_parser.gparser import Rule, Nonterminal, Terminal, Epsilon

class BootstrapParser(object):

    def __init__(self, lr_type=1, whitespaces=False):
        self.lr_type = lr_type
        self.whitespaces = whitespaces
        # load (old) parser for grammar grammar
        self.lexer = IncrementalLexer(grammar.priorities)
        self.parser = IncParser(grammar.grammar, 1, True)
        self.parser.init_ast()
        self.ast = self.parser.previous_version
        self.treemanager = TreeManager()
        self.treemanager.add_parser(self.parser, self.lexer, grammar.name)
        self.rules = {}
        self.lrules = []
        self.start_symbol = None
        self.incparser = None
        self.inclexer = None

    def parse(self, ecogrammar):
        self.treemanager.import_file(ecogrammar)
        if self.parser.last_status == False:
            raise Exception("Invalid input grammar")
        self.create_parser()
        self.create_lexer()

    def create_parser(self):
        startrule = self.parser.previous_version.parent.children[1] # startrule
        grammar = startrule.children[1]
        parser = grammar.children[0]
        assert parser.symbol.name == "parser"
        self.parse_rules(parser)
        incparser = IncParser()
        incparser.from_dict(self.rules, self.start_symbol, self.lr_type, self.whitespaces)
        incparser.init_ast()
        self.incparser = incparser

    def parse_rules(self, node):
        if node.children[0].symbol.name == "parser":
            self.parse_rules(node.children[0])
            self.parse_rule(node.children[3])
        elif node.children[0].symbol.name == "rule":
            self.parse_rule(node.children[0])

    def parse_rule(self, node):
        name = node.children[0].symbol.name
        alternatives = self.parse_alternatives(node.children[4])
        symbol = Nonterminal(name)
        if self.start_symbol is None:
            self.start_symbol = symbol
        r = Rule(symbol)
        for a in alternatives:
            r.add_alternative(a[0], a[1])
        self.rules[symbol] = r

    def parse_alternatives(self, node):
        if node.children[0].symbol.name == "alternatives":
            alternatives = self.parse_alternatives(node.children[0])
            alternative = self.parse_alternative(node.children[3])
            alternatives.append(alternative)
            return alternatives
        elif node.children[0].symbol.name == "right":
            return [self.parse_alternative(node.children[0])]

    def parse_alternative(self, node):
        if len(node.children) > 0:
            symbols = self.parse_symbols(node.children[0])
            annotations = None
            if len(node.children) > 1:
                annotations = self.parse_annotations(node.children[1])
            return (symbols, annotations)
        else:
            return ([Epsilon()], None)

    def parse_symbols(self, node):
        if node.children[0].symbol.name == "symbols":
            symbols = self.parse_symbols(node.children[0])
            symbol = self.parse_symbol(node.children[1])
            symbols.append(symbol)
            return symbols
        elif node.children[0].symbol.name == "symbol":
            return [self.parse_symbol(node.children[0])]

    def parse_symbol(self, node):
        node = node.children[0]
        if node.lookup == "nonterminal":
            return Nonterminal(node.symbol.name)
        elif node.lookup == "terminal":
            return Terminal(node.symbol.name[1:-1])

    def parse_annotations(self, node):
        pass

    def create_lexer(self):
        startrule = self.parser.previous_version.parent.children[1] # startrule
        grammar = startrule.children[1]
        lexer = grammar.children[5]
        assert lexer.symbol.name == "lexer"
        self.parse_lexer(lexer)
        names = []
        regexs = []
        for name, regex in self.lrules:
            names.append(name)
            regexs.append(regex)
        self.inclexer = IncrementalLexerCF()
        self.inclexer.from_name_and_regex(names, regexs)

    def parse_lexer(self, lexer):
        if lexer.children[0].symbol.name == "lrule":
            self.parse_lrule(lexer.children[0])
        elif lexer.children[0].symbol.name == "lexer":
            self.parse_lexer(lexer.children[0])
            self.parse_lrule(lexer.children[1])

    def parse_lrule(self, lrule):
        assert lrule.children[0].symbol.name == "tokenname"
        name = lrule.children[0].children[0].symbol.name
        regex = lrule.children[3].symbol.name[1:-1]
        self.lrules.append((name, regex))
