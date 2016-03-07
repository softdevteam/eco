# import copy
import os
import os.path
import tempfile
import subprocess

from incparser.annotation import Annotation, ToolTip, Footnote

from incparser.astree import EOS
from grammar_parser.gparser import MagicTerminal, IndentationTerminal

from PyQt4.QtCore import QSettings

class JRubyMorphismMsg(Annotation):
    def __init__(self, annotation):
        self._hints = [ToolTip(), Footnote()]
        super(JRubyMorphismMsg, self).__init__(annotation)

    def get_hints(self):
        return self._hints


class JRubyExporter(object):
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
        if run:
            return self._run()
        elif profile:
            return self._profile()

    def _language_box(self, name, node):
        if name == "<Ruby>":
            self._walk_rb(node)

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
        output = "".join(self._output)
        with open(path, "w") as fp:
            fp.write("".join(output))

    def _run(self):
        f = tempfile.mkstemp(suffix=".rb")
        settings = QSettings("softdev", "Eco")
        jruby_bin =str (settings.value("env_jruby").toString())
        self._export_as_text(f[1])
        # Run this command:
        #     $ jruby -X+T FILE.rb
        return subprocess.Popen([jruby_bin,
                                 "-X+T",
                                 f[1]],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                bufsize=0)

    def _profile(self):
        src_file_fd, src_file_name = tempfile.mkstemp(suffix=".rb")
        self.tm.export_as_text(src_file_name).split("\n")

        info_file_name = os.path.join("/",
                                      "tmp",
                                      next(tempfile._get_candidate_names()) + ".txt")
        print 'Placing callgraph trace in', info_file_name

        # Run this command:
        #  $ cd $GRAAL_WORKSPACE/jruby
        #  $ jruby -X+T -Xtruffle.callgraph=true -Xtruffle.callgraph.write=test.txt -Xtruffle.dispatch.cache=2 FILE
        settings = QSettings("softdev", "Eco")
        jruby_bin = str(settings.value("env_jruby", "").toString())
        cmd = [jruby_bin, "-X+T", "-Xtruffle.callgraph=true",
               "-Xtruffle.callgraph.write=" + info_file_name,
               "-Xtruffle.dispatch.cache=2",
               src_file_name]
        print 'Running command:'
        print ' '.join(cmd)
        subprocess.call(cmd)

        methods = dict()
        with open(info_file_name) as fd:
            output = fd.read()
            lines = output.split('\n')
            i = 0
            while i < len(lines):
                line = lines[i]
                if line.startswith('method') and src_file_name in line:
                    tokens = line.split()
                    if tokens[2] == '<main>':
                        i += 1
                        continue
                    method_id = int(tokens[1])
                    methods[method_id] = { 'name': tokens[2],
                                           'lineno': int(tokens[4]),
                                           'versions': 0,
                                           'callsites': 0,
                                           'callsite-versions': 0,
                                           'calls': 0,
                                           'is_mega': False }
                    i += 1
                    line = lines[i]
                    # Note the space here to avoid confusion between methods
                    # and method versions.
                    while not line.startswith('method '):
                        print line
                        if line.startswith('method-version'):
                            methods[method_id]['versions'] += 1
                        elif line.startswith('callsite'):
                            methods[method_id]['callsites'] += 1
                        elif line.startswith('callsite-versions'):
                            methods[method_id]['callsite-versions'] += 1
                        elif line.startswith('calls'):
                            tokens = line.split()
                            if tokens[-1] == 'mega':
                                methods[method_id]['is_mega'] = True
                            methods[method_id]['calls'] += 1
                        i += 1
                        line = lines[i]
                i += 1

        for mid in methods:
            print methods[mid]
            print '-------------------------------------------------------'

        for mid in methods:
            if methods[mid]['is_mega']:
                msg = ("Method %s is megamorphic. %s has %g versions and %g callsite versions and is called %g times" %
                       (methods[mid]['name'],
                        methods[mid]['name'],
                        methods[mid]['versions'],
                        methods[mid]['callsite-versions'],
                        methods[mid]['calls']))
            else:
                msg = ("Method %s is not megamorphic. %s has %g versions and %g callsite versions and is called %g times" %
                       (methods[mid]['name'],
                        methods[mid]['name'],
                        methods[mid]['versions'],
                        methods[mid]['callsite-versions'],
                        methods[mid]['calls']))
            # node = self.tm.get_node_at_pos(methods[mid]['lineno'], 0)
            try:
                # Locate the line of code in the original text
                temp_cursor = self.tm.cursor.copy()
                lineno = methods[mid]['lineno']
                temp_cursor.line = lineno - 1
                temp_cursor.move_to_x(0, self.tm.lines)
                node = temp_cursor.find_next_visible(temp_cursor.node)
                if node.lookup == "<ws>":
                    node = node.next_term
                node.remove_annotations_by_class(JRubyMorphismMsg)
                node.add_annotation(JRubyMorphismMsg(msg))
            except ValueError:
                continue
