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

import os, json

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
        self.auto_limit_new = False

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
        if isinstance(language, EcoFile):
            # Backwards compatibility
            lang = language.name
        else:
            lang = language
        if nonterminal not in self.alts:
            self.alts[nonterminal] = []
        self.alts[nonterminal].append("<%s>" % lang)
        self.included_langs.add(lang)

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

    def __eq__(self, other):
        if self.name != other.name:
            return False
        if self.base != other.base:
            return False
        if self.filename != other.filename:
            return False
        if self.alts != other.alts:
            return False
        if self.included_langs != other.included_langs:
            return False
        if self.extract != other.extract:
            return False
        if self.auto_include != other.auto_include:
            return False
        if self.auto_exclude != other.auto_exclude:
            return False
        if self.auto_limit_new != other.auto_limit_new:
            return False
        if self.nb_file != other.nb_file:
            return False
        return True

    def __hash__(self):
        h1 = hash(file(self.filename, "r").read())
        h2 = hash(repr(self.alts))
        h3 = hash(str(self.extract))
        return h1 ^ h2 ^ h3

languages = []
newfile_langs = []
submenu_langs = []
lang_dict = {}

def add_lang(lang, new=False, sub=False):
    if lang in languages:
        # if two language definitions are identical we only need to add one of
        # them
        return
    languages.append(lang)
    if lang_dict.has_key(lang.name):
        print("Error: Multiple definitions for language '{}'".format(lang))
        exit()
    lang_dict[lang.name] = lang
    if new:
        newfile_langs.append(lang)
    if sub:
        submenu_langs.append(lang)

regex = EcoFile("Regex", "grammars/regex.eco", "Regex")
add_lang(regex, True, False)

if not __pypy__:
    from rubyparser.rubyparser import RubyProxy
    ruby = RubyProxy()
    add_lang(ruby, True, True)

# import languages from grammars/include

def create_grammar_from_config(cfg, filename):
    main = EcoFile(cfg["name"], cfg["file"], cfg["base"])
    if cfg.has_key("limit_historic_tokens"):
        main.auto_limit_new = cfg["limit_historic_tokens"]
    if cfg.has_key("subset") and cfg["subset"]:
        main.change_start(cfg["subset"])
    if cfg.has_key("custom_namebinding"):
        main.set_custom_nb(cfg["custom_namebinding"])
    if cfg.has_key("compositions"):
        for c in cfg["compositions"]:
            if not c.has_key("file"):
                sub = c["name"]
                reused.append((filename, sub))
            else:
                sub = create_grammar_from_config(c, filename)
            main.add_alternative(c["location"], sub)
    show_newfile = "newfile" in cfg["visibility"]
    show_submenu = "submenu" in cfg["visibility"]
    add_lang(main, show_newfile, show_submenu)
    return main.name

reused = []
for root, _, files in os.walk("grammars/include/"):
    for filename in files:
        with open(os.path.join(root, filename)) as f:
            grmcfg = json.load(f)
            create_grammar_from_config(grmcfg, filename)
    error = False

for r in reused:
    if not r[1] in lang_dict:
        error = True
        print "Error in '{}': Referenced language '{}' doesn't exist.".format(r[0], r[1])
if error:
    exit()
