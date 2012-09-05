import re


RE_ID = re.compile("[a-zA-Z_][a-zA-Z0-9_]*")

class Class(object):
    def __init__(self, name):
        self.name = name
        self.functions = []

    def __repr__(self):
        return "class " + self.name + ": " + str(self.functions)

class Function(object):
    def __init__(self, name):
        self.name = name
        self.body = ""
        self.statements = []

    def __repr__(self):
        return "func " + str(self.name) + ": " + self.body

class Statement(object):
    def __init__(self, expression):
        self.expression = expression

class RecursiveDescentParser(object):

    def __init__(self, code):
        self.code = self.remove_whitespace(code)
        self.pos = 0
        self.elements = []

    def remove_whitespace(self, code):
        return re.sub("[ \t\n]", "", code)

    def parse(self):
        c = self.parse_class()
        self.elements.append(c)

    def parse_class(self):
        self.parse_string("class")
        name = self.parse_id()
        c = Class(name)
        self.parse_string("{")
        while self.code[self.pos] != "}":
            f = self.parse_function()
            c.functions.append(f)
        return c

    def parse_function(self):
        self.parse_string("function")
        name = self.parse_id()
        f = Function(name)
        self.parse_string("{")
        i = self.pos
        while self.code[self.pos] != "}":
            self.pos += 1
        code = self.code[i:self.pos]
        f.body = code
        return f

    def parse_string(self, s):
        if self.code[self.pos:self.pos+len(s)] != s:
            raise ParseError(char, self.code[self.pos])
        self.pos += len(s)

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
