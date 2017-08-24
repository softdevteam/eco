from grammars.grammars import lang_dict
from incparser.astree import BOS, EOS, TextNode
from grammar_parser.gparser import MagicTerminal, Terminal, Nonterminal, IndentationTerminal
from incparser.syntaxtable import Shift, Reduce, Goto, Accept

ws_tokens = ["<ws>", "<return>", "<slcomment>", "<mlcomment>"]

def get_lookup(la):
    """Get the lookup symbol of a node. If no such lookup symbol exists use
    the nodes symbol instead."""
    if la.lookup != "":
        lookup_symbol = Terminal(la.lookup)
    else:
        lookup_symbol = la.symbol
    if isinstance(lookup_symbol, IndentationTerminal):
        lookup_symbol = Terminal(lookup_symbol.name)
    return lookup_symbol

class NewAutoLboxDetector(object):
    """Automatic languagebox detector that runs during parsing when an error
    occurs. Similar to error recovery it uses the current parse stack to
    determine a location where a language box can be inserted and then tries to
    wrap the error into that box."""
    def __init__(self, origparser):
        self.op = origparser
        self.langs = {}

    def preload(self, langname):
        if langname in self.langs:
            return

        main = lang_dict[langname]

        # preload nested languages
        for sub in main.included_langs:
            self.langs[sub] = get_recognizer(sub)

    def find_terminal(self, node):
        while node.children:
            node = node.children[-1]
        if type(node.symbol) is Terminal:
            return node.next_term
        return None

    def detect_lbox(self, errornode):
        # Find position on stack where lbox would be valid
        valid = []
        for sub in self.langs:
            lbox = MagicTerminal("<{}>".format(sub))
            cut = len(self.op.stack) - 1
            while cut >= 0:
                top = self.op.stack[cut]
                if isinstance(top, EOS):
                    top = top.parent.children[0] # bos
                    state = 0
                else:
                    state = self.op.stack[cut].state
                # get all possible sublangs
                element = self.op.syntaxtable.lookup(state, lbox)
                if type(element) in [Reduce, Shift]:
                    term = self.find_terminal(top)
                    if type(term) is EOS:
                        cut = cut - 1
                        continue
                    if term:
                        n = term
                        # See if we can get a valid language box using the Recogniser
                        r = self.langs[sub]
                        result = r.parse(n)
                        if r.possible_ends:
                            # Filter results and test if remaining file can be
                            # parsed after shifting the language box
                            for e in r.possible_ends:
                                if e.lookup == "<ws>" or e.lookup == "<return>":
                                    continue
                                if (self.contains_errornode(n, e, errornode) \
                                    and self.parse_after_lbox(lbox, e, cut)) \
                                    or self.parse_after_lbox(lbox, e, cut, errornode):
                                        # Either the error was solved by
                                        # moving it into the box or a box
                                        # was created before it, allowing
                                        # the error to be shifted
                                        valid.append((n, e, sub))
                cut = cut - 1
        if errornode.autobox is False:
            # XXX might have to only limit certain (node, autobox) combinations to
            # allow boxes with different content later on
            return # don't use this node for autoboxes anymore
        if valid:
            errornode.autobox = valid
        else:
            errornode.autobox = None

    def contains_errornode(self, start, end, errornode):
        while start is not end:
            if start is errornode:
                return True
            start = start.next_term
        if start is errornode:
            return True
        return False

    def parse_after_lbox(self, lbox, end, cut, errornode=None):
        # copy stack
        stack = []
        for i in range(cut+1):
            stack.append(self.op.stack[i].state)
        after_end = self.op.next_terminal(end)
        # do all reductions until there's a shift or accept (whitespace doesn't
        # count) XXX: parse entire file incrementally?
        lboxnode = TextNode(lbox)
        la = lboxnode
        la.next_term = after_end
        while True:
            if la.deleted:
                la = la.next_term
                continue
            element = self.op.syntaxtable.lookup(stack[-1], self.op.get_lookup(la))
            if type(element) is Reduce:
                for i in range(element.amount()):
                    stack.pop()
                goto = self.op.syntaxtable.lookup(stack[-1], element.action.left)
                assert goto is not None
                stack.append(goto.action)
                continue
            if type(element) is Shift:
                if errornode and la is errornode:
                    return True
                # if whitespace continue
                if la.lookup in ws_tokens or la is lboxnode:
                    stack.append(element.action)
                    la = la.next_term
                    continue
                if not errornode:
                    return True
            if type(element) is Accept:
                return True
            return False

from inclexer.inclexer import StringWrapper
from cflexer.lexer import LexingError
from incparser.incparser import FinishSymbol

class Recognizer(object):
    """A parser that simulates parsing some input without actually creating a
    parse tree. Used to test if some input is valid in some language."""

    def __init__(self, syntaxtable, lexer, lang):
        self.syntaxtable = syntaxtable
        self.lexer = lexer
        self.lang = lang
        self.state = [0]
        self.reached_eos = False
        self.seen_error = False
        self.possible_ends = []
        self.last_read = None

    def reset(self):
        self.state = [0]
        self.reached_eos = False
        self.seen_error = False
        self.possible_ends = []
        self.last_read = None

    def parse(self, startnode, ppmode=False):
        # as we are reusing recogisers now, reset it
        if not ppmode:
            self.reset()

        self.tokeniter = self.lexer.get_token_iter(StringWrapper(startnode, startnode))
        token = self.next_token()
        if not ppmode and not self.valid_start(token):
            return None
        while True:
            element = self.syntaxtable.lookup(self.state[-1], token)
            if isinstance(element, Shift):
                self.state.append(element.action)
                if self.is_finished() and self.last_read:
                    self.possible_ends.append(self.last_read)
                    self.last_read = None
                token = self.next_token()
                continue
            elif isinstance(element, Reduce):
                i = 0
                while i < element.amount():
                   self.state.pop()
                   i += 1
                goto = self.syntaxtable.lookup(self.state[-1], element.action.left)
                assert isinstance(goto, Goto)
                self.state.append(goto.action)
                continue
            elif isinstance(element, Accept):
                return self.last_read
            else:
                return None

    def next_token(self):
        try:
            t = self.tokeniter()
            self.last_read = t[3][-1]
            return Terminal(t[1])
        except StopIteration:
            self.reached_eos = True
            return FinishSymbol() # No more tokens to read
        except LexingError:
           return FinishSymbol() # Couldn't continue lexing with given language

    def valid_start(self, token):
        if token.name in ["<ws>", "<return>"]:
            return False
        return True

    def is_finished(self):
        result = self.syntaxtable.lookup(self.state[-1], FinishSymbol())
        states = list(self.state)
        while isinstance(result, Reduce):
            i = 0
            for i in range(result.amount()):
                states.pop()
            goto = self.syntaxtable.lookup(states[-1], result.action.left)
            states.append(goto.action)
            result = self.syntaxtable.lookup(states[-1], FinishSymbol())
        if isinstance(result, Accept):
            return True
        return False

    def temp_parse(self, states, terminal):
        while True:
            element = self.syntaxtable.lookup(states[-1], terminal)
            if type(element) is Shift:
                states.append(element.action)
                return True
            elif type(element) is Reduce:
                i = 0
                while i < element.amount():
                   states.pop()
                   i += 1
                goto = self.syntaxtable.lookup(states[-1], element.action.left)
                assert isinstance(goto, Goto)
                states.append(goto.action)
                continue
            else:
                return False

class RecognizerIndent(Recognizer):

    def __init__(self, syntaxtable, lexer, lang):
        Recognizer.__init__(self, syntaxtable, lexer, lang)
        self.todo = []
        self.indents = [0]
        self.last_ws = 0
        self.logical_line = False

    def parse(self, node):
        self.indents = [0]
        self.todo = []
        Recognizer.parse(self, node)

    def reset(self):
        self.todo = []
        self.indents = [0]
        self.last_ws = 0
        self.logical_line = False
        Recognizer.reset(self)

    def get_token_iter(self):
        try:
            return self.tokeniter()
        except StopIteration:
            return None
        except LexingError:
            return None

    def is_logical(self, tok):
        if tok == "<ws>":
            return False
        if tok == "<return>":
            return False
        return True

    def next_token(self):

        if self.todo:
           return self.todo.pop(0)

        tok1 = self.get_token_iter()
        if tok1 is None:
            self.todo.append(Terminal("NEWLINE"))
            while self.indents[-1] != 0:
                self.todo.append(Terminal("DEDENT"))
                self.indents.pop()
            self.todo.append(FinishSymbol())
            return self.todo.pop(0)

        if tok1[3][-1].symbol.name.endswith(tok1[0]):
            # only use fully parsed nodes as possible ends
            self.last_read = tok1[3][-1]

        if tok1[1] == "<return>":
            if self.logical_line: # last line was logical
                self.todo.append(Terminal("NEWLINE"))
                self.logical_line = False
                self.last_ws = 0
            return Terminal(tok1[1]) # parse <return> token first

        if tok1[1] == "<ws>":
            self.last_ws = len(tok1[0])
            return Terminal(tok1[1])

        if self.is_logical(tok1[1]):
            if self.logical_line is False: # first logical token in this line
                self.logical_line = True
                if self.last_ws > self.indents[-1]:
                    self.todo.append(Terminal("INDENT"))
                    self.indents.append(self.last_ws)
                elif self.last_ws == self.indents[-1]:
                    pass
                else:
                    while self.last_ws < self.indents[-1]:
                        self.todo.append(Terminal("DEDENT"))
                        self.indents.pop()
                self.todo.append(Terminal(tok1[1]))
                return self.todo.pop(0)
        return Terminal(tok1[1])

    def is_finished(self):
        states = list(self.state)
        if self.temp_parse(states, Terminal("NEWLINE")):
            # XXX need to test ALL dedents not just one
            # XXX also can just check for shift which should be enough
            element = self.syntaxtable.lookup(states[-1], FinishSymbol())
            if element:
                return True
            elif self.temp_parse(states, Terminal("DEDENT")):
                return True
        return False

class IncrementalRecognizer(Recognizer):

    def preparse(self, outer_root, stop):
        """Puts the recogniser into the state just before `stop`."""
        #print("Preparsing {} upto {}".format(outer_root, stop))
        path_to_stop = set()
        parent = stop.parent
        while parent is not None:
            path_to_stop.add(parent)
            parent = parent.parent

        # setup parser to the state just before lbox
        node = outer_root.children[1]
        while True:
            if node.deleted:
                node = node.right
                continue
            if node is stop:
                # Reached stop node
                return True
            if node not in path_to_stop:
                # Skip/Shift nodes that are not parents of the language box
                lookup = get_lookup(node)
                element = self.syntaxtable.lookup(self.state[-1], lookup)
                if type(element) is Goto:
                    self.state.append(element.action)
                elif type(element) is Shift:
                    self.state.append(element.action)
                elif type(element) is Reduce:
                    i = 0
                    while i < element.amount():
                       self.state.pop()
                       i += 1
                    goto = self.syntaxtable.lookup(self.state[-1], element.action.left)
                    assert isinstance(goto, Goto)
                    self.state.append(goto.action)
                    continue
                else:
                    return False
                node  = node.right
            else:
                if node.children:
                    node = node.children[0]
                else:
                    node = node.right

    def parse(self, node):
        """Parse normally starting at `node`."""

        # parsing a language box is successful if the last token
        # in the box has been processed without errors

        # try parsing lbox content in outer language
        result = Recognizer.parse(self, node, ppmode=True)
        if self.reached_eos:
            return True
        return False

def get_recognizer(lang):
        main = lang_dict[lang]
        parser, lexer = main.load()
        if lexer.indentation_based:
            return RecognizerIndent(parser.syntaxtable, lexer.lexer, lang)
        else:
            return Recognizer(parser.syntaxtable, lexer.lexer, lang)
