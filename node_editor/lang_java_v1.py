from languages import Language

javav1 = Language("Java 1.0",
"""

CompilationUnit ::= ProgramFile

TypeSpecifier ::=
	  TypeName
	| TypeName Dims

TypeName ::=
	  PrimitiveType
	| QualifiedName

ClassNameList ::=
          QualifiedName
        | ClassNameList "," QualifiedName

PrimitiveType ::=
	  "BOOLEAN"
	| "CHAR"
	| "BYTE"
	| "SHORT"
	| "INT"
	| "LONG"
	| "FLOAT"
	| "DOUBLE"
	| "VOID"

SemiColons ::=
          ";"
        | SemiColons ";"

ProgramFile ::=
	  PackageStatement ImportStatements TypeDeclarations
	| PackageStatement ImportStatements
	| PackageStatement                  TypeDeclarations
	|                  ImportStatements TypeDeclarations
	| PackageStatement
	|                  ImportStatements
	|                                   TypeDeclarations

PackageStatement ::=
	  "PACKAGE" QualifiedName SemiColons

TypeDeclarations ::=
	  TypeDeclarationOptSemi
	| TypeDeclarations TypeDeclarationOptSemi

TypeDeclarationOptSemi ::=
          TypeDeclaration
        | TypeDeclaration SemiColons

ImportStatements ::=
	  ImportStatement
	| ImportStatements ImportStatement

ImportStatement ::=
	  "IMPORT" QualifiedName SemiColons
	| "IMPORT" QualifiedName "." "*" SemiColons

QualifiedName ::=
	  "IDENTIFIER"
	| QualifiedName "." "IDENTIFIER"

TypeDeclaration ::=
	  ClassHeader "{" FieldDeclarations "}"
	| ClassHeader "{" "}"

ClassHeader ::=
	  Modifiers ClassWord "IDENTIFIER" Extends Interfaces
	| Modifiers ClassWord "IDENTIFIER" Extends
	| Modifiers ClassWord "IDENTIFIER"       Interfaces
	|           ClassWord "IDENTIFIER" Extends Interfaces
	| Modifiers ClassWord "IDENTIFIER"
	|           ClassWord "IDENTIFIER" Extends
	|           ClassWord "IDENTIFIER"       Interfaces
	|           ClassWord "IDENTIFIER"

Modifiers ::=
	  Modifier
	| Modifiers Modifier

Modifier ::=
	  "ABSTRACT"
	| "FINAL"
	| "PUBLIC"
	| "PROTECTED"
	| "PRIVATE"
	| "STATIC"
	| "TRANSIENT"
	| "VOLATILE"
	| "NATIVE"
	| "SYNCHRONIZED"

ClassWord ::=
	  "CLASS"
	| "INTERFACE"

Interfaces ::=
	  "IMPLEMENTS" ClassNameList

FieldDeclarations ::=
	  FieldDeclarationOptSemi
        | FieldDeclarations FieldDeclarationOptSemi

FieldDeclarationOptSemi ::=
          FieldDeclaration
        | FieldDeclaration SemiColons

FieldDeclaration ::=
	  FieldVariableDeclaration ";"
	| MethodDeclaration
	| ConstructorDeclaration
	| StaticInitializer
    | NonStaticInitializer
    | TypeDeclaration

FieldVariableDeclaration ::=
	  Modifiers TypeSpecifier VariableDeclarators
	|           TypeSpecifier VariableDeclarators

VariableDeclarators ::=
	  VariableDeclarator
	| VariableDeclarators "," VariableDeclarator

VariableDeclarator ::=
	  DeclaratorName
	| DeclaratorName "=" VariableInitializer

VariableInitializer ::=
	  Expression
	| "{" "}"
    | "{" ArrayInitializers "}"

ArrayInitializers ::=
	  VariableInitializer
	| ArrayInitializers "," VariableInitializer
	| ArrayInitializers ","

MethodDeclaration ::=
	  Modifiers TypeSpecifier MethodDeclarator Throws MethodBody
	| Modifiers TypeSpecifier MethodDeclarator        MethodBody
	|           TypeSpecifier MethodDeclarator Throws MethodBody
	|           TypeSpecifier MethodDeclarator        MethodBody

MethodDeclarator ::=
	  DeclaratorName "(" ParameterList ")"
	| DeclaratorName "(" ")"
	| MethodDeclarator "[" "]"

ParameterList ::=
	  Parameter
	| ParameterList "," Parameter

Parameter ::=
	  TypeSpecifier DeclaratorName
    | "FINAL" TypeSpecifier DeclaratorName

DeclaratorName ::=
	  "IDENTIFIER"
    | DeclaratorName "[" "]"

Throws ::=
	  "THROWS" ClassNameList

MethodBody ::=
	  Block
	| ";"

ConstructorDeclaration ::=
	  Modifiers ConstructorDeclarator Throws Block
	| Modifiers ConstructorDeclarator        Block
	|           ConstructorDeclarator Throws Block
	|           ConstructorDeclarator        Block

ConstructorDeclarator ::=
	  "IDENTIFIER" "(" ParameterList ")"
	| "IDENTIFIER" "(" ")"

StaticInitializer ::=
	  "STATIC" Block

NonStaticInitializer ::=
          Block

Extends ::=
	  "EXTENDS" TypeName
	| Extends "," TypeName

Block ::=
	  "{" LocalVariableDeclarationsAndStatements "}"
	| "{" "}"

LocalVariableDeclarationsAndStatements ::=
	  LocalVariableDeclarationOrStatement
	| LocalVariableDeclarationsAndStatements LocalVariableDeclarationOrStatement

LocalVariableDeclarationOrStatement ::=
	  LocalVariableDeclarationStatement
	| Statement

LocalVariableDeclarationStatement ::=
	  TypeSpecifier VariableDeclarators ";"
        | "FINAL" TypeSpecifier VariableDeclarators ";"

Statement ::=
	  EmptyStatement
	| LabelStatement
	| ExpressionStatement ";"
    | SelectionStatement
    | IterationStatement
	| JumpStatement
	| GuardingStatement
	| Block

EmptyStatement ::= ";"

LabelStatement ::=
	  "IDENTIFIER" ":"
    | "CASE" ConstantExpression ":"
	| "DEFAULT" ":"

ExpressionStatement ::=
	  Expression

SelectionStatement ::=
	  "IF" "(" Expression ")" Statement
    | "IF" "(" Expression ")" Statement "ELSE" Statement
    | "SWITCH" "(" Expression ")" Block

IterationStatement ::=
	  "WHILE" "(" Expression ")" Statement
	| "DO" Statement "WHILE" "(" Expression ")" ";"
	| "FOR" "(" ForInit ForExpr ForIncr ")" Statement
	| "FOR" "(" ForInit ForExpr         ")" Statement

ForInit ::=
	  ExpressionStatements ";"
	| LocalVariableDeclarationStatement
	| ";"

ForExpr ::=
	  Expression ";"
	| ";"

ForIncr ::=
	  ExpressionStatements

ExpressionStatements ::=
	  ExpressionStatement
	| ExpressionStatements "," ExpressionStatement

JumpStatement ::=
	  "BREAK" "IDENTIFIER" ";"
	| "BREAK"              ";"
    | "CONTINUE" "IDENTIFIER" ";"
	| "CONTINUE"              ";"
	| "RETURN" Expression ";"
	| "RETURN"            ";"
	| "THROW" Expression ";"

GuardingStatement ::=
	  "SYNCHRONIZED" "(" Expression ")" Statement
	| "TRY" Block Finally
	| "TRY" Block Catches
	| "TRY" Block Catches Finally

Catches ::=
	  Catch
	| Catches Catch

Catch ::=
	  CatchHeader Block

CatchHeader ::=
	  "CATCH" "(" TypeSpecifier "IDENTIFIER" ")"
	| "CATCH" "(" TypeSpecifier ")"

Finally ::=
	  "FINALLY" Block

PrimaryExpression ::=
	  QualifiedName
	| NotJustName

NotJustName ::=
	  SpecialName
	| NewAllocationExpression
	| ComplexPrimary

ComplexPrimary ::=
	  "(" Expression ")"
	| ComplexPrimaryNoParenthesis

ComplexPrimaryNoParenthesis ::=
	  "LITERAL"
	| "BOOLLIT"
	| ArrayAccess
	| FieldAccess
	| MethodCall

ArrayAccess ::=
	  QualifiedName "[" Expression "]"
	| ComplexPrimary "[" Expression "]"

FieldAccess ::=
	  NotJustName "." "IDENTIFIER"
	| RealPostfixExpression "." "IDENTIFIER"
    | QualifiedName "." "THIS"
    | QualifiedName "." "CLASS"
    | PrimitiveType "." "CLASS"

MethodCall ::=
	  MethodAccess "(" ArgumentList ")"
	| MethodAccess "(" ")"

MethodAccess ::=
	  ComplexPrimaryNoParenthesis
	| SpecialName
	| QualifiedName

SpecialName ::=
	  "THIS"
	| "SUPER"
	| "JNULL"

ArgumentList ::=
	  Expression
	| ArgumentList "," Expression

NewAllocationExpression ::=
          PlainNewAllocationExpression
        | QualifiedName "." PlainNewAllocationExpression

PlainNewAllocationExpression ::=
    	  ArrayAllocationExpression
    	| ClassAllocationExpression
    	| ArrayAllocationExpression "{" "}"
    	| ClassAllocationExpression "{" "}"
    	| ArrayAllocationExpression "{" ArrayInitializers "}"
    	| ClassAllocationExpression "{" FieldDeclarations "}"

ClassAllocationExpression ::=
	  "NEW" TypeName "(" ArgumentList ")"
	| "NEW" TypeName "("              ")"

ArrayAllocationExpression ::=
	  "NEW" TypeName DimExprs Dims
	| "NEW" TypeName DimExprs
    | "NEW" TypeName Dims

DimExprs ::=
	  DimExpr
	| DimExprs DimExpr

DimExpr ::=
	  "[" Expression "]"

Dims ::=
	  "[" "]"
	| Dims "[" "]"

PostfixExpression ::=
	  PrimaryExpression
	| RealPostfixExpression

RealPostfixExpression ::=
	  PostfixExpression "OP_INC"
	| PostfixExpression "OP_DEC"

UnaryExpression ::=
	  "OP_INC" UnaryExpression
	| "OP_DEC" UnaryExpression
	| ArithmeticUnaryOperator CastExpression
	| LogicalUnaryExpression

LogicalUnaryExpression ::=
	  PostfixExpression
	| LogicalUnaryOperator UnaryExpression

LogicalUnaryOperator ::=
	  "~"
	| "!"

ArithmeticUnaryOperator ::=
	  "+"
	| "-"

CastExpression ::=
	  UnaryExpression
	| "(" PrimitiveTypeExpression ")" CastExpression
	| "(" ClassTypeExpression ")" CastExpression
	| "(" Expression ")" LogicalUnaryExpression

PrimitiveTypeExpression ::=
	  PrimitiveType
    | PrimitiveType Dims

ClassTypeExpression ::=
	  QualifiedName Dims

MultiplicativeExpression ::=
	  CastExpression
	| MultiplicativeExpression "*" CastExpression
	| MultiplicativeExpression "/" CastExpression
	| MultiplicativeExpression "%" CastExpression

AdditiveExpression ::=
	  MultiplicativeExpression
    | AdditiveExpression "+" MultiplicativeExpression
	| AdditiveExpression "-" MultiplicativeExpression

ShiftExpression ::=
	  AdditiveExpression
        | ShiftExpression "OP_SHL" AdditiveExpression
        | ShiftExpression "OP_SHR" AdditiveExpression
        | ShiftExpression "OP_SHRR" AdditiveExpression

RelationalExpression ::=
	  ShiftExpression
    | RelationalExpression "<" ShiftExpression
	| RelationalExpression ">" ShiftExpression
	| RelationalExpression "OP_LE" ShiftExpression
	| RelationalExpression "OP_GE" ShiftExpression
	| RelationalExpression "INSTANCEOF" TypeSpecifier

EqualityExpression ::=
	  RelationalExpression
    | EqualityExpression "OP_EQ" RelationalExpression
    | EqualityExpression "OP_NE" RelationalExpression

AndExpression ::=
	  EqualityExpression
    | AndExpression "&" EqualityExpression

ExclusiveOrExpression ::=
	  AndExpression
	| ExclusiveOrExpression "^" AndExpression

InclusiveOrExpression ::=
	  ExclusiveOrExpression
	| InclusiveOrExpression "|" ExclusiveOrExpression

ConditionalAndExpression ::=
	  InclusiveOrExpression
	| ConditionalAndExpression "OP_LAND" InclusiveOrExpression

ConditionalOrExpression ::=
	  ConditionalAndExpression
	| ConditionalOrExpression "OP_LOR" ConditionalAndExpression

ConditionalExpression ::=
	  ConditionalOrExpression
	| ConditionalOrExpression "?" Expression ":" ConditionalExpression

AssignmentExpression ::=
	  ConditionalExpression
	| UnaryExpression AssignmentOperator AssignmentExpression

AssignmentOperator ::=
	  "="
	| "ASS_MUL"
	| "ASS_DIV"
	| "ASS_MOD"
	| "ASS_ADD"
	| "ASS_SUB"
	| "ASS_SHL"
	| "ASS_SHR"
	| "ASS_SHRR"
	| "ASS_AND"
	| "ASS_XOR"
	| "ASS_OR"

Expression ::=
	  AssignmentExpression

ConstantExpression ::=
	  ConditionalExpression

"""
,
"""
"boolean":BOOLEAN
"char":CHAR
"byte":BYTE
"short":SHORT
"int":INT
"long":LONG
"float":FLOAT
"double":DOUBLE
"void":VOID
"abstract":ABSTRACT
"final":FINAL
"public":PUBLIC
"protected":PROTECTED
"private":PRIVATE
"static":STATIC
"transient":TRANSIENT
"volatile":VOLATILE
"native":NATIVE
"synchronized":SYNCHRONIZED
"class":CLASS
"interface":INTERFACE
"implements":IMPLEMENTS
"if":IF
"else":ELSE
"for":FOR
"do":DO
"while":WHILE
"break":BREAK
"continue":CONTINUE
"return":RETURN
"throw":THROW
"try":TRY
"catch":CATCH
"finally":FINALLY
"[0-9]+":LITERAL
"true|false":BOOLLIT
"this":THIS
"super":SUPER
"jnull":JNULL
"new":NEW
"instanceof":INSTANCEOF
"\+\+":OP_INC
"\-\-":OP_DEC
";":;
"{":{
"}":}
",":,
"\(":(
"\)":)
"\[":[
"\]":]
"!":!
"~":~
"\+":+
"\*":*
"/":/
"\%":%
"\<\<":OP_SHL
"\>\>":OP_SHR
"\>\>\>":OP_SHRR
"\<=":OP_LE
"\>=":OP_GE
"==":OP_EQ
"!=":OP_NE
"&&":OP_LAND
"\|\|":OP_LOR
"\+=":ASS_ADD
"\-=":ASS_SUB
"\*=":ASS_MUL
"/=":ASS_DIV
"\<\<=":ASS_SHL
"\>\>=":ASS_SHR
"\>\>\>=":ASS_SHRR
"&=":ASS_AND
"\^=":ASS_XOR
"\|=":ASS_OR
"[a-zA-Z]+":IDENTIFIER
"[ \\t]+":<ws>
"[\\n\\r]":<return>
"""
)
