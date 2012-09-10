import re


RE_ID = re.compile("[a-zA-Z_][a-zA-Z0-9_]*")
RE_EXPR = re.compile("([0-9]+[\+\*-/])+[0-9]+")
RE_PARA = re.compile("\(.*\)")
RE_NUM = re.compile("[0-9]+")
RE_OP = re.compile("\+|-|\*|/")

class Class(object):
    def __init__(self, name):
        self.name = name
        self.functions = []

    def __repr__(self):
        return "class %s: %s" % (self.name, self.functions)

    def pprint(self, indent):
        print("%sclass %s:" % (" " * indent, self.name))
        for f in self.functions:
            f.pprint(indent + 3)

class Function(object):
    def __init__(self, name):
        self.name = name
        self.statements = []
        self.args = []

    def __repr__(self):
        return "func %s(%s) : %s " % (self.name, self.args, self.statements)

    def pprint(self, indent):
        print("%s|- def %s:" % (" " * indent, self.name))
        for s in self.statements:
            s.pprint(indent + 3)

class Statement(object):
    def __init__(self, expression):
        self.expression = expression

    def pprint(self, indent):
        print("%s|- %s" % (" " * indent, self.expression))

    def __repr__(self):
        return "%s" % self.expression

class Expression(object):

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __repr__(self):
        return "%s(%s, %s)" % (self.__class__.__name__, self.left, self.right)

    def pprint(self, indent):
        print("%s|- %s:" % (" " * indent, self.__class__.__name__))
        self.left.pprint(indent + 3)
        self.right.pprint(indent + 3)

class AddExpression(Expression): pass
class MulExpression(Expression): pass


class RecursiveDescentParser(object):

    def __init__(self, code):
        self.code = self.remove_whitespace(code)
        self.pos = 0
        self.elements = []

    def pprint(self):
        for e in self.elements:
            e.pprint(0)

    def remove_whitespace(self, code):
        return re.sub("[ \t\n]|#.*\n", "", code)

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
        return args

    def parse_statements(self, body):
        statements = []
        l = body.split(";")
        for s in l:
            if s == "":
                continue
            expr = self.parse_expression(s)
            statements.append(expr)
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
        l = self._tokenize_expression(code)
        return self._parse_expr_tokens(l)

    def _tokenize_expression(self, code):
        l = []
        i = 0
        while i < len(code):
            # find expressions in paranthesises
            result = RE_PARA.match(code[i:])
            if result:
                s = result.group(0)
                subexpr = self._tokenize_expression(code[i+1:i+len(s)-1])
                l.append(subexpr)
                i += len(s)

            # tokenize the rest
            result = RE_NUM.match(code[i:])
            if result:
                nums = result.group(0)
                l.append(nums)
                i += len(nums)

            result = RE_OP.match(code[i:])
            if result:
                ops = result.group(0)
                l.append(ops)
                i += len(ops)
        return l

    def _parse_expr_tokens(self, l):

        if len(l) == 1:
            if isinstance(l[0], list):
                return self._parse_expr_tokens(l[0])
            return Statement(l[0])

        i = 0
        while i < len(l):
            if l[i] == "+":
                left = self._parse_expr_tokens(l[:i])
                right = self._parse_expr_tokens(l[i+1:])
                return AddExpression(left, right)
            i += 1

        i = 0
        while i < len(l):
            if l[i] == "*":
                left = self._parse_expr_tokens(l[:i])
                right = self._parse_expr_tokens(l[i+1:])
                return MulExpression(left, right)
            i += 1

    def parse_expression_old(self, code):

        if re.match("[0-9]+$", code):
            return Statement(code)

        left = None

        # parse brackets first
        i = 0
        plevel = 0
        first_open = 0
        while i < len(code):
            if code[i] == "(":
                if plevel == 0:
                    first_open = i
                plevel += 1
            if code[i] == ")":
                plevel -= 1
                if plevel < 0:
                    raise ParseError("Wrong paranthesis number", self)
                if plevel == 0:
                    left = self.parse_expression(code[first_open+1:i])
            i += 1

        # multiplication glues stronger, so parse addition first
        i = 0
        while i < len(code):
            if code[i] == "+":
                if not left:
                    left = self.parse_expression(code[0:i])
                right = self.parse_expression(code[i+1:])
                return AddExpression(left, right)
            if code[i] == "*":
                if not left:
                    left = self.parse_expression(code[0:i])
                right = self.parse_expression(code[i+1:])
                return MulExpression(left, right)
            i += 1

        raise ParseError("Expression", self)


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
        1+2+3;
        3*4
    }

    function do2(a, b){
        5+6*7; # => Add(5, Mul(6, 7))
        5*6+7; # => Add(Mul(5, 6), 7)
        (5+6)*7
    }


    function do3(){
        5*6*7*(3+2)
    }

}

class Test2{}
"""
    p = RecursiveDescentParser(s)
    p.parse()
    p.pprint()
