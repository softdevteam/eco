import sys
import re

whitespace = " "
endoffile = "\n"

identifier = "[a-zA-Z]+"
assignment = ":="
operation = "\+|-|\*|\/"
conjunction = "\;"
newrule = "\n"
integer = "INT"

def make_groups(**expressions):
    regex = []
    for name in expressions:
        s = "(?P<%s>%s)" % (name, expressions[name])
        regex.append(s)
    return r"|".join(regex)

regex = make_groups(Identifier=identifier, Assignment=assignment, Whitespace=whitespace,
                    Operation=operation, Newrule=newrule, Integer=integer, Conjunction=conjunction)

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

    def lex(self):
        self.tokens.append(Token("Newrule", ""))
        token = self.next()
        while token is not None:
            self.pos += len(token.value)
            if token.name not in ["Whitespace"]:
                self.tokens.append(token)
            token = self.next()

    def next(self):
        m = re.match(regex, self.code[self.pos:])
        if m:
            result = m.groupdict()
            for r in result:
                value = result[r]
                if value is not None:
                    return Token(r, value)


if __name__ == "__main__":
    l = Lexer()
    l.lex(sys.argv[1])
