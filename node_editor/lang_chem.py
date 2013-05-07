from languages import Language

chemicals = Language("Chemicals","""
S ::= "h2o"
"""
,
"""
"(h2o|H2O)":h2o
"""
)
