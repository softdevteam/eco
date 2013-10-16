from grammars import Language

prolog = Language("Prolog",
"""
query ::= toplevel_op_expr "."

toplevel_op_expr ::= expr1150 "-->" expr1150
                   | expr1150 ":-"  expr1150
                   |          ":-"  expr1150
                   |          "?-"  expr1150
                   |                expr1150

expr1150 ::= "meta_predicate" expr1100 | expr1100

expr1100 ::= expr1050 ";" expr1100 | expr1050

expr1050 ::= expr1000 "->" expr1050 | "block" expr1000 | expr1000

expr1000 ::= expr900 "," expr1000 | expr900

expr900 ::= "\+" expr900 | "~" expr700 | expr700

expr700 ::= expr600 "<" expr600
          | expr600 ">" expr600
          | expr600 "=" expr600
          | expr600 "=.." expr600
          | expr600 "=@=" expr600
          | expr600 "=:=" expr600
          | expr600 "=<" expr600
          | expr600 "==" expr600
          | expr600 "=\=" expr600
          | expr600 "?=" expr600
          | expr600 ">=" expr600
          | expr600 "@<" expr600
          | expr600 "@=<" expr600
          | expr600 "@>" expr600
          | expr600 "@>=" expr600
          | expr600 "\=" expr600
          | expr600 "\==" expr600
          | expr600 "is" expr600
          | expr600

expr600 ::= expr500 ":" expr600 | expr500


expr500 ::= "+"  extraexpr500
          | "-"  extraexpr500
          | "?"  extraexpr500
          | "\\" extraexpr500
          |      extraexpr500

extraexpr500 ::= extraexpr500 "+"   expr400
               | extraexpr500 "-"   expr400
               | extraexpr500 "/\\" expr400
               | extraexpr500 "\/"  expr400
               | extraexpr500 "xor" expr400
               | expr400

expr400 ::= expr400 "*" expr200
          | expr400 "slash" expr200
          | expr400 "//"    expr200
          | expr400 "<<"    expr200
          | expr400 ">>"    expr200
          | expr400 "mod"   expr200
          | expr400 "rem"   expr200
          |                 expr200

expr200 ::= complexterm "**" complexterm | complexterm "^" expr200 | complexterm


complexterm ::= "ATOM" "(" toplevel_op_expr ")" | expr

expr ::= "VAR" | "NUMBER" | "NUMBER" | "NUMBER" | "FLOAT" | "ATOM" | "(" toplevel_op_expr ")" | "{" toplevel_op_expr "}" | listexpr

listexpr ::= "[" listbody "]"

listbody ::= toplevel_op_expr "|" toplevel_op_expr | toplevel_op_expr
"""
,
"""
"[ \\t]+":<ws>
"[\\n\\r]":<return>
"\.":.
"-->":-->
";":;
"\:-"::-
"\?-":?-
"/\\\\":/\\
"\\\\":\\
"slash":/
"//"://
"\<\<":<<
"\>\>":>>
"\<":<
"\>":>
"\(":(
"\)":)
"\?":?
"\{":{
"\}":}
"\[":[
"\]":]
"~":~
"\\+":\\+
"\+":+
"\-":-
"\=":=
"\=@\=":=@=
"\=:\=":=:=
"\\\=\=
"mod":mod
"rem":rem
"is":is
"xor":xor
"(%[^\\n]*)":COMMENT
"[A-Z_]([a-zA-Z0-9]|_)*|_":VAR
"(0|[1-9][0-9]*)":NUMBER
"(0|[1-9][0-9]*)(\.[0-9]+)([eE][-+]?[0-9]+)?":FLOAT
"([a-z]([a-zA-Z0-9]|_)*)|('[^']*')|\[\]|!|\+|\-|\{\}":ATOM
"\"[^\"]*\"":STRING
""")
