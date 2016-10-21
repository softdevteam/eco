# Copyright (c) 2013--2014 King's College London
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

import py
from cflexer import deterministic, regex

class Token(object):
    def __init__(self, name, source, source_pos, lookahead=None):
        self.name = name
        self.source = source
        self.source_pos = source_pos
        self.lookahead = lookahead

    def copy(self):
        return Token(self.name, self.source, self.source_pos)

    def __eq__(self, other):
        # for testing only
        return self.name == other.name and self.source == other.source and self.source_pos == other.source_pos

    def __ne__(self, other):
        # for testing only
        return not self == other

    def __repr__(self):
        return "Token(%r, %r, %r, %r)" % (self.name, self.source, self.source_pos, self.lookahead)

class SourcePos(object):
    """An object to record position in source code."""
    def __init__(self, i, lineno, columnno):
        self.i = i                  # index in source string
        self.lineno = lineno        # line number in source
        self.columnno = columnno    # column in line

    def copy(self):
        return SourcePos(self.i, self.lineno, self.columnno)

    def __eq__(self, other):
        # for testing only
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        # for testing only
        return not self == other

    def __repr__(self):
        return "SourcePos(%r, %r, %r)" % (self.i, self.lineno, self.columnno)

import os
try:
    import cPickle as pickle
except:
    import pickle

class Lexer(object):
    def __init__(self, token_regexs, names, ignore=None):
        self.token_regexs = token_regexs
        self.names = names
        self.rex = regex.LexingOrExpression(token_regexs, names)
        # pickling automaton to increase loading times
        h = hash(str(token_regexs)) ^ hash(str(names))
        filename = "".join([os.path.dirname(__file__), "/../pickle/", str(h), ".pcl"])
        try:
            f = open(filename, "r")
            self.automaton = pickle.load(f)
        except IOError:
            automaton = self.rex.make_automaton()
            self.automaton = automaton.make_deterministic(names)
            self.automaton.optimize() # XXX not sure whether this is a good idea
            pickle.dump(self.automaton, open(filename, "w"))
        if ignore is None:
            ignore = []
        for ign in ignore:
            assert ign in names
        self.ignore = dict.fromkeys(ignore)
        self.matcher = self.automaton.make_lexing_code()

    def get_runner(self, text, eof=False):
        return LexingDFARunner(self.matcher, self.automaton, text,
                               self.ignore, eof)

    def tokenize(self, text, eof=False):
        """Return a list of Token's from text."""
        r = self.get_runner(text, eof)
        result = []
        while 1:
            try:
                tok = r.find_next_token()
                result.append(tok)
            except StopIteration:
                break
        return result

    def get_dummy_repr(self):
        return '%s\nlexer = DummyLexer(recognize, %r, %r)' % (
                py.code.Source(self.matcher),
                self.automaton,
                self.ignore)

    def __getstate__(self):
        return (self.token_regexs, self.names, self.ignore)

    def __setstate__(self, args):
        self.__init__(*args)

    def get_token_iter(self, text, eof=False):
        r = self.get_runner(text, eof)
        return r.find_next_token

class DummyLexer(Lexer):
    def __init__(self, matcher, automaton, ignore):
        self.token_regexs = None
        self.names = None
        self.rex = None
        self.automaton = automaton
        self.ignore = ignore
        self.matcher = matcher

class AbstractLexingDFARunner(deterministic.DFARunner):
    i = 0
    def __init__(self, matcher, automaton, text, eof=False):
        self.automaton = automaton
        self.state = 0
        self.text = text
        self.last_matched_state = 0
        self.last_matched_index = -1
        self.eof = eof
        self.matcher = matcher
        self.lineno = 0
        self.columnno = 0
        self.reachedend = False

    def find_next_token(self):
        while 1:
            self.state = 0
            start = self.last_matched_index + 1
            assert start >= 0

            # Handle end of file situation
            if start == len(self.text) and self.eof:
                self.last_matched_index += 1
                assert False
                return self.make_token(start, -1, "", eof=True, lookahead = 0)
            elif start >= len(self.text):
                raise StopIteration

            i = self.inner_loop(start)
            if i < 0:
                # normal token eating
                i = ~i
                stop = self.last_matched_index + 1
                assert stop >= 0
                if start == stop:
                    source = self.text[start:]
                    raise LexingError("Could not successfully parse %s" % source)
                    result = self.make_token(start, -1, self.last_matched_state, lookahead = i - stop)
                    self.last_matched_index = start + len(source)
                    return result
                    #source_pos = SourcePos(i - 1, self.lineno, self.columnno)
                    #raise deterministic.LexerError(self.text, self.state,
                    #                               source_pos)
                source = self.text[start:stop]
                lookahead = i - stop
                if self.reachedend:
                    lookahead += 1
                result = self.make_token(start, stop, self.last_matched_state, lookahead = lookahead)
                self.adjust_position(source)
                if self.ignore_token(self.last_matched_state):
                    continue
                return result
            if self.last_matched_index == i - 1:
                # no progress (loop)
                lookahead = 0
                for from_, to in self.automaton.transitions.iterkeys():
                    if from_ == self.state:
                        lookahead = 1
                        break
                source = self.text[start: ]
                result = self.make_token(start, -1, self.last_matched_state, lookahead = lookahead)
                self.last_matched_index = start + len(source)
                self.adjust_position(source)
                if self.ignore_token(self.last_matched_state):
                    if self.eof:
                        self.last_matched_index += 1
                        assert False
                        return None#self.make_token(i, -1, "", eof=True)
                    else:
                        raise StopIteration
                return result
            source_pos = SourcePos(i - 1, self.lineno, self.columnno)
            raise deterministic.LexerError(self.text, self.state, source_pos)

    def adjust_position(self, token):
        """Update the line# and col# as a result of this token."""
        newlines = token.count("\n")
        self.lineno += newlines
        if newlines==0:
            self.columnno += len(token)
        else:
            self.columnno = token.rfind("\n")

#   def inner_loop(self, i):
#       state = self.state
#       while i < len(self.text):
#           char = self.text[i]
#           #print i, self.last_matched_index, self.last_matched_state, repr(char)
#           try:
#               state = self.nextstate(char) # self.automaton.transitions[(state, char)]
#           except KeyError:
#               return ~i
#           if state in self.automaton.final_states:
#               self.last_matched_state = state
#               self.last_matched_index = i
#           i += 1
#       if state not in self.automaton.final_states:
#           return ~i
#       return i

    def inner_loop(self, i):
        return self.matcher(self, i)

    next = find_next_token

    def __iter__(self):
        return self

class LexingDFARunner(AbstractLexingDFARunner):
    def __init__(self, matcher, automaton, text, ignore, eof=False):
        AbstractLexingDFARunner.__init__(self, matcher, automaton, text, eof)
        self.ignore = ignore

    def ignore_token(self, state):
        return self.automaton.names[state] in self.ignore

    def make_token(self, start, stop, state, eof=False, lookahead=None):
        assert (eof and state == -1) or 0 <= state < len(self.automaton.names)
        #source_pos = SourcePos(index, self.lineno, self.columnno)
        source_pos = None
        if self.last_matched_state == 0:
            raise LexingError("blupp")
        tokentype = self.automaton.names[self.last_matched_state]
        if isinstance(self.text, str):
            # lexing normal strings
            if eof:
                return Token("EOF", "EOF", source_pos, lookahead)
            if stop == -1:
                text = self.text[start:]
            else:
                text = self.text[start:stop]
            return Token(self.automaton.names[self.last_matched_state],
                    text, source_pos, lookahead)
        else:
            # lexing nodes using stringwrapper
            token, read = self.text.make_token(start, stop, tokentype)
            return token, tokentype, lookahead, read

class LexingError(Exception):
    pass
