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
        self.rules = {}
        self.lrules = []
        self.start_symbol = None
        self.incparser = None
        self.inclexer = None

    def parse(self, ecogrammar):
        self.lexer = IncrementalLexer(grammar.priorities)
        self.parser = IncParser(grammar.grammar, 1, True)
        self.parser.init_ast()
        self.ast = self.parser.previous_version.parent
        self.treemanager = TreeManager()
        self.treemanager.add_parser(self.parser, self.lexer, grammar.name)
        self.treemanager.import_file(ecogrammar)
        if self.parser.last_status == False:
            raise Exception("Invalid input grammar: at %s %s" % (self.parser.error_node.prev_term, self.parser.error_node))
        self.create_parser()
        self.create_lexer()

    def create_parser(self, pickle_id = None):
        startrule = self.ast.children[1] # startrule
        grammar = startrule.children[1]
        parser = grammar.children[0]
        assert parser.symbol.name == "parser"
        self.parse_rules(parser)

        if self.whitespaces:
            ws_rule = Rule()
            ws_rule.symbol = Nonterminal("WS")
            ws_rule.add_alternative([Terminal("<ws>"), Nonterminal("WS")])
            ws_rule.add_alternative([Terminal("<return>"), Nonterminal("WS")])
            ws_rule.add_alternative([]) # or empty
            self.rules[ws_rule.symbol] = ws_rule

            # allow whitespace/comments at beginning of file
            start_rule = Rule()
            start_rule.symbol = Nonterminal("Startrule")
            start_rule.add_alternative([Nonterminal("WS"), self.start_symbol])
            self.rules[start_rule.symbol] = start_rule
            self.start_symbol = start_rule.symbol

        incparser = IncParser()
        incparser.from_dict(self.rules, self.start_symbol, self.lr_type, self.whitespaces, pickle_id)
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
            annotation = None
            if len(node.children) > 1:
                annotation = self.parse_annotation(node.children[1])
            return (symbols, annotation)
        else:
            return ([], None)

    def parse_symbols(self, node):
        if node.children[0].symbol.name == "symbols":
            symbols = self.parse_symbols(node.children[0])
            symbol = self.parse_symbol(node.children[1])
            symbols.append(symbol)
            if isinstance(symbol, Terminal) and self.whitespaces:
                symbols.append(Nonterminal("WS"))
            return symbols
        elif node.children[0].symbol.name == "symbol":
            l = []
            symbol = self.parse_symbol(node.children[0])
            l.append(symbol)
            if isinstance(symbol, Terminal) and self.whitespaces:
                l.append(Nonterminal("WS"))
            return l

    def parse_symbol(self, node):
        node = node.children[0]
        if node.lookup == "nonterminal":
            return Nonterminal(node.symbol.name)
        elif node.lookup == "terminal":
            return Terminal(node.symbol.name[1:-1])

    def parse_annotation(self, node):
        a_options = node.children[2]
        assert a_options.symbol.name == "a_options"
        if a_options.children[0].symbol.name == "astnode":
            return self.parse_astnode(a_options.children[0])
        elif a_options.children[0].symbol.name == "expression":
            return self.parse_expression(a_options.children[0])
        elif a_options.children[0].symbol.name == "foreach":
            return self.parse_foreach(a_options.children[0])

    def parse_astnode(self, node):
        name = node.children[0].symbol.name
        children = self.parse_astnode_children(node.children[4])
        d = {}
        for n, expr in children:
            d[n] = expr
        return AstNode(name, d)

    def parse_astnode_children(self, node):
        assert node.symbol.name == "astnode_children"
        if node.children[0].symbol.name == "astnode_child":
            return [self.parse_astnode_child(node.children[0])]
        elif node.children[0].symbol.name == "astnode_children":
            children = self.parse_astnode_children(node.children[0])
            child = self.parse_astnode_child(node.children[3])
            children.append(child)
            return children

    def parse_astnode_child(self, node):
        assert node.symbol.name == "astnode_child"
        name = node.children[0].symbol.name
        if node.children[4].symbol.name == "expression":
            expr = self.parse_expression(node.children[4])
        elif node.children[4].symbol.name == "reference":
            expr = self.parse_reference(node.children[4])
        return (name, expr)

    def parse_expression(self, node):
        if node.children[0].symbol.name == "node":
            return self.parse_node(node.children[0])
        elif node.children[0].symbol.name == "list":
            return self.parse_list(node.children[0])
        elif node.children[0].symbol.name == "node_ref":
            return self.parse_noderef(node.children[0])
        else:
            expr1 = self.parse_expression(node.children[0])
            if node.children[3].symbol.name == "node":
                expr2 = self.parse_node(node.children[3])
            else:
                expr2 = self.parse_list(node.children[3])
            return AddExpr(expr1, expr2)

    def parse_foreach(self, node):
        item = self.parse_node(node.children[4])
        expr = self.parse_astnode(node.children[7])
        return Foreach(node.symbol.name, item, expr)

    def parse_noderef(self, node):
        lookup = self.parse_node(node.children[0])
        attr = node.children[3]
        lookup.attribute = attr.symbol.name
        return lookup

    def parse_node(self, node):
        return LookupExpr(int(node.children[2].symbol.name))

    def parse_list(self, node):
        return ListExpr(self.parse_listloop(node.children[2]))

    def parse_reference(self, node):
        base = node.children[0].symbol.name
        ref = node.children[4].symbol.name
        return ReferenceExpr(base, ref)

    def parse_listloop(self, node):
        if node.children[0].symbol.name == "list_loop":
            l = self.parse_listloop(node.children[0])
            element = self.parse_unknown(node.children[3])
            l.append(element)
            return l
        else:
            return [self.parse_unknown(node.children[0])]

    def parse_unknown(self, node):
        if node.symbol.name == "node":
            return self.parse_node(node)
        elif node.symbol.name == "astnode":
            return self.parse_astnode(node)

    def create_lexer(self):
        startrule = self.ast.children[1] # startrule
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

class AstNode(object):
    def __init__(self, name, children):
        self.name = name
        self.children = children

    def __eq__(self, other):
        return self.name == other.name and self.children == other.children

    def interpret(self, node, reference=None):
        d = {}
        for c in self.children:
            if isinstance(self.children[c], ReferenceExpr):
                ref = self.children[c].interpret(reference)
                if ref:
                    d[c] = ref
            else:
                d[c] = self.children[c].interpret(node)
        return AstNode(self.name, d)

    def __repr__(self):
        return "AstNode(%s, %s)" % (self.name, self.children)

    def __getattribute__(self, name):
        if name == "symbol":
            return self
        if name == "changed":
            return False
        return object.__getattribute__(self, name)

    def get(self, name):
        if self.children.has_key(name):
            return self.children[name]

class Expr(object):
    pass

class Foreach(object):
    def __init__(self, name, item, expression):
        self.name = name
        self.item = item
        self.expression = expression

    def interpret(self, node):
        item = self.item.interpret(node)
        assert isinstance(item, ListNode)
        l = []
        for c in item.children:
            expr = self.expression.interpret(node, c)
            l.append(expr)
        return ListNode(node.symbol.name, l)


    def __eq__(self, other):
        return self.item == other.item and self.expression == other.expression

    def __repr__(self):
        return "Foreach(%s, %s, %s)" % (self.name, self.item, self.expression)

class LookupExpr(Expr):
    def __init__(self, number, attribute=None):
        self.number = number
        self.attribute = attribute

    def __eq__(self, other):
        return self.number == other.number and self.attribute == other.attribute

    def interpret(self, node):
        # skip whitespaces
        i = 0
        n = None
        for c in node.children:
            if c.symbol.name != "WS":
                if i == self.number:
                    n = c
                    break
                i += 1

        if n is None:
            return

        if n.alternate:
            n = n.alternate

        if self.attribute:
            return n.get(self.attribute)
        return n

    def __repr__(self):
        return "LookupExpr(%s, %s)" % (self.number, self.attribute)

class ReferenceExpr(Expr):
    def __init__(self, base, reference):
        self.base = base
        self.reference = reference

    def __eq__(self, other):
        return self.base == other.base and self.reference == other.reference

    def interpret(self, reference):
        assert isinstance(reference, AstNode)
        try:
            x = reference.children[self.reference]
        except KeyError:
            x = None
        return x

    def __repr__(self):
        return "ReferenceExpr(%s, %s)" % (self.base, self.reference)

class AddExpr(Expr):
    def __init__(self, expr1, expr2):
        self.expr1 = expr1
        self.expr2 = expr2

    def __eq__(self, other):
        return self.expr1 == other.expr1 and self.expr2 == other.expr2

    def interpret(self, node):
        expr1 = self.expr1.interpret(node)
        expr2 = self.expr2.interpret(node)
        assert isinstance(expr1, ListNode)
        assert isinstance(expr2, ListNode)
        return expr1 + expr2

    def __repr__(self):
        return "AddExpr(%s, %s)" % (self.expr1, self.expr2)

class ListExpr(Expr):
    def __init__(self, l):
        self.elements = l

    def __eq__(self, other):
        return self.elements == other.elements

    def __repr__(self):
        return "ListExpr(%s)" % (self.elements)

    def interpret(self, node):
        l = []
        for e in self.elements:
            l.append(e.interpret(node))
        return ListNode(node.symbol.name, l)

class ListNode(object):
    def __init__(self, name, l):
        self.name = name
        self.children = l

    def __add__(self, other):
        if isinstance(other, ListNode):
            l = self.children + other.children
            return ListNode(self.name, l)
        raise TypeError("cannot concatenate ListNode and %s" % type(other))

    def __getattribute__(self, name):
        if name == "symbol":
            return self
        if name == "changed":
            return False
        return object.__getattribute__(self, name)

    def __repr__(self):
        return "ListNode(%s, %s)" % (self.name, self.children)
