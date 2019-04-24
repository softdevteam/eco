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

class RE_STAR(RE_DEFAULT):
    def __init__(self, c, ng=False):
        self.c = c
        self.ng = ng

class RE_PLUS(RE_STAR): pass
class RE_QUESTION(RE_DEFAULT): pass

class RE_RANGE(RE_DEFAULT):
    def __init__(self, c, neg=False):
        RE_DEFAULT.__init__(self, c)
        self.neg = neg

    def __repr__(self):
        return "%s(%s, %s)" % (self.__class__.__name__, self.c, self.neg)

class PatternMatcher(object):

    def __init__(self):
        self.pos = 0
        self.exactmatch = True
        self.la = 0

    def inc(self):
        self.pos += 1

    def char(self):
        return self.text[self.pos]

    def append(self):
        self.result.append(self.char())

    def get_token(self):
        """Rejoins all matched characters back to a single token string"""
        return "".join(self.result)

    def isend(self):
        return self.pos >= len(self.text)

    def textlength(self):
        return len(self.text)

    def load_state(self, state):
        self.pos = state[0]
        self.exactmatch = state[1]
        self.result = state[2]
        self.la = state[3]

    def save_state(self):
        return (self.pos, self.exactmatch, list(self.result), self.la)

    def match_one(self, pattern):
        if self.isend():
            # Existing pattern can't match empty input
            self.exactmatch = False
            return False
        char = self.char()
        if pattern.c == ".":
            # Wild card always matches
            return True
        if pattern.c == char:
            return True
        if len(pattern.c) == 2 and pattern.c[0] == "\\" and pattern.c[1] == char:
            return True
        self.exactmatch = False
        return False

    def match_star(self, pattern, l=None):
        if l is None or len(l) == 1:
            while self._inner_match(pattern.c):
                pass
            return True

        if pattern.ng: # non-greedy
            while True:
                tmp = self.save_state()
                if self.match_list(l[1:]):
                    return True
                self.load_state(tmp)
                if self._inner_match(pattern.c):
                    continue
                return False
        else: # greedy
            stack = []
            while True:
                stack.append(self.save_state())
                if self._inner_match(pattern.c):
                    continue
                break
            max_la = self.la
            if len(l) > 1:
                while stack:
                    self.load_state(stack.pop())
                    if self.match_list(l[1:]):
                        return True
                    max_la = max(self.la, max_la)
                self.la = max_la
            return False

    def match_plus(self, pattern, l=None):
        if not self._inner_match(pattern.c):
            # we have to at least match one
            return False
        return self.match_star(pattern, l)

    def match_question(self, pattern):
        self._inner_match(pattern.c)
        return True

    def match_list(self, pattern):
        for i in range(len(pattern)):
            p = pattern[i]
            if type(p) is RE_STAR:
                return self.match_star(p, pattern[i:])
            if type(p) is RE_PLUS:
                return self.match_plus(p, pattern[i:])
            elif not self._inner_match(p):
                return False
        return True

    def match_or(self, pattern):
        tmp = self.save_state()
        if self._inner_match(pattern.lhs):
            return True
        self.load_state(tmp)
        return self._inner_match(pattern.rhs)

    def match_range(self, pattern):
        if self.isend():
            return False
        if (pattern.neg and ord(self.char()) not in pattern.c) \
                    or (not pattern.neg and ord(self.char()) in pattern.c):
            return True
        self.exactmatch = False
        return False

    def _inner_match(self, pattern):
        if not pattern:
            self.pos = self.textlength()
            return True
        if type(pattern) is list:
            return self.match_list(pattern)
        if type(pattern) is RE_CHAR:
            self.la += 1
            if self.match_one(pattern):
                self.append()
                self.inc()
                return True
            return False
        if type(pattern) is RE_STAR:
            return self.match_star(pattern)
        if type(pattern) is RE_STAR:
            return self.match_star(pattern)
        if type(pattern) is RE_PLUS:
            return self.match_plus(pattern)
        if type(pattern) is RE_OR:
            return self.match_or(pattern)
        if type(pattern) is RE_RANGE:
            self.la += 1
            if self.match_range(pattern):
                self.append()
                self.inc()
                return True
            return False
        if type(pattern) is RE_QUESTION:
            return self.match_question(pattern)
        raise NotImplementedError(pattern)

    def match(self, pattern, text, pos=0):
        # reset
        self.exactmatch = True
        self.pos = pos
        self.text = text
        self.result = []
        self.la = 0
        if self._inner_match(pattern):
            return self.get_token()
        return None

from incparser.astree import TextNode, BOS, EOS, MultiTextNode
from grammar_parser.gparser import MagicTerminal, Terminal, IndentationTerminal
from grammars.grammars import regex

class LBPH(object):
    # Placeholder for language boxes to be used within the generated tokens.
    # Will be replaced with the actual language box in inclexer:merge_back
    def __len__(self):
        return 1

lbph = LBPH()

class TreePatternMatcher(PatternMatcher):

    def __init__(self):
        self.la = -1
        PatternMatcher.__init__(self)

    def char(self):
        return self.text.symbol.name[self.pos]

    def exists_in_readnodes(self, node):
        for n in self.read_nodes:
            if node is n:
                return True
        return False

    def inc(self):
        self.pos += 1
        if self.text.ismultichild():
            if not self.exists_in_readnodes(self.text.parent):
                self.read_nodes.append(self.text.parent)
        elif self.read_nodes[-1] is not self.text:
            self.read_nodes.append(self.text)
        if type(self.text.symbol) in [MagicTerminal, IndentationTerminal]:
            self.pos = 0
            self.inc_node()
        elif self.pos >= len(self.text.symbol.name):
            self.inc_node()
            self.pos = 0

    def inc_node(self):
        if self.text.next_term is None and self.text.ismultichild():
            self.text = self.text.parent.next_term
        else:
            assert self.text.next_term is not None
            self.text = self.text.next_term

        if type(self.text) is MultiTextNode:
            self.text = self.text.children[0]

        if self.text.symbol.name == "":
            self.inc_node()

    def append(self):
        if type(self.text.symbol) is MagicTerminal:
            self.result.append(None)
        elif type(self.text.symbol) is IndentationTerminal:
            pass
        else:
            self.result.append(self.char())

    def get_token(self):
        """Rejoins all matched characters back to a single token string. If the
        matched token contains newlines or language boxes, the token is split
        into a list of subtokens."""
        l = []
        j = 0
        for i in xrange(len(self.result)):
            if self.result[i] is None:
                if j < i:
                    l.append("".join(self.result[j:i]))
                l.append(lbph)
                j = i+1
            elif self.result[i] == "\r":
                if j < i:
                    l.append("".join(self.result[j:i]))
                l.append(self.result[i])
                j = i+1
        if j < len(self.result):
            l.append("".join(self.result[j:]))

        if len(l) == 1:
            self.scanned_chars = len(l[0])
            return l[0]
        self.scanned_chars = len(self.result)
        return l

    def isend(self):
        if type(self.text) is EOS:
            return True
        return False

    def load_state(self, state):
        self.pos = state[0]
        self.text = state[1]
        self.exactmatch = state[2]
        self.result = state[3]
        self.read_nodes = state[4]
        self.la = state[5]

    def save_state(self):
        return (self.pos, self.text, self.exactmatch, list(self.result), list(self.read_nodes), self.la)

    def match_one(self, pattern):
        if type(self.text.symbol) in [MagicTerminal, IndentationTerminal]:
            if pattern.c == ".":
                return True
            return False
        return PatternMatcher.match_one(self, pattern)

    def match_range(self, pattern):
        if type(self.text.symbol) in [MagicTerminal, IndentationTerminal]:
            if pattern.neg:
                # Negated char ranges can never exclude a language box
                return True
            self.exactmatch = False
            return False
        return PatternMatcher.match_range(self, pattern)

    def match(self, pattern, text, pos=0):
        if text.ismultichild():
            self.read_nodes = [text.parent]
        else:
            self.read_nodes = [text]
        self.la = 0
        self.lookahead = 0
        return PatternMatcher.match(self, pattern, text, pos)

class RegexParser(object):

    def __init__(self):
        p, l = regex.load(buildlexer=False)
        self.incparser = p
        self.lrules = zip(l[0],l[1])

    def load(self, pattern):
        from incparser.astree import TextNode
        from grammar_parser.gparser import Terminal
        self.incparser.reset()
        bos = self.incparser.previous_version.parent.children[0]
        self.manual_relex(bos, pattern)
        self.incparser.reparse()
        return self.incparser.last_status

    def manual_relex(self, bos, pattern):
        """To avoid a bootstrapping loop (inclexer depends on Lexer and thus
        RegexParser), we need to lex the regex grammar manually"""
        import re
        pos = 0
        while pos < len(pattern):
            for name, regex in self.lrules:
                r = re.match(regex, pattern[pos:])
                if r:
                    n = TextNode(Terminal(r.group(0)))
                    n.lookup = name
                    bos.insert_after(n)
                    bos = n
                    pos += len(r.group(0))
                    break

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
        elif node.name == "NGSTAR":
            return self.parse_star(node, ng=True)
        elif node.name == "PLUS":
            return self.parse_plus(node)
        elif node.name == "NGPLUS":
            return self.parse_plus(node, ng=True)
        elif node.name == "CHAR":
            return self.parse_char(node)
        elif node.name == "RANGE":
            return self.parse_range(node)
        elif node.name == "NRANGE":
            return self.parse_range(node, True)
        elif node.name == "QST":
            return self.parse_question(node)
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
        name = node.get("value").symbol.name
        if name == "\\r":
            return RE_CHAR("\r")
        elif name == "\\n":
            return RE_CHAR("\n")
        elif name == "\\t":
            return RE_CHAR("\t")
        else:
            return RE_CHAR(name)

    def parse_range(self, node, neg=False):
        l = []
        for n in node.get("value").children:
            if n.lookup == "rangetype":
                a = ord(n.symbol.name[0])
                b = ord(n.symbol.name[2])
                if a > b:
                    l.extend(range(b, a+1))
                else:
                    l.extend(range(a, b+1))
            elif len(n.symbol.name) == 2: # escaped
                if n.symbol.name == "\\r":
                    l.append(ord('\r'))
                elif n.symbol.name == "\\n":
                    l.append(ord('\n'))
                elif n.symbol.name == "\\t":
                    l.append(ord('\t'))
                else:
                    l.append(ord(n.symbol.name[1]))
            else:
                l.append(ord(n.symbol.name))
        if neg:
            return RE_RANGE(l, True)
        return RE_RANGE(l)

    def parse_star(self, node, ng=False):
        content = self.parse(node.get("value"))
        return RE_STAR(content, ng)

    def parse_group(self, node):
        return self.parse(node.get("value"))

    def parse_plus(self, node, ng=False):
        content = self.parse(node.get("value"))
        return RE_PLUS(content, ng)

    def parse_question(self, node):
        content = self.parse(node.get("value"))
        return RE_QUESTION(content)

class LexingError(Exception):
    pass

class Lexer(object):

    def __init__(self, rules):
        rp = RegexParser()
        self.patterns = []
        for name, rule in rules:
            pattern = rp.compile(rule)
            self.patterns.append((pattern, name))

    def lex(self, text):
        """Lexes a given string by trying all patterns. When a match is found a
        token is created, and the lexing continues with the remainder of the
        string. Lookahead is calculated by observing how far the patternmatcher
        got before returning 'no match'. If a token was matched by a plus or
        star rule (e.g. [a-z]+), then the generated token is not an exact match,
        as it could potentially be longer. This means its lookahead is one
        character longer (and at least 1), since the pattern matcher had to look
        ahead one character to decide that the token is complete."""
        pm = PatternMatcher()
        self.pos = 0
        result = []
        progress = 0
        while True:
            lookahead = 0
            oldpos = self.pos
            tmpresult = ("", None, None)
            for p, n in self.patterns:
                if pm.match(p, text[self.pos:]):
                    lookahead = max(pm.la, lookahead)
                    value = text[self.pos:self.pos + pm.pos]
                    lookahead = lookahead - len(value)
                    if len(value) > len(tmpresult[0]):
                        tmpresult = (value, n, lookahead)
                        progress = pm.pos
                    lookahead = 0
                else:
                    lookahead = max(pm.la, lookahead)
            if tmpresult[0]:
                result.append(tmpresult)
                self.pos += progress
            if self.pos == oldpos:
                # no more matches
                if self.pos < len(text):
                    result.append((text[self.pos:], None, 0))
                break
        return result

    def treelex(self, node):
        pm = TreePatternMatcher()
        pos = 0
        result = []
        while True:
            lookahead = 0
            oldpos = pos
            oldnode = node
            for p, n in self.patterns:
                token = pm.match(p, node)
                if token:
                    lookahead = lookahead + (1 if not pm.exactmatch else 0)
                    result.append((token, n, lookahead))
                    pos = pm.pos
                    node = pm.text
                    lookahead = 0
                else:
                    lookahead = max(pm.pos, lookahead)
            if pos == oldpos and oldnode is node:
                # no more matches
                break
        return result

    def get_token_iter(self, node):
        pm = TreePatternMatcher()
        pos = 0
        progress = pos, node
        while True:
            lookahead = 0
            oldpos = pos
            oldnode = node
            result = ("", None, -1, None)
            while type(node.symbol) is IndentationTerminal:
                node = node.next_term
            if type(node) is MultiTextNode:
                node = node.children[0]
            if type(node) is EOS:
                break
            if type(node.symbol) is MagicTerminal:
                # language boxes relex to themselves
                if node.ismultichild():
                    read = [node.parent]
                else:
                    read = [node]
                yield (lbph, "", 0, read)
                if node.next_term is None and node.ismultichild():
                    node = node.parent.next_term
                else:
                    node = node.next_term
                continue
            for p, n in self.patterns:
                token = pm.match(p, node, pos)
                lookahead = max(pm.la, lookahead)
                if token and self.tlen(token) > self.tlen(result[0]): # find longest match
                    result = (token, n, lookahead - pm.scanned_chars, pm.read_nodes)
                    progress = pm.pos, pm.text
                    continue
                else:
                    pass
            pos, node = progress
            if oldnode is node and oldpos == pos:
                # no progress means we failed to lex something
                raise LexingError("Failed to lex node '{}' at position {})".format(node, pos))
            yield result

    def tlen(self, token):
        if type(token) is list:
            return sum([len(t) for t in token])
        return len(token)
