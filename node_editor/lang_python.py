from languages import Language

lang_python = Language("Python 2.7.5",
"""

file_input ::= file_input "NEWLINE"
             | file_input stmt
             |

decorator ::= "@" dotted_name "(" [arglist] ")" "NEWLINE"
            | "@" dotted_name "NEWLINE"
decorators ::= decorator | decorator decorators
decorated ::= decorators classdef
            | decorators funcdef
funcdef ::= "def" "NAME" parameters ":" suite
parameters ::= "(" varargslist ")"
             | "(" ")"

varargslist ::= fpdef_loop
              | fpdef_loop ","
              | fpdef_loop "," kwargs_opt
              |                kwargs_opt

fpdef_loop ::= fpdef_loop "," fpdef_opt
             | fpdef_opt

fpdef_opt ::= fpdef
            | fpdef "=" test

kwargs_opt ::= "*" "NAME"
             | "**" "NAME"
             | "*" "NAME" "**" "NAME"

fpdef ::= "NAME" | "(" fplist ")"
fplist ::= fpdef fplist_loop1 ","
         | fpdef fplist_loop1
fplist_loop1 ::= fplist_loop1 "," fpdef
               |

stmt ::= simple_stmt | compound_stmt
simple_stmt ::=
                small_stmt simple_stmt_loop1 ";" "NEWLINE"
              | small_stmt simple_stmt_loop1     "NEWLINE"

simple_stmt_loop1 ::= simple_stmt_loop1 ";" small_stmt
                    |
small_stmt ::= expr_stmt
             | print_stmt
             | del_stmt
             | pass_stmt
             | flow_stmt
             | import_stmt
             | global_stmt
             | exec_stmt
             | assert_stmt

expr_stmt ::= testlist augassign yield_expr
           | testlist augassign testlist
           | testlist expr_stmt_loop1

expr_stmt_loop1 ::= expr_stmt_loop1 "="            testlist
                  | expr_stmt_loop1 "=" yield_expr
                  |

augassign ::= "+=" | "-=" | "*=" | "/=" | "%=" | "&=" | "|=" | "^=" | "<<=" | ">>=" | "**=" | "//="

print_stmt ::= "print"
             | "print" test print_stmt_loop1
             | "print" test print_stmt_loop1 ","
             | "print" ">>" test
             | "print" ">>" test print_stmt_loop2
             | "print" ">>" test print_stmt_loop2 ","

print_stmt_loop1 ::=  print_stmt_loop1 "," test
                   |

print_stmt_loop2 ::=                  "," test
                   | print_stmt_loop2 "," test

del_stmt ::= "del" exprlist
pass_stmt ::= "pass"
flow_stmt ::= break_stmt | continue_stmt | return_stmt | raise_stmt | yield_stmt
break_stmt ::= "break"
continue_stmt ::= "continue"
return_stmt ::= "return"
              | "return" testlist
yield_stmt ::= yield_expr
raise_stmt ::= "raise"
             | "raise" test
             | "raise" test "," test
             | "raise" test "," test "," test

import_stmt ::= import_name | import_from
import_name ::= "import" dotted_as_names

import_from ::= "from" import_option1 "import" import_option2
import_option1 ::=          dotted_name
                 | dot_loop dotted_name
                 | dot_loop
dot_loop ::= dot_loop "."
           |           "."
import_option2 ::= "*"
                 | "(" import_as_names ")"
                 | import_as_names

import_as_name ::= "NAME"
                 | "NAME" "as" "NAME"

dotted_as_name ::= dotted_name
                 | dotted_name "as" "NAME"

import_as_names ::= import_as_name import_as_names_loop1
                  | import_as_name import_as_names_loop1 ","
import_as_names_loop1 ::= import_as_names_loop1 "," import_as_name
                        |

dotted_as_names ::= dotted_as_name dotted_as_names_loop1
dotted_as_names_loop1 ::= dotted_as_names_loop1 "," dotted_as_name
                        |

dotted_name ::= "NAME" dotted_name_loop1
dotted_name_loop1 ::= dotted_name_loop1 "." "NAME"
                    |
global_stmt ::= "global" "NAME" global_stmt_loop1
global_stmt_loop1 ::= global_stmt_loop1 "," "NAME"
                    |

exec_stmt ::= "exec" expr
            | "exec" expr "in" test
            | "exec" expr "in" test "," test

assert_stmt ::= "assert" test
              | "assert" test "," test

compound_stmt ::= if_stmt | while_stmt | for_stmt | try_stmt | with_stmt | funcdef | classdef | decorated

if_stmt ::= "if" test ":" suite if_stmt_loop1
          | "if" test ":" suite if_stmt_loop1 "else" ":" suite
if_stmt_loop1 ::= if_stmt_loop1 "elif" test ":" suite
                |

while_stmt ::= "while" test ":" suite
             | "while" test ":" suite "else" ":" suite

for_stmt ::= "for" exprlist "in" testlist ":" suite
           | "for" exprlist "in" testlist ":" suite "else" ":" suite

try_stmt ::= "try" ":" suite "finally" ":" suite
           | "try" ":" suite try_stmt_loop1
           | "try" ":" suite try_stmt_loop1 "else" ":" suite
           | "try" ":" suite try_stmt_loop1                  "finally" ":" suite
           | "try" ":" suite try_stmt_loop1 "else" ":" suite "finally" ":" suite

try_stmt_loop1 ::= try_stmt_loop1 except_clause ":" suite
                 |                except_clause ":" suite

with_stmt ::= "with" with_item with_stmt_loop1  ":" suite
with_stmt_loop1 ::= with_stmt_loop1 "," with_item
                  |
with_item ::= test
            | test "as" expr

except_clause ::= "except"
                | "except" test
                | "except" test "as" test
                | "except" test "," test

suite ::= simple_stmt
        | "NEWLINE" "INDENT" suite_loop "DEDENT"
suite_loop ::= suite_loop stmt
             | stmt

testlist_safe ::= old_test
                | old_test testlist_safe_loop1
                | old_test testlist_safe_loop1 ","
testlist_safe_loop1 ::= testlist_safe_loop1 "," old_test
                      |                     "," old_test

old_test ::= or_test | old_lambdef
old_lambdef ::= "lambda"             ":" old_test
              | "lambda" varargslist ":" old_test

test ::= or_test
       | or_test "if" or_test "else" test
       | lambdef

or_test ::= and_test or_test_loop1
or_test_loop1 ::= or_test_loop1 "or" and_test
                |

and_test ::= not_test and_test_loop1
and_test_loop1 ::= and_test_loop1 "and" not_test
                 |

not_test ::= "not" not_test
           | comparison

comparison ::= expr comparison_loop1
comparison_loop1 ::= comparison_loop1 comp_op expr
                   |
comp_op ::= "<"
          | ">"
          | "=="
          | ">="
          | "<="
          | "<>"
          | "!="
          | "in"
          | "not" "in"
          | "is"
          | "is" "not"

expr ::= xor_expr expr_loop1
expr_loop1 ::= expr_loop1 "|" xor_expr
             |
xor_expr ::= and_expr xor_expr_loop
xor_expr_loop ::= xor_expr_loop "^" and_expr
                |
and_expr ::= shift_expr and_expr_loop
and_expr_loop ::= and_expr_loop "&" shift_expr
                |
shift_expr ::= arith_expr shift_expr_loop
shift_expr_loop ::= shift_expr_loop "<<" arith_expr
                  | shift_expr_loop ">>" arith_expr
                  |
arith_expr ::= term arith_expr_loop
arith_expr_loop ::= arith_expr_loop "+" term
                  | arith_expr_loop "-" term
                  |
term ::= factor term_loop
term_loop ::= term_loop "*"  factor
            | term_loop "/"  factor
            | term_loop "%"  factor
            | term_loop "//" factor
            |
factor ::= "+" factor
         | "-" factor
         | "~" factor
         | power

power ::= atom power_loop
        | atom power_loop "**" factor
power_loop ::= power_loop trailer
             |
atom ::= "("                ")"
       | "(" yield_expr     ")"
       | "(" testlist_comp  ")"
       | "["                "]"
       | "[" listmaker      "]"
       | "{"                "}"
       | "{" dictorsetmaker "}"
       | "`" testlist1 "`"
       | "NAME"
       | "NUMBER"
       | atom_loop
atom_loop ::= atom_loop "STRING"
            |           "STRING"

listmaker ::= test list_for
            | test listmaker_loop
            | test listmaker_loop ","
listmaker_loop ::= listmaker_loop "," test
                 |
testlist_comp ::= test comp_for
                | test testlist_comp_loop
                | test testlist_comp_loop ","
testlist_comp_loop ::= testlist_comp_loop "," test
                     |

lambdef ::= "lambda"             ":" test
          | "lambda" varargslist ":" test
trailer ::= "("         ")"
          | "(" arglist ")"
          | "[" subscriptlist "]"
          | "." "NAME"

subscriptlist ::= subscript subscriptlist_loop
                | subscript subscriptlist_loop ","
subscriptlist_loop ::= subscriptlist_loop "," subscript
                     |
subscript ::= "." "." "."
            | test
            |      ":"
            |      ":" test
            |      ":"      sliceop
            |      ":" test sliceop
            | test ":"
            | test ":" test
            | test ":"      sliceop
            | test ":" test sliceop
sliceop ::= ":"
          | ":" test

exprlist ::= expr exprlist_loop
           | expr exprlist_loop ","
exprlist_loop ::= exprlist_loop "," expr
                |

testlist ::= test testlist_loop
           | test testlist_loop ","
testlist_loop ::= testlist_loop "," test
                |

dictorsetmaker ::=
                   test ":" test comp_for
                 | test ":" test          dictorsetmaker_loop1
                 | test ":" test          dictorsetmaker_loop1 ","
                 | test comp_for
                 | test          dictorsetmaker_loop2
                 | test          dictorsetmaker_loop2 ","
dictorsetmaker_loop1 ::= dictorsetmaker_loop1 "," test ":" test
                       |
dictorsetmaker_loop2 ::= dictorsetmaker_loop2 "," test
                       |

classdef ::= "class" "NAME"                  ":" suite
           | "class" "NAME" "("          ")" ":" suite
           | "class" "NAME" "(" testlist ")" ":" suite

arglist ::= arglist_loop1 argument
          | arglist_loop1 argument ","
          | arglist_loop1 "*" test arglist_loop2
          | arglist_loop1 "*" test arglist_loop2 "," "**" test
          | arglist_loop1 "**" test

arglist_loop1 ::= arglist_loop1 argument ","
                |
arglist_loop2 ::= arglist_loop2 "," argument
                |
argument ::= test
           | test comp_for
           | test "=" test

list_iter ::= list_for
            | list_if
list_for ::= "for" exprlist "in" testlist_safe
           | "for" exprlist "in" testlist_safe list_iter
list_if ::= "if" old_test
          | "if" old_test list_iter

comp_iter ::= comp_for | comp_if
comp_for ::= "for" exprlist "in" or_test
           | "for" exprlist "in" or_test comp_iter
comp_if ::= "if" old_test
          | "if" old_test comp_iter

testlist1 ::= test testlist1_loop
testlist1_loop ::= testlist1_loop "," test
                 |
yield_expr ::= "yield"
             | "yield" testlist


"""
,
"""%indentation=true
"#[^\\r\\n]*":<ws>
"class":class
"pass":pass
"break":break
"continue":continue
"return":return
"yield":yield
"import":import
"from":from
"as":as
"def":def
"for":for
"while":while
"exec":exec
"raise":raise
"global":global
"assert":assert
"try":try
"finally":finally
"except":except
"\.":.
"\,":,
":"::
";":;
"=":=
"[ \\t]+":<ws>
"[\\n\\r]":<return>
"\(":(
"\)":)
"\[":[
"\]":]
"@":@
"\*":*
"\*\*":**
"\+=":+=
"-=":-=
"\*=":*=
"\/=":/=
"%=":%=
"&=":ANDEQ
"\|=":|=
"\^=":^=
"<<=":<<=
">>=":>>=
"\*\*=":**=
"\/\/="://=
"=":=
"==":==
"<":<
">":>
"<=":<=
">=":>=
"<>":<>
"!=":!=
"in":in
"not":not
"is":is
"\+":+
"-":-
"/":/
"\*":*
"~":~
"//"://
"%":%
"`":`
"[a-zA-Z_][a-zA-Z_0-9]*":NAME
"[0-9]+":NUMBER

""")

