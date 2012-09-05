import re


RE_ID = re.compile("[a-zA-Z_][a-zA-Z0-9_]*")
RE_EXPR = re.compile("([0-9]+[\+\*-/])+[0-9]+")

class Class(object):
    def __init__(self, name):
        self.name = name
        self.functions = []

    def __repr__(self):
        return "class %s: %s" % (self.name, self.functions)

class Function(object):
    def __init__(self, name):
        self.name = name
        self.statements = []
        self.args = []

    def __repr__(self):
        return "func %s(%s) : %s " % (self.name, self.args, self.statements)

class Statement(object):
    def __init__(self, expression):
        self.expression = expression

    def __repr__(self):
        return self.expression

class Expression(Statement):
    pass

class RecursiveDescentParser(object):

    def __init__(self, code):
        self.code = self.remove_whitespace(code)
        self.pos = 0
        self.elements = []

    def remove_whitespace(self, code):
        return re.sub("[ \t\n]", "", code)

    def parse(self):
        while self.pos < len(self.code):
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
        self.pos += 1
        return c

    def parse_function(self):
        self.parse_string("function")
        name = self.parse_id()
        f = Function(name)

        args = self.parse_arguments()
        f.args.append(args)

        self.parse_string("{")
        i = self.pos
        while self.code[self.pos] != "}":
            self.pos += 1
        body = self.code[i:self.pos]
        statements = self.parse_statements(body)
        f.statements = statements
        self.pos += 1
        print("parsed function", f)
        return f

    def parse_arguments(self):
        args = []
        self.parse_string("(")
        while True:
            arg = self.parse_id()
            args.append(arg)
            try:
                self.parse_string(",")
            except ParseError:
                break
        self.parse_string(")")
        print("parsed args", args)
        return args

    def parse_statements(self, body):
        statements = []
        l = body.split(";")
        for s in l:
            if s == "":
                continue
            expr = self.parse_expression(s)
            if expr:
                statements.append(Expression(expr))
        print("Parsed statements", statements)
        return statements

    def parse_string(self, s):
        if self.code[self.pos:self.pos+len(s)] != s:
            raise ParseError(s, self)
        self.pos += len(s)

    def parse_id(self):
        match = RE_ID.match(self.code[self.pos:])
        if not match:
            return None
        name = match.group(0)
        self.pos += len(name)
        return name

    def parse_expression(self, code):
        match = RE_EXPR.match(code)
        if not match:
            return None
        expr = match.group(0)
        return expr


class ParseError(Exception):
    def __init__(self, expected, parser):
        self.expected = expected
        self.parser = parser

    def __str__(self):
        found = self.parser.code[self.parser.pos]
        return "Expected \"%s\" found \"%s\". (at: %s)" % (self.expected, found, self.parser.code[self.parser.pos:])

if __name__ == "__main__":
    s = """
class Test {

    function do1(i){
        2+3+4;
        1*2
    }

    function do2(a, b){5*4-3; 3+2}

}

class Test2{}
"""
    p = RecursiveDescentParser(s)
    p.parse()
    print(p.elements)
