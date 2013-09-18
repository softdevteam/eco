from languages import Language

indent_based = Language("Indentation based language",
"""
    class_def ::= "class" "ID" ":" "INDENT" class_body "DEDENT"
    class_body ::= "pass" | func_defs
    func_defs ::= func_def func_defs | func_def
    func_def ::= "def" "ID" ":" "INDENT" func_body "DEDENT"
    func_body ::= func_body_def func_body | func_body_def
    func_body_def ::= for_loop | assignment | "pass"
    for_loop ::= "for" "ID" "in" "ID" ":" "INDENT" func_body "DEDENT"
    assignment ::= "ID" "=" "ID"
"""
,
"""
"pass":pass
"class":class
"def":def
"for":for
"in":in
"[a-zA-Z][a-zA-Z_0-9]*":ID
":"::
"=":=
"[ \\t]+":<ws>
"[\\n\\r]":<return>
""")

