from grammars import Language

chemicals = Language("Chemicals","""
S ::= "chem"
"""
,
"""
"[a-zA-Z0-9]+":chem
"""
)
