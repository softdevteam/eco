import re


RE_ID = re.compile("[a-zA-Z_][a-zA-Z0-9_]*")

class Class(object):
    def __init__(self, name):
        self.name = name
        self.functions = []

class Function(object):
    def __init__(self, name):
        self.name = name
        self.body = None
        self.statements = []

class Statement(object):
    def __init__(self, expression):
        self.expression = expression

class RecursiveDescentParser(object):

    def __init__(self, code):
        self.code = code
        self.pos = 0
        self.elements = []

    def skip_whitespace(self):
        while self.code[self.pos] in " \t\n":
            self.pos += 1

    def parse(self):
        self.skip_whitespace()
        c = self.parse_class()
        self.elements.append(c)

    def parse_class(self):
        if self.code[self.pos:self.pos+len("class")] != "class":
            return None
        self.skip_whitespace()
        name = self.parse_id()
        c = Class(name)
        self.parse_char("{")
        while self.code[self.pos] != "}":
            f = self.parse_func()
            c.functions.append(f)
        self.pos += 1
        return c

    def parse_function(self):
        self.skip_whitespace()
        name = self.parse_id()
        f = Function(name)
        self.parse_char("{")
        i = self.pos
        while self.code[self.pos] != "}":
            self.pos += 1
        code = self.code[self.pos - i]
        f.body = code
        return f

    def parse_char(self, char):
        if self.code[self.pos] != char:
            raise ParseError(char, self.code[self.pos])

    def parse_id(self):
        match = RE_ID.match(self.code[self.pos:])
        if not match:
            return None
        name = match.group(0)
        self.pos += len(name)
        return name

class ParseError(Exception):
    def __init__(self, expected, found):
        self.expected = expected
        self.found = found

    def __str__(self):
        return "Expected \"%s\" found \"%s\"." % (self.expected, self.found)

if __name__ == "__main__":
    s = """
class Test {

    function bla{
        2+3
    }

}
"""
    p = RecursiveDescentParser(s)
    p.parse()
    print(p.elements)
