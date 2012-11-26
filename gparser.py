from lexer import Lexer

class Rule(object):

    def __init__(self):
        self.symbol = None
        self.alternatives = []

    def add_alternative(self, alternative):
        # create symbol for empty alternative
        #if alternative == []:
        #    alternative = [Epsilon()]
        self.alternatives.append(alternative)

    def __repr__(self):
        return "Rule(%s => %s)" % (self.symbol, self.alternatives)

class Symbol(object):
    def __init__(self, name=""):
        try:
            self.name = name.strip("\"")
        except AttributeError:
            raise Exception("Symbol name is not a string:", name)

    def __eq__(self, other):
        if other.__class__ != self.__class__:
            return False
        return self.name == other.name

    def __hash__(self):
        #XXX unsafe hashfunction
        return hash(self.__class__.__name__ + self.name)

class Terminal(Symbol):
    def __repr__(self):
        return "Terminal(%s)" % (self.name,)

class Nonterminal(Symbol):
    def __repr__(self):
        return "Nonterminal(%s)" % (self.name,)

class Epsilon(Symbol):

    def __eq__(self, other):
        return isinstance(other, Epsilon)

    def __repr__(self):
        return self.__class__.__name__

    def __hash__(self):
        #XXX why doesn't Epsilon inherit this method from Symbol!?
        return hash(self.__class__.__name__ + self.name)

class Parser(object):

    def __init__(self, code):
        self.lexer = Lexer(code)
        self.lexer.lex()
        self.curtok = 0
        self.start_symbol = None
        self.rules = {}

    def __repr__(self):
        s = []
        for r in self.rules:
            s.append(r.__repr__())
        return "\n".join(s)

    def parse(self):
        while self.curtok < len(self.lexer.tokens):
            rule = self.parse_rule()
            self.rules[rule.symbol] = rule
            if not self.start_symbol:
                self.start_symbol = rule.symbol

        # add whitespace rule
        ws_rule = Rule()
        ws_rule.symbol = Nonterminal("WS")
        ws_rule.add_alternative([Terminal("_")])
        ws_rule.add_alternative([]) # or empty
        self.rules[ws_rule.symbol] = ws_rule

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

        # skip to next rule for further parsing
        self.curtok += len(tokenlist)

        # parse right side of rule
        symbols = []
        for t in tokenlist:
            if t.name == "Nonterminal":
                symbols.append(Nonterminal(t.value))
            if t.name == "Terminal":
                symbols.append(Terminal(t.value))
                symbols.append(Nonterminal("WS"))
            if t.name == "Alternative":
                rule.add_alternative(symbols)
                symbols = []
        rule.add_alternative(symbols)
        return rule

    def add_implicit_whitespaces(self, l):
        return l
        with_whitespaces = []
        for e in l:
            with_whitespaces.append(e)
            if e is not l[-1]:
                with_whitespaces.append(Terminal("WS"))
        return with_whitespaces

    def parse_nonterminal(self):
        t = self.next_token()
        assert t.name == "Nonterminal"
        self.inc()
        return Nonterminal(t.value)

    def parse_mappingsymbol(self):
        t = self.next_token()
        assert t.name == "Mapsto"
        self.inc()
