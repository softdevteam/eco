import sys
import re

whitespace = " "
endoffile = "\n"

identifier = "[a-zA-Z]+"

class Token(object):

    def __init__(self, name, value):
        self.name = name
        self.value = value

class Lexer(object):

    def __init__(self):
        self.tokens = []

    def lex(self, code):
        m = re.match(identifier, code)
        if m:
            value = m.group(0)
            token = Token("Identifier", value)
            self.tokens.append(token)


if __name__ == "__main__":
    l = Lexer()
    l.lex(sys.argv[1])
