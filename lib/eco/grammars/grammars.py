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

class Language(object):

    def __init__(self, name, grammar, priorities, base=""):
        self.name = name
        self.grammar = grammar
        self.priorities = priorities
        self.base = base

    def __str__(self):
        return self.name

class EcoGrammar(object):

    def __init__(self, name, grammar, base=""):
        self.name = name
        self.grammar = grammar
        self.base = base

    def __str__(self):
        return self.name

class EcoFile(object):
    def __init__(self, name, filename, base=""):
        self.name = name
        self.filename = filename
        self.base = base
        self.alts = {}
        self.extract = None

    def load(self):
        from grammar_parser.bootstrap import BootstrapParser
        from jsonmanager import JsonManager

        manager = JsonManager(unescape=True)
        root, language, whitespaces = manager.load(self.filename)[0]
        pickle_id = hash(self)
        bootstrap = BootstrapParser(lr_type=1, whitespaces=whitespaces)
        bootstrap.ast = root
        bootstrap.extra_alternatives = self.alts
        bootstrap.change_startrule = self.extract
        bootstrap.read_options()
        bootstrap.create_parser(pickle_id)
        bootstrap.create_lexer()
        return (bootstrap.incparser, bootstrap.inclexer)

    def add_alternative(self, nonterminal, language):
        if nonterminal not in self.alts:
            self.alts[nonterminal] = []
        self.alts[nonterminal].append("<%s>" % language.name)

    def change_start(self, name):
        self.extract = name

    def __str__(self):
        return self.name

    def __hash__(self):
        h1 = hash(file(self.filename, "r").read())
        h2 = hash(repr(self.alts))
        h3 = hash(str(self.extract))
        return h1 ^ h2 ^ h3

from eco_grammar import eco_grammar # needed to edit EcoGrammar

# base languages
calc = EcoFile("Basic Calculator", "grammars/basiccalc.eco", "Calc")
java = EcoFile("Java 1.5", "grammars/java15.eco", "Java")
python = EcoFile("Python 2.7.5", "grammars/python275.eco", "Python")
prolog = EcoFile("Prolog", "grammars/prolog.eco", "Prolog")
scoping = EcoFile("Scoping Rules (Ecofile)", "grammars/scoping_grammar.eco", "Scoping")
eco = EcoFile("Eco Grammar (Ecofile)", "grammars/eco_grammar.eco", "Grammar") # based on eco_grammar
html = EcoFile("HTML", "grammars/html.eco", "Html")
sql = EcoFile("SQL", "grammars/sql.eco", "Sql")
img = EcoFile("Image", "grammars/img.eco", "Image")
chemical = EcoFile("Chemicals", "grammars/chemicals.eco", "Chemicals")
php = EcoFile("PHP", "grammars/php.eco", "Php")

# extensions
pythonprolog = EcoFile("Python + Prolog", "grammars/python275.eco", "Python")
pythonprolog.add_alternative("atom", prolog)

pythonhtmlsql = EcoFile("Python + HTML + SQL", "grammars/python275.eco", "Python")
pythonhtmlsql.add_alternative("atom", html)
pythonhtmlsql.add_alternative("atom", sql)

htmlpythonsql = EcoFile("HTML + Python + SQL", "grammars/html.eco", "Html")
htmlpythonsql.add_alternative("element", pythonhtmlsql)
htmlpythonsql.add_alternative("attribute_value", img)

java_expr = EcoFile("Java expression", "grammars/java15.eco", "Java")
java_expr.change_start("expression")
java_expr.add_alternative("unary_expression", chemical)

sql_ref_java = EcoFile("SQL ref. Java expression", "grammars/sql.eco", "Sql")
sql_ref_java.add_alternative("y_condition", java_expr)

javasqlchemical = EcoFile("Java + SQL + Chemical", "grammars/java15.eco", "Java")
javasqlchemical.add_alternative("unary_expression", sql_ref_java)

languages = [calc, java, javasqlchemical, java_expr, php, python, pythonhtmlsql, pythonprolog, prolog, sql, sql_ref_java, html, htmlpythonsql, eco, scoping, img, chemical, eco_grammar]
newfile_langs = [java, javasqlchemical, php, python, pythonhtmlsql, pythonprolog, prolog, sql, html, htmlpythonsql]
submenu_langs = [java, javasqlchemical, java_expr, php, python, pythonhtmlsql, pythonprolog, prolog, sql, sql_ref_java, html, htmlpythonsql, img, chemical]

lang_dict = {}
for l in languages:
    lang_dict[l.name] = l
