# Copyright (c) 2012--2013 King's College London
# Created by the Software Development Team <http://soft-dev.org/>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

from grammars import Language

java15 = Language("Java 1.5","""
goal ::=    compilation_unit

literal ::=    "INTEGER_LITERAL"
    |    "FLOATING_POINT_LITERAL"
    |    "BOOLEAN_LITERAL"
    |    "CHARACTER_LITERAL"
    |    "STRING_LITERAL"
    |    "NULL_LITERAL"


type    ::=    primitive_type
    |    reference_type

primitive_type ::=
        numeric_type
    |    "BOOLEAN"

numeric_type::=    integral_type
    |    floating_point_type

integral_type ::=
        "BYTE"
    |    "SHORT"
    |    "INT"
    |    "LONG"
    |    "CHAR"

floating_point_type ::=
        "FLOAT"
    |    "DOUBLE"


reference_type ::=
        class_or_interface_type
    |    array_type

type_variable ::=
        "IDENTIFIER"

class_or_interface ::=
        name
    |    class_or_interface "LT" type_argument_list_1 "DOT" name

class_or_interface_type ::=
        class_or_interface
    |    class_or_interface "LT" type_argument_list_1


class_type ::=    class_or_interface_type
interface_type ::= class_or_interface_type

array_type ::=    primitive_type dims
    |    name dims
    |    class_or_interface "LT" type_argument_list_1 "DOT" name dims
    |    class_or_interface "LT" type_argument_list_1 dims


type_arguments_opt ::= type_arguments |

type_arguments ::=
        "LT" type_argument_list_1

wildcard ::=    "QUESTION"
    |    "QUESTION" "EXTENDS" reference_type
    |    "QUESTION" "SUPER" reference_type

wildcard_1 ::=    "QUESTION" "GT"
    |    "QUESTION" "EXTENDS" reference_type_1
    |    "QUESTION" "SUPER" reference_type_1

wildcard_2 ::=    "QUESTION" "RSHIFT"
    |    "QUESTION" "EXTENDS" reference_type_2
    |    "QUESTION" "SUPER" reference_type_2

wildcard_3 ::=    "QUESTION" "URSHIFT"
    |    "QUESTION" "EXTENDS" reference_type_3
    |    "QUESTION" "SUPER" reference_type_3

reference_type_1 ::=
        reference_type "GT"
    |    class_or_interface "LT" type_argument_list_2

reference_type_2 ::=
        reference_type "RSHIFT"
    |    class_or_interface "LT" type_argument_list_3

reference_type_3 ::=
        reference_type "URSHIFT"

type_argument_list ::=
        type_argument
    |    type_argument_list "COMMA" type_argument

type_argument_list_1 ::=
        type_argument_1
    |    type_argument_list "COMMA" type_argument_1

type_argument_list_2 ::=
        type_argument_2
    |    type_argument_list "COMMA" type_argument_2

type_argument_list_3 ::=
        type_argument_3
    |    type_argument_list "COMMA" type_argument_3

type_argument ::=
        reference_type
    |    wildcard

type_argument_1 ::=
        reference_type_1
    |    wildcard_1

type_argument_2 ::=
        reference_type_2
    |    wildcard_2

type_argument_3 ::=
        reference_type_3
    |    wildcard_3


name    ::=    simple_name
    |    qualified_name

simple_name ::=    "IDENTIFIER"

qualified_name ::=
        name "DOT" "IDENTIFIER"


compilation_unit ::=
        package_declaration_opt
        import_declarations_opt
        type_declarations_opt

package_declaration_opt ::= package_declaration |
import_declarations_opt ::= import_declarations |
type_declarations_opt   ::= type_declarations   |

import_declarations ::=
        import_declaration
    |    import_declarations import_declaration

type_declarations ::=
        type_declaration
    |    type_declarations type_declaration

package_declaration ::=
        "PACKAGE" name "SEMICOLON"

import_declaration ::=
        single_type_import_declaration
    |    type_import_on_demand_declaration
    |    static_single_type_import_declaration
    |    static_type_import_on_demand_declaration

single_type_import_declaration ::=
        "IMPORT" name "SEMICOLON"

static_single_type_import_declaration ::=
        "IMPORT" "STATIC" name "SEMICOLON"

type_import_on_demand_declaration ::=
        "IMPORT" name "DOT" "MULT" "SEMICOLON"

static_type_import_on_demand_declaration ::=
        "IMPORT" "STATIC" name "DOT" "MULT" "SEMICOLON"

type_declaration ::=
        class_declaration
    |    enum_declaration
    |    interface_declaration
    |    "SEMICOLON"


modifiers_opt::=
    |    modifiers

modifiers ::=     modifier
    |    modifiers modifier

modifier ::=    "PUBLIC" | "PROTECTED" | "PRIVATE"
    |    "STATIC"
    |    "ABSTRACT" | "FINAL" | "NATIVE" | "SYNCHRONIZED" | "TRANSIENT" | "VOLATILE"
    |    "STRICTFP"



class_declaration ::=
    modifiers_opt "CLASS" "IDENTIFIER" type_parameters_opt
      super_opt interfaces_opt class_body

super ::=    "EXTENDS" class_type

super_opt ::=
    |    super

interfaces ::=    "IMPLEMENTS" interface_type_list

interfaces_opt::=
    |    interfaces

interface_type_list ::=
        interface_type
    |    interface_type_list "COMMA" interface_type

class_body ::=    "LBRACE" class_body_declarations_opt "RBRACE"

class_body_opt ::=
    |    class_body
class_body_declarations_opt ::=
    |    class_body_declarations
class_body_declarations ::=
        class_body_declaration
    |    class_body_declarations class_body_declaration

class_body_declaration ::=
        class_member_declaration
    |    static_initializer
    |    constructor_declaration
    |    block

class_member_declaration ::=
        field_declaration
    |    method_declaration
    |    modifiers_opt "CLASS" "IDENTIFIER" type_parameters_opt super_opt interfaces_opt class_body
    |    enum_declaration
    |    interface_declaration
    |    "SEMICOLON"


enum_declaration ::=
        modifiers_opt "ENUM" "IDENTIFIER" interfaces_opt enum_body

enum_body ::=
        "LBRACE" enum_constants_opt enum_body_declarations_opt "RBRACE"

enum_constants_opt ::=
    |    enum_constants

enum_constants ::=
        enum_constant
    |    enum_constants "COMMA" enum_constant

enum_constant ::=
        "IDENTIFIER" enum_arguments_opt
    |    "IDENTIFIER" enum_arguments_opt class_body

enum_arguments_opt ::=
    |    "LPAREN" argument_list_opt "RPAREN"

enum_body_declarations_opt ::=
    |    "SEMICOLON" class_body_declarations_opt


field_declaration ::=
        modifiers_opt type variable_declarators "SEMICOLON"

variable_declarators ::=
        variable_declarator
    |    variable_declarators "COMMA" variable_declarator

variable_declarator ::=
        variable_declarator_id
    |    variable_declarator_id "EQ" variable_initializer

variable_declarator_id ::=
        "IDENTIFIER"
    |    variable_declarator_id "LBRACK" "RBRACK"

variable_initializer ::=
        expression
    |    array_initializer


method_declaration ::=
        method_header method_body

method_header ::=
        modifiers_opt type method_declarator throws_opt
    |    modifiers_opt "LT" type_parameter_list_1 type method_declarator throws_opt
    |    modifiers_opt "VOID" method_declarator throws_opt
    |    modifiers_opt "LT" type_parameter_list_1 "VOID" method_declarator throws_opt

method_declarator ::=
        "IDENTIFIER" "LPAREN" formal_parameter_list_opt "RPAREN"
    |    method_declarator "LBRACK" "RBRACK"

formal_parameter_list_opt ::=
    |    formal_parameter_list

formal_parameter_list ::=
        formal_parameter
    |    formal_parameter_list "COMMA" formal_parameter

formal_parameter ::=
        type variable_declarator_id
    |    "FINAL" type variable_declarator_id
    |    type "ELLIPSIS" "IDENTIFIER"
    |    "FINAL" type "ELLIPSIS" "IDENTIFIER"

throws_opt ::=
    |    throws

throws ::=    "THROWS" class_type_list

class_type_list ::=
        class_type
    |    class_type_list "COMMA" class_type

method_body ::=    block
    |    "SEMICOLON"


static_initializer ::=
        "STATIC" block


constructor_declaration ::=
        modifiers_opt constructor_declarator
            throws_opt constructor_body
    |    modifiers_opt "LT" type_parameter_list_1 constructor_declarator
            throws_opt constructor_body

constructor_declarator ::=
        simple_name "LPAREN" formal_parameter_list_opt "RPAREN"

constructor_body ::=
        "LBRACE" explicit_constructor_invocation
            block_statements "RBRACE"
    |    "LBRACE" explicit_constructor_invocation "RBRACE"
    |    "LBRACE" block_statements "RBRACE"
    |    "LBRACE" "RBRACE"

explicit_constructor_invocation ::=
        "THIS" "LPAREN" argument_list_opt "RPAREN" "SEMICOLON"
    |    type_arguments "THIS" "LPAREN" argument_list_opt "RPAREN" "SEMICOLON"
    |    "SUPER" "LPAREN" argument_list_opt "RPAREN" "SEMICOLON"
    |    type_arguments "SUPER" "LPAREN" argument_list_opt "RPAREN" "SEMICOLON"
    |    primary "DOT" "SUPER" "LPAREN" argument_list_opt "RPAREN" "SEMICOLON"
    |    primary "DOT" type_arguments "SUPER"
            "LPAREN" argument_list_opt "RPAREN" "SEMICOLON"
    |    name "DOT" "SUPER" "LPAREN" argument_list_opt "RPAREN" "SEMICOLON"
    |    name "DOT" type_arguments "SUPER" "LPAREN" argument_list_opt "RPAREN" "SEMICOLON"


interface_declaration ::=
        modifiers_opt "INTERFACE" "IDENTIFIER" type_parameters_opt
          extends_interfaces_opt interface_body

extends_interfaces_opt ::=
    |    extends_interfaces

extends_interfaces ::=
        "EXTENDS" interface_type
    |    extends_interfaces "COMMA" interface_type

interface_body ::=
        "LBRACE" interface_member_declarations_opt "RBRACE"

interface_member_declarations_opt ::=
    |    interface_member_declarations

interface_member_declarations ::=
        interface_member_declaration
    |    interface_member_declarations interface_member_declaration

interface_member_declaration ::=
        constant_declaration
    |    abstract_method_declaration
    |    class_declaration
    |    enum_declaration
    |    interface_declaration
    |    "SEMICOLON"

constant_declaration ::=
        field_declaration

abstract_method_declaration ::=
        method_header "SEMICOLON"


array_initializer ::=
        "LBRACE" variable_initializers "COMMA" "RBRACE"
    |    "LBRACE" variable_initializers "RBRACE"
    |    "LBRACE" "COMMA" "RBRACE"
    |    "LBRACE" "RBRACE"

variable_initializers ::=
        variable_initializer
    |    variable_initializers "COMMA" variable_initializer


block ::=    "LBRACE" block_statements_opt "RBRACE"

block_statements_opt ::=
    |    block_statements

block_statements ::=
        block_statement
    |    block_statements block_statement

block_statement ::=
        local_variable_declaration_statement
    |    statement
    |    class_declaration
    |    enum_declaration
    |    interface_declaration

local_variable_declaration_statement ::=
        local_variable_declaration "SEMICOLON"

local_variable_declaration ::=
        type variable_declarators
    |    "FINAL" type variable_declarators

statement ::=    statement_without_trailing_substatement
    |    labeled_statement
    |    if_then_statement
    |    if_then_else_statement
    |    while_statement
    |    for_statement
    |    foreach_statement

statement_no_short_if ::=
        statement_without_trailing_substatement
    |    labeled_statement_no_short_if
    |    if_then_else_statement_no_short_if
    |    while_statement_no_short_if
    |    for_statement_no_short_if
    |    foreach_statement_no_short_if

statement_without_trailing_substatement ::=
        block
    |    empty_statement
    |    expression_statement
    |    switch_statement
    |    do_statement
    |    break_statement
    |    continue_statement
    |    return_statement
    |    synchronized_statement
    |    throw_statement
    |    try_statement
    |    assert_statement

empty_statement ::=
        "SEMICOLON"

labeled_statement ::=
        "IDENTIFIER" "COLON" statement

labeled_statement_no_short_if ::=
        "IDENTIFIER" "COLON" statement_no_short_if

expression_statement ::=
        statement_expression "SEMICOLON"

statement_expression ::=
        assignment
    |    preincrement_expression
    |    predecrement_expression
    |    postincrement_expression
    |    postdecrement_expression
    |    method_invocation
    |    class_instance_creation_expression

if_then_statement ::=
        "IF" "LPAREN" expression "RPAREN" statement

if_then_else_statement ::=
        "IF" "LPAREN" expression "RPAREN" statement_no_short_if
            "ELSE" statement

if_then_else_statement_no_short_if ::=
        "IF" "LPAREN" expression "RPAREN" statement_no_short_if
            "ELSE" statement_no_short_if

switch_statement ::=
        "SWITCH" "LPAREN" expression "RPAREN" switch_block

switch_block ::=
        "LBRACE" switch_block_statement_groups switch_labels "RBRACE"
    |    "LBRACE" switch_block_statement_groups "RBRACE"
    |    "LBRACE" switch_labels "RBRACE"
    |    "LBRACE" "RBRACE"

switch_block_statement_groups ::=
        switch_block_statement_group
    |    switch_block_statement_groups switch_block_statement_group

switch_block_statement_group ::=
        switch_labels block_statements

switch_labels ::=
        switch_label
    |    switch_labels switch_label

switch_label ::=
        "CASE" constant_expression "COLON"
    |    "DEFAULT" "COLON"


while_statement ::=
        "WHILE" "LPAREN" expression "RPAREN" statement

while_statement_no_short_if ::=
        "WHILE" "LPAREN" expression "RPAREN" statement_no_short_if

do_statement ::=
        "DO" statement "WHILE" "LPAREN" expression "RPAREN" "SEMICOLON"

foreach_statement ::=
        "FOR" "LPAREN" type variable_declarator_id "COLON" expression "RPAREN"
            statement
    |    "FOR" "IDENTIFIER" "LPAREN" type variable_declarator_id "IDENTIFIER"
            expression "RPAREN" statement

foreach_statement_no_short_if ::=
        "FOR" "LPAREN" type variable_declarator_id "COLON" expression "RPAREN"
            statement_no_short_if
    |    "FOR" "IDENTIFIER" "LPAREN" type variable_declarator_id "IDENTIFIER"
            expression "RPAREN" statement_no_short_if

for_statement ::=
        "FOR" "LPAREN" for_init_opt "SEMICOLON" expression_opt "SEMICOLON"
            for_update_opt "RPAREN" statement

for_statement_no_short_if ::=
        "FOR" "LPAREN" for_init_opt "SEMICOLON" expression_opt "SEMICOLON"
            for_update_opt "RPAREN" statement_no_short_if

for_init_opt ::=
    |    for_init

for_init ::=    statement_expression_list
    |    local_variable_declaration

for_update_opt ::=
    |    for_update

for_update ::=    statement_expression_list

statement_expression_list ::=
        statement_expression
    |    statement_expression_list "COMMA" statement_expression


identifier_opt ::=
    |    "IDENTIFIER"


break_statement ::=
        "BREAK" identifier_opt "SEMICOLON"


continue_statement ::=
        "CONTINUE" identifier_opt "SEMICOLON"

return_statement ::=
        "RETURN" expression_opt "SEMICOLON"

throw_statement ::=
        "THROW" expression "SEMICOLON"

synchronized_statement ::=
        "SYNCHRONIZED" "LPAREN" expression "RPAREN" block

try_statement ::=
        "TRY" block catches
    |    "TRY" block catches_opt finally

catches_opt ::=
    |    catches

catches ::=    catch_clause
    |    catches catch_clause

catch_clause ::=
        "CATCH" "LPAREN" formal_parameter "RPAREN" block

finally ::=    "FINALLY" block

assert_statement ::=
        "ASSERT" expression "SEMICOLON"
    |    "ASSERT" expression "COLON" expression "SEMICOLON"


primary ::=    primary_no_new_array
    |    array_creation_init
    |    array_creation_uninit

primary_no_new_array ::=
        literal
    |    "THIS"
    |    "LPAREN" name "RPAREN"
    |    "LPAREN" expression_nn "RPAREN"
    |    class_instance_creation_expression
    |    field_access
    |    method_invocation
    |    array_access
    |    name "DOT" "THIS"
    |    "VOID" "DOT" "CLASS"
    |    primitive_type "DOT" "CLASS"
    |    primitive_type dims "DOT" "CLASS"
    |    name "DOT" "CLASS"
    |    name dims "DOT" "CLASS"

class_instance_creation_expression ::=
        "NEW" class_or_interface_type "LPAREN" argument_list_opt "RPAREN" class_body_opt
    |    "NEW" type_arguments class_or_interface_type "LPAREN" argument_list_opt "RPAREN" class_body_opt
    |    primary "DOT" "NEW" type_arguments_opt "IDENTIFIER" type_arguments_opt
            "LPAREN" argument_list_opt "RPAREN" class_body_opt
    |    name "DOT" "NEW" type_arguments_opt "IDENTIFIER" type_arguments_opt
            "LPAREN" argument_list_opt "RPAREN" class_body_opt

argument_list_opt ::=
    |    argument_list

argument_list ::=
        expression
    |    argument_list "COMMA" expression

array_creation_uninit ::=
        "NEW" primitive_type dim_exprs dims_opt
    |    "NEW" class_or_interface_type dim_exprs dims_opt

array_creation_init ::=
        "NEW" primitive_type dims array_initializer
    |    "NEW" class_or_interface_type dims array_initializer

dim_exprs ::=    dim_expr
    |    dim_exprs dim_expr

dim_expr ::=    "LBRACK" expression "RBRACK"

dims_opt ::=
    |    dims

dims ::=    "LBRACK" "RBRACK"
    |    dims "LBRACK" "RBRACK"

field_access ::=
        primary "DOT" "IDENTIFIER"
    |    "SUPER" "DOT" "IDENTIFIER"
    |    name "DOT" "SUPER" "DOT" "IDENTIFIER"

method_invocation ::=
        name "LPAREN" argument_list_opt "RPAREN"
    |    primary "DOT" "IDENTIFIER" "LPAREN" argument_list_opt "RPAREN"
    |    primary "DOT" type_arguments "IDENTIFIER" "LPAREN" argument_list_opt "RPAREN"
    |    name "DOT" type_arguments "IDENTIFIER" "LPAREN" argument_list_opt "RPAREN"
    |    "SUPER" "DOT" "IDENTIFIER" "LPAREN" argument_list_opt "RPAREN"
    |    "SUPER" "DOT" type_arguments "IDENTIFIER" "LPAREN" argument_list_opt "RPAREN"
    |    name "DOT" "SUPER" "DOT" "IDENTIFIER" "LPAREN" argument_list_opt "RPAREN"
    |    name "DOT" "SUPER" "DOT" type_arguments "IDENTIFIER" "LPAREN" argument_list_opt "RPAREN"

array_access ::=
        name "LBRACK" expression "RBRACK"
    |    primary_no_new_array "LBRACK" expression "RBRACK"
    |    array_creation_init "LBRACK" expression "RBRACK"

postfix_expression ::=
        primary
    |    name
    |    postincrement_expression
    |    postdecrement_expression

postincrement_expression ::=
        postfix_expression "PLUSPLUS"

postdecrement_expression ::=
        postfix_expression "MINUSMINUS"

unary_expression ::=
        preincrement_expression
    |    predecrement_expression
    |    "PLUS" unary_expression
    |    "MINUS" unary_expression
    |    unary_expression_not_plus_minus

preincrement_expression ::=
        "PLUSPLUS" unary_expression

predecrement_expression ::=
        "MINUSMINUS" unary_expression

unary_expression_not_plus_minus ::=
        postfix_expression
    |    "COMP" unary_expression
    |    "NOT" unary_expression
    |    cast_expression

cast_expression ::=
        "LPAREN" primitive_type dims_opt "RPAREN" unary_expression
    |    "LPAREN" name "RPAREN" unary_expression_not_plus_minus
    |    "LPAREN" name dims "RPAREN" unary_expression_not_plus_minus
    |    "LPAREN" name "LT" type_argument_list_1 dims_opt "RPAREN"
            unary_expression_not_plus_minus
    |    "LPAREN" name "LT" type_argument_list_1 "DOT"
            class_or_interface_type dims_opt "RPAREN"
            unary_expression_not_plus_minus

multiplicative_expression ::=
        unary_expression
    |    multiplicative_expression "MULT" unary_expression
    |    multiplicative_expression "DIV" unary_expression
    |    multiplicative_expression "MOD" unary_expression

additive_expression ::=
        multiplicative_expression
    |    additive_expression "PLUS" multiplicative_expression
    |    additive_expression "MINUS" multiplicative_expression

shift_expression ::=
        additive_expression
    |    shift_expression "LSHIFT" additive_expression
    |    shift_expression "RSHIFT" additive_expression
    |    shift_expression "URSHIFT" additive_expression

relational_expression ::=
        shift_expression
    |    relational_expression "LT" shift_expression
    |    relational_expression "GT" shift_expression
    |    relational_expression "LTEQ" shift_expression
    |    relational_expression "GTEQ" shift_expression

instanceof_expression ::=
        relational_expression
    |    instanceof_expression "INSTANCEOF" reference_type

equality_expression ::=
        instanceof_expression
    |    equality_expression "EQEQ" instanceof_expression
    |    equality_expression "NOTEQ" instanceof_expression

and_expression ::=
        equality_expression
    |    and_expression "AND" equality_expression

exclusive_or_expression ::=
        and_expression
    |    exclusive_or_expression "XOR" and_expression

inclusive_or_expression ::=
        exclusive_or_expression
    |    inclusive_or_expression "OR" exclusive_or_expression

conditional_and_expression ::=
        inclusive_or_expression
    |    conditional_and_expression "ANDAND" inclusive_or_expression

conditional_or_expression ::=
        conditional_and_expression
    |    conditional_or_expression "OROR" conditional_and_expression

conditional_expression ::=
        conditional_or_expression
    |    conditional_or_expression "QUESTION" expression "COLON" conditional_expression

assignment_expression ::=
        conditional_expression
    |    assignment

assignment ::=    postfix_expression assignment_operator assignment_expression

assignment_operator ::=
        "EQ"
    |    "MULTEQ"
    |    "DIVEQ"
    |    "MODEQ"
    |    "PLUSEQ"
    |    "MINUSEQ"
    |    "LSHIFTEQ"
    |    "RSHIFTEQ"
    |    "URSHIFTEQ"
    |    "ANDEQ"
    |    "XOREQ"
    |    "OREQ"

expression_opt ::=
    |    expression

expression ::=    assignment_expression

constant_expression ::=
        expression


type_parameters_opt ::= type_parameters |
type_parameters ::=
        "LT" type_parameter_list_1

type_parameter_list ::=
        type_parameter_list "COMMA" type_parameter
    |    type_parameter

type_parameter_list_1 ::=
        type_parameter_1
    |    type_parameter_list "COMMA" type_parameter_1

type_parameter ::=
        type_variable type_bound_opt

type_parameter_1 ::=
        type_variable "GT"
    |    type_variable type_bound_1

type_bound_opt ::= type_bound |
type_bound ::=
        "EXTENDS" reference_type additional_bound_list_opt

type_bound_1 ::=
        "EXTENDS" reference_type_1
    |    "EXTENDS" reference_type additional_bound_list_1

additional_bound_list_opt ::= additional_bound_list |
additional_bound_list ::=
        additional_bound additional_bound_list
    |    additional_bound

additional_bound_list_1 ::=
        additional_bound additional_bound_list_1
    |    additional_bound_1

additional_bound ::=
        "AND" interface_type

additional_bound_1 ::=
        "AND" reference_type_1

postfix_expression_nn ::=
        primary
    |    postincrement_expression
    |    postdecrement_expression

unary_expression_nn ::=
        preincrement_expression
    |    predecrement_expression
    |    "PLUS" unary_expression
    |    "MINUS" unary_expression
    |    unary_expression_not_plus_minus_nn

unary_expression_not_plus_minus_nn ::=
        postfix_expression_nn
    |    "COMP" unary_expression
    |    "NOT" unary_expression
    |    cast_expression

multiplicative_expression_nn ::=
        unary_expression_nn
    |    name                         "MULT" unary_expression
    |    multiplicative_expression_nn "MULT" unary_expression
    |    name                         "DIV" unary_expression
    |    multiplicative_expression_nn "DIV" unary_expression
    |    name                         "MOD" unary_expression
    |    multiplicative_expression_nn "MOD" unary_expression

additive_expression_nn ::=
        multiplicative_expression_nn
    |    name                   "PLUS" multiplicative_expression
    |    additive_expression_nn "PLUS" multiplicative_expression
    |    name                   "MINUS" multiplicative_expression
    |    additive_expression_nn "MINUS" multiplicative_expression

shift_expression_nn ::=
        additive_expression_nn
    |    name                "LSHIFT" additive_expression
    |    shift_expression_nn "LSHIFT" additive_expression
    |    name                "RSHIFT" additive_expression
    |    shift_expression_nn "RSHIFT" additive_expression
    |    name                "URSHIFT" additive_expression
    |    shift_expression_nn "URSHIFT" additive_expression

relational_expression_nn ::=
        shift_expression_nn
    |    name                "LT" shift_expression
    |    shift_expression_nn "LT" shift_expression
    |    name                "GT" shift_expression
    |    shift_expression_nn "GT" shift_expression
    |    name                     "LTEQ" shift_expression
    |    relational_expression_nn "LTEQ" shift_expression
    |    name                     "GTEQ" shift_expression
    |    relational_expression_nn "GTEQ" shift_expression

instanceof_expression_nn ::=
        relational_expression_nn
    |    name                     "INSTANCEOF" reference_type
    |    instanceof_expression_nn "INSTANCEOF" reference_type

equality_expression_nn ::=
        instanceof_expression_nn
    |    name                   "EQEQ" instanceof_expression
    |    equality_expression_nn "EQEQ" instanceof_expression
    |    name                   "NOTEQ" instanceof_expression
    |    equality_expression_nn "NOTEQ" instanceof_expression

and_expression_nn ::=
        equality_expression_nn
    |    name              "AND" equality_expression
    |    and_expression_nn "AND" equality_expression

exclusive_or_expression_nn ::=
        and_expression_nn
    |    name                       "XOR" and_expression
    |    exclusive_or_expression_nn "XOR" and_expression

inclusive_or_expression_nn ::=
        exclusive_or_expression_nn
    |    name                       "OR" exclusive_or_expression
    |    inclusive_or_expression_nn "OR" exclusive_or_expression

conditional_and_expression_nn ::=
        inclusive_or_expression_nn
    |    name                          "ANDAND" inclusive_or_expression
    |    conditional_and_expression_nn "ANDAND" inclusive_or_expression

conditional_or_expression_nn ::=
        conditional_and_expression_nn
    |    name                         "OROR" conditional_and_expression
    |    conditional_or_expression_nn "OROR" conditional_and_expression

conditional_expression_nn ::=
        conditional_or_expression_nn
    |    name "QUESTION" expression "COLON" conditional_expression
    |    conditional_or_expression_nn "QUESTION" expression
            "COLON" conditional_expression

assignment_expression_nn ::=
        conditional_expression_nn
    |    assignment

expression_nn ::=    assignment_expression_nn
"""
,
"""
"//[^\\r\\n]*":<ws>
"\"(\\\\.|[^\\\\"])*\"":STRING_LITERAL
"\'[^\']*\'":CHARACTER_LITERAL
"boolean":BOOLEAN
"byte":BYTE
"short":SHORT
"int":INT
"long":LONG
"char":CHAR
"float":FLOAT
"double":DOUBLE
"\[":LBRACK
"\]":RBRACK
"\.":DOT
";":SEMICOLON
"\*":MULT
",":COMMA
"{":LBRACE
"}":RBRACE
"=":EQ
"\(":LPAREN
"\)":RPAREN
":":COLON
"package":PACKAGE
"import":IMPORT
"public":PUBLIC
"protected":PROTECTED
"private":PRIVATE
"static":STATIC
"abstract":ABSTRACT
"final":FINAL
"native":NATIVE
"synchronized":SYNCHRONIZED
"transient":TRANSIENT
"volatile":VOLATILE
"class":CLASS
"extends":EXTENDS
"implements":IMPLEMENTS
"void":VOID
"throws":THROWS
"this":THIS
"super":SUPER
"interface":INTERFACE
"if":IF
"else":ELSE
"switch":SWITCH
"case":CASE
"default":DEFAULT
"do":DO
"while":WHILE
"for":FOR
"break":BREAK
"continue":CONTINUE
"return":RETURN
"throw":THROW
"try":TRY
"catch":CATCH
"finally":FINALLY
"assert":ASSERT
"new":NEW
"\+\+":PLUSPLUS
"\-\-":MINUSMINUS
"\+":PLUS
"\-":MINUS
"~":COMP
"!":NOT
"\/":DIV
"\%":MOD
"<<":LSHIFT
">>":RSHIFT
">>>":URSHIFT
"\<\<=":LSHIFTEQ
"\>\>=":RSHIFTEQ
"\>\>\>=":URSHIFTEQ
"\<=":LTEQ
"\>=":GTEQ
"\<":LT
"\>":GT
"instanceof":INSTANCEOF
"==":EQEQ
"!=":NOTEQ
"&&":ANDAND
"\|\|":OROR
"&":AND
"\^":XOR
"\|":OR
"\?":QUESTION
"\*=":MULTEQ
"\/=":DIVEQ
"%=":MODEQ
"\+=":PLUSEQ
"-=":MINUSEQ
"&=":ANDEQ
"\^=":XOREQ
"\|=":OREQ

"0x[0-9A-Fa-f]+|[0-9]+":INTEGER_LITERAL
"[0-9]+\.[0-9]+([eE][0-9]+)?[fFdD]?|[0-9]+[eE][0-9]+[fFdD]?":FLOATING_POINT_LITERAL
"(true|false)":BOOLEAN_LITERAL
"null":NULL_LITERAL
"[a-zA-Z_][a-zA-Z0-9_]*":IDENTIFIER

"const":CONST
"goto":GOTO
"strictfp":STRICTFP
"ellipsis":ELLIPSIS
"enum":ENUM

"[ \\t]+":<ws>
"[\\n\\r]":<return>
""",
"Java"
)
