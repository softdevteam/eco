import sys
sys.path.append(".")
sys.path.append("../")
sys.path.append("../lr-parser/")

from plexer import PriorityLexer
from gparser import MagicTerminal, Terminal, IndentationTerminal
from astree import BOS, EOS, TextNode, ImageNode
from PyQt4.QtGui import QImage
import re, os

class IncrementalLexer(object):
    # XXX needs to be replaced by a lexing automaton to avoid uneccessary
    # relexing of unchanged nodes

    def __init__(self, rules, language=""):
        self.language = language
        pl = PriorityLexer(rules)
        self.regexlist = pl.rules
        self.compiled_regexes = {}
        for regex in self.regexlist:
            self.compiled_regexes[regex] = re.compile(regex)

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

    def relex(self, startnode):
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

        if isinstance(startnode, BOS) or isinstance(startnode.symbol, MagicTerminal):
            startnode = startnode.next_term

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
                    else:
                        additional_node.image = None
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
                    else:
                        old_node.image = None

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
