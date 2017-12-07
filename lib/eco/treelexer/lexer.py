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

class PatternMatcher(object):

    def match_one(self, pattern, text):
        if not pattern:
            # Empty pattern always matches
            return True
        if not text:
            # Existing pattern can't match empty input
            return False
        if pattern[0] == ".":
            # Wild card always matches
            return True
        return pattern[0] == text[0]

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
        if self.match_one(pattern, text):
            # matched one, continue matching *
            return self.match(pattern, text[1:])
        # couldn't match star, remove star regex and continue
        return self.match(pattern[2:], text)

    def match(self, pattern, text):
        if not pattern:
            return True
        if len(pattern) > 1 and pattern[1] == "?":
            return self.match_question(pattern, text)
        if len(pattern) > 1 and pattern[1] == "*":
            return self.match_star(pattern, text)
        if len(pattern) > 1 and pattern[1] == "+":
            if self.match_one(pattern, text):
                # rewrite pattern from + to *
                return self.match_star(pattern[0] + "*" + pattern[2:], text[1:])
            return False
        return self.match_one(pattern, text) and self.match(pattern[1:], text[1:])

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

    def ast(self, pattern):
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

    def parse_star(self, node):
        content = self.parse(node.get("value"))
        return RE_STAR(content)

    def parse_group(self, node):
        return self.parse(node.get("value"))

    def parse_plus(self, node):
        content = self.parse(node.get("value"))
        return RE_PLUS(content)
