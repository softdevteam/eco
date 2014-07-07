# Copyright (c) 2014 King's College London
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

from grammar_parser.bootstrap import AstNode, ListNode

class URI(object):
    def __init__(self):
        self.kind = ""
        self.path = []
        self.name = ""
        self.ruleid = ""
        self.index = -1

    def __repr__(self):
        path = []
        for p in self.path:
            path.append(repr(p))
        return "URI(%s:%s,\"%s\",%s)" % (self.kind, ",".join(path), self.name, self.index)

class Reference(object):
    def __init__(self, kind, name, nbrule=None):
        self.kind = kind
        self.name = name
        self.nbrule = nbrule

    def __eq__(self, other):
        return self.kind == other.kind and self.name == other.name

    def __repr__(self):
        return "Ref(%s/%s)" % (self.kind, self.name)

class AstAnalyser(object):
    def __init__(self, filename):
        self.errors = {}
        self.scope = None

        self.d = {}

        self.data = {}
        self.index = 0

        rootnode = self.load_nb_file(filename)
        self.definitions = RuleReader().read(rootnode)

        self.processed_nodes = set()

    def load_nb_file(self, filename):
        from jsonmanager import JsonManager
        from grammar_parser.bootstrap import BootstrapParser
        from grammars.grammars import lang_dict

        manager = JsonManager(unescape=True)

        # load nb file
        root, language, whitespaces = manager.load(filename)[0]

        # load scoping grammar
        grammar = lang_dict[language]
        parser, lexer = grammar.load()
        parser.previous_version.parent = root
        parser.reparse()
        return parser.previous_version.parent

    def has_var(self, name):
        return False

    def get_field(self, ref):
        return None

    def get_definition(self, node):
        nodename = node.symbol.name
        for d in self.definitions:
            if d.name == nodename:
                # overloaded definitions allowed: check if types match
                if self.match(node, d):
                    return d

    def match(self, astnode, nbrule):
        for p in nbrule.params:
            if isinstance(p, tuple):
                name = p[0]  # nbrule parameter name, e.g. lhs
                _type = p[1] # nbrule parameter type, e.g. Name
                ref = astnode.get(name.symbol.name) # reference in AstNode, e.g. lhs -> AstNode("Name")
                if not isinstance(ref, AstNode):
                    return False
                if ref.name != _type.symbol.name:
                    return False
        return True

    def scan(self, node, path):
        if node is None:
            return

        if hasattr(node, 'alternate') and node.alternate:
            node = node.alternate

        from grammar_parser.bootstrap import AstNode, ListNode

        if isinstance(node, AstNode):
            if id(node) in self.processed_nodes: # skip nodes that have been processed in parent
                return

            base = None
            nbrule = self.get_definition(node)
            uris = []
            _type = None
            if nbrule:

                uri = URI()
                if nbrule.is_reference():
                    _type = "reference"
                    uri = self.create_uri(node, nbrule, _type, list(path), path)
                    uris.extend(uri)
                    uri = uri[0]

                if nbrule.is_definition():
                    _type = nbrule.get_definition()[0]

                    scoped_path = list(path)
                    if scoped_path != [] and not self.scopes(scoped_path[-1], _type): #XXX should be while?
                        # if last parent hasn't scope, delete from path
                        scoped_path.pop(-1)

                    uri = self.create_uri(node, nbrule, _type, scoped_path, path)
                    uris.extend(uri)
                    uri = uri[0]

                path = list(path)
                path.append(Reference(_type, uri.name, nbrule))

            # scan ASTNodes children
            for c in node.children:
                if node.children[c] is base:
                    continue # don't scan base twice
                self.scan(node.children[c], path)

            # set index AFTER children have been scanned: XXX not correct. int x = x needs to be treated extra
            uri = None
            for uri in uris:
                uri.index = self.index
                self.data.setdefault(uri.kind, [])
                self.data[uri.kind].append(uri)
                self.index += 1

            return uri # only needed for base

        else:
            for c in node.children:
                self.scan(c, path)
            return

    def resolve_name(self, node, dotnames):
        tempnode = node
        if isinstance(dotnames, list):
            for n in dotnames:
                tempnode = tempnode.get(n)
                self.processed_nodes.add(id(tempnode))
            name = tempnode
        else:
            name = node.get(dotnames) # scopes returns None

        if isinstance(name, ListNode):
            names = name.children
        else:
            names = [name]
        return names

    def create_uri(self, node, nbrule, _type, newpath, prevpath):
        if _type == "reference":
            names = self.resolve_name(node, nbrule.get_refname())
        else:
            names = self.resolve_name(node, nbrule.get_defname())
        uris = []
        for n in names: #XXX ast should use foreach instead
            uri = URI()
            if n is None:
                uri.name = None
            else:
                uri.name = n.symbol.name
            uri.kind = _type
            uri.path = newpath
            uri.nbrule = nbrule
            uri.node = n
            uri.vartype = node.get('type') # XXX needs to be defined by autocomplete rules
            uri.astnode = node

            visibility = nbrule.get_visibility()
            if visibility not in ['surrounding','subsequent']:
                # URI has a base
                base = node.get(visibility)
                base_uri = self.scan(base, prevpath) # this has to be an ASTNode to be successfully scanned
                path = [base_uri]
                uri.path = path

            uris.append(uri)
        return uris

    def analyse(self, node):
        # scan
        self.errors = {}

        self.data.clear()
        self.processed_nodes.clear()
        self.index = 0
        self.scan(node, [])
        self.analyse_refs()

    def analyse_refs(self):
       #for key in self.data:
       #    nbrule = self.data[key][0].nbrule
       #    if nbrule.is_reference():
       #        obj = self.data[key]
        if self.data.has_key("reference"):
            for reference in self.data["reference"]:
                self.find_reference(reference)

    def find_reference(self, reference):
        for refers in reference.nbrule.get_references()[0]:

            # global variable
            if len(reference.path) == 0:
                x = self.get_reference(refers, reference.path, reference.name)
                if x:
                    return x

            # iteratate through path prefixes
            path = list(reference.path)
            while len(path) > 0:
                x = self.get_reference(refers, path, reference.name)
                if x:
                    if x.nbrule.get_visibility() != "subsequent":
                        return x
                    if x.nbrule.get_visibility() == "subsequent" and x.index < reference.index:
                        return x
                path.pop() # try with prefix of path

        # URI is alias (nested URIs)
        # evaluate references, then get_reference
        if len(reference.path) > 0 and isinstance(reference.path[0], URI):
            x = self.find_reference(reference.path[0])
            if x:
                for refers in reference.nbrule.get_references()[0]:
                    z = self.get_reference(refers, x.path + [Reference(x.kind, x.name)], reference.name)
                    if z:
                        return z

        self.errors[reference.node] = "'%s' cannot be resolved to a variable." % (reference.name)

    def get_reference(self, kind, path, name):
        if not self.data.has_key(kind):
            return None
        for candidate in self.data[kind]:
            if candidate.name != name:
                continue
            if not self.paths_eq(candidate.path, path):
                continue
            return candidate
        return None

    def paths_eq(self, path1, path2):
        if len(path1) != len(path2):
            return False
        for i in range(len(path1)):
            if path1[i].name != path2[i].name:
                return False
            if path1[i].kind != path2[i].kind: #XXX only if types matter (e.g. python doesn't care)
                return False
        return True

    def scopes(self, scope, _type):
        return _type in scope.nbrule.get_scopes()

    def has_error(self, node):
        return self.errors.has_key(node)

    def get_error(self, node):
        try:
            return self.errors[node]
        except KeyError:
            return ""

    def get_completion(self, scope):
        # find astnode with rule
        astnode = self.get_correct_astnode(scope)
        if not astnode:
            return []
        nbrule = self.get_definition(astnode)
        name = astnode.get(nbrule.get_name())

        uri = self.find_uri_by_astnode(name)
        if uri:
            path = uri.path + [uri]
            names = self.get_reachable_names_by_path(path)
            if scope.lookup in ["NAME","nonterminal","IDENTIFIER"]: #XXX this needs to be provided by the grammar
                filtered_names = []
                for uri in names:
                    if uri.name.startswith(scope.symbol.name):
                        filtered_names.append(uri)
                return filtered_names
            return names

    def get_correct_astnode(self, scope):
        # returns the correct astnode for a corresponding scope. Is needed for
        # nested astnodes that have rules, e.g. blocks inside methods
        while scope is not None:
            astnode = scope.alternate
            if astnode:
                nbrule = self.get_definition(scope.alternate)
                # astnode must have a corresponding entry in self.data
                if nbrule and self.data.has_key(nbrule.get_type()):
                    for e in self.data[nbrule.get_type()]:
                        if e.astnode is astnode:
                            return astnode
            scope = scope.parent

    def find_uri_by_astnode(self, node):
        for key in self.data:
            for uri in self.data[key]:
                if uri.node == node:
                    return uri
        return None

    def get_reachable_names_by_path(self, path):
        names = []
        path = list(path)   # copy to not manipulate existing path
        while path != []:
            for key in self.data:
                if key in ["reference", "block"]: #XXX needs to be supplied by codecompletion rules
                    continue
                for uri in self.data[key]:
                    if uri.path == path:
                        names.append(uri)
            path.pop()
        return names

class RuleReader(object):
    def read(self, root):
        definitions = root.children[1].children[1].alternate
        l = self.read_definitions(definitions)
        return l

    def read_definitions(self, definitions):
        l = []
        for definition in definitions.children:
            name = definition.get("name").symbol.name
            params = self.read_names(definition.get('args'))
            options = self.read_options(definition.get('options'))
            l.append(NBRule(name, params, options))
        return l

    def read_names(self, node):
        l = []
        if node:
            for n in node.children:
                if isinstance(n, AstNode) and n.name == "Parameter":
                    name = n.get("name")
                    _type = n.get("type")
                    l.append((name, _type))
                else:
                    l.append(n.symbol.name)
        return l

    def read_options(self, options):
        d = {}
        for option in options.children:
            if option.symbol.name == "Defines":
                names = self.get_dotnames(option.get("name"))
                d['defines'] = (option.get('type').symbol.name, names) # Class(name): defines class name
                scope = option.get('scope')
                if scope:
                    d['in'] = scope.symbol.name
            elif option.symbol.name == "Scopes":
                d['scopes'] = self.read_names(option.get('types'))
            elif option.symbol.name == "References":
                names = self.get_dotnames(option.get("name"))
                d['references'] = (self.read_names(option.get('types')), names) # Lookup(name): references field, variable name
                scope = option.get('scope')
                if scope:
                    d['in'] = scope.symbol.name
        return d

    def get_dotnames(self, node):
        if isinstance(node, ListNode):
            names = []
            for name in node.children:
                names.append(name.symbol.name)
        else:
            names = [name.symbol.name]
        return names

class NBRule(object):
    def __init__(self, name, params, options):
        self.name = name
        self.params = params
        self.options = options

    def is_definition(self):
        return self.options.has_key('defines')

    def is_reference(self):
        return self.options.has_key('references')

    def get_scopes(self):
        if self.options.has_key('scopes'):
            return self.options['scopes']
        return []

    def get_references(self):
        if self.options.has_key('references'):
            return self.options['references']
        return []

    def get_definition(self):
        if self.options.has_key('defines'):
            return self.options['defines']
        return None

    def get_visibility(self):
        if self.options.has_key('in'):
            return self.options['in']
        return "surrounding"

    def get_in(self):
        if self.options.has_key('in'):
            return self.options['in']
        return None

    def get_reftype(self):
        if self.is_reference():
            return "reference"

    def get_deftype(self):
        if self.is_definition():
            return self.options['defines'][0]

    def get_refname(self):
        if self.is_reference():
            return self.options['references'][1]
    def get_defname(self):
        if self.is_definition():
            return self.options['defines'][1]

    def __repr__(self):
        return "NBRule(%s, %s, %s)" % (self.name, self.params, self.options)
