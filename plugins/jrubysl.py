from plugins.api import Plugin
from incparser.annotation import Annotation, ToolTip, Heatmap

import os.path
import subprocess
import tempfile

class JRubyCoverageCounterMsg(Annotation):
    def __init__(self, annotation):
        self._hints = [ToolTip()]
        super(JRubyCoverageCounterMsg, self).__init__(annotation)

    def get_hints(self):
        return self._hints


class JRubyCoverageCounterVal(Annotation):
    def __init__(self, annotation):
        self._hints = [Heatmap()]
        super(JRubyCoverageCounterVal, self).__init__(annotation)

    def get_hints(self):
        return self._hints


class JRubySLCoverage(Plugin):
    """Coverage counter for Ruby + SimpleLanguage programs.
    Requires Truffle / Graal.
    """

    def __init__(self):
        super(JRubySLCoverage, self).__init__("Ruby + SimpleLanguage",
                                              "Truffle coverage counter")

    def run_tool(self):
        if not "GRAAL_WORKSPACE" in os.environ:
            return

        working_dir = os.path.join(os.environ["GRAAL_WORKSPACE"], "jruby")

        f = tempfile.mkstemp()
        self.export(f[1])

        plain_file = tempfile.mkstemp(suffix=".rb")

        # Get a plain text version of the original code, to map
        # line numbers back to the code in the view port.
        plain_lines = self.export_as_text(plain_file[1]).split("\n")

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

        # Lex the result of the profiler. Lines look like this:
        #                 11: function main() {
        # (    20000000)   5:     sum = sum + i;
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
                    node = self.get_node_at_pos(lineno, 0)
                    # Remove old annotation
                    node.remove_annotations_by_class(JRubyCoverageCounterMsg)
                    # Add new annotation
                    node.add_annotation(JRubyCoverageCounterMsg(msg))
                    ncalls_dict[node] = ncalls
                except ValueError:
                    continue

        # Normalise profiler information.
        vals = ncalls_dict.values()
        if len(vals) == 1:
            for node in ncalls_dict:
                ncalls_dict[node] = 1.0
                node.remove_annotations_by_class(JRubyCoverageCounterVal)
                node.add_annotation(JRubyCoverageCounterVal(ncalls_dict[node]))
        elif len(vals) > 1:
            val_min = float(min(vals))
            val_max = float(max(vals))
            val_diff = val_max - val_min
            for node in ncalls_dict:
                ncalls_dict[node] = (ncalls_dict[node] - val_min) / val_diff
            for node in ncalls_dict:
                node.remove_annotations_by_class(JRubyCoverageCounterVal)
                node.add_annotation(JRubyCoverageCounterVal(ncalls_dict[node]))


# Create the plugin object that will be loaded by Eco.
jruby_sl_coverage = JRubySLCoverage()
