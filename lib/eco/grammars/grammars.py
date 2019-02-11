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

import os

try:
    import __pypy__
except ImportError:
    __pypy__ = None

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

_cache = {}
class EcoFile(object):
    def __init__(self, name, filename, base=""):
        self.name = name
        self.filename = filename
        self.base = base
        self.alts = {}
        self.included_langs = set()
        self.extract = None
        self.auto_include = None
        self.auto_exclude = None
        self.nb_file = os.path.splitext(filename)[0] + ".nb"

    def load(self, buildlexer=True):
        from grammar_parser.bootstrap import BootstrapParser
        from jsonmanager import JsonManager
        from incparser.incparser import IncParser

        if _cache.has_key(self.name + "::parser"):

            syntaxtable, whitespaces = _cache[self.name + "::parser"]
            incparser = IncParser()
            incparser.syntaxtable = syntaxtable
            incparser.whitespaces = whitespaces
            incparser.init_ast()
            incparser.lang = self.name

            inclexer = _cache[self.name + "::lexer"]
            incparser.lexer = inclexer # give parser a reference to its lexer (needed for multiline comments)
            incparser.previous_version.parent.name = self.name

            return (incparser, inclexer)
        else:
            manager = JsonManager(unescape=True)
            root, language, whitespaces = manager.load(self.filename)[0]

            pickle_id = hash(self)
            bootstrap = BootstrapParser(lr_type=1, whitespaces=whitespaces)
            bootstrap.ast = root
            bootstrap.extra_alternatives = self.alts
            bootstrap.change_startrule = self.extract
            bootstrap.read_options()

            bootstrap.parse_both()
            bootstrap.create_parser(pickle_id)
            bootstrap.create_lexer(buildlexer)
            whitespace = bootstrap.implicit_ws()

            _cache[self.name + "::lexer"] = bootstrap.inclexer
            _cache[self.name + "::json"] = (root, language, whitespaces)
            _cache[self.name + "::parser"] = (bootstrap.incparser.syntaxtable, whitespace)

            bootstrap.incparser.lang = self.name
            bootstrap.incparser.previous_version.parent.name = self.name
            bootstrap.incparser.lexer = bootstrap.inclexer
            return (bootstrap.incparser, bootstrap.inclexer)

    def add_alternative(self, nonterminal, language):
        if nonterminal not in self.alts:
            self.alts[nonterminal] = []
        self.alts[nonterminal].append("<%s>" % language.name)
        self.included_langs.add(language.name)

    def change_start(self, name):
        self.extract = name

    def set_auto_include(self, lang, tokentype):
        if self.auto_include is None:
            self.auto_include = {}
        self.auto_include[lang] = tokentype

    def set_auto_exclude(self, lang, tokentype):
        if self.auto_include is not None:
            print "Warning: Inclusion and exclusion rules may conflict! Exclusion rules will be ignored."
            return
        if self.auto_exclude is None:
            self.auto_exclude = {}
        self.auto_exclude[lang] = tokentype

    def set_custom_nb(self, basename):
        self.nb_file = "{}/{}".format(os.path.dirname(self.filename), basename)

    def auto_allows(self, lang, tokentype):
        if self.auto_include and self.auto_include.has_key(lang):
            return tokentype in self.auto_include[lang]
        if self.auto_exclude and self.auto_exclude.has_key(lang):
            return tokentype not in self.auto_exclude[lang]
        return True

    def __str__(self):
        return self.name

    def __hash__(self):
        h1 = hash(file(self.filename, "r").read())
        h2 = hash(repr(self.alts))
        h3 = hash(str(self.extract))
        return h1 ^ h2 ^ h3

languages = []
newfile_langs = []
submenu_langs = []
def add_lang(lang, new=False, sub=False):
    languages.append(lang)
    if new:
        newfile_langs.append(lang)
    if sub:
        submenu_langs.append(lang)

from eco_grammar import eco_grammar # needed to edit EcoGrammar

# base languages
calc = EcoFile("Basic Calculator", "grammars/basiccalc.eco", "Calc")
add_lang(calc, True)
java = EcoFile("Java 1.5", "grammars/java15.eco", "Java")
add_lang(java, True, True)
python = EcoFile("Python 2.7.5", "grammars/python275.eco", "Python")
add_lang(python, True, True)
ipython = EcoFile("IPython", "grammars/python275.eco", "IPython")
add_lang(ipython, False, True)
prolog = EcoFile("Prolog", "grammars/prolog.eco", "Prolog")
add_lang(prolog, True, True)
scoping = EcoFile("Scoping Rules (Ecofile)", "grammars/scoping_grammar.eco", "Scoping")
add_lang(scoping, False, False)
eco = EcoFile("Eco Grammar (Ecofile)", "grammars/eco_grammar.eco", "Grammar") # based on eco_grammar
add_lang(eco, False, False)
html = EcoFile("HTML", "grammars/html.eco", "Html")
add_lang(html, True, True)
sql = EcoFile("SQL (Dummy)", "grammars/sql.eco", "Sql")
add_lang(sql, True, True)
sqlite = EcoFile("SQLite", "grammars/sqlite.eco", "Sql")
add_lang(sqlite, True, True)
img = EcoFile("Image", "grammars/img.eco", "Image")
add_lang(img, False, True)
chemical = EcoFile("Chemicals", "grammars/chemicals.eco", "Chemicals")
add_lang(chemical, False, True)
php = EcoFile("PHP", "grammars/php.eco", "Php")
add_lang(php, True, True)
javascript = EcoFile("JavaScript", "grammars/javascript.eco", "JavaScript")
add_lang(javascript, True, True)

# extensions
pythonprolog = EcoFile("Python + Prolog", "grammars/python275.eco", "Python")
pythonprolog.add_alternative("atom", prolog)
add_lang(pythonprolog, True, True)

sql_single = EcoFile("SQL Statement", "grammars/sql.eco", "Sql")
sql_single.change_start("sql_line")
add_lang(sql_single, False, True)

pythonhtmlsql = EcoFile("Python + HTML + SQL", "grammars/python275.eco", "Python")
pythonhtmlsql.add_alternative("atom", html)
pythonhtmlsql.add_alternative("atom", sql)
add_lang(pythonhtmlsql, True, True)

pythonhtmlsqlsingle = EcoFile("Python + HTML + SQLStmt", "grammars/python275.eco", "Python")
pythonhtmlsqlsingle.add_alternative("atom", html)
pythonhtmlsqlsingle.add_alternative("atom", sql_single)
add_lang(pythonhtmlsqlsingle, True, False)

htmlpythonsql = EcoFile("HTML + Python + SQL", "grammars/html.eco", "Html")
htmlpythonsql.add_alternative("element", pythonhtmlsql)
htmlpythonsql.add_alternative("attribute_value", img)
add_lang(htmlpythonsql, True, True)

java_expr = EcoFile("Java expression", "grammars/java15.eco", "Java")
java_expr.change_start("expression")
java_expr.add_alternative("unary_expression", chemical)
add_lang(java_expr, False, True)

sql_ref_java = EcoFile("SQL ref. Java expression", "grammars/sql.eco", "Sql")
sql_ref_java.add_alternative("y_condition", java_expr)
add_lang(sql_ref_java, False, True)

javasql = EcoFile("Java + SQL", "grammars/java15.eco", "Java")
javasql.add_alternative("unary_expression", sqlite)
add_lang(javasql, True, False)

javasqlchemical = EcoFile("Java + SQL + Chemical", "grammars/java15.eco", "Java")
javasqlchemical.add_alternative("unary_expression", sql_ref_java)
add_lang(javasqlchemical, True, True)

python_expr = EcoFile("Python expression", "grammars/python275.eco", "Python")
python_expr.change_start("simple_stmt")
add_lang(python_expr, False, True)

python_method = EcoFile("Python method", "grammars/python275.eco", "Python")
python_method.change_start("funcdef")
add_lang(python_method, False, True)

python_class = EcoFile("Python class", "grammars/python275.eco", "Python")
python_class.change_start("classdef")
add_lang(python_class, False, True)

phppython = EcoFile("PHP + Python", "grammars/php.eco", "Php")
phppython.set_custom_nb("phppython.nb")
pythonphp = EcoFile("Python + PHP", "grammars/python275.eco", "Python")
phppython.add_alternative("top_statement", pythonphp)
phppython.add_alternative("class_statement", pythonphp)
phppython.add_alternative("expr", pythonphp)
phppython.add_alternative("expr", python_expr)
pythonphp.add_alternative("atom", phppython)
add_lang(phppython, True, True)
add_lang(pythonphp, True, True)

pythonipython = EcoFile("Python + IPython", "grammars/python275.eco", "Python")
pythonipython.add_alternative("atom", ipython)
add_lang(pythonipython, True, False)

simplelang = EcoFile("SimpleLanguage", "grammars/simplelang.eco", "SimpleLanguage")
add_lang(simplelang, True, True)

if not __pypy__:
    from rubyparser.rubyparser import RubyProxy
    ruby = RubyProxy()
    add_lang(ruby, True, True)

rubysl = EcoFile("Ruby + SimpleLanguage", "grammars/ruby.eco", "Ruby")
rubysl.add_alternative("top_stmt", simplelang)
add_lang(rubysl, True, True)

rubyjs = EcoFile("Ruby + JavaScript", "grammars/ruby.eco", "Ruby")
rubyjs.add_alternative("top_stmt", javascript)
add_lang(rubyjs, True, True)

regex = EcoFile("Regex", "grammars/regex.eco", "Regex")
add_lang(regex, True, False)

javapy = EcoFile("Java + Python", "grammars/java15.eco", "Java")
javapy.add_alternative("unary_expression", python_expr)
javapy.add_alternative("class_body_declaration", python_method)
javapy.add_alternative("class_body_declaration", python_class)
add_lang(javapy, True, False)

lang_dict = {}
for l in languages:
    lang_dict[l.name] = l
