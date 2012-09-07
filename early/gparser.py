from lexer import Lexer

class Rule(object):

    def __init__(self):
        self.symbol = None
        self.alternatives = []

    def __repr__(self):
        return "Rule(%s => %s)" % (self.symbol, self.alternatives)

class Terminal(object):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "Terminal(%s)" % (self.name,)

    def __eq__(self, other):
        if other.__class__ != self.__class__:
            return False
        return self.name == other.name

class Nonterminal(object):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "Nonterminal(%s)" % (self.name,)

    def __eq__(self, other):
        if other.__class__ != self.__class__:
            return False
        return self.name == other.name

class Parser(object):

    def __init__(self, code):
        self.lexer = Lexer(code)
        self.lexer.lex()
        self.curtok = 0
        self.rules = []

    def __repr__(self):
        s = []
        for r in self.rules:
            s.append(r.__repr__())
        return "\n".join(s)

    def parse(self):
        while self.curtok < len(self.lexer.tokens):
            rule = self.parse_rule()
            self.rules.append(rule)

    def inc(self):
        self.curtok += 1

    def next_token(self):
        t = self.lexer.tokens[self.curtok]
        return t

    def parse_rule(self):
        rule = Rule()
        rule.symbol = self.parse_nonterminal()

        self.parse_mappingsymbol()

        # find beginning of next rule
        i = self.curtok
        while i < len(self.lexer.tokens):
            if self.lexer.tokens[i].name == "Mapsto":
                i = i - 1 # go back to end of last rule
                break
            i += 1

        tokenlist = self.lexer.tokens[self.curtok:i]
        print(tokenlist)

        # skip to next rule for further parsing
        self.curtok += len(tokenlist)

        # parse right side of rule
        symbols = []
        for t in tokenlist:
            if t.name == "Nonterminal":
                symbols.append(Nonterminal(t.value))
            if t.name == "Terminal":
                symbols.append(Terminal(t.value))
            if t.name == "Alternative":
                rule.alternatives.append(symbols)
                symbols = []
        rule.alternatives.append(symbols)
        return rule

    def parse_nonterminal(self):
        t = self.next_token()
        assert t.name == "Nonterminal"
        self.inc()
        return Nonterminal(t.value)

    def parse_mappingsymbol(self):
        t = self.next_token()
        assert t.name == "Mapsto"
        self.inc()
