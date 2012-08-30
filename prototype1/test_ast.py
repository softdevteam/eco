from simpleast import Program, IntLiteral, Expression, AddExpression

def test_program():
    p = Program()
    assert p.statements == None

def test_intliteral():
    i = IntLiteral(10)
    assert i.value == 10

def test_expression():
    i1 = IntLiteral(5)
    expr = Expression(i1)
    assert expr.expression is i1

def test_add():
    i1 = IntLiteral(5)
    i2 = IntLiteral(2)
    a = AddExpression(i1, i2)
    assert a.left is i1
    assert a.right is i2
