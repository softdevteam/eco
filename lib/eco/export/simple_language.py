import os
import os.path
import tempfile
import subprocess
import sys

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
