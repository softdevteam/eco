from plexer import PriorityLexer

code = """
    "IF":KEYWORD
    "[0-9]+":INT
"""

def test_plexer():
    plexer = PriorityLexer(code)
    plexer.priority("IF") == 0
    plexer.priority("[0-9]+") == 1

    plexer.class_type("IF") == "KEYWORD"
    plexer.class_type("[0-9]+") == "INT"
