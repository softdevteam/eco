from plexer import PriorityLexer

code = """
    "IF":KEYWORD
    "[a-zA-Z_]+":VAR
    "[0-9]+":INT
"""

def test_plexer():
    plexer = PriorityLexer(code)
    assert plexer.get_priority("IF") == 0
    assert plexer.get_priority("[0-9]+") == 2

    assert plexer.get_cls("IF") == "KEYWORD"
    assert plexer.get_cls("[0-9]+") == "INT"

def test_match():
    plexer = PriorityLexer(code)
    assert plexer.matches("13", "INT")
    assert not plexer.matches("13a", "INT")

    assert plexer.matches("variable_", "VAR")
    assert not plexer.matches("not variable", "VAR")
