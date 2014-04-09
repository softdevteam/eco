class URI(object):
    def __init__(self):
        self.kind = ""
        self.path = []
        self.name = ""
        self.ruleid = ""

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

        # rules
        self.rules = {
            'CompilationUnit': {'kind': 'compunit', 'args': [], 'scopes':['class']},
            'ClassDecl': {'kind': 'class', 'args': ['name'], 'scopes': ['field','method', 'class']},
            'FieldDecl': {'kind': 'field', 'args': ['name', 'type','value'], 'scopes': [], 'visibility': 'subsequent'},
            'MethodDecl': {'kind': 'method', 'args': ['name'], 'scopes': ['variable']},
            'LocalVar': {'kind': 'variable', 'args': ['name', 'type', 'value'], 'scopes': [], 'visibility': 'subsequent'},
            'id': {'kind': 'varref', 'args': ['name'], 'scopes':[], 'refers':['variable', 'field', 'class']},
            'FieldAccess': {'kind': 'fieldaccess', 'args': ['name','base'], 'scopes':[], 'refers':['field', 'class'], 'in':'base'},
        }

        self.d = {}

        self.data = {}
        self.index = 0

        rootnode = self.load_nb_file(filename)
        self.definitions = RuleReader().read(rootnode)

    def load_nb_file(self, filename):
        from jsonmanager import JsonManager
        from grammar_parser.bootstrap import BootstrapParser
        from grammars.grammars import lang_dict

        manager = JsonManager(unescape=True)

        # load nb file
        root, language, whitespaces = manager.load(filename)[0]

        # load scoping grammar
        grammar = lang_dict[language]
        bsroot, language, whitespaces = manager.load(grammar.filename)[0]
        pickle_id = hash(open(grammar.filename, "r").read())
        #XXX once we store the annotations in the json files invoking bootstrap parser becomes obsolete
        bootstrap = BootstrapParser(lr_type=1, whitespaces=whitespaces)
        bootstrap.ast = bsroot
        bootstrap.create_parser(pickle_id)
        bootstrap.create_lexer()
        bootstrap.incparser.previous_version.parent = root
        bootstrap.incparser.reparse()
        return bootstrap.incparser.previous_version.parent

    def has_var(self, name):
        return False

    def get_field(self, ref):
        return None

    def get_definition(self, nodename):
        for d in self.definitions:
            if d.name == nodename:
                return d

    def scan(self, node, path):
        if not node:
            return
        if node.__dict__.has_key('alternate') and node.alternate:
            self.scan(node.alternate, path)
            return

        from grammar_parser.bootstrap import AstNode
        if not isinstance(node, AstNode):
            for c in node.children:
                self.scan(c, path)
            return

        try:
            nbrule = self.get_definition(node.symbol.name)
            if not nbrule:
                return

            if nbrule.is_definition():
                kind, name = nbrule.get_definition()
            elif nbrule.is_reference():
                kind = "reference"
                _, name = nbrule.get_references()
            obj = URI()
            obj.nbrule = nbrule
            obj.kind = kind

            obj.node = node.get(name)
            if obj.node:
                obj.name = obj.node.symbol.name
            obj.path = list(path)

            # if last parent hasn't scope, delete from path
            if path != [] and not self.scopes(path[-1], obj): #XXX should be while?
                obj.path.pop(-1)

            base = nbrule.get_visibility()
            if base not in ['surrounding', 'subsequent']:
                base = node.get(base)
                base_uri = self.scan(base, path)
                path = [base_uri]
                obj.path = path
            else:
                base = None
                path = list(path)
                path.append(Reference(obj.kind, obj.name, obj.nbrule))

            for c in node.children:
                if node.children[c] is base:
                    continue # don't scan base twice
                self.scan(node.children[c], path)

            obj.index = self.index
            self.data.setdefault(obj.kind, [])
            self.data[obj.kind].append(obj)
            self.index += 1

            return obj # only needed for base

        except KeyError:
            for c in node.children:
                self.scan(node.children[c], path)
            return

    def analyse(self, node):
        # scan
        self.errors = {}

        self.data.clear()
        self.index = 0
        self.scan(node, [])
        self.analyse_refs()

    def analyse_refs(self):
        for key in self.data:
            nbrule = self.data[key][0].nbrule
            if nbrule.is_reference():
                obj = self.data[key]
                for reference in self.data[key]:
                    self.find_reference(reference)

    def find_reference(self, reference):
        for refers in reference.nbrule.get_references()[0]:
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

    def scopes(self, scope, obj):
        return obj.kind in scope.nbrule.get_scopes()

    def has_error(self, node):
        return self.errors.has_key(node)

    def get_error(self, node):
        try:
            return self.errors[node]
        except KeyError:
            return ""

class RuleReader(object):
    def read(self, root):
        l = self.read_definitions(root.children[1].children[1].alternate)
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
                l.append(n.symbol.name)
        return l

    def read_options(self, options):
        d = {}
        for option in options.children:
            if option.symbol.name == "Defines":
                d['defines'] = (option.get('type').symbol.name, option.get('name').symbol.name)
                scope = option.get('scope')
                if scope:
                    d['in'] = scope.symbol.name
            elif option.symbol.name == "Scopes":
                d['scopes'] = self.read_names(option.get('types'))
            elif option.symbol.name == "References":
                d['references'] = (self.read_names(option.get('types')), option.get('name').symbol.name)
                scope = option.get('scope')
                if scope:
                    d['in'] = scope.symbol.name
        return d

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

    def __repr__(self):
        return "NBRule(%s, %s, %s)" % (self.name, self.params, self.options)
