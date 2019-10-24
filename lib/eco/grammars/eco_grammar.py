# Copyright (c) 2012--2014 King's College London
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

eco_grammar = Language("Eco Grammar",
"""
grammar ::= parser ";" "%%" lexer

parser ::= rule
         | parser ";" rule

rule ::= "nonterminal" "assign" alternatives
alternatives ::= right
               | alternatives "|" right

right ::= symbols
        | symbols annotations
        |

annotations ::= "{" a_options "}"
a_options ::= astnode
            | expression
            | forloop

astnode ::= "nonterminal" "(" astnode_children ")"
astnode_children ::= astnode_child
                   | astnode_children "," astnode_child

astnode_child ::= "nonterminal" "=" expression
                | "nonterminal" "=" reference

reference ::= "nonterminal" "." "nonterminal"

expression ::= node
             | node_ref
             | list
             | expression "+" node
             | expression "+" list

forloop ::= "foreach" "(" node ")" astnode

node ::= "#" "NUMBER"
node_ref ::= node "." "nonterminal"

list ::= "[" "]"
       | "[" list_loop "]"
list_loop ::= astnode
            | list_loop "," astnode
            | node
            | list_loop "," node

symbols ::= symbols symbol
          | symbol
symbol ::= "nonterminal" | "terminal" | "languagebox"

lexer ::= lrule
        | lexer lrule

lrule ::= tokenname ":" "terminal"
tokenname ::= "nonterminal" | "languagebox"
""",
"""
"foreach":foreach
"[ \\t]+":<ws>
"[\\n\\r]":<return>
"[0-9]+":NUMBER
"[a-zA-Z_0-9]+":nonterminal
"\<[a-zA-Z_0-9 \.]+\>":languagebox
"\\"([^\\"\\\\]|\\\\.)*\\"":terminal
"::\=":assign
":"::
"\=":=
"\+":+
"\,":,
"\#":#
"\|":|
";":;
"\{":{
"\}":}
"\[":[
"\]":]
"\(":(
"\)":)
"\.":.
"%%":%%
""",
"Grammar")

#"\"((?:[^\"\\\]|(\\\\)+\")*)\"":terminal
