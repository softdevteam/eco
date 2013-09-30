from grammars import Language

sql = Language("SQL",
"""
sql_list ::=
        sql ";"
    |   sql_list sql ";"


sql ::=     schema
    | cursor_def
    | manipulative_statement
    | "WHENEVER" "NOT" "FOUND" when_action
    | "WHENEVER" "SQLERROR" when_action

schema ::=
        "CREATE" "SCHEMA" "AUTHORIZATION" user opt_schema_element_list

opt_schema_element_list ::=
    |   schema_element_list

schema_element_list ::=
        schema_element
    |   schema_element_list schema_element

schema_element ::=
        base_table_def
    |   view_def
    |   privilege_def

base_table_def ::=
        "CREATE" "TABLE" table "(" base_table_element_commalist ")"

base_table_element_commalist ::=
        base_table_element
    |   base_table_element_commalist "," base_table_element

base_table_element ::=
        column_def
    |   table_constraint_def

column_def ::=
        column data_type column_def_opt_list

column_def_opt_list ::=
    |   column_def_opt_list column_def_opt


column_def_opt ::=
        "NOT" "NULLX"
    |   "NOT" "NULLX" "UNIQUE"
    |   "NOT" "NULLX" "PRIMARY" "KEY"
    |   "DEFAULT" literal
    |   "DEFAULT" "NULLX"
    |   "DEFAULT" "USER"
    |   "CHECK" "(" search_condition ")"
    |   "REFERENCES" table
    |   "REFERENCES" table "(" column_commalist ")"


table_constraint_def ::=
        "UNIQUE" "(" column_commalist ")"
    |   "PRIMARY" "KEY" "(" column_commalist ")"
    |   "FOREIGN" "KEY" "(" column_commalist ")" "REFERENCES" table
    |   "FOREIGN" "KEY" "(" column_commalist ")" "REFERENCES" table "(" column_commalist ")"
    |   "CHECK" "(" search_condition ")"


column_commalist ::=
        column
    |   column_commalist "," column


view_def ::=
        "CREATE" "VIEW" table opt_column_commalist "AS" query_spec opt_with_check_option


opt_with_check_option ::=
    |   "WITH" "CHECK" "OPTION"


opt_column_commalist ::=
    |   "(" column_commalist ")"


privilege_def ::=
        "GRANT" privileges "ON" table "TO" grantee_commalist opt_with_grant_option


opt_with_grant_option ::=
    |   "WITH" "GRANT" "OPTION"


privileges ::=
        "ALL" "PRIVILEGES"
    |   "ALL"
    |   operation_commalist


operation_commalist ::=
        operation
    |   operation_commalist "," operation


operation ::=
        "SELECT"
    |   "INSERT"
    |   "DELETE"
    |   "UPDATE" opt_column_commalist
    |   "REFERENCES" opt_column_commalist



grantee_commalist ::=
        grantee
    |   grantee_commalist "," grantee


grantee ::=
        "PUBLIC"
    |   user




cursor_def ::=
        "DECLARE" cursor "CURSOR" "FOR" query_exp opt_order_by_clause


opt_order_by_clause ::=
    |   "ORDER" "BY" ordering_spec_commalist


ordering_spec_commalist ::=
        ordering_spec
    |   ordering_spec_commalist "," ordering_spec


ordering_spec ::=
        "INTNUM" opt_asc_desc
    |   column_ref opt_asc_desc


opt_asc_desc ::=
    |   "ASC"
    |   "DESC"





manipulative_statement ::=
        close_statement
    |   commit_statement
    |   delete_statement_positioned
    |   delete_statement_searched
    |   fetch_statement
    |   insert_statement
    |   open_statement
    |   rollback_statement
    |   select_statement
    |   update_statement_positioned
    |   update_statement_searched


close_statement ::=
        "CLOSE" cursor


commit_statement ::=
        "COMMIT" "WORK"


delete_statement_positioned ::=
        "DELETE" "FROM" table "WHERE" "CURRENT" "OF" cursor


delete_statement_searched ::=
        "DELETE" "FROM" table opt_where_clause


fetch_statement ::=
        "FETCH" cursor "INTO" target_commalist


insert_statement ::=
        "INSERT" "INTO" table opt_column_commalist values_or_query_spec


values_or_query_spec ::=
        "VALUES" "(" insert_atom_commalist ")"
    |   query_spec


insert_atom_commalist ::=
        insert_atom
    |   insert_atom_commalist "," insert_atom


insert_atom ::=
        atom
    |   "NULLX"


open_statement ::=
        "OPEN" cursor


rollback_statement ::=
        "ROLLBACK" "WORK"


select_statement ::=
        "SELECT" opt_all_distinct selection
        "INTO" target_commalist
        table_exp


opt_all_distinct ::=
    |   "ALL"
    |   "DISTINCT"


update_statement_positioned ::=
        "UPDATE" table "SET" assignment_commalist
        "WHERE" "CURRENT" "OF" cursor


assignment_commalist ::=
    |   assignment
    |   assignment_commalist "," assignment


assignment ::=
        column "=" scalar_exp
    |   column "=" "NULLX"


update_statement_searched ::=
        "UPDATE" table "SET" assignment_commalist opt_where_clause


target_commalist ::=
        target
    |   target_commalist "," target


target ::=
        parameter_ref


opt_where_clause ::=
    |   where_clause



query_exp ::=
        query_term
    |   query_exp "UNION" query_term
    |   query_exp "UNION" "ALL" query_term


query_term ::=
        query_spec
    |   "(" query_exp ")"


query_spec ::=
        "SELECT" opt_all_distinct selection table_exp


selection ::=
        scalar_exp_commalist
    |   "*"


table_exp ::=
        from_clause opt_where_clause opt_group_by_clause opt_having_clause

from_clause ::=
        "FROM" table_ref_commalist


table_ref_commalist ::=
        table_ref
    |   table_ref_commalist "," table_ref


table_ref ::=
        table 
    |   table range_variable


where_clause ::=
        "WHERE" search_condition


opt_group_by_clause ::=
    |   "GROUP" "BY" column_ref_commalist


column_ref_commalist ::=
        column_ref
    |   column_ref_commalist "," column_ref


opt_having_clause ::=
    |   "HAVING" search_condition



search_condition ::=
        search_condition_fix1
    |   "NOT" search_condition_fix1

search_condition_fix1 ::=
        search_condition_fix1 "OR" search_condition_fix2
    |   search_condition_fix1 "AND" search_condition_fix2
    |   "(" search_condition_fix1 ")"
    |   search_condition_fix2

search_condition_fix2 ::=
       predicate


predicate ::=
        comparison_predicate
    |   between_predicate
    |   like_predicate
    |   test_for_null
    |   in_predicate
    |   all_or_any_predicate
    |   existence_test


comparison_predicate ::=
        scalar_exp "COMPARISON" scalar_exp
    |   scalar_exp "COMPARISON" subquery


between_predicate ::=
        scalar_exp "NOT" "BETWEEN" scalar_exp "AND" scalar_exp
    |   scalar_exp "BETWEEN" scalar_exp "AND" scalar_exp


like_predicate ::=
        scalar_exp "NOT" "LIKE" atom opt_escape
    |   scalar_exp "LIKE" atom opt_escape


opt_escape ::=
    |   "ESCAPE" atom


test_for_null ::=
        column_ref "IS" "NOT" "NULLX"
    |   column_ref "IS" "NULLX"


in_predicate ::=
        scalar_exp "NOT" "IN" "(" subquery ")"
    |   scalar_exp "IN" "(" subquery ")"
    |   scalar_exp "NOT" "IN" "(" atom_commalist ")"
    |   scalar_exp "IN" "(" atom_commalist ")"


atom_commalist ::=
        atom
    |   atom_commalist "," atom


all_or_any_predicate ::=
        scalar_exp "COMPARISON" any_all_some subquery

any_all_some ::=
        "ANY"
    |   "ALL"
    |   "SOME"


existence_test ::=
        "EXISTS" subquery


subquery ::=
        "(" "SELECT" opt_all_distinct selection table_exp ")"



scalar_exp ::=
        scalar_exp "+" scalar_exp_fix
    |   scalar_exp "-" scalar_exp_fix
    |   scalar_exp "*" scalar_exp_fix
    |   scalar_exp "/" scalar_exp_fix
    |   "+" scalar_exp_fix
    |   "-" scalar_exp_fix
    |   scalar_exp_fix

scalar_exp_fix ::=
        atom
    |   column_ref
    |   function_ref
    |   "(" scalar_exp ")"


scalar_exp_commalist ::=
        scalar_exp
    |   scalar_exp_commalist "," scalar_exp


atom ::=
        parameter_ref
    |   literal
    |   "USER"


parameter_ref ::=
        parameter
    |   parameter parameter
    |   parameter "INDICATOR" parameter


function_ref ::=
        "AMMSC" "(" "*" ")"
    |   "AMMSC" "(" "DISTINCT" column_ref ")"
    |   "AMMSC" "(" "ALL" scalar_exp ")"
    |   "AMMSC" "(" scalar_exp ")"


literal ::=
        "STRING"
    |   "INTNUM"
    |   "APPROXNUM"



table ::=
        "NAME"
    |   "NAME" "." "NAME"


column_ref ::=
        "NAME"
    |   "NAME" "." "NAME"
    |   "NAME" "." "NAME" "." "NAME"



data_type ::=
        "CHARACTER"
    |   "CHARACTER" "(" "INTNUM" ")"
    |   "NUMERIC"
    |   "NUMERIC" "(" "INTNUM" ")"
    |   "NUMERIC" "(" "INTNUM" "," "INTNUM" ")"
    |   "DECIMAL"
    |   "DECIMAL" "(" "INTNUM" ")"
    |   "DECIMAL" "(" "INTNUM" "," "INTNUM" ")"
    |   "INTEGER"
    |   "SMALLINT"
    |   "FLOAT"
    |   "FLOAT" "(" "INTNUM" ")"
    |   "REAL"
    |   "DOUBLE" "PRECISION"



column ::= "NAME"


cursor ::= "NAME"


parameter ::= "PARAMETER"


range_variable ::= "NAME"


user ::=        "NAME"




when_action ::= "GOTO" "NAME"
    |   "CONTINUE"

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
"""
)
