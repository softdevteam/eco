import sys
import re

whitespace = "( |\n|\r|\t)+"
nonterminal = "[a-zA-Z_]+"  # e.g. E, T, Nonterminal
terminal = "\"([0-9]+|[a-zA-Z_]+|\+|-|\*|\/|\&|{|}|\t| |\n|\r|,|;)\""  # e.g. a, b, +, -
terminal = "\"[^\"]*\""  # everthing except ticks
mapsto = "::="
alternative = "\|"

def make_groups(expressions):
    regex = []
    for name in expressions:
        s = "(?P<%s>%s)" % (name, expressions[name])
        regex.append(s)
    return r"|".join(regex)

regex = make_groups({"Nonterminal":nonterminal, "Terminal":terminal, "Mapsto":mapsto,
                    "Whitespace":whitespace, "Alternative":alternative})

class Token(object):

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __repr__(self):
        return "%s(%s)" % (self.name, self.value)

class Lexer(object):

    def __init__(self, code):
        self.tokens = []
        self.code = code
        self.pos = 0
        self.regex = regex

    def set_regex(self, expressions):
        self.regex = make_groups(expressions)
        print(self.regex)

    def lex(self):
        token = self.next()
        while token is not None:
            self.pos += len(token.value)
            if token.name != "Whitespace":
                self.tokens.append(token)
            token = self.next()
        if self.pos == len(self.code):
            return True
        return False

    def next(self):
        m = re.match(self.regex, self.code[self.pos:])
        if m:
            result = m.groupdict()
            for r in result:
                value = result[r]
                if value is not None:
                    print("returning", r, value)
                    return Token(r, value)


if __name__ == "__main__":
    l = Lexer()
    l.lex(sys.argv[1])
