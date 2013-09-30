class Language(object):

    def __init__(self, name, grammar, priorities):
        self.name = name
        self.grammar = grammar
        self.priorities = priorities

    def __str__(self):
        return self.name

super_simple = Language("Shifting optimisation",
"""
    S ::= X | Y
    X ::= "x" B
    Y ::= "y" B
    B ::= "b"
"""
,
"""
    "x":x
    "y":y
    "b":b
    " ":<ws>
""")

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
"\+":+
"\*":*
"[ \\t]+":<ws>
"[\\n\\r]":<return>
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

not_in_lr1 = Language("Not in LR(1): Type abf (then it is not possible to type x although it should be)",
"""
    S ::= Rule1 | Rule2
    Rule1 ::= "a" "b" Rule1b "f" "x"
    Rule1b ::= "c" "d" "e"
        |

    Rule2 ::= "a" "b" Rule2b "f" "y"
    Rule2b ::= "c" "d" "f"
        |
"""
,
"""
    "a":a
    "b":b
    "c":c
    "d":d
    "e":e
    "f":f
    "x":x
    "y":y
""")

not_in_lr1_fixed = Language("Not in LR(1) (fixed)",
"""
    S ::= Rule1 | Rule2
    Rule1 ::= "a" "b" Rule1b "f" "x"
        | "a" "b" "f" "x"
    Rule1b ::= "c" "d" "e"

    Rule2 ::= "a" "b" Rule2b "f" "y"
        | "a" "b" "f" "y"
    Rule2b ::= "c" "d" "f"
"""
,
"""
    "a":a
    "b":b
    "c":c
    "d":d
    "e":e
    "f":f
    "x":x
    "y":y
""")



smalltalk = Language("Smalltalk",
#"""
#Character ::= "CHAR"
#WhitespaceCharacter ::= "WHITESPACE"
#DecimalDigit ::= "INT"
#Letter ::= "LETTER"
#Comment ::= "COMMENT"
#OptionalWhitespace ::= OptionalWhitespace2
#OptionalWhitespace2 ::= OptionalWhitespace2 WhitespaceCharacter3
#    |
#OptionalWhitespace3 ::= WhitespaceCharacter | Comment
#Whitespace ::= Whitespace2 OptionalWhitespace
#Whitespace2 ::= WhitespaceCharacter | Comment
#
#LetterOrDigit ::= DecimalDigit | Letter
#Identifier ::= Identifier2 Identifier3
#Identifier2 ::= Letter | "_"
#Identifier3 ::= Identifier3 Identifier4
#    |
#Identifier4 ::= LetterOrDigit | "_"
#Reference ::= Identifier
#
#ConstantReference ::= "nil"
#    | "false"
#    | "true"
#
#PseudoVariableReference ::= "self"
#    | "super"
#    | "thisContext"
#
#ReservedIdentifier ::= PseudoVariableReference
#    | ConstantReference
#
#BindableIdentifier ::= Identifier - ReservedIdentifier
#Keyword ::= Identifier ":"
#KeywordMessageSelector ::= Keyword KeywordMessageSelector2
#KeywordMessageSelector2 ::= Keyword
#    |
#IntegerLiteral ::= "-" UnsignedIntegerLiteral
#    | UnsignedIntegerLiteral
#UnsignedIntegerLiteral ::= DecimalIntegerLiteral
#    | Radix "r" BaseNIntegerLiteral
#DecimalIntegerLiteral ::= DecimalIntegerLiteral DecimalDigit
#    |
#Radix ::= DecimalIntegerLiteral
#BaseNIntegerLiteral ::= BaseNIntegerLiteral LetterOrDigit
#    |
#
#-----
#"""
"""
MethodDeclaration ::= MethodHeader ExecutableCode

MethodHeader ::= UnaryMethodHeader
               | BinaryMethodHeader
               | KeywordMethodHeader

UnaryMethodHeader ::= UnaryMessageSelector
UnaryMessageSelector ::= Identifier
UnaryMessageChain ::= UnaryMessageChain OptionalWhitespace UnaryMessage
                    | OptionalWhitespace UnaryMessage

BinaryMethodHeader ::= BinaryMessageSelector BindableIdentifier
BinaryMessageSelector ::= BinaryMessageSelector BinarySelectorChar
                        | BinarySelectorChar
BinarySelectorChar ::= "~" | "!" | "@" | "%" | "&" | "*" | "-" | "+" | "=" | "|" | "\\" | "<" | ">" | "," | "?" | "/"


KeywordMethodHeader ::= KeywordMethodHeaderSegment KeywordMethodHeaderLoop
                      | KeywordMethodHeaderSegment
KeywordMethodHeaderLoop ::= KeywordMethodHeaderLoop Whitespace KeywordMethodHeaderSegment
                          | Whitespace KeywordMethodHeaderSegment
KeywordMethodHeaderSegment ::= Keyword OptionalWhitespace BindableIdentifier

ExecutableCode ::= LocalVariableDeclarationList Statements FinalStatement
                 | LocalVariableDeclarationList
                 | Statements FinalStatement
                 |

LocalVariableDeclarationList ::=
    OptionalWhitespace "|" OptionalWhitespace LocalVariableDeclarationList2 OptionalWhitespace "|"
LocalVariableDeclarationList2 ::= BindableIdentifier
                                | BindableIdentifier LocalVariableDeclarationList3
LocalVariableDeclarationList3 ::=
    LocalVariableDeclarationList3 Whitespace BindableIdentifier

MethodReturnOperator ::= OptionalWhitespace "^"

Statements ::= Statements "." Statement
             | Statement

Statement ::=  AssignmentOperation Expression
AssignmentOperation ::= AssignmentOperation BindableIdentifier ":="
                      | BindableIdentifier ":="

FinalStatement ::= MethodReturnOperator Statement
                 | Statement

Expression ::= Operand Expression2
             | Operand
Expression2 ::= OptionalWhitespace MessageChain Expression3
              | OptionalWhitespace MessageChain
Expression3 ::= Expression3 OptionalWhitespace CascadedMessage
    | OptionalWhitespace CascadedMessage

CascadedMessage ::= ";" OptionalWhitespace MessageChain
MessageChain ::= UnaryMessage BinaryMessageChain
               | UnaryMessage BinaryMessageChain KeywordMessage
               | UnaryMessage UnaryMessageChain BinaryMessageChain
               | UnaryMessage UnaryMessageChain BinaryMessageChain KeywordMessage
               | BinaryMessage BinaryMessageChain
               | BinaryMessage BinaryMessageChain KeywordMessage
               | KeywordMessage

KeywordMessage ::= KeywordMessageSegment KeywordMessageSegmentLoop
KeywordMessageSegmentLoop ::= KeywordMessageSegmentLoop KeywordMessage
    |

KeywordMessageSegment ::= Keyword OptionalWhitespace KeywordMessageArgument
KeywordMessageArgument ::= BinaryMessageOperand BinaryMessageChain
BinaryMessageChain ::= BinaryMessageChain OptionalWhitespace BinaryMessage
    |
BinaryMessage ::= BinaryMessageSelector OptionalWhitespace BinaryMessageOperand
BinaryMessageOperand ::= Operand UnaryMessageChain
UnaryMessage ::= UnaryMessageSelector

Operand ::= Literal
    | Reference
    | NestedExpression

NestedExpression ::= "(" Statement OptionalWhitespace ")"

Literal ::= ConstantReference
    | IntegerLiteral
    | ScaledDecimalLiteral
    | FloatingPointLiteral
    | CharacterLiteral
    | StringLiteral
    | SymbolLiteral
    | ArrayLiteral
    | BlockLiteral

BlockLiteral ::= "[" FormalBlockArgumentDeclarationListOption ExecutableCode OptionalWhitespace "]"
FormalBlockArgumentDeclarationListOption ::= FormalBlockArgumentDeclarationList
    |

FormalBlockArgumentDeclarationLoop ::= FormalBlockArgumentDeclarationLoop FormalBlockArgumentDeclaration
    |

FormalBlockArgumentDeclaration ::= ":" BindableIdentifier
FormalBlockArgumentDeclarationList ::= FormalBlockArgumentDeclaration FormalBlockArgumentDeclarationLoop

OptionalWhitespace ::= Whitespace
    |

Whitespace ::= "WS"

Reference ::= Identifier
BindableIdentifier ::= Identifier
Identifier ::= "IDENT"
Keyword ::= Identifier ":"
ConstantReference ::= "CONSTANT"
IntegerLiteral ::= "INTEGER"
ScaledDecimalLiteral ::= "SCALEDDECIMAL"
FloatingPointLiteral ::= "FLOAT"
CharacterLiteral ::= "CHARLIT"
StringLiteral ::= "STRING"
SymbolLiteral ::= "#" ConstantReference
    | "#" StringLiteral
ArrayLiteral ::= "#" "(" ArrayElement ")"
ArrayElementLoop ::= ArrayElementLoop Whitespace ArrayElement
    | ArrayElement

ArrayElement ::= Identifier | Literal

"""
,
"""
"[ \\t\\r\\n]+":"WS"
":="::=
"nil|false|true":"CONSTANT"
"[a-zA-Z_][a-zA-Z0-9_]*":"IDENT"
"[0-9]+":"INTEGER"
"[0-9]+?(\.[0-9])s[0-9]":"SCALEDDECIMAL"
"[0-9]+\.[0-9]+":"FLOAT"
"$.":"CHARLIT"
"abc":"STRING"
""")

#%token int_const char_const float_const id string enumeration_const
#%%
c_language = Language("C Syntax",
"""

translation_unit ::= external_decl
			| translation_unit external_decl

external_decl		::= function_definition
			| decl

function_definition	::= decl_specs declarator decl_list compound_stat
			|		declarator decl_list compound_stat
			| decl_specs declarator		compound_stat
			|		declarator 	compound_stat

decl			::= decl_specs init_declarator_list ";"
			| decl_specs			";"

decl_list		::= decl
			| decl_list decl

decl_specs		::= storage_class_spec decl_specs
			| storage_class_spec
			| type_spec decl_specs
			| type_spec
			| type_qualifier decl_specs
			| type_qualifier

storage_class_spec	::= "auto" | "register" | "static" | "extern" | "typedef"

type_spec		::= "void" | "char" | "short" | "int" | "long" | "float"
			| "double" | "signed" | "unsigned"
			| struct_or_union_spec
			| enum_spec
			| typedef_name

type_qualifier		::= "const" | "volatile"

struct_or_union_spec	::= struct_or_union id "{" struct_decl_list "}"
			| struct_or_union	"{" struct_decl_list "}"
			| struct_or_union id

struct_or_union		::= "struct" | "union"

struct_decl_list	::= struct_decl
			| struct_decl_list struct_decl

init_declarator_list	::= init_declarator
			| init_declarator_list "," init_declarator

init_declarator		::= declarator
			| declarator "=" initializer

struct_decl		::= spec_qualifier_list struct_declarator_list ";"

spec_qualifier_list	::= type_spec spec_qualifier_list
			| type_spec
			| type_qualifier spec_qualifier_list
			| type_qualifier

struct_declarator_list	::= struct_declarator
			| struct_declarator_list "," struct_declarator

struct_declarator	::= declarator
			| declarator ":" const_exp
			|		":" const_exp

enum_spec		::= "enum" id "{" enumerator_list "}"
			| "enum"	"{" enumerator_list "}"
			| "enum" id

enumerator_list		::= enumerator
			| enumerator_list "," enumerator

enumerator		::= id
			| id "=" const_exp

declarator		::= pointer direct_declarator
			|	direct_declarator

direct_declarator	::= id
			| "(" declarator ")"
			| direct_declarator "[" const_exp "]"
			| direct_declarator "["		"]"
			| direct_declarator "(" param_type_list ")"
			| direct_declarator "(" id_list ")"
			| direct_declarator "("		")"

pointer			::= "*" type_qualifier_list
			| "*"
			| "*" type_qualifier_list pointer
			| "*"			pointer

type_qualifier_list	::= type_qualifier
			| type_qualifier_list type_qualifier

param_type_list		::= param_list
			| param_list "," "..."

param_list		::= param_decl
			| param_list "," param_decl

param_decl		::= decl_specs declarator
			| decl_specs abstract_declarator
			| decl_specs

id_list			::= id
			| id_list "," id

initializer		::= assignment_exp
			| "{" initializer_list "}"
			| "{" initializer_list "," "}"

initializer_list	::= initializer
			| initializer_list "," initializer

type_name		::= spec_qualifier_list abstract_declarator
			| spec_qualifier_list

abstract_declarator	::= pointer
			| pointer direct_abstract_declarator
			|	direct_abstract_declarator

direct_abstract_declarator::= "(" abstract_declarator ")"
			| direct_abstract_declarator "[" const_exp "]"
			|				"[" const_exp "]"
			| direct_abstract_declarator "["	"]"
			|				"["	"]"
			| direct_abstract_declarator "(" param_type_list ")"
			|				"(" param_type_list ")"
			| direct_abstract_declarator "("		")"
			|				"("		")"

typedef_name		::= id

stat			::= labeled_stat
			| exp_stat
			| compound_stat
			| selection_stat
			| iteration_stat
			| jump_stat

labeled_stat		::= id ":" stat
			| "case" const_exp ":" stat
			| "default" ":" stat

exp_stat		::= exp ";"
			|	";"

compound_stat		::= "{" decl_list stat_list "}"
			| "{"		stat_list "}"
			| "{" decl_list		"}"
			| "{"			"}"

stat_list		::= stat
			| stat_list stat

selection_stat		::= "if" "(" exp ")" stat
			| "if" "(" exp ")" stat "else" stat
			| "switch" "(" exp ")" stat

iteration_stat		::= "while" "(" exp ")" stat
			| "do" stat "while" "(" exp ")" ";"
			| "for" "(" exp ";" exp ";" exp ")" stat
			| "for" "(" exp ";" exp ";"	")" stat
			| "for" "(" exp ";"	";" exp ")" stat
			| "for" "(" exp ";"	";"	")" stat
			| "for" "("	";" exp ";" exp ")" stat
			| "for" "("	";" exp ";"	")" stat
			| "for" "("	";"	";" exp ")" stat
			| "for" "("	";"	";"	")" stat

jump_stat		::= "goto" id ";"
			| "continue" ";"
			| "break" ";"
			| "return" exp ";"
			| "return"	";"

exp			::= assignment_exp
			| exp "," assignment_exp

assignment_exp		::= conditional_exp
			| unary_exp assignment_operator assignment_exp

assignment_operator	::= "=" | "*=" | "/=" | "%=" | "+=" | "-=" | "<<="
			| ">>=" | "&=" | "^=" | "|="

conditional_exp		::= logical_or_exp
			| logical_or_exp "?" exp ":" conditional_exp

const_exp		::= conditional_exp

logical_or_exp		::= logical_and_exp
			| logical_or_exp "||" logical_and_exp

logical_and_exp		::= inclusive_or_exp
			| logical_and_exp "&&" inclusive_or_exp

inclusive_or_exp	::= exclusive_or_exp
			| inclusive_or_exp "|" exclusive_or_exp

exclusive_or_exp	::= and_exp
			| exclusive_or_exp "^" and_exp

and_exp			::= equality_exp
			| and_exp "&" equality_exp

equality_exp		::= relational_exp
			| equality_exp "==" relational_exp
			| equality_exp "!=" relational_exp

relational_exp		::= shift_expression
			| relational_exp "<" shift_expression
			| relational_exp ">" shift_expression
			| relational_exp "<=" shift_expression
			| relational_exp ">=" shift_expression

shift_expression	::= additive_exp
			| shift_expression "<<" additive_exp
			| shift_expression ">>" additive_exp

additive_exp		::= mult_exp
			| additive_exp "+" mult_exp
			| additive_exp "-" mult_exp

mult_exp		::= cast_exp
			| mult_exp "*" cast_exp
			| mult_exp "/" cast_exp
			| mult_exp "%" cast_exp

cast_exp		::= unary_exp
			| "(" type_name ")" cast_exp

unary_exp		::= postfix_exp
			| "++" unary_exp
			| "--" unary_exp
			| unary_operator cast_exp
			| "sizeof" unary_exp
			| "sizeof" "(" type_name ")"

unary_operator		::= "&" | "*" | "+" | "-" | "~" | "!"

postfix_exp		::= primary_exp
			| postfix_exp "[" exp "]"
			| postfix_exp "(" argument_exp_list ")"
			| postfix_exp "("			")"
			| postfix_exp "." id
			| postfix_exp "->" id
			| postfix_exp "++"
			| postfix_exp "--"

primary_exp		::= id
			| const
			| string
			| "(" exp ")"

argument_exp_list	::= assignment_exp
			| argument_exp_list "," assignment_exp

const			::= int_const
			| char_const
			| float_const
			| enumeration_const

id ::= "[a-zA-Z]+"
int_const ::= "[0-9]+"
char_const ::= "[a-zA-Z]"
float_const ::= "[0-9]+\.[0-9]+"
enumeration_const ::= "enum"
string ::= "[a-zA-Z]+"
""",
"""
"[a-zA-Z]+":ID
"[0-9]+":INT
"[a-zA-Z]+":CHAR
"[0-9]+\.[0-9]+":FLOAT
"""
)

smalltalk_ebnf = Language("Smalltalk EBNF",
"""
MethodDeclaration ::= OptionalWhitespace MethodHeader ExecutableCode

FormalBlockArgumentDeclaration ::= ":" BindableIdentifier
FormalBlockArgumentDeclarationList ::= FormalBlockArgumentDeclaration {Whitespace FormalBlockArgumentDeclaration}
BlockLiteral ::= "[" [OptionalWhitespace FormalBlockArgumentDeclarationList OptionalWhitespace "|"] ExecutableCode OptionalWhitespace "]"

Literal ::= ConstantReference
          | IntegerLiteral
          | ScaledDecimalLiteral
          | FloatingPointLiteral
          | CharacterLiteral
          | StringLiteral
          | SymbolLiteral
          | ArrayLiteral
          | BlockLiteral

NestedExpression ::= "(" Statement OptionalWhitespace ")"
Operand ::= Literal
          | Reference
          | NestedExpression

UnaryMessage ::= UnaryMessageSelector
UnaryMessageSelector ::= Identifier
UnaryMessageChain ::= {OptionalWhitespace UnaryMessage}
BinaryMessageOperand ::= Operand UnaryMessageChain
BinaryMessage ::= BinaryMessageSelector OptionalWhitespace BinaryMessageOperand
BinaryMessageChain ::= {OptionalWhitespace BinaryMessage}
KeywordMessageArgument ::= BinaryMessageOperand BinaryMessageChain
KeywordMessageSegment ::= Keyword OptionalWhitespace KeywordMessageArgument
KeywordMessage ::= KeywordMessageSegment {OptionalWhitespace KeywordMessageSegment}
MessageChain ::=
                  UnaryMessage UnaryMessageChain BinaryMessageChain [KeywordMessage]
                | BinaryMessage BinaryMessageChain [KeywordMessage]
                | KeywordMessage
CascadedMessage ::= ";" OptionalWhitespace MessageChain
Expression ::= Operand [OptionalWhitespace MessageChain {OptionalWhitespace CascadedMessage}]

AssignmentOperation ::= OptionalWhitespace BindableIdentifier OptionalWhitespace ":="
Statement ::= {AssignmentOperation} OptionalWhitespace Expression
MethodReturnOperator ::= OptionalWhitespace "^"
FinalStatement ::= [MethodReturnOperator] Statement
LocalVariableDeclarationList ::= OptionalWhitespace "|" OptionalWhitespace [BindableIdentifier {Whitespace BindableIdentifier}] OptionalWhitespace "|"
ExecutableCode ::= [LocalVariableDeclarationList] [{Statement OptionalWhitespace "."} FinalStatement ["."]]

UnaryMethodHeader ::= UnaryMessageSelector
BinaryMethodHeader ::= BinaryMessageSelector OptionalWhitespace BindableIdentifier
KeywordMethodHeaderSegment ::= Keyword OptionalWhitespace BindableIdentifier
KeywordMethodHeader ::= KeywordMethodHeaderSegment {Whitespace KeywordMethodHeaderSegment}
MethodHeader ::=
                UnaryMethodHeader
                | BinaryMethodHeader
                 | KeywordMethodHeader


OptionalWhitespace ::= Whitespace
    |

Whitespace ::= "WS"

BinaryMessageSelector ::= "BINARYSELECTOR"
Reference ::= Identifier
BindableIdentifier ::= Identifier
Identifier ::= "IDENT"
Keyword ::= Identifier ":"
ConstantReference ::= "CONSTANT"
IntegerLiteral ::= "INTEGER"
ScaledDecimalLiteral ::= "SCALEDDECIMAL"
FloatingPointLiteral ::= "FLOAT"
CharacterLiteral ::= "CHARLIT"
StringLiteral ::= "STRING"
SymbolLiteral ::= "#" ConstantReference
    | "#" StringLiteral
ArrayLiteral ::= "#" "(" ArrayElement ")"
ArrayElementLoop ::= ArrayElementLoop Whitespace ArrayElement
    | ArrayElement

ArrayElement ::= Identifier | Literal
""",
"""
"[ \\t\\r\\n]+":"WS"
":="::=
"nil|false|true":"CONSTANT"
"[a-zA-Z_][a-zA-Z0-9_]*":"IDENT"
"[0-9]+":"INTEGER"
"[0-9]+?(\.[0-9])s[0-9]":"SCALEDDECIMAL"
"[0-9]+\.[0-9]+":"FLOAT"
"$.":"CHARLIT"
"abc":"STRING"
"[~!@%&*-+=|\\<>,?/]+":"BINARYSELECTOR"
""")

smalltalk_ebnf_nows = Language("Smalltalk EBNF (no whitespaces)",
"""
MethodDeclaration ::= MethodHeader ExecutableCode

FormalBlockArgumentDeclaration ::= ":" BindableIdentifier
FormalBlockArgumentDeclarationList ::= FormalBlockArgumentDeclaration {FormalBlockArgumentDeclaration}
BlockLiteral ::= "[" [FormalBlockArgumentDeclarationList "|"] ExecutableCode "]"

Literal ::= ConstantReference
          | IntegerLiteral
          | ScaledDecimalLiteral
          | FloatingPointLiteral
          | CharacterLiteral
          | StringLiteral
          | SymbolLiteral
          | ArrayLiteral
          | BlockLiteral

NestedExpression ::= "(" Statement ")"
Operand ::= Literal
          | Reference
          | NestedExpression

UnaryMessage ::= UnaryMessageSelector
UnaryMessageSelector ::= Identifier
UnaryMessageChain ::= {UnaryMessage}
BinaryMessageOperand ::= Operand UnaryMessageChain
BinaryMessage ::= BinaryMessageSelector BinaryMessageOperand
BinaryMessageChain ::= {BinaryMessage}
KeywordMessageArgument ::= BinaryMessageOperand BinaryMessageChain
KeywordMessageSegment ::= Keyword KeywordMessageArgument
KeywordMessage ::= KeywordMessageSegment {KeywordMessageSegment}
MessageChain ::=
                  UnaryMessage UnaryMessageChain BinaryMessageChain [KeywordMessage]
                | BinaryMessage BinaryMessageChain [KeywordMessage]
                | KeywordMessage
CascadedMessage ::= ";" MessageChain
Expression ::= Operand [MessageChain {CascadedMessage}]

AssignmentOperation ::= BindableIdentifier ":="
Statement ::= {AssignmentOperation} Expression
MethodReturnOperator ::= "^"
FinalStatement ::= [MethodReturnOperator] Statement
LocalVariableDeclarationList ::= "|" [BindableIdentifier {BindableIdentifier}] "|"
ExecutableCode ::= [LocalVariableDeclarationList] [{Statement "."} FinalStatement ["."]]

UnaryMethodHeader ::= UnaryMessageSelector
BinaryMethodHeader ::= BinaryMessageSelector BindableIdentifier
BinaryMessageSelector ::= BinarySelectorChar [BinarySelectorChar]
BinarySelectorChar ::= "BINARYSELECTOR"
KeywordMethodHeaderSegment ::= Keyword BindableIdentifier
KeywordMethodHeader ::= KeywordMethodHeaderSegment {KeywordMethodHeaderSegment}
MethodHeader ::=
                UnaryMethodHeader
                | BinaryMethodHeader
                 | KeywordMethodHeader


Reference ::= Identifier
BindableIdentifier ::= Identifier
Identifier ::= "IDENT"
Keyword ::= Identifier ":"
ConstantReference ::= "CONSTANT"
IntegerLiteral ::= "INTEGER"
ScaledDecimalLiteral ::= "SCALEDDECIMAL"
FloatingPointLiteral ::= "FLOAT"
CharacterLiteral ::= "CHARLIT"
StringLiteral ::= "STRING"
SymbolLiteral ::= "#" ConstantReference
    | "#" StringLiteral
ArrayLiteral ::= "#" "(" ArrayElement ")"
ArrayElementLoop ::= ArrayElementLoop ArrayElement
    | ArrayElement

ArrayElement ::= Identifier | Literal
""",
"""
"[ \\t\\r\\n]+":"WS"
":="::=
"nil|false|true":"CONSTANT"
"[a-zA-Z_][a-zA-Z0-9_]*":"IDENT"
"[0-9]+":"INTEGER"
"[0-9]+?(\.[0-9])s[0-9]":"SCALEDDECIMAL"
"[0-9]+\.[0-9]+":"FLOAT"
"$.":"CHARLIT"
"abc":"STRING"
"[~!@%&*-+=|\\<>,?/]":"BINARYSELECTOR"
""")


lisp = Language("Lisp",
"""
s_expression ::= atomic_symbol
    | "(" s_expression "." s_expression ")"
    | list
list ::= "(" s_expression list_loop ")"
list_loop ::= list_loop s_expression
    |
atomic_symbol ::= letter atom_part
atom_part ::= empty
    | letter atom_part
    | number atom_part
letter ::= "LETTER"
number ::= "INT"
empty ::= " "
""",
"""
"[a-z]":"LETTER"
"[0-9]":"INT"
""")

ebnf_loop = Language("EBNF: Loops",
"""
A ::= "a" { "b" } "c"
""",
"""
"a":a
"b":b
"c":c
""")

bnf_loop = Language("BNF: Loops (for comparing graph differences)",
"""
A ::= "a" B
B ::= b B | c
""",
"""
"a":a
"b":b
"c":c
""")

ebnf_loop_nested = Language("EBNF: Loops (nested)",
"""
A ::= "a" { "b" {"c"} } "d"
""",
"""
"a":a
"b":b
"c":c
"d":d
""")

ebnf_loop_multiple = Language("EBNF: Loops (multiple)",
"""
A ::= "a" { "b" } {"c"}
""",
"""
"a":a
"b":b
"c":c
"d":d
""")

ebnf_option = Language("EBNF: Option",
"""
A ::= "a" [ "b" ] "c"
""",
"""
"a":a
"b":b
"c":c
""")

bnf_option = Language("BNF: Option (for comparing)",
"""
A ::= "a" "c" | "a" "b" "c"
""",
"""
"a":a
"b":b
"c":c
""")

ebnf_option_loop = Language("EBNF: Loop within Option",
"""
A ::= "a" [ "b" {"c"}] "d"
""",
"""
"a":a
"b":b
"c":c
"d":d
""")

ebnf_grouping = Language("EBNF: Alternatives in group",
"""
A ::= "a" ( "b" | "c" | "d" ) "e"
""",
"""
"a":a
"b":b
"c":c
"d":d
"e":e
""")

bnf_grouping = Language("BNF: Alternatives in group (for comparing)",
"""
A ::= "a" "b" "e"
    | "a" "c" "e"
    | "a" "d" "e"
""",
"""
"a":a
"b":b
"c":c
"d":d
"e":e
""")

test = Language("Extract from Smalltalk EBNF to show shift/reduce conflict",
"""
Start ::= Keyword [Local]
Keyword ::= "x" {WS "x"}
Local ::= OptWS "|" OptWS "x"
OptWS ::= WS |
WS ::= "_"
""",
"""
"x":x
"_":_
""")

pager = Language("Grammar to test efficient LR(1) as described by Pager",
"""
X ::= "a" Y "d" | "a" Z "c" | "a" T | "b" Y "e" | "b" Z "d" | "b" T
Y ::= "t" W | "u" X
Z ::= "t" "u"
T ::= "u" X "a"
W ::= "u" V
V ::= 
""",
"""
"x":x
"y":y
""")

base_language = Language("Base",
"""
Start ::= Start Language | Language
Language ::= Java | SQL | Calc | Shifting
Java ::= "Java" ":" <Java 1.0> ";"
SQL ::= "SQL" ":" <SQL> ";"
Calc ::= "Calc" ":" <Basic calculator> ";"
Shifting ::= "Shifting" ":" <Shifting optimisation> ";"
""",
"""
"Java":Java
"SQL":SQL
"Calc":Calc
"Shifting":Shifting
":"::
";":;
"[ \\t]+":<ws>
"[\\n\\r]":<return>
""")

from java10 import java10
from java15 import java15
from sql_simple import sql
from greenmarl import greenmarl
from chemical import chemicals
from indentation import indent_based
from python275 import python275

import gops
java15_chem = gops.add_alt("Java 1.5 + chemical", java15, "unary_expression", "<Chemicals>")
java15_exp = gops.extract("Java 1.5 expression", java15_chem, "expression")
sql_java_exp = gops.add_alt("SQL ref. Java 1.5 expression", sql,  "y_condition", "<Java 1.5 expression>")
java15_sql = gops.add_alt("Java 1.5 + chemical + SQL", java15_chem,  "unary_expression", "<SQL ref. Java 1.5 expression>")

#languages = [java_error, java_error_simplified, super_simple, calc1, merge1, not_in_lr1, not_in_lr1_fixed, mylang, test, smalltalk, smalltalk_ebnf, lisp,
#             ebnf_loop, bnf_loop, ebnf_loop_nested, ebnf_loop_multiple, ebnf_option, bnf_option, ebnf_option_loop,
#             ebnf_grouping, bnf_grouping, test, test2, smalltalk_ebnf_nows, java, javav1, javav1_e, java15, pager]

languages = [base_language, indent_based, python275, super_simple, calc1, lisp, java10, java15, java15_sql, sql, java15_exp, sql_java_exp, chemicals]

lang_dict = {}
for l in languages:
    lang_dict[l.name] = l
