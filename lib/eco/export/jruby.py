# Copyright (c) 2015--2016 King's College London
# Created by the Software Development Team <http://soft-dev.org/>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

import logging
import os
import os.path
import tempfile
import subprocess

from incparser.annotation import Annotation, ToolTip, Railroad

from incparser.astree import EOS
from grammar_parser.gparser import MagicTerminal, IndentationTerminal

from PyQt4.QtCore import QSettings


class JRubyMorphismLine(Annotation):
    """Annotation for JRuby callgraph railroad diagrams.
    """

    def __init__(self, annotation):
        self._hints = [Railroad()]
        super(JRubyMorphismLine, self).__init__(annotation)

    def get_hints(self):
        return self._hints


class JRubyMorphismMsg(Annotation):
    """Annotation for JRuby callgraph tooltips.
    """

    def __init__(self, annotation):
        self._hints = [ToolTip()]
        super(JRubyMorphismMsg, self).__init__(annotation)

    def get_hints(self):
        return self._hints


class Source(object):
    """JRuby source file (needed by callgraph profiler).
    """

    def __init__(self, file, line_start, line_end):
        self.file = file
        self.line_start = int(line_start)
        self.line_end = int(line_end)


class Method(object):
    """JRuby method (needed by callgraph profiler).
    """

    def __init__(self, id_, name, source):
        self.id = int(id_)
        self.name = name
        self.source = source
        self.versions = []
        self.callsites = []
        self.is_mega = False

    def is_core(self):
        return ('/core/' in self.source.file or 'core.rb' in self.source.file
                or self.source.file == '(unknown)')

    def is_hidden(self):
        return (self.source.file == 'run_jruby_root' or
                self.source.file == 'context' or
                self.name == 'Truffle::Primitive#run_jruby_root' or
                self.name == 'Truffle::Primitive#context')

    def reachable(self):
        return self.callsites

    def __str__(self):
        return ('Method: %s id=%g callsites=[ %s ]' %
                (self.name, self.id, ' '.join([str(cs) for cs in self.callsites])))


class MethodVersion(object):

    def __init__(self, id_, method):
        self.id = int(id_)
        self.method = method
        self.callsite_versions = []
        self.called_from = []

    def reachable(self):
        # called_from isn't reachable
        return [self.method] + self.callsite_versions

    def __str__(self):
        return ('Method Version: %s id=%g called_from=[ %s ]' %
                (self.method.name, self.id,
                 ' '.join([str(cs) for cs in self.called_from])))


class CallSite(object):
    """JRuby callsite (needed by callgraph profiler).
    """

    def __init__(self, id_, method, line):
        self.id = int(id_)
        self.method = method
        self.line = int(line)
        self.versions = []

    def reachable(self):
        return [self.method] + self.versions

    def __str__(self):
        return ('Callsite: %s id=%g line=%g' %
                (self.method.name, self.id, self.line))


class CallSiteVersion(object):
    """JRuby callsite version (needed by callgraph profiler).
    """

    def __init__(self, id_, callsite, method_version):
        self.id = int(id_)
        self.callsite = callsite
        self.method_version = method_version
        self.calls = []

    def reachable(self):
        # Method_version isn't reachable - find it through calls
        return [self.callsite] + self.calls

    def __str__(self):
        return ('Callsite Version: %s id=%g' %
                (self.callsite.method.name, self.id))


class Mega(object):
    """Class used to indicate that a method is megamorphic.
    """

    def __str__(self):
        return 'Megamorphic'


class JRubyExporter(object):
    """Export, run or profile a JRuby file.
    """

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
        if name == '<Ruby>':
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
            elif sym.name == '\r':
                self._output.append('\n')
            else:
                self._output.append(sym.name)

    def _export_as_text(self, path):
        node = self.tm.lines[0].node # first node
        self._walk_rb(node)
        output = ''.join(self._output)
        with open(path, 'w') as fp:
            fp.write(''.join(output))

    def _run(self):
        f = tempfile.mkstemp(suffix='.rb')
        settings = QSettings('softdev', 'Eco')
        jruby_bin =str (settings.value('env_jruby').toString())
        self._export_as_text(f[1])
        # Run this command:
        #     $ jruby -X+T FILE.rb
        return subprocess.Popen([jruby_bin, '-X+T', f[1]],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                bufsize=0)

    def _annotate_text(self, lineno, text, annotation, klass):
        """Annotate a node on a given line with a given symbol name.
        FIXME: Should handle case where line (and all subsequent lines) have
        already been deleted by the user.
        FIXME: Needs to handle the case where same text appears in more than
        one node on the same line.
        """
        try:
            temp_cursor = self.tm.cursor.copy()
            temp_cursor.line = lineno - 1
            temp_cursor.move_to_x(0)
            node = temp_cursor.find_next_visible(temp_cursor.node)
            while node.lookup == '<ws>' or node.symbol.name != text:
                node = node.next_term
                if isinstance(node, EOS):
                    raise ValueError('EOS')
            node.remove_annotations_by_class(klass)
            node.add_annotation(klass(annotation))
        except ValueError:
            pass

    def _profile(self):
        """Run JRuby and dump a callgraph to disk.
        Parse the callgraph and annotate the syntax tree.
        """

        src_file_fd, src_file_name = tempfile.mkstemp(suffix='.rb')
        self.tm.export_as_text(src_file_name).split('\n')

        info_file_name = os.path.join('/',
                                      'tmp',
                                      next(tempfile._get_candidate_names()) + '.txt')
        logging.debug('Placing callgraph trace in', info_file_name)

        # Run this command:
        #  $ jruby -X+T -Xtruffle.callgraph=true -Xtruffle.callgraph.write=test.txt -Xtruffle.dispatch.cache=2 FILE
        settings = QSettings('softdev', 'Eco')
        jruby_bin = str(settings.value('env_jruby', '').toString())
        pic_size = str(settings.value('graalvm_pic_size', '').toString())
        cmd = [jruby_bin, '-X+T', '-Xtruffle.callgraph=true',
               '-Xtruffle.callgraph.write=' + info_file_name,
               '-Xtruffle.dispatch.cache=' + pic_size,
               src_file_name]
        logging.debug('Running command: ' + ' '.join(cmd))
        settings = QSettings('softdev', 'Eco')
        graalvm_bin = str(settings.value('env_graalvm', '').toString())
        subprocess.call(cmd, env={'JAVACMD':graalvm_bin})

        objects = dict()
        with open(info_file_name) as fd:
            output = fd.read()
            lines = output.split('\n')
            i = 0
            while i < len(lines):
                line = lines[i]
                tokens = line.split()
                if len(tokens) == 0:
                    pass
                elif tokens[0] == 'method':
                    method = Method(tokens[1], tokens[2], Source(*tokens[3:6]))
                    objects[method.id] = method
                elif tokens[0] == 'method-version':
                    method = objects[int(tokens[1])]
                    method_version = MethodVersion(tokens[2], method)
                    objects[method_version.id] = method_version
                    method.versions.append(method_version)
                elif tokens[0] == 'callsite':
                    method = objects[int(tokens[1])]
                    callsite = CallSite(tokens[2], method, tokens[3])
                    objects[callsite.id] = callsite
                    method.callsites.append(callsite)
                elif tokens[0] == 'callsite-version':
                    callsite = objects[int(tokens[1])]
                    method_version = objects[int(tokens[2])]
                    callsite_version = CallSiteVersion(tokens[3], callsite, method_version)
                    objects[callsite_version.id] = callsite_version
                    callsite.versions.append(callsite_version)
                    method_version.callsite_versions.append(callsite_version)
                elif tokens[0] == 'calls':
                    callsite_version = objects[int(tokens[1])]
                    if tokens[2] == 'mega':
                      callsite_version.calls.append(Mega())
                    else:
                      # We just store the method id here for now as we may not have seen all methods yet
                      callsite_version.calls.append(int(tokens[2]))
                elif tokens[0] == 'local':
                    pass
                else:
                    logging.debug('Cannot parse the following:', line)
                    return
                i += 1

        # Resolve method ids to point to the actual object
        for obj in objects.itervalues():
            if isinstance(obj, CallSiteVersion):
                callsite_version = obj
                new_calls = []
                for call in callsite_version.calls:
                    if isinstance(call, Mega):
                        new_calls.append(Mega())
                        callsite_version.method_version.method.is_mega = True
                    else:
                        called = objects[call]
                        called.called_from.append(callsite_version)
                        new_calls.append(called)
                callsite_version.calls = new_calls

        # Find which objects were actually used
        reachable_objects = set()
        reachable_worklist = set()
        for obj in objects.itervalues():
            if ((isinstance(obj, Method) and not obj.is_core()) or
                (isinstance(obj, MethodVersion) and
                 obj.method.name == '<main>' and
                 not obj.method.is_core())):
                reachable_worklist.add(obj)

        while len(reachable_worklist) > 0:
            obj = reachable_worklist.pop()
            if isinstance(obj, Mega):
                continue
            elif obj in reachable_objects:
                continue
            else:
                reachable_objects.add(obj)
                reachable_worklist.update(obj.reachable())

        for obj in reachable_objects:
            if isinstance(obj, Method) and obj.source.file == src_file_name:
                method = obj
                num_calls = 0
                for version in method.versions:
                    for callsite_version in version.called_from:
                        if method.is_mega:
                            cmsg = ('Call to %s defined on line %g (megamorphic).' %
                                    (method.name, method.source.line_start))
                        else:
                            cmsg = ('Call to %s defined on line %g.' %
                                    (method.name, method.source.line_start))
                        self._annotate_text(callsite_version.callsite.line,
                                            method.name, cmsg, JRubyMorphismMsg)
                        if callsite_version.callsite.line > 0:
                            self._annotate_text(callsite_version.callsite.line,
                                                method.name,
                                                { method.name : method.is_mega },
                                                JRubyMorphismLine)
                        num_calls += 1
                if method.is_mega:
                    dmsg = ('Method %s is megamorphic. %s has %g version(s) and %g callsite version(s) and is called %g time(s)' %
                            (method.name,
                             method.name,
                             len(method.versions),
                             len(method.callsites),
                             num_calls))
                else:
                    dmsg = ('Method %s has %g version(s) and %g callsite version(s) and is called %g time(s)' %
                            (method.name,
                             len(method.versions),
                             len(method.callsites),
                             num_calls))
                self._annotate_text(method.source.line_start, method.name,
                                    dmsg, JRubyMorphismMsg)
