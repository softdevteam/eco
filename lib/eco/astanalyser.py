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
        return "URI(%s:%s,\"%s\")" % (self.kind, ",".join(path), self.name)

class Reference(object):
    def __init__(self, kind, name, ruleid=""):
        self.kind = kind
        self.name = name
        self.ruleid = ruleid

    def __eq__(self, other):
        return self.kind == other.kind and self.name == other.name

    def __repr__(self):
        return "Ref(%s/%s)" % (self.kind, self.name)

class AstAnalyser(object):
    def __init__(self):
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

    def has_var(self, name):
        return False

    def get_field(self, ref):
        return None

    def scan(self, node, scope):
        from grammar_parser.bootstrap import AstNode
        if not node:
            return
        if isinstance(node, AstNode):
            try:
                self.__getattribute__("scan" + node.symbol.name)(node, scope)
            except AttributeError:
                pass
            return

        if node.__dict__.has_key('alternate') and node.alternate:
            self.scan(node.alternate, scope)
            return

        for c in node.children:
            self.scan(c, scope)

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
            kind = self.rules[node.symbol.name]['kind']
            obj = URI()
            obj.ruleid = node.symbol.name

            obj.node = node.get('name')
            if obj.node:
                obj.name = obj.node.symbol.name
            obj.kind = kind
            obj.path = list(path)

            # if last parent hasn't scope, delete from path
            if path != [] and not self.scopes(path[-1], obj): #XXX should be while?
                obj.path.pop(-1)

            if self.rules[node.symbol.name].has_key('in'):
                where = self.rules[node.symbol.name]['in']
                base = node.get(where)
                base_uri = self.scan(base, path)
                path = [base_uri]
                obj.path = path
            else:
                base = None
                path = list(path)
                path.append(Reference(obj.kind, obj.name, obj.ruleid))

            for c in node.children:
                if node.children[c] is base:
                    continue # don't scan base twice
                self.scan(node.children[c], path)

            obj.index = self.index
            self.data.setdefault(obj.kind, [])
            self.data[obj.kind].append(obj)
            self.index += 1

            return obj

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

    def find_references(self, parent, refs):
        for c in parent.children:
            if self.rules[c.ruleid].has_key('refers'):
                refs.append(c)
            self.find_references(c, refs)

    def analyse_refs(self):
        for key in self.data:
            ruleid = self.data[key][0].ruleid
            if self.rules[ruleid].has_key('refers'):
                obj = self.data[key]
                for reference in self.data[key]:
                    self.find_reference(reference)

    def find_reference(self, reference):
        for refers in self.rules[reference.ruleid]['refers']:
            path = list(reference.path)
            while len(path) > 0:
                x = self.get_reference(refers, path, reference.name)
                if x:
                    try:
                        visibility = self.rules[x.ruleid]['visibility']
                    except KeyError:
                        visibility = 'normal'
                    if visibility == "normal":
                        return x
                    if visibility == "subsequent" and x.index < reference.index:
                        return x
                path.pop() # try with prefix of path

        # URI is alias (nested URIs)
        # evaluate references, then get_reference
        if len(reference.path) > 0 and isinstance(reference.path[0], URI):
            x = self.find_reference(reference.path[0])
            if x:
                for refers in self.rules[reference.ruleid]['refers']:
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
        try:
            return obj.kind in self.rules[scope.ruleid]['scopes']
        except KeyError:
            return False

    def has_error(self, node):
        return self.errors.has_key(node)

    def get_error(self, node):
        try:
            return self.errors[node]
        except KeyError:
            return ""
