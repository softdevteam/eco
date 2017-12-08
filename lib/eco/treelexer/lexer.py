class RE_OR(object):
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs

    def __repr__(self):
        return "OR(%s, %s)" % (self.lhs, self.rhs)

    def __eq__(self, other):
        return type(other) is type(self) and \
                self.lhs == other.lhs and self.rhs == other.rhs

class RE_DEFAULT(object):
    def __init__(self, c):
        self.c = c

    def __eq__(self, other):
        return type(other) is type(self) and self.c == other.c

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.c)

class RE_CHAR(RE_DEFAULT): pass
class RE_STAR(RE_DEFAULT): pass
class RE_PLUS(RE_DEFAULT): pass
class RE_RANGE(RE_DEFAULT): pass

class PatternMatcher(object):

    def __init__(self):
        self.pos = 0

    def match_one(self, pattern, text):
        if not pattern:
            # Empty pattern always matches
            return True
        if self.pos >= len(text):
            # Existing pattern can't match empty input
            return False
        if pattern.c == ".":
            # Wild card always matches
            self.pos += 1
            return True
        if pattern.c == text[self.pos]:
            self.pos += 1
            return True
        return False

    def match_question(self, pattern, text):
        if not text:
            # No more text, so ? is automatically true
            return True
        if self.match_one(pattern, text):
            # character appears 1 time. Remove question pattern and continue
            return self.match(pattern[2:], text[1:])
        # character appears zero times
        return self.match(pattern[2:], text)

    def match_star(self, pattern, text):
        while True:
            if not self.match(pattern.c, text):
                break
        return True

    def match_plus(self, pattern, text):
        if not self.match(pattern.c, text):
            # we have to at least match one
            return False
        while True:
            if not self.match(pattern.c, text):
                break
        return True

    def match_list(self, pattern, text):
        for p in pattern:
            if not self.match(p, text):
                return False
        return True

    def match_or(self, pattern, text):
        tmp = self.pos
        if self.match(pattern.lhs, text):
            return True
        self.pos = tmp # backtrack
        return self.match(pattern.rhs, text)

    def match_range(self, pattern, text):
        for r in pattern.c:
            if self.pos >= len(text):
                return False

            s = ord(r[0])
            e = ord(r[2])
            if s <= ord(text[self.pos]) <= e:
                self.pos += 1
                return True
        return False

    def match(self, pattern, text):
        if not pattern:
            return True
        if type(pattern) is list:
            return self.match_list(pattern, text)
        if type(pattern) is RE_CHAR:
            return self.match_one(pattern, text)
        if type(pattern) is RE_STAR:
            return self.match_star(pattern, text)
        if type(pattern) is RE_STAR:
            return self.match_star(pattern, text)
        if type(pattern) is RE_PLUS:
            return self.match_plus(pattern, text)
        if type(pattern) is RE_OR:
            return self.match_or(pattern, text)
        if type(pattern) is RE_RANGE:
            return self.match_range(pattern, text)
        raise NotImplementedError(pattern)

class RegexParser(object):

    def __init__(self):
        from grammars.grammars import regex
        p, l = regex.load()
        self.incparser = p
        self.inclexer = l

    def load(self, pattern):
        from incparser.astree import TextNode
        from grammar_parser.gparser import Terminal
        self.incparser.reset()
        bos = self.incparser.previous_version.parent.children[0]
        bos.insert_after(TextNode(Terminal(pattern)))
        self.inclexer.relex(bos)
        self.incparser.reparse()
        return self.incparser.last_status

    def compile(self, pattern):
        self.load(pattern)
        start = self.incparser.previous_version.parent.children[1].alternate
        return self.parse(start)

    def parse(self, node):
        from grammar_parser.bootstrap import ListNode
        if type(node) is ListNode:
            return self.parse_list(node)
        if node.name == "OR":
            return self.parse_or(node)
        elif node.name == "GROUP":
            return self.parse_group(node)
        elif node.name == "STAR":
            return self.parse_star(node)
        elif node.name == "PLUS":
            return self.parse_plus(node)
        elif node.name == "CHAR":
            return self.parse_char(node)
        elif node.name == "RANGE":
            return self.parse_range(node)
        raise NotImplementedError(node)

    def parse_list(self, node):
        if len(node.children) > 1:
            return [self.parse(c) for c in node.children]
        return self.parse(node.children[0])

    def parse_or(self, node):
        lhs = self.parse(node.get("lhs"))
        rhs = self.parse(node.get("rhs"))
        return RE_OR(lhs, rhs)

    def parse_char(self, node):
        return RE_CHAR(node.get("value").symbol.name)

    def parse_range(self, node):
        return RE_RANGE([n.symbol.name for n in node.get("value").children])

    def parse_star(self, node):
        content = self.parse(node.get("value"))
        return RE_STAR(content)

    def parse_group(self, node):
        return self.parse(node.get("value"))

    def parse_plus(self, node):
        content = self.parse(node.get("value"))
        return RE_PLUS(content)
