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

from .grammars import Language

indent_based = Language("Indentation based language",
"""
    class_def ::= "class" "ID" ":" "INDENT" class_body "DEDENT"
    class_body ::= "pass" | func_defs
    func_defs ::= func_def func_defs | func_def
    func_def ::= "def" "ID" ":" "INDENT" func_body "DEDENT"
    func_body ::= func_body_def func_body | func_body_def
    func_body_def ::= for_loop | assignment | "pass" | func_def
    for_loop ::= "for" "ID" "in" "ID" ":" "INDENT" func_body "DEDENT"
    assignment ::= "ID" "=" "ID"
                 | "ID" "=" "INT"
"""
,
"""%indentation=true
"pass":pass
"class":class
"def":def
"for":for
"in":in
"[0-9]+":INT
"[a-zA-Z][a-zA-Z_0-9]*":ID
":"::
"=":=
"[ \\t]+":<ws>
"[\\n\\r]":<return>
""")

