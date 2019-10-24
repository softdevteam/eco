from .grammars import Language

newprolog = Language("New Prolog", """
top ::=         clause_list

clause_list ::= clause_list clause | clause
clause ::=      term | arith | unify | relation

relation ::=    unifiable relop unifiable
relop ::=       ">" | "<" | ">=" | "=<"

unify ::=       unifiable "=" unifiable
unifiable ::=   var | term | num | list

arith ::=           atom "is" arith_rhs
                    | var "is" arith_rhs
arith_rhs ::=       num_or_var binary_arithop num_or_var
                    | unary_arithop num_or_var
binary_arithop ::=  "*" | "/" | "+" | "-"
unary_arithop ::=   "-"

num_or_var ::=  num | var

term ::=        atom | atom "(" term_list ")"
term_list ::=   term | term_list "," term

predicate ::=   term "." | term ":-" clause_list

var ::= "var"
atom ::= "atom"
num ::= "num"

list ::=        "[" "]" | "[" unifiable_list "]" |
                "[" unifiable "|" list "]"
                | "[" unifiable "|" unifiable "]"

unifiable_list ::=  unifiable | unifiable_list "," unifiable
""",
"""
"[ \\t]+":<ws>
"[\\n\\r]":<return>
"[A-Z_][a-z0-9_]*|_":var
"[a-z][a-z0-9_]*":atom
"[0-9]+":num
"\[":[
"\]":]
"\|":|
"is":is
"\=":=
">":>
"<":<
">=":>=
"=<":=<
"\*":*
"\/":/
"\+":+
"-":-
"\.":.
"\(":(
"\)":)
""")
