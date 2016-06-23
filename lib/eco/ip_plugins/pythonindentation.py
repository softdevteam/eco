from grammar_parser.gparser import IndentationTerminal, Nonterminal
from incparser.astree import BOS, EOS, TextNode

Node = TextNode

class PythonIndent(object):

    def __init__(self, incparser):
        self.incparser = incparser
        self.multimode = None

    def incparse_init(self):
        self.comment_tokens = []
        self.indent_stack = None

    def incparse_inc_parse_top(self):
        self.incparser.stack[0].indent = [0] # init bos with indent
        self.last_indent = [0]
        self.multimode = None
        self.multinewlines = []

        bos = self.incparser.previous_version.parent.children[0]
        eos = self.incparser.previous_version.parent.children[-1]
        d = eos.prev_term
        while isinstance(d.symbol, IndentationTerminal):
            d = d.prev_term
        self.last_token_before_eos = d

        if isinstance(d, BOS):
            # if file is empty, delete left over indentation tokens
            n = d.next_term
            while isinstance(n.symbol, IndentationTerminal):
                n.parent.remove_child(n)
                n = n.next_term

        # fix indentation after bos. Should result in an error for whitespace
        # at the beginning
        if bos.next_term.lookup == "<ws>":
            bos.insert_after(TextNode(IndentationTerminal("INDENT")))
        elif isinstance(bos.next_term.symbol, IndentationTerminal):
            bos.next_term.parent.remove_child(bos.next_term)

    def incparse_optshift(self, la):
        if la.indent:
            self.last_indent = list(la.indent)

    def incparse_shift(self, la, rb):
        self.toggle_multimode(la)
        if self.incparser.indentation_based and not rb and not self.multimode:
            return self.parse_whitespace(la)
        if self.incparser.indentation_based and self.multimode and la.lookup == "<return>":
            self.multinewlines.append(la)

    def incparse_reduce(self, new_node):
        self.set_total_indent(new_node)

    def incparse_end_any(self, newlines):
        # update succeeding
        if self.incparser.indentation_based:
            for n in newlines:
                # remove indentation tokens from multilines
                n = n.next_term
                while isinstance(n.symbol, IndentationTerminal):
                    n.parent.remove_child(n)
                    n = n.next_term
                n.indent = None
                self.update_succeeding_lines(n, self.last_indent[-1], list(self.last_indent))

    def incparse_from_dict(self, rules):
        if not rules:
            print("Warning: incparser has not access to comment tokens")
        elif rules.has_key(Nonterminal("comment")):
            rule = rules[Nonterminal("comment")]
            for a in rule.alternatives:
                if len(a) > 0:
                    self.comment_tokens.append(a[0].name)

    def toggle_multimode(self, la):
        if la.lookup == "MLS" and self.multimode:
            self.multimode = None
            self.incparse_end_any(self.multinewlines)
            self.multinewlines = []
        elif la.lookup == "MLS" and not self.multimode: self.multimode = "MLS"

    def get_previous_ws(self, node):
        """Returns the whitespace of the previous logical line"""
        node = node.prev_term
        while True:
            if isinstance(node, BOS):
                return 0
            if node.lookup != "<return>":
                node = node.prev_term
                continue
            if not self.is_logical_line(node):
                node = node.prev_term
                continue
            if node.next_term.lookup == "<ws>":
                return len(node.next_term.symbol.name)
            else:
                return 0

    def indents_differ(self, this, other):
        if len(this) != len(other):
            return True
        for i in range(len(this)):
            if this[i].symbol != other[i].symbol:
                return True
        return False

    def repair_indents(self, node, there, needed):
        """Updates the indentation tokens of a line, given a list of needed
        tokens and tokens already there"""
        it = iter(there)
        last = node
        # update indentation tokens with new values or insert new ones
        for e in needed:
            try:
                ne = it.next()
                if e.symbol == ne.symbol:
                    last = ne
                    continue
                else:
                    ne.symbol.name = e.symbol.name
                    ne.mark_changed()
                    continue
            except StopIteration:
                pass
            last.insert_after(e)
            last = e
        # delete all leftovers
        while True:
            try:
                x = it.next()
                x.parent.remove_child(x)
            except StopIteration:
                break

    def is_logical_line(self, node):
        """Checks if a line is logical, i.e. doesn't only consist of whitespaces or comments"""
        if node.symbol.name == "\r" and node.prev_term.symbol.name == "\\": # <backslash>
            return False
        node = node.next_term
        while True:
            if isinstance(node, EOS):
                return False
            # this doesn't work as we only know if something is part of a
            # comment AFTER we parsed it. But by this time it's too late to add
            # indentation tokens:
            # if node.parent.symbol.name in ["multiline_string", "single_string", "comment"] and not node.parent.changed:
            #     return False
            # instead we need to manually check if one of the known comment tokens appears
            # in the line
            if node.lookup in self.comment_tokens:
                #XXX return false or continue?
                return False
            if node.lookup == "<return>": # reached next line
                return False
            if node.lookup == "<ws>":
                node = node.next_term
                continue
            if  isinstance(node.symbol, IndentationTerminal):
                node = node.next_term
                continue
            # if we are here, we reached a normal node
            return True

    def parse_whitespace(self, la):
        """Calculates and repairs indentation levels and tokens after parsing a <return> token.

        Special case: The last token before EOS triggers the generation of the closing dedentations

        1) Check if a line is logical or not
           a) Logical: Update indent levels, compare needed indetation tokens
              with current ones and update if needed
           b) Not logical: Remove all indentation tokens and set indent level to None
        2) Update succeeding lines that depend(ed) on this line
        """
        if la.lookup == "<return>" or isinstance(la, BOS) or la is self.last_token_before_eos:
            if not self.is_logical_line(la) and not la is self.last_token_before_eos:
                # delete indentation tokens and indent level
                n = la.next_term
                while isinstance(n.symbol, IndentationTerminal):
                    n.parent.remove_child(n)
                    n = n.next_term
                la.indent = None
                newindent = list(self.get_last_indent(la))
                ws = self.get_previous_ws(la)
            else:
                there = []
                n = la.next_term
                while isinstance(n.symbol, IndentationTerminal):
                    there.append(n)
                    n = n.next_term

                if n.lookup == "<ws>":
                    ws = len(n.symbol.name)
                else:
                    ws = 0

                last_indent = list(self.get_last_indent(la))
                needed, newindent = self.get_indentation_tokens_and_indent(last_indent, ws)
                indent_stack_eq = newindent == la.indent
                if la is not self.last_token_before_eos:
                    la.indent = list(newindent)
                    self.last_indent = list(la.indent)

                if self.indents_differ(there, needed):
                    self.repair_indents(la, there, needed)
                elif indent_stack_eq:
                    return
            self.update_succeeding_lines(la, ws, newindent)

    def update_succeeding_lines(self, la, ws, newindent):
        # update succeeding lines
        # XXX this causes a chain reaction iterating over some lines
        # multiple times. we might only have to do this for the <return>
        # that has actually changed during the parse
        next_r = la.next_term
        while True:
            if isinstance(next_r, EOS):
                # if changes reach end of file, repair indentations now or
                # it will be too late
                eos_there = []
                d = next_r.prev_term
                while isinstance(d.symbol, IndentationTerminal):
                    eos_there.insert(0, d)
                    d = d.prev_term
                eos_needed, _ = self.get_indentation_tokens_and_indent(list(self.get_last_indent(d)), 0)
                if self.indents_differ(eos_there, eos_needed):
                    self.last_token_before_eos.mark_changed() # don't repair here, only mark and repair just before last token is parsed
                break
            if next_r.lookup != "<return>":
                next_r = next_r.next_term
                continue

            # XXX need to skip unlogical lines (what if don't know if unlogical yet)

            # if tokens need to be updated, mark as changed, so the parser will go down this tree to update
            next_ws = self.get_whitespace(next_r)
            if next_ws is None:
                next_r = next_r.next_term
                continue
            needed, newindent = self.get_indentation_tokens_and_indent(newindent, next_ws)
            if not self.indents_match(next_r, needed) or next_r.indent != newindent:
                next_r.mark_changed()
            if next_ws < ws:
                # if newline has smaller whitespace -> mark and break
                break

            next_r = next_r.next_term

    def get_indentation_tokens_and_indent(self, indent, ws):
        needed = []
        newindent = []
        if ws > indent[-1]:
            needed.append(Node(IndentationTerminal("NEWLINE")))
            needed.append(Node(IndentationTerminal("INDENT")))
            newindent = indent + [ws]
        elif ws < indent[-1]:
            needed.append(Node(IndentationTerminal("NEWLINE")))
            while ws < indent[-1]:
                indent.pop()
                needed.append(Node(IndentationTerminal("DEDENT")))
            newindent = list(indent)
            if ws != indent[-1]:
                # XXX in future, just ERROR here
                needed.append(Node(IndentationTerminal("UNBALANCED")))
        else:
            needed.append(Node(IndentationTerminal("NEWLINE")))
            newindent = list(indent)
        return needed, newindent

    def indents_match(self, node, needed):
        there = []
        n = node.next_term
        while isinstance(n.symbol, IndentationTerminal):
            there.append(n)
            n = n.next_term

        if len(there) != len(needed):
            return False
        for i in range(len(there)):
            if there[i].symbol != needed[i].symbol:
                return False
        return True

    def get_whitespace(self, node):
        if not self.is_logical_line(node):
            return None

        node = node.next_term
        while isinstance(node.symbol, IndentationTerminal):
            node = node.next_term

        if node.lookup == "<ws>":
            return len(node.symbol.name)

        return 0

    def get_last_indent(self, la):
        return self.last_indent

    def set_total_indent(self, node):
        l = []
        if node.children:
            for c in node.children:
                if c.indent:
                    l = c.indent
        if l:
            node.indent = l

def load(caller):
    # XXX only load if incparser is indentation_based
    if type(caller).__name__ == "IncParser":
        return PythonIndent(caller)
    return None
