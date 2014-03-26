class Declaration(object):
    pass

class ScopeDeclaration(Declaration):

    def __init__(self, name, scope):
        self.name = name
        self.scope = scope
        self.declarations = []
        self.references = []
        self.index = 0

    def add(self, var):
        if isinstance(var, VarReference):
            self.references.append(var)
        elif isinstance(var, Declaration):
            self.declarations.append(var)
        var.index = self.index
        self.index += 1

    def get_field(self, ref):
        for d in self.declarations:
            # a valid reference  has:
            # - same name
            # - different scope OR smaller index
            # - different kind
            if d.name.symbol.name != ref.name.symbol.name:
                continue
            if d.kind != ref.kind: # XXX: doesn't apply for languages like Python
                continue
            if d.scope == ref.scope and d.index > ref.index:
                continue
            return d
        return self.scope.get_field(ref)

    def get_references(self):
        l = list(self.references)
        for d in self.declarations:
            l = l + d.get_references()
        return l

    def has_var(self, name):
        for d in self.declarations:
            if d.name.symbol.name == name.symbol.name:
                return True
        return self.scope.has_var(name)

class ClassDeclaration(ScopeDeclaration):
    def __init__(self, name, scope):
        ScopeDeclaration.__init__(self, name, scope)
        self.kind = "class"

class MethodDeclaration(ScopeDeclaration):
    def __init__(self, name, scope):
        ScopeDeclaration.__init__(self, name, scope)
        self.kind = "method"


class FieldDeclaration(Declaration):
    def __init__(self, name, scope, field_type, value):
        self.name = name
        self.scope = scope
        self.field_type = field_type
        self.index = -1
        self.kind = "var"
        self.value = value

    def __repr__(self):
        return "FieldDeclaration(%s, %s, %s)" % (self.name.symbol.name, self.scope.name, self.index)

    def get_references(self):
        return []

class VarReference(object):
    def __init__(self, name, scope):
        self.name = name
        self.scope = scope
        self.index = -1
        self.kind = "var"

    def __repr__(self):
        return "VarReference(%s, %s, %s)" % (self.name.symbol.name, self.scope.name, self.index)

class Value(object):
    def __init__(self, value_type, value):
        self.value_type = value_type
        self.value = value

class AstAnalyser(object):
    def __init__(self):
        self.errors = {}
        self.scope = None

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

    def scanClassDecl(self, node, scope):
        decl = ClassDeclaration(node.get('name'), scope)
        scope.add(decl)
        self.scan(node.get('body'), decl)

    def scanFieldDecl(self, node, scope):
        field_type = node.get('type')
        name = node.get('name')
        value = node.get('value')
        self.scan(value, scope)
        decl = FieldDeclaration(name, scope, field_type, value)
        scope.add(decl)

    def scanLocalVar(self, node, scope):
        self.scanFieldDecl(node, scope)
        return
        name = node.get('var').get('name')
        decl = FieldDeclaration(name, scope, None)
        self.scan(node.get('var'), scope)
        scope.add(decl)

    def scanint(self, node, scope):
        decl = Value('int', node.get('value'))
        return decl

    def scanid(self, node, scope):
        varref = VarReference(node.get('name'), scope)
        scope.add(varref)

    def scanVar(self, node, scope):
        self.scan(node.get('value'), scope)

    def scanPlus(self, node, scope):
        pass

    def scanMethodDecl(self, node, scope):
        name = node.get('header').get('name')
        decl = MethodDeclaration(name, scope)
        scope.add(decl)
        self.scan(node.get('body'), decl)

    def analyse(self, node):
        # scan
        self.errors = {}
        main = ScopeDeclaration("program", self)
        main.kind = main.name
        self.scan(node, main)
        # analyse
        refs = main.get_references()
        for e in refs:
            if isinstance(e, VarReference):
                decl = e.scope.get_field(e)
                if not decl:
                    self.errors[e.name] = "'%s' cannot be resolved to a variable." % (e.name.symbol.name)

    def has_error(self, node):
        return self.errors.has_key(node)

    def get_error(self, node):
        try:
            return self.errors[node]
        except KeyError:
            return ""
