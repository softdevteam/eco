from grammar_parser.gparser import MagicTerminal, IndentationTerminal
from incparser.astree import BOS, EOS
import re

class HtmlPythonSQL(object):

    def export(self, bos, filename):
        node = bos
        html_text = []
        output = []
        while True:
            node = node.next_term
            if isinstance(node, EOS):
                if html_text:
                    text = "".join(html_text)
                    output.append(self.create_print(text))
                break
            if isinstance(node.symbol, MagicTerminal):
                if html_text:
                    text = "".join(html_text)
                    output.append(self.create_print(text))
                    output.append("\n")
                html_text = []
                p = self.get_python(node)
                output.extend(p)
                output.append("\n")
                continue
            # html
            if node.symbol.name == "\r":
                if html_text:
                    text = "".join(html_text)
                    output.append(self.create_print(text))
                    output.append("\n")
                html_text = []
                continue
            else:
                html_text.append(node.symbol.name)
                continue

        f = open(filename, "w")
        output = "".join(output)
        m = re.search("([a-zA-Z_][a-zA-Z_0-9]*) = sqlite3.connect",output)
        if m:
            f.write("""
def gen_exec(query):
    try:
        _c = %s.cursor()
        _c.execute(query)
        while True:
            o = _c.fetchone()
            if o == None:
                break
            yield o
    finally:
        _c.close()
""" % m.group(1))
        f.write(output)
        f.close()

    def get_python(self, lbox):
        node = lbox.symbol.ast.children[0]
        ws = len(node.next_term.symbol.name)
        text = []
        while True:
            node = node.next_term
            if isinstance(node, EOS):
                break
            if isinstance(node.symbol, IndentationTerminal):
                continue
            if isinstance(node.symbol, MagicTerminal):
                x = "".join(self.get_sql(node))
                text.append("gen_exec(\"\"\"")
                text.append(self.escape_quotes(x))
                text.append("\"\"\")")
                continue
            if node.symbol.name == "\r":
                text.append("\n")
            elif node.lookup == "<ws>" and (isinstance(node.prev_term.symbol, IndentationTerminal) or isinstance(node.prev_term, BOS) or node.prev_term.symbol.name == "\r"):
                text.append(node.symbol.name[ws:])
            else:
                text.append(node.symbol.name)
        return text

    def get_sql(self, lbox):
        node = lbox.symbol.ast.children[0]
        text = []
        while True:
            node = node.next_term
            if isinstance(node, EOS):
                break
            if node.symbol.name == "\r":
                text.append("\n")
            else:
                text.append(node.symbol.name)
        return text

    def escape_quotes(self, text):
        text = text.replace("\"", "\\\"")
        text = text.replace("\'", "\\\'")
        return text

    def create_print(self, text):
        text = self.escape_quotes(text)
        text = "print \"\"\"%s\"\"\"" % text
        return text
