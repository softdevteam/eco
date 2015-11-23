import os
import os.path
import tempfile
import subprocess
import sys

from incparser.astree import EOS
from grammar_parser.gparser import MagicTerminal, IndentationTerminal

class JRubySimpleLanguageExporter(object):
    def __init__(self, tm):
        self.tm = tm  # TreeManager object.
        self.sl_functions = dict()
        self._sl_output = list()
        self._wrappers = list()
        self._output = list()
        self._sl_functions = list()

    def export(self, path=None, run=False):
        if path is not None:
            self._export_as_text(path)
            return
        if run:
            if not os.environ.has_key("GRAAL_WORKSPACE"):
                sys.stderr.write("GRAAL_WORKSPACE environment not set")
                return
        if run:
            return self._run()

    def _language_box(self, name, node):
        if name == "<Ruby + SimpleLanguage>":
            self._walk_rb(node)
        elif name == "<SimpleLanguage>":
            self._walk_sl(node)

    def _walk_sl(self, node):
        while True:
            node = node.next_term
            sym = node.symbol
            if isinstance(node, EOS):
                break
            if isinstance(sym, MagicTerminal):
                self._language_box(sym.name, node.symbol.ast.children[0])
            elif isinstance(sym, IndentationTerminal):
                self._sl_output.append(sym)
            elif sym.name == "function":
                self._sl_functions.append(node.next_term.next_term.symbol.name)
                self._sl_output.append(sym.name)
            elif sym.name == "\r":
                self._sl_output.append("\n")
            else:
                self._sl_output.append(sym.name)

    def _walk_rb(self, node):
        while True:
            node = node.next_term
            sym = node.symbol
            if isinstance(node, EOS):
                break
            if isinstance(sym, MagicTerminal):
                self._language_box(sym.name, node.symbol.ast.children[0])
            elif isinstance(sym, IndentationTerminal):
                self._output.append(sym)
            elif sym.name == "\r":
                self._output.append("\n")
            else:
                self._output.append(sym.name)

    def _apply_template(self, name):
        return "Truffle::Interop.import_method(:%s)" % name

    def _export_as_text(self, path):
        node = self.tm.lines[0].node # first node
        self._walk_rb(node)
        for func in self._sl_functions:
            self._wrappers.append(self._apply_template(func))
        output = "Truffle::Interop.eval('application/x-sl', %{\n"
        output += "".join(self._sl_output)
        output += "})\n\n"
        output += "\n".join(self._wrappers)
        output += "\n\n"
        rb_code = "".join(self._output)
        output += rb_code
        with open(path, "w") as fp:
            fp.write("".join(output))

    def _run(self):
        f = tempfile.mkstemp(suffix=".rb")
        working_dir = os.path.join(os.environ["GRAAL_WORKSPACE"], "jruby")
        truffle_jar = os.path.join(os.environ["GRAAL_WORKSPACE"],
                                   "truffle/mxbuild/dists/truffle-sl.jar")
        self._export_as_text(f[1])
        # Run this command:
        #     $ cd $GRAAL_WORKSPACE/jruby
        #     $ ./bin/jruby -X+T -J-classpath truffle-sl.jar FILE.rb
        return subprocess.Popen(["bin/jruby",
                                 "-X+T",
                                 "-J-classpath",
                                 truffle_jar,
                                 f[1]],
                                cwd=working_dir,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                bufsize=0)
