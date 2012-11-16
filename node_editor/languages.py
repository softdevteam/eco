class Language(object):

    def __init__(self, name, grammar, priorities):
        self.name = name
        self.grammar = grammar
        self.priorities = priorities

    def __str__(self):
        return self.name

calc1 = Language("Basic calculator",
"""
    E ::= T
        | E "+" T
    T ::= P
        | T "*" P
    P ::= "INT"
""",
"""
    "[0-9]+":INT
    "[+]":+
    "[*]":*
""")

merge1 = Language("Grammar to test merging behaviour",
"""
    S ::= "a" | "ab" 
"""
,
"""
    "[ab]":ab
    "[a]":a
""")

ambiguity1 = Language("Ambiguous grammar",
"""
    S ::= "a" | "bc" | "abc"
"""
,
"""
    "[abc]":abc
    "[ab]":ab
    "[a]":a
""")

languages = [calc1, merge1, ambiguity1]
