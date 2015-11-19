import copy
import os
import os.path
import tempfile
import subprocess
import sys

from mocks import MockPopen


class SimpleLanguageExporter(object):

    def __init__(self, tm):
        self.tm = tm  # TreeManager object.

    def export(self, path=None, run=False, profile=False):
        if path is not None:
            self._export_as(path)
            return
        if run or profile:
            if not os.environ.has_key("GRAAL_WORKSPACE"):
                sys.stderr.write("GRAAL_WORKSPACE environment not set")
                return
        if run:
            return self._run()
        elif profile:
            return self._profile()

    def _export_as(self, path):
        self.tm.export_as_text(path)

    def _run(self):
        working_dir = os.path.join(os.environ["GRAAL_WORKSPACE"], "graal-compiler")
        f = tempfile.mkstemp(suffix=".sl")
        self.tm.export_as_text(f[1])
        # Run this command:
        #     $ cd $GRAAL_WORKSPACE/graal-compiler
        #     $ ../../mx/mx --vm graal sl tempfile.sl
        return subprocess.Popen(["../../mx/mx", "--vm", "graal", "sl", f[1]],
                                cwd=working_dir,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                bufsize=0)

    def _profile(self):
            self.tm.profile_is_dirty = False
            self.tm.profile_map = dict()
            self.tm.profile_data = dict()
            working_dir = os.path.join(os.environ["GRAAL_WORKSPACE"], "graal-compiler")
            f = tempfile.mkstemp(suffix=".sl")
            self.tm.export_as_text(f[1])
            # Run this command:
            #     $ cd $GRAAL_WORKSPACE/graal-compiler
            #     $ ../../mx/mx --vm graal slcoverage tempfile.sl
            proc = subprocess.Popen(["../../mx/mx", "--vm", "graal", "slcoverage", f[1]],
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
            for line in stdout_value.split('\n'):
                tokens = line.strip().split()
                if not tokens:
                    continue
                if ((tokens[0] == '(') and
                    tokens[1].endswith(')') and
                    tokens[2].endswith(':')):
                    ncalls = int(tokens[1][:-1])
                    lineno = int(tokens[2][:-1])
                    msg = ('Line %s ran %s times' % (lineno, ncalls))
                    temp_cursor.line = lineno - 1
                    temp_cursor.move_to_x(0, self.tm.lines)
                    node = temp_cursor.find_next_visible(temp_cursor.node)
                    if node.lookup == "<ws>":
                        node = node.next_term
                    self.tm.profile_map[node] = msg
                    self.tm.profile_data[lineno] = (float(ncalls), node)
            return mock
