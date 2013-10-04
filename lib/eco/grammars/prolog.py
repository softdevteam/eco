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

prolog = Language("Prolog",
"""
program ::= clause_list query | query
clause_list ::= clause | clause_list clause
clause ::= predicate "." | predicate ":-" predicate_list "."
predicate_list ::= predicate | predicate_list "," predicate
predicate ::= atom | atom "(" term_list ")"
term_list ::= term | term_list "," term
term ::= "numeral" | atom | "variable" | structure
structure ::= atom "(" term_list ")"
query ::= "?-" predicate_list "."

atom ::= "small_atom" | "string"
""",
"""
"[ \\t]+":<ws>
"[\\n\\r]":<return>
"[0-9]+":numeral
"\'(\\\\.|[^\\\\'])*\'":string
"[a-z][a-zA-Z0-9\+\-\*\/\\\^\~\:\? \#\$\&]+":small_atom
"[A-Z][a-zA-Z0-9\+\-\*\/\\\^\~\:\? \#\$\&]+":variable
"\(":(
"\)":)
":-"::-
",":,
"\?-":?-
".":.
"""
)
