from grammars.grammars import lang_dict
from incparser.astree import BOS, EOS
from grammar_parser.gparser import MagicTerminal, Terminal, Nonterminal, IndentationTerminal
from incparser.syntaxtable import Shift, Reduce, Goto, Accept

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

class AutoLBoxDetector(object):
    """Automatic language box detection that runs after the parse has finished.
    Uses text search to find a valid location for a language box that encloses
    the error."""

    def __init__(self):
        self.langs = {}

    def init_language(self, langname):
        if langname in self.langs:
            return

        main = lang_dict[langname]
        self.langs[langname] = main.load()

        for sub in main.included_langs:
            self.init_language(sub)

    def detect_autoremove(self, lbox):
        outer_root = lbox.get_root()
        outer_lang = outer_root.name
        outer_parser, outer_lexer = self.langs[outer_lang]
        r = IncrementalRecognizer(outer_parser.syntaxtable, outer_lexer.lexer, outer_lang)
        r.preparse(outer_root, lbox)
        return r.parse(lbox.symbol.ast.children[0].next_term)

    def detect_languagebox(self, node):
        # Get current language
        mainlang = node.get_root().name
        parser, _ = self.langs[mainlang]

        # Find beginning terminal
        term = node
        while True:
            # get most left terminal
            if type(term) is BOS:
                break
            if type(term) is EOS:
                term = term.prev_term
                continue
            if  term.lookup == "<return>":
                break

            #XXX check if term is valid in any of the langs first? If not we don't need to increc
            outer_root = term.get_root()
            outer_lang = outer_root.name
            outer_parser, outer_lexer = self.langs[outer_lang]
            r = IncrementalRecognizer(outer_parser.syntaxtable, outer_lexer.lexer, outer_lang)
            result = r.preparse(outer_root, term)
            if result:
                # Check if first token is valid in one of the autobox grammars
                for langname in self.langs:
                    magic = MagicTerminal("<%s>" % (langname,))
                    if r.is_valid(magic):
                        ends = self.detect_end(langname, term)
                        ends = self.reduce_ends(r, ends, magic, term, node)
                        if ends:
                            return (term, ends, langname)
                    else:
                        #print("Language box {} not valid at position {} in {}\n".format(langname, term, outer_lang))
                        pass
            term = term.prev_term

    def detect_end(self, lang, start):
        parser, lexer = self.langs[lang]
        #print("Language box valid. Find lbox end")
        if lexer.indentation_based:
            r = RecognizerIndent(parser.syntaxtable, lexer.lexer, lang)
        else:
            r = Recognizer(parser.syntaxtable, lexer.lexer, lang)
        end = r.parse(start)
        return r.possible_ends

    def reduce_ends(self, r, possible_ends, magic, start, errornode):
        """Remove unwanted language box boundaries from the results that
        - do not span the error node
        - end on whitespace/newline
        - don't allow terminal following box to be parsed"""
        tstates = list(r.state)
        r.temp_parse(tstates, magic)
        new = []
        for p in possible_ends:
            if p.lookup in ["<return>", "<ws>"]:
                continue
            la = get_lookup(p.next_term)
            # XXX this will almost always success if la is whitespace as
            # whitespace can always be shifted/reduced In theory we have to
            # continue incrementally parsing the entire remaining tree. So GLR
            # parsing is probably the proper way to do this
            result = r.syntaxtable.lookup(tstates[-1], la)
            if type(result) is Shift or type(result) is Reduce:
                # Check if it spans the error
                if self.contains_errornode(start, p, errornode):
                    new.append(p)
        return new

    def adjust_end(self, end):
        """Remove newlines/whitespace from end"""
        if end is None:
            return None
        while True:
            if end.lookup not in ["<ws>", "<return>"]:
                break
            end = end.prev_term
        return end

    def contains_errornode(self, start, end, error):
        while True:
            if start is error:
                return True
            if start is end:
                break
            start = start.next_term
        return False

from incparser.astree import TextNode

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
            while cut > 0:
                top = self.op.stack[cut]
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
                                if not self.contains_errornode(n, e, errornode):
                                    continue
                                if self.parse_after_lbox(lbox, e, cut, errornode):
                                    valid.append((n, e, sub))
                cut = cut - 1
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

    def parse_after_lbox(self, lbox, end, cut, errornode):
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
                # if whitespace continue
                if la.lookup in ["<ws>", "<return>"] or la is lboxnode:
                    stack.append(element.action)
                    la = la.next_term
                    continue
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
                if not isinstance(token, FinishSymbol):
                    if self.last_read:
                        self.last_read = self.last_read.prev_term
                    token = FinishSymbol()
                    continue
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
       #if self.lang == "Python + PHP":
       #    return token.name in ["def"]
       #elif self.lang == "SQL":
       #    return token.name in ["SELECT"]
       #elif self.lang == "SQL Statement":
       #    return token.name in ["SELECT"]
       #elif self.lang == "Python expression":
       #    return token.name in ["[", "NUMBER"]
       #elif self.lang == "SimpleLanguage":
       #    return token.name in ["function"]
       #elif self.lang == "HTML":
       #    return token.name.startswith("<") and token.name not in ["<ws>", "<return>"]
       #elif self.lang.find("Python") > -1: # other Python derivatives
       #    return token.name in ["def"]
       #return False

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

    def is_valid(self, token):
        """Checks if a token is valid in the current state."""
        state = list(self.state)
        while True:
            element = self.syntaxtable.lookup(state[-1], token)
            #print("Checking validity of {} in state {}: {}".format(token, state, element))
            if type(element) is Shift:
                state.append(element.action)
                return True
            elif type(element) is Reduce:
                i = 0
                while i < element.amount():
                   state.pop()
                   i += 1
                goto = self.syntaxtable.lookup(state[-1], element.action.left)
                assert isinstance(goto, Goto)
                state.append(goto.action)
            else:
                #print("Error on", token, state)
                return False
        return False

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
