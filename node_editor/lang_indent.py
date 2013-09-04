from languages import Language

indent_based = Language("Indentation based language",
"""
    class_def ::= "class" "ID" ":" "INDENT" class_body "DEDENT"
    class_body ::= "pass" | func_defs
    func_defs ::= func_def func_defs | func_def
    func_def ::= "def" "ID" ":" "INDENT" func_body "DEDENT"
    func_body ::= "pass"
"""
,
"""
"pass":pass
"class":class
"def":def
"[a-zA-Z][a-zA-Z_0-9]*":ID
":"::
"[ \\t]+":<ws>
"[\\n\\r]":<return>
""")

