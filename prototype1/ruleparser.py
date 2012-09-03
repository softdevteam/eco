from simplelexer import Lexer

class Rule(object):

    def __init__(self, _from, _to):
        self.mapfrom = _from
        self.mapto = _to

    def __repr__(self):
        return "Rule(%s => %s)" % (self.mapfrom, self.mapto)

class Identifier(object):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "Identifier(%s)" % (self.name,)

class Operation(object):
    def __init__(self, op):
        self.operation = op

    def __repr__(self):
        return "Operation(%s)" % (self.operation,)

class Integer(object):
    def __repr__(self):
        return "Integer"

class Expression(object):
    def __init__(self, operation, left, right):
        self.operation = operation
        self.left = left
        self.right = right

    def __repr__(self):
        return "Expression(%s %s %s)" % (self.operation, self.left, self.right)

class RuleParser(object):

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
            newrule = self.rule()
            self.rules.append(newrule)

    def inc(self):
        self.curtok += 1

    def gettoken(self):
        t = self.lexer.tokens[self.curtok]
        print("parsing:", t)
        return t

    def rule(self):
        self.newrule()
        ident = self.identifier()
        self.assignment()
        try:
            expr = self.expression()
        except AssertionError:
            expr = None
        if not expr:
            expr = self.integer()
        return Rule(ident, expr)

    def newrule(self):
        t = self.gettoken()
        assert t.name == "Newrule"
        self.inc()

    def identifier(self):
        t = self.gettoken()
        assert t.name == "Identifier"
        self.inc()
        return Identifier(t.value)

    def assignment(self):
        t = self.gettoken()
        assert t.name == "Assignment"
        self.inc()

    def operation(self):
        t = self.gettoken()
        assert t.name == "Operation"
        self.inc()
        return Operation(t.value)

    def expression(self):
        ident1 = self.identifier()
        operation = self.operation()
        ident2 = self.identifier()
        return Expression(operation, ident1, ident2)

    def integer(self):
        t = self.gettoken()
        assert t.name == "Integer"
        self.inc()
        return Integer()

if __name__ == "__main__":
    p = RuleParser("E := E + E\nE := INT")
    p.parse()
    print("Result:")
    print(p)
