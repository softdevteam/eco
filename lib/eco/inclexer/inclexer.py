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

from grammar_parser.plexer import PriorityLexer
from grammar_parser.gparser import MagicTerminal, Terminal, IndentationTerminal
from incparser.astree import BOS, EOS, TextNode, ImageNode
from PyQt4.QtGui import QImage
import re, os

class IncrementalLexer(object):
    # XXX needs to be replaced by a lexing automaton to avoid uneccessary
    # relexing of unchanged nodes

    def __init__(self, rules, language=""):
        self.indentation_based = False
        self.language = language
        if rules.startswith("%"):
            config_line = rules.splitlines()[0]     # get first line
            self.parse_config(config_line[1:])      # remove %
            rules = "\n".join(rules.splitlines()[1:]) # remove config line
        pl = PriorityLexer(rules)
        self.regexlist = pl.rules
        self.compiled_regexes = {}
        for regex in self.regexlist:
            self.compiled_regexes[regex] = re.compile(regex)

    def is_indentation_based(self):
        return self.indentation_based

    def parse_config(self, config):
        settings = config.split(",")
        for s in settings:
            name, value = s.split("=")
            if name == "indentation" and value == "true":
                self.indentation_based = True

    def lex(self, text):
        matches = []
        remaining = text
        any_match_found = False
        while remaining != "":
            longest_match = ("", "", 999999)
            for regex in self.regexlist:
                m = self.compiled_regexes[regex].match(remaining)
                if m:
                    result = m.group(0)
                    if len(result) > len(longest_match[0]):
                        new_priority = self.regexlist[regex][0]
                        regex_name = self.regexlist[regex][1]
                        longest_match = (result, regex_name, new_priority)
                    if len(result) == len(longest_match[0]):
                        new_priority = self.regexlist[regex][0]
                        old_priority = longest_match[2]
                        if new_priority < old_priority: # use token with higher priority (smaller numbers have higher priority)
                            regex_name = self.regexlist[regex][1]
                            longest_match = (result, regex_name, new_priority)
            if longest_match[0] != "":
                any_match_found = True
                remaining = remaining[len(longest_match[0]):]
                matches.append(longest_match)
            else:
                matches.append((remaining, ""))
                break
        if any_match_found:
            stripped_priorities = []
            for m in matches:
                stripped_priorities.append((m[0], m[1]))
            return stripped_priorities
        else:
            return [(text, '', 0)]

    def relex(self, node):

        if isinstance(node, BOS):
            return

        start = node
        while True:
            if isinstance(start.symbol, IndentationTerminal):
                start = start.next_term
                break
            if isinstance(start, BOS):
                start = start.next_term
                break
            if start.lookup == "<return>":
                start = start.next_term
                break
            if isinstance(start.symbol, MagicTerminal):
                start = start.next_term
                break
            start = start.prev_term

        # find end node
        end = node
        while True:
            if isinstance(end.symbol, IndentationTerminal):
                end = end.prev_term
                break
            if isinstance(end, EOS):
                end = end.prev_term
                break
            if isinstance(end.symbol, MagicTerminal):
                end = end.prev_term
                break
            if end.lookup == "<return>":
                end = end.prev_term
                break
            end = end.next_term

        token = start
        relex_string = []
        if start is end:
            relex_string = [start.symbol.name]
        else:
            while token is not end.next_term:
                if isinstance(token.symbol, MagicTerminal): # found a language box
                    # start another relexing process after the box
                    next_token = token.next_term
                    self.relex(next_token)
                    break
                if isinstance(token, EOS): # reached end of language box
                    break
                relex_string.append(token.symbol.name)
                token = token.next_term

        success = self.lex("".join(relex_string))

        old_node = start
        old_x = 0
        new_x = 0
        after_startnode = False
        debug_old = []
        debug_new = []
        for match in success:
            if after_startnode:
                if old_node.symbol.name == match[0] and old_node.lookup == match[1]:
                    # XXX optimisation only
                    # from here everything is going to be relexed to the same
                    # XXX check construction location
                    break

            # 1) len(relexed) == len(old) => update old with relexed
            # 2) len(relexed) >  len(old) => update old with relexed and delete following previous until counts <=
            # 3) len(relexed) <  len(old) => insert token

            if new_x < old_x: # insert
                if self.language == "Chemicals":
                    filename = "chemicals/" + node.symbol.name + ".png"
                    if os.path.isfile(filename):
                        additional_node = ImageNode(node, 0)
                        additional_node.image = QImage(filename)
                        old_node.image_src = filename
                    else:
                        additional_node.image = None
                        old_node.image_src = None
                else:
                    additional_node = TextNode(Terminal(match[0]), -1, [], -1)
                additional_node.lookup = match[1]
                old_node.prev_term.parent.insert_after_node(old_node.prev_term, additional_node)
                #self.add_node(old_node.prev_term, additional_node)
                old_x += 0
                new_x  += len(match[0])
                debug_old.append("")
                debug_new.append(match[0])
            else: #overwrite
                old_x += len(old_node.symbol.name)
                new_x  += len(match[0])
                debug_old.append(old_node.symbol.name)
                debug_new.append(match[0])
                old_node.symbol.name = match[0]
                old_node.lookup = match[1]

                if self.language == "Chemicals":
                    filename = "chemicals/" + old_node.symbol.name + ".png"
                    if os.path.isfile(filename):
                        old_node.image = QImage(filename)
                        old_node.image_src = filename
                    else:
                        old_node.image = None
                        old_node.image_src = None

                old_node = old_node.next_term

            # relexed was bigger than old_node => delete as many nodes that fit into len(relexed)
            while old_x < new_x:
                if old_x + len(old_node.symbol.name) <= new_x:
                    old_x += len(old_node.symbol.name)
                    delete_node = old_node
                    old_node = delete_node.next_term
                    delete_node.parent.remove_child(delete_node)
                else:
                    break

        if old_x != new_x: # sanity check
            raise AssertionError("old_x(%s) != new_x(%s) %s => %s" % (old_x, new_x, debug_old, debug_new))

        return

    def relex_from_node(self, startnode):
        # XXX when typing to not create new node but insert char into old node
        #     (saves a few insertions and is easier to lex)

        # if ndoe itself is a newline it won't be relexed, so do it manually
        if startnode.symbol.name == "\r":
            result = self.lex(startnode.symbol.name)
            startnode.lookup = result[0][1]

        if isinstance(startnode.symbol, IndentationTerminal):
            startnode = startnode.next_term
        else:
            startnode = startnode.prev_term

        if isinstance(startnode, BOS) or isinstance(startnode.symbol, MagicTerminal) or isinstance(startnode.symbol, IndentationTerminal):
            startnode = startnode.next_term

        if isinstance(startnode, EOS):
            # empty line
            return

        # find end node
        end_node = startnode.next_term
        while True:
            if isinstance(end_node.symbol, IndentationTerminal):
                break
            if isinstance(end_node, EOS):
                break
            if isinstance(end_node.symbol, MagicTerminal):
                break
            if end_node.symbol.name == "\r":
                break
            end_node = end_node.next_term

        token = startnode
        relex_string = []
        while token is not end_node:
            if isinstance(token.symbol, MagicTerminal): # found a language box
                # start another relexing process after the box
                next_token = token.next_term
                self.relex(next_token)
                break
            if isinstance(token, EOS): # reached end of language box
                break
            relex_string.append(token.symbol.name)
            token = token.next_term

        success = self.lex("".join(relex_string))

        old_node = startnode
        old_x = 0
        new_x = 0
        after_startnode = False
        debug_old = []
        debug_new = []
        for match in success:
            if after_startnode:
                if old_node.symbol.name == match[0] and old_node.lookup == match[1]:
                    # XXX optimisation only
                    # from here everything is going to be relexed to the same
                    # XXX check construction location
                    break

            # 1) len(relexed) == len(old) => update old with relexed
            # 2) len(relexed) >  len(old) => update old with relexed and delete following previous until counts <=
            # 3) len(relexed) <  len(old) => insert token

            if new_x < old_x: # insert
                if self.language == "Chemicals":
                    filename = "chemicals/" + node.symbol.name + ".png"
                    if os.path.isfile(filename):
                        additional_node = ImageNode(node, 0)
                        additional_node.image = QImage(filename)
                        old_node.image_src = filename
                    else:
                        additional_node.image = None
                        old_node.image_src = None
                else:
                    additional_node = TextNode(Terminal(match[0]), -1, [], -1)
                additional_node.lookup = match[1]
                old_node.prev_term.parent.insert_after_node(old_node.prev_term, additional_node)
                #self.add_node(old_node.prev_term, additional_node)
                old_x += 0
                new_x  += len(match[0])
                debug_old.append("")
                debug_new.append(match[0])
            else: #overwrite
                old_x += len(old_node.symbol.name)
                new_x  += len(match[0])
                debug_old.append(old_node.symbol.name)
                debug_new.append(match[0])
                old_node.symbol.name = match[0]
                old_node.lookup = match[1]

                if self.language == "Chemicals":
                    filename = "chemicals/" + old_node.symbol.name + ".png"
                    if os.path.isfile(filename):
                        old_node.image = QImage(filename)
                        old_node.image_src = filename
                    else:
                        old_node.image = None
                        old_node.image_src = None

                old_node = old_node.next_term

            # relexed was bigger than old_node => delete as many nodes that fit into len(relexed)
            while old_x < new_x:
                if old_x + len(old_node.symbol.name) <= new_x:
                    old_x += len(old_node.symbol.name)
                    delete_node = old_node
                    old_node = delete_node.next_term
                    delete_node.parent.remove_child(delete_node)
                else:
                    break

        if old_x != new_x: # sanity check
            raise AssertionError("old_x(%s) != new_x(%s) %s => %s" % (old_x, new_x, debug_old, debug_new))

        return

    def relex_import(self, startnode, version=0):
        success = self.lex(startnode.symbol.name)
        bos = startnode.prev_term # bos
        startnode.parent.remove_child(startnode)
        parent = bos.parent
        eos = parent.children.pop()
        last_node = bos
        for match in success:
            node = TextNode(Terminal(match[0]))
            node.version = version
            node.lookup = match[1]
            parent.children.append(node)
            last_node.next_term = node
            last_node.right = node
            node.left = last_node
            node.prev_term = last_node
            node.parent = parent
            last_node = node
        parent.children.append(eos)
        last_node.right = eos # link to eos
        last_node.next_term = eos
        eos.left = last_node
        eos.prev_term = last_node

from cflexer.regexparse import parse_regex
from cflexer.lexer import Lexer
class IncrementalLexerCF(object):
    def __init__(self, rules=None, language=""):
        self.indentation_based = False
        if rules:
            if rules.startswith("%"):
                config_line = rules.splitlines()[0]     # get first line
                self.parse_config(config_line[1:])      # remove %
                rules = "\n".join(rules.splitlines()[1:]) # remove config line
            self.createDFA(rules)

    def parse_config(self, config):
        settings = config.split(",")
        for s in settings:
            name, value = s.split("=")
            if name == "indentation" and value == "true":
                self.indentation_based = True

    def from_name_and_regex(self, names, regexs):
        parsed_regexs = []
        for regex in regexs:
            r = parse_regex(regex)
            parsed_regexs.append(r)
        self.lexer = Lexer(parsed_regexs, names)

    def createDFA(self, rules):
        # lex lexing rules
        pl = PriorityLexer(rules)
        rules = sorted(pl.rules.items(), key=lambda node: node[1][0]) # sort by priority

        # create lexer automaton from rules
        regexs = []
        names = []
        for k, _ in rules:
            regex = k
            name = pl.rules[k][1]
            r = parse_regex(regex)
            regexs.append(r)
            names.append(name)
        self.lexer = Lexer(regexs, names)

    def is_indentation_based(self):
        return self.indentation_based

    def lex(self, text):
        tokens = self.lexer.tokenize(text)
        return self.reformat_tokens(tokens)

    def reformat_tokens(self, tokens):
        l = []
        for t in tokens:
            l.append((t.source, t.name))
        return l

    def relex_import(self, startnode, version = 0):
        success = self.lex(startnode.symbol.name)
        bos = startnode.prev_term # bos
        startnode.parent.remove_child(startnode)
        parent = bos.parent
        eos = parent.children.pop()
        last_node = bos
        for match in success:
            node = TextNode(Terminal(match[0]))
            node.version = version
            node.lookup = match[1]
            parent.children.append(node)
            last_node.next_term = node
            last_node.right = node
            node.left = last_node
            node.prev_term = last_node
            node.parent = parent
            last_node = node
        parent.children.append(eos)
        last_node.right = eos # link to eos
        last_node.next_term = eos
        eos.left = last_node
        eos.prev_term = last_node


    def split_endcomment(self, node):
        read_nodes = [node]
        generated_tokens = []
        l = node.symbol.name.split("*/", 1)
        t1 = self.lexer.tokenize(l[0])
        generated_tokens.extend(t1)
        t2 = self.lexer.tokenize("*/")
        generated_tokens.extend(t2)
        if l[1] != "":
            t3 = self.lexer.tokenize(l[1])
            generated_tokens.extend(t3)

        self.merge_back(read_nodes, generated_tokens)

    def relex(self, node):
        # find farthest node that has lookahead into node
        # start munching tokens and spit out nodes
        #     if generated node already exists => stop
        #     (only if we passed edited node)

        # find node to start relaxing
        startnode = node
        nodes = self.find_preceeding_nodes(node)
        if nodes:
            node = nodes[0]
        if node is startnode:
            past_startnode = True
        else:
            past_startnode = False

        if isinstance(node, EOS):
            # nothing to do here
            return False

        # relex
        read_nodes = []
        generated_tokens = []
        pos = 0  # read tokens
        read = 0 # generated tokens
        current_node = node
        next_token = self.lexer.get_token_iter(StringWrapper(node))
        while True:
            token = next_token()
            if token.source == "":
                read_nodes.append(current_node)
                break
            read += len(token.source)
            # special case when inserting a newline into a string, the lexer
            # creates a single token. We need to make sure that that newline
            # gets lexed into its own token
            if len(token.source) > 1 and token.source.find("\r") >= 0:
                l = token.source.split("\r")
                for e in l:
                    t = self.lexer.tokenize(e)
                    generated_tokens.extend(t)
                    if e is not l[-1]:
                        newline = self.lexer.tokenize("\r")
                        generated_tokens.extend(newline)
            else:
                generated_tokens.append(token)
            while read > pos + len(current_node.symbol.name):
                pos += len(current_node.symbol.name)
                read_nodes.append(current_node)
                current_node = current_node.next_term
                if current_node is startnode:
                    past_startnode = True
            if past_startnode and read == pos + len(current_node.symbol.name):
                read_nodes.append(current_node)
                break

        return self.merge_back(read_nodes, generated_tokens)

    def merge_back(self, read_nodes, generated_tokens):

        any_changes = False
        # insert new nodes into tree
        it = iter(read_nodes)
        for t in generated_tokens:
            try:
                node = it.next()
            except StopIteration:
                node = TextNode(Terminal(""))
                last_node.insert_after(node)
                any_changes = True
            last_node = node
            node.symbol.name = t.source
            node.indent = None
            if node.lookup != t.name:
                node.mark_changed()
                any_changes = True
            else:
                node.mark_version()
            # we need to invalidate the newline if we changed whitespace or
            # logical nodes that come after it
            if node.lookup == "<ws>" or node.lookup != t.name:
                print("MARK newline as changed")
                prev = node.prev_term
                print("prev:", prev)
                while isinstance(prev.symbol, IndentationTerminal):
                    prev = prev.prev_term
                print("prev:", prev)
                if prev.lookup == "<return>":
                    prev.mark_changed()
                    any_changes = True
                elif isinstance(prev, BOS):
                    # if there is no return, re-indentation won't be triggered
                    # in the incremental parser so we have to mark the next
                    # terminal. possibly only use case: bos <ws> pass DEDENT eos
                    node.next_term.mark_changed()
            # XXX this should become neccessary with incparse optimisations turned on
            if node.lookup == "\\" and node.next_term.lookup == "<return>":
                node.next_term.mark_changed()
                any_changes = True
            node.lookup = t.name
            node.lookahead = t.lookahead
        # delete left over nodes
        while True:
            try:
                node = it.next()
                node.parent.remove_child(node)
                any_changes = True
            except StopIteration:
                break
        return any_changes

    def find_preceeding_nodes(self, node):
        chars = 0
        nodes = []
        if node.symbol.name == "\r": # if at line beginning there are no previous nodes to consider
            return nodes
        while True:
            node = node.prev_term
            if node.lookahead and node.lookahead > chars:
                nodes.insert(0, node)
                chars += len(node.symbol.name)
            else:
                break
        return nodes

IncrementalLexer = IncrementalLexerCF
import sys

class StringWrapper(object):
    # XXX This is just a temprary solution. To do this right we have to alter
    # the lexer to work on (node, index)-tuples

    def __init__(self, startnode):
        self.node = startnode
        self.length = sys.maxint

    def __len__(self):
        return self.length

    def __getitem__(self, index):
        startindex = index
        node = self.node
        while index > len(node.symbol.name) - 1:
            index -= len(node.symbol.name)
            node = node.next_term
            if node is None:
                raise IndexError
        if node.next_term and (isinstance(node.next_term, EOS) or isinstance(node.next_term.symbol, IndentationTerminal) or node.next_term.symbol.name == "\r" or isinstance(node.next_term.symbol, MagicTerminal)):
            self.length = startindex + len(node.symbol.name[index:])
        return node.symbol.name[index]

    def __getslice__(self, start, stop):
        if stop <= start:
            return ""

        name = self.node.symbol.name
        if start < len(name) and stop < len(name):
            return name[start: stop]

        text = []
        node = self.node
        i = 0
        while i < stop:
            text.append(node.symbol.name)
            i += len(node.symbol.name)
            node = node.next_term
            if isinstance(node, EOS):
                break
            if isinstance(node.symbol, IndentationTerminal):
                break
            if node.symbol.name == "\r":
                break
            if isinstance(node.symbol, MagicTerminal):
                break

        return "".join(text)[start:stop]
