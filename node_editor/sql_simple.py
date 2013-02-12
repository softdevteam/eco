from languages import Language

sql= Language("SQL",
"""
y_sql ::=
        y_alter
    |   y_create
    |   y_drop
    |   y_insert
    |   y_select
    |   y_update
    |   y_delete


y_alter ::=
        "ALTER" "TTABLE" y_table "ADD" "COLUMN" y_columndef
    |   "ALTER" "TTABLE" y_table "ADD" y_columndef

y_create ::=
        "CREATE" "TTABLE" y_table "(" y_columndefs ")"

y_drop ::=
        "DROP" "TTABLE" y_table

y_select ::=
        "SELECT" y_columns "FROM" y_table
    |   "SELECT" y_columns "FROM" y_table "WHERE" y_condition
    |   "SELECT" y_columns "FROM" y_table "ORDER" "BY" y_order
    |   "SELECT" y_columns "FROM" y_table "WHERE" y_condition "ORDER" "BY" y_order

y_delete ::=
        "DELETE" "FROM" y_table
    |   "DELETE" "FROM" y_table "WHERE" y_condition

y_insert ::=
        "INSERT" "INTO" y_table y_values
    |   "INSERT" "INTO" y_table "(" y_columns ")" y_values

y_update ::=
        "UPDATE" y_table "SET" y_assignments
    |   "UPDATE" y_table "SET" y_assignments "WHERE" y_condition


y_columndefs ::=
        y_columndef
    |   y_columndefs "," y_columndef


y_columndef ::=
        "NAME" "VARCHAR" "(" "INTNUM" ")"
    |   "NAME" "INT"
    |   "NAME" "INTEGER"
    |   "NAME" "DOUBLE"
    |   "NAME" "DOUBLE" "PRECISION"
    |   "NAME" "DATE"


y_columns ::=
        "*"
    |   y_column_list


y_column_list ::=
        "NAME"
    |   y_column_list "," "NAME"


y_table ::=
        "NAME"


y_values ::=
        "VALUES" "(" y_value_list ")"


y_value_list ::=
        "NULL_VALUE"
    |   "STRING"
    |   "INTNUM"
    |   "-" "INTNUM"
    |   "FLOATNUM"
    |   "-" "FLOATNUM"
    |   y_value_list "," "NULL_VALUE"
    |   y_value_list "," "STRING"
    |   y_value_list "," "INTNUM"
    |   y_value_list "," "-" "INTNUM"
    |   y_value_list "," "FLOATNUM"
    |   y_value_list "," "-" "FLOATNUM"

y_assignments ::=
        y_assignment
    |   y_assignments "," y_assignment


y_assignment ::=
        "NAME" "EQUAL" "NULL_VALUE"
    |   "NAME" "EQUAL" y_expression


y_condition ::=
        y_sub_condition


y_sub_condition ::=
        y_sub_condition2
    |   y_sub_condition "OR" y_sub_condition2


y_sub_condition2 ::=
        y_boolean
    |   y_sub_condition2 "AND" y_boolean


y_boolean ::=
        y_comparison
    |   "(" y_sub_condition ")"
    |   "NOT" y_boolean


y_comparison ::=
        y_expression "EQUAL" y_expression
    |   y_expression "COMPARISON_OPERATOR" y_expression
    |   y_expression "IS" "NULL_VALUE"
    |   y_expression "NOT" "NULL_VALUE"



y_expression ::=
        y_product
    |   y_expression "+" y_product
    |   y_expression "-" y_product


y_product ::=
        y_term
    |   y_product "*" y_term
    |   y_product "/" y_term


y_term ::=
        y_atom
    |   "-"y_term


y_atom ::=
        y_value
    |   y_column
    |   "(" y_expression ")"



y_value ::=
        "STRING"
    |   "INTNUM"
    |   "FLOATNUM"



y_column ::=
        "NAME"


y_order ::=
        "NAME"
""",
"""
"ALL":ALL
"AND":AND
"AVG":AVG
"MIN":MIN
"MAX":MAX
"SUM":SUM
"COUNT":COUNT
"ANY":ANY
"AS":AS
"ASC":ASC
"AUTHORIZATION":AUTHORIZATION
"BETWEEN":BETWEEN
"BY":BY
"CHARACTER":CHARACTER
"CHAR":CHAR
"CHECK":CHECK
"CLOSE":CLOSE
"COMMIT":COMMIT
"CONTINUE":CONTINUE
"CREATE":CREATE
"CURRENT":CURRENT
"CURSOR":CURSOR
"DECIMAL":DECIMAL
"DECLARE":DECLARE
"DEFAULT":DEFAULT
"DELETE":DELETE
"DESC":DESC
"DISTINCT":DISTINCT
"DOUBLE":DOUBLE
"ESCAPE":ESCAPE
"EXISTS":EXISTS
"FETCH":FETCH
"FLOAT":FLOAT
"FOR":FOR
"FOREIGN":FOREIGN
"FOUND":FOUND
"FROM":FROM
"GOTO":GOTO
"GO":GO
"GRANT":RANT
"GROUP":GROUP
"HAVING":HAVING
"IN":IN
"INDICATOR":INDICATOR
"INSERT":INSERT
"INTEGER":INTEGER
"INT":INT
"INTO":INTO
"IS":IS
"KEY":KEY
"LANGUAGE":LANGUAGE
"LIKE":LIKE
"NOT":NOT
"NULL":NULL
"NUMERIC":NUMERIC
"OF":OF
"ON":ON
"OPEN":OPEN
"OPTION":OPTION
"OR":OR
"ORDER":ORDER
"PRECISION":PRECISION
"PRIMARY":PRIMARY
"PRIVILEGES":PRIVILEGES
"PROCEDURE":PROCEDURE
"PUBLIC":PUBLIC
"REAL":REAL
"REFERENCES":REFERENCES
"ROLLBACK":ROLLBACK
"SCHEMA":SCHEMA
"SELECT":SELECT
"SET":SET
"SMALLINT":SMALLINT
"SOME":SOME
"SQLCODE":SQLCODE
"TABLE":TABLE
"TO":TO
"UNION":UNION
"UNIQUE":UNIQUE
"UPDATE":UPDATE
"USER":USER
"VALUES":VALUES
"VIEW":VIEW
"WHENEVER":WHENEVER
"WHERE":WHERE
"WITH":WITH
"WORK":WORK
"\*":*
"[ \t]":<ws>
"[\n\r]":<ws>
"[A-Za-z][A-Za-z_]*":NAME
"[0-9]+":INTNUM
"=|<>|<=|>=|<|>":COMPARISON
"\"([a-zA-Z0-9 ]|\\\\\")*\"":STRING
":[A-Za-z][A-Za-z0-9_]*":PARAMETER

""")
