from plugins.api import Plugin
from incparser.annotation import Annotation, Heatmap, ToolTip

import os
import os.path
import subprocess
import tempfile

class SLCoverageCounterMsg(Annotation):
    def __init__(self, annotation):
        self._hints = [ToolTip()]
        super(SLCoverageCounterMsg, self).__init__(annotation)

    def get_hints(self):
        return self._hints


class SLCoverageCounterVal(Annotation):
    def __init__(self, annotation):
        self._hints = [Heatmap()]
        super(SLCoverageCounterVal, self).__init__(annotation)

    def get_hints(self):
        return self._hints


class SimpleLanguageCoverage(Plugin):
    """Coverage counter for SimpleLanguage programs.
    Requires Truffle / Graal.
    """

    def __init__(self):
        super(SimpleLanguageCoverage, self).__init__("SimpleLanguage",
                                                     "Truffle coverage counter")

    def run_tool(self):
        if not "GRAAL_WORKSPACE" in os.environ:
            return

        working_dir = os.path.join(os.environ["GRAAL_WORKSPACE"], "graal-compiler")
        f = tempfile.mkstemp(suffix=".sl")
        self.export(f[1])

        # Run this command:
        #     $ cd $GRAAL_WORKSPACE/graal-compiler
        #     $ ../../mx/mx --vm graal slcoverage tempfile.sl
        proc = subprocess.Popen(["../../mx/mx", "--vm", "graal", "slcoverage", f[1]],
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
                msg = ('Line %s ran %s times' % (lineno, ncalls))
                node = self.get_node_at_pos(lineno, 0)
                # Remove old annotation
                node.remove_annotations_by_class(SLCoverageCounterMsg)
                # Add new annotation
                node.add_annotation(SLCoverageCounterMsg(msg))
                ncalls_dict[node] = ncalls

        # Normalise profiler information.
        vals = ncalls_dict.values()
        if len(vals) == 1:
            for node in ncalls_dict:
                ncalls_dict[node] = 1.0
                node.remove_annotations_by_class(SLCoverageCounterVal)
                node.add_annotation(SLCoverageCounterVal(ncalls_dict[node]))
        elif len(vals) > 1:
            val_min = float(min(vals))
            val_max = float(max(vals))
            val_diff = val_max - val_min
            for node in ncalls_dict:
                ncalls_dict[node] = (ncalls_dict[node] - val_min) / val_diff
            for node in ncalls_dict:
                node.remove_annotations_by_class(SLCoverageCounterVal)
                node.add_annotation(SLCoverageCounterVal(ncalls_dict[node]))


# Create the plugin object that will be loaded by Eco.
sl_coverage = SimpleLanguageCoverage()
