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

greenmarl = Language("Greenmarl",
"""
 prog ::=
       | prog proc_def

  proc_def ::= proc_head proc_body

  proc_head ::= proc_name "(" arg_declist1 ")" proc_return_opt
            | proc_name "(" arg_declist1 ";" arg_declist2 ")" proc_return_opt

  proc_name ::= "T_PROC" id
           | "T_LOCAL" id

  arg_declist1 ::=
               | arg_declist

  arg_declist::= arg_decl
             | arg_declist "," arg_decl


  arg_declist2 ::= arg_decl
               | arg_declist2 "," arg_decl

  proc_return_opt ::=
              | proc_return

  proc_return ::= ":" prim_type
              | ":" node_type


  arg_decl ::= arg_target ":" typedecl

  arg_target::= id_comma_list

  typedecl ::=  prim_type
            | graph_type
            | property
            | nodeedge_type
            | set_type
            | map_type


  graph_type ::= "T_GRAPH"

  prim_type ::= "T_INT"
            | "T_LONG"
            | "T_FLOAT"
            | "T_DOUBLE"
            | "T_BOOL"

  nodeedge_type ::= node_type
                | edge_type

  node_type ::= "T_NODE" "(" id  ")"
            | "T_NODE"
  edge_type ::= "T_EDGE" "(" id  ")"
            | "T_EDGE"

  set_type ::=  "T_NSET"   "(" id ")"
           |  "T_NSET"

           |  "T_NSEQ"   "(" id ")"
           |  "T_NSEQ"

           |  "T_NORDER" "(" id ")"
           |  "T_NORDER"

           |  "T_COLLECTION" "<" set_type ">" "(" id ")"
           |  "T_COLLECTION" "<" set_type ">"

  key_type ::= nodeedge_type
  		   | prim_type

  value_type ::= nodeedge_type
  			 | prim_type

  map_type ::=  "T_MAP" "<" key_type "," value_type ">"


  property ::= "T_NODEPROP" "<" prim_type ">"     "(" id ")"
           | "T_NODEPROP" "<" nodeedge_type ">" "(" id ")"
           | "T_NODEPROP" "<" set_type ">" 	  "(" id ")"
           | "T_NODEPROP" "<" prim_type ">"
           | "T_NODEPROP" "<" nodeedge_type ">"
           | "T_NODEPROP" "<" set_type ">"

           | "T_EDGEPROP" "<" prim_type ">"     "(" id ")"
           | "T_EDGEPROP" "<" nodeedge_type ">" "(" id ")"
           | "T_EDGEPROP" "<" set_type ">" 	  "(" id ")"
           | "T_EDGEPROP" "<" prim_type ">"
           | "T_EDGEPROP" "<" nodeedge_type ">"
           | "T_EDGEPROP" "<" set_type ">"

  id_comma_list   ::= id
                  | id_comma_list "," id


  proc_body ::= sent_block

  sent_block ::= sb_begin sent_list sb_end
  sb_begin::= "{"
  sb_end::= "}"

  sent_list ::=
            | sent_list  sent

  sent::= sent_assignment  ";"
      | sent_variable_decl ";"
      | sent_block
      | sent_foreach
      | sent_if
      | sent_reduce_assignment ";"
      | sent_defer_assignment ";"
      | sent_do_while ";"
      | sent_while
      | sent_return ";"
      | sent_bfs
      | sent_dfs
      | sent_call ";"
      | sent_user ";"
      | sent_argminmax_assignment ";"
      | ";"

  sent_call ::= built_in

  sent_while ::= "T_WHILE" "(" bool_expr ")" sent_block

  sent_do_while ::= "T_DO" sent_block "T_WHILE" "(" bool_expr ")"


  sent_foreach ::=  "T_FOREACH" foreach_header foreach_filter sent
               |  "T_FOR"     foreach_header foreach_filter sent

  foreach_header ::= "(" id ":" foreach_src "." iterator1 ")"

  foreach_src    ::= id     foreach_dir
                 | field  foreach_dir

  foreach_dir    ::=
                 | "-"
                 | "+"

  foreach_filter ::=
                 | "(" bool_expr ")"

  iterator1 ::= "T_NODES"
            | "T_EDGES"
            | "T_NBRS"
            | "T_IN_NBRS"
            | "T_UP_NBRS"
            | "T_DOWN_NBRS"
            | "T_ITEMS"
            | "T_COMMON_NBRS" "(" id ")"

  sent_dfs    ::= "T_DFS" bfs_header_format bfs_filters sent_block dfs_post
  sent_bfs    ::= "T_BFS" bfs_header_format bfs_filters sent_block bfs_reverse

  dfs_post     ::=
               | "T_POST" bfs_filter sent_block
               | "T_POST" sent_block

  bfs_reverse  ::=
               | "T_BACK" bfs_filter sent_block
               | "T_BACK" sent_block

  bfs_header_format ::=  "(" id ":" id opt_tp "." "T_NODES" from_or_semi id ")"

  opt_tp       ::=
               | "^"

  from_or_semi ::= "T_FROM"
               | ";"


bfs_filters   ::=
              |  bfs_navigator
              |  bfs_filter
              |  bfs_navigator bfs_filter
              |  bfs_filter bfs_navigator

bfs_navigator ::=  "[" expr "]"

  bfs_filter  ::= "(" expr ")"


  sent_variable_decl ::=  typedecl var_target
                     |  typedecl id "=" rhs

  var_target::= id_comma_list

  sent_assignment ::= lhs "=" rhs
  sent_reduce_assignment ::= lhs reduce_eq rhs optional_bind
                         | lhs "T_PLUSPLUS" optional_bind

  sent_defer_assignment ::= lhs "T_LE" rhs optional_bind

  sent_argminmax_assignment ::= lhs_list2 minmax_eq rhs_list2 optional_bind

  optional_bind ::=
                |  "@" id

  reduce_eq ::= "T_PLUSEQ"
            | "T_MULTEQ"
            | "T_MINEQ"
            | "T_MAXEQ"
            | "T_ANDEQ"
            | "T_OREQ"

  minmax_eq ::= "T_MINEQ"
            | "T_MAXEQ"

  rhs ::= expr


  sent_return::= "T_RETURN" expr
             | "T_RETURN"

  sent_if ::= "T_IF" "(" bool_expr ")" sent
          | "T_IF" "(" bool_expr ")" sent "T_ELSE" sent


  sent_user ::= expr_user
            | expr_user "T_DOUBLE_COLON" "[" lhs_list "]"


  expr ::=     "(" expr ")"
             | "|" expr "|"
             | "-" expr  "NEG"

             | "!" expr    "NEG"
             | "(" prim_type ")" expr  "NEG"
             | reduce_op foreach_header "(" expr ")" "{" expr "}"
             | reduce_op foreach_header "{" expr "}"
             | reduce_op2 foreach_header "(" expr ")"
             | reduce_op2 foreach_header

             | expr "%" expr_fix
             | expr "*" expr_fix
             | expr "/" expr_fix
             | expr "+" expr_fix
             | expr "-" expr_fix
             | expr "T_LE" expr_fix
             | expr "T_GE" expr_fix
             | expr "<" expr_fix
             | expr ">" expr_fix
             | expr "T_EQ" expr_fix
             | expr "T_NEQ" expr_fix
             | expr "T_AND" expr_fix
             | expr "T_OR" expr_fix

             | expr "?" expr  ":" expr

             | expr_fix

    expr_fix ::=
            | "BOOL_VAL"
            | "INT_NUM"
            | "FLOAT_NUM"
            | inf
            | "T_NIL"
            | scala
            | field
            | built_in
            | expr_user
            | map_access

   bool_expr ::= expr
   numeric_expr::= expr

   reduce_op ::= "T_SUM"
             | "T_PRODUCT"
             | "T_MIN"
             | "T_MAX"
             | "T_EXIST"
             | "T_ALL"
             | "T_AVG"

  reduce_op2 ::= "T_COUNT"


  inf ::= "T_P_INF"
      | "T_M_INF"

  lhs ::= scala
      | field
      | map_access

  lhs_list ::= lhs
           | lhs "," lhs_list

  scala::= id
 field ::= id "." id
       | "T_EDGE" "("id ")" "." id

  map_access::= id "[" expr "]"

  built_in ::= id "." id arg_list
           | id arg_list
           | field "." id arg_list

  arg_list ::= "(" expr_list ")"
           | "(" ")"

  expr_list ::= expr
            | expr "," expr_list

  lhs_list2 ::=  "<" lhs ";" lhs_list ">"
  rhs_list2 ::= "<" expr ";" expr_list ">"


  expr_user ::= "[" "USER_TEXT" "]"

  id ::= "ID"
""",
"""
""")
