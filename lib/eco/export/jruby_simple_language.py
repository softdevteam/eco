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
        output += "".join(self._sl_output)
        output += "})\n\n"
        output += "".join(self._wrappers)
        output += "\n\n"
        rb_code = "".join(self._output)
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
        self.tm.profile_is_dirty = False
        self.tm.profile_map = dict()
        self.tm.profile_data = dict()
        working_dir = os.path.join(os.environ["GRAAL_WORKSPACE"], "jruby")
        f = tempfile.mkstemp(suffix=".rb")
        self._export_as_text(f[1])

        # Get a plain text version of the original code, to map
        # line numbers back to the code in the view port.
        plain_lines = self.tm.export_as_text(None).split("\n")

        # Run this command:
        #     $ cd $GRAAL_WORKSPACE/jruby
        #     $ ./bin/jruby -X+T -Xtruffle.coverage.global=true -J-classpath ./truffle-sl.jar FILE.rb
        proc =  subprocess.Popen(["bin/jruby",
                                  "-X+T",
                                  "-Xtruffle.coverage.global=true",
                                  "-J-classpath",
                                  "../truffle/mxbuild/dists/truffle-sl.jar",
                                  f[1]],
                                 cwd=working_dir,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT,
                                 bufsize=0)
        stdout_value, stderr_value = proc.communicate()

        # Mock Popen here, so that we can return a Popen-like object.
        # This allows Eco to append the output of the profiler
        # to the console.
        mock = MockPopen(copy.copy(stdout_value), copy.copy(stderr_value))

        # Lex the result of the profiler. Lines look like this:
        #                 11: function main() {
        # (    20000000)   5:     sum = sum + i;
        temp_cursor = self.tm.cursor.copy()
        ncalls_dict = dict()
        for line in stdout_value.split('\n'):
            tokens = line.strip().split()
            if not tokens:
                continue
            if ((tokens[0] == '(') and
                tokens[1].endswith(')') and
                tokens[2].endswith(':')):
                ncalls = int(tokens[1][:-1])
                lineno = int(tokens[2][:-1])
                if ncalls == 0:
                    continue
                try:
                    # Locate the line of code in the original text
                    lineno = plain_lines.index(line.split(":")[1][1:]) + 1
                    msg = ('Line %s ran %s times' % (lineno, ncalls))
                    temp_cursor.line = lineno - 1
                    temp_cursor.move_to_x(0, self.tm.lines)
                    node = temp_cursor.find_next_visible(temp_cursor.node)
                    if node.lookup == "<ws>":
                        node = node.next_term
                    # Remove old annotation
                    node.remove_annotations_by_class(JRubyCoverageCounterMsg)
                    # Add new annotation
                    node.add_annotation(JRubyCoverageCounterMsg(msg))
                    ncalls_dict[node] = ncalls
                except ValueError:
                    continue

        # Normalise profiler information.
        vals = ncalls_dict.values()
        val_min = float(min(vals))
        val_max = float(max(vals))
        val_diff = val_max - val_min
        for node in ncalls_dict:
            ncalls_dict[node] = (ncalls_dict[node] - val_min) / val_diff
        for node in ncalls_dict:
            node.remove_annotations_by_class(JRubyCoverageCounterVal)
            node.add_annotation(JRubyCoverageCounterVal(ncalls_dict[node]))

        return mock
