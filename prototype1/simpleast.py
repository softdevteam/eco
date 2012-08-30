class AstNode(object):

    def getText(self):
        return self.__class__.__name__

class Program(AstNode):
    def __init__(self):
        self.statements = []

    def addStatement(self, statement):
        self.statements.append(statement)

class Statement(AstNode):
    pass

class Expression(Statement):
    def __init__(self, expression):
        self.expression = expression

class IntLiteral(Statement):
    def __init__(self, value):
        self.value = value

    def getText(self):
        return str(self.value)

class AddExpression(Expression):
    def __init__(self, left=None, right=None):
        self.left = left
        self.right = right

    def setLeft(self, left):
        self.left = left

    def setRight(self, right):
        self.right = right

def createTestProgram():
    p = Program()
    p.addStatement(AddExpression(IntLiteral(1), IntLiteral(2)))
    return p

def createTestProgram2():
    p = Program()
    p.addStatement(AddExpression(IntLiteral(1), AddExpression(IntLiteral(2), IntLiteral(3))))
    return p
