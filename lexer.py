import sys
import re

whitespace = "( |\n|\r|\t)+"
nonterminal = "[a-zA-Z_0-9]+"  # e.g. E, T, Nonterminal
terminal = "\"([0-9]+|[a-zA-Z_]+|\+|-|\*|\/|\&|{|}|\t| |\n|\r|,|;)\""  # e.g. a, b, +, -
terminal = "\"[^\"]*\""  # everthing except ticks
mapsto = "::="
alternative = "\|"
option_start = "\["
option_end = "\]"
loop_start = "\{"
loop_end = "\}"
group_start = "\("
group_end = "\)"

def make_groups(expressions):
    regex = []
    for name in expressions:
        s = "(?P<%s>%s)" % (name, expressions[name])
        regex.append(s)
    return r"|".join(regex)

regex = make_groups({"Nonterminal":nonterminal, "Terminal":terminal, "Mapsto":mapsto,
                    "Whitespace":whitespace, "Alternative":alternative, "Option_Start":option_start,
                    "Option_End":option_end, "Loop_Start":loop_start, "Loop_End":loop_end,
                    "Group_Start":group_start, "Group_End": group_end})

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
                    return Token(r, value)


if __name__ == "__main__":
    l = Lexer()
    l.lex(sys.argv[1])
