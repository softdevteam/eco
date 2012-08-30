class AstNode(object):
	pass

class Program(AstNode):
    def __init__(self):
        self.statements = None

class Statement(AstNode):
    pass

class Expression(Statement):
    def __init__(self, expression):
        self.expression = expression

class IntLiteral(Expression):
    def __init__(self, value):
        self.value = value

class AddExpression(Expression):
    def __init__(self, left, right):
        self.left = left
        self.right = right
