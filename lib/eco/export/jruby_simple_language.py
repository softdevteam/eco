import copy
import os
import os.path
import tempfile
import subprocess
import sys

from incparser.annotation import Annotation, ToolTip, Footnote, Heatmap

from incparser.astree import EOS
from grammar_parser.gparser import MagicTerminal, IndentationTerminal

from mocks import MockPopen


class JRubyCoverageCounterMsg(Annotation):
    def __init__(self, annotation):
        self._hints = [ToolTip(), Footnote()]
        super(JRubyCoverageCounterMsg, self).__init__(annotation)

    def get_hints(self):
        return self._hints


class JRubyCoverageCounterVal(Annotation):
    def __init__(self, annotation):
        self._hints = [Heatmap()]
        super(JRubyCoverageCounterVal, self).__init__(annotation)

    def get_hints(self):
        return self._hints


class JRubySimpleLanguageExporter(object):
    def __init__(self, tm):
        self.tm = tm  # TreeManager object.
        self.sl_functions = dict()
        self._sl_output = list()
        self._wrappers = list()
        self._output = list()
        self._sl_functions = list()
        self._line_no_map = dict()

    def export(self, path=None, run=False, profile=False):
        if path is not None:
            self._export_as_text(path)
            return
        if run or profile:
            if not os.environ.has_key("GRAAL_WORKSPACE"):
                sys.stderr.write("GRAAL_WORKSPACE environment not set")
                return
        if run:
            return self._run()
        elif profile:
            return self._profile()

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

    def _apply_template(self, name, magic_name):
        return """  {1} = Truffle::Interop.import('{0}')
  def {0}(*args)
    Truffle::Interop.execute({1}, *args)
  end

""".format(name, magic_name)

    def _export_as_text(self, path):
        node = self.tm.lines[0].node # first node
        self._walk_rb(node)
        for func in self._sl_functions:
            magic = func.upper() + "_"
            self._wrappers.append(self._apply_template(func, magic))
        output = "Truffle::Interop.eval('application/x-sl', %{\n"
        sl_funcs = "".join(self._sl_output)
        for n in xrange(sl_funcs.count("\n")):
            self._line_no_map[n] = n - 1
        last_line_no_in_map = n
        output += sl_funcs
        output += "})\n\n"
        wrappers = "".join(self._wrappers)
        for n in xrange(wrappers.count("\n")):
            self._line_no_map[last_line_no_in_map + n] = last_line_no_in_map + n - 3
        last_line_no_in_map += n
        output += wrappers
        output += "\n\n"
        rb_code = "".join(self._output)
        for n in xrange(rb_code.count("\n")):
            self._line_no_map[last_line_no_in_map + n] = last_line_no_in_map + n - 5
        output += rb_code
        with open(path, "w") as fp:
            fp.write("".join(output))

    def _run(self):
        working_dir = os.path.join(os.environ["GRAAL_WORKSPACE"], "jruby")
        f = tempfile.mkstemp(suffix=".rb")
        self._export_as_text(f[1])
        # Run this command:
        #     $ cd $GRAAL_WORKSPACE/jruby
        #     $ ./bin/jruby -X+T -J-classpath ./truffle-sl.jar FILE.rb
        return subprocess.Popen(["bin/jruby",
                                 "-X+T",
                                 "-J-classpath",
                                 "../truffle/mxbuild/dists/truffle-sl.jar",
                                 f[1]],
                                cwd=working_dir,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                bufsize=0)

    def _profile(self):
        pass
