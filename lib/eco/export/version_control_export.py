# Copyright (c) 2014 King's College London
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


import re
import helper



class VersionControlBuffer (helper.Generic):
    def __init__(self, root_node, exporter):
        helper.Generic.__init__(self)
        self.root_node = root_node
        self.exporter = exporter

    def pp(self, node):
        # Clear the buffer first
        self.buf = []
        # Walk the tree
        self.walk(node)
        # Return the buffer
        return self.buf

    def language_box(self, name, node):
        # Export the contents of the language box
        ref, box_content = self.exporter._export_node(node)
        # Append the reference text to the buffer
        self.buf.append(ref)


class VersionControlExporter:
    NODE_REF_START = u'\ue000'
    NODE_REF_END = u'\ue001'

    def __init__(self):
        self.node_id_to_buffer = {}
        self.root_node_id = None


    def export_document(self, node):
        # Set the ID of the root node to `node`
        node_id = id(node)
        self.root_node_id = node_id
        # Export content
        self._export_node(node)

    def _export_node(self, node):
        # Get the node ID and see if we have already exported it
        node_id = id(node)
        if node_id != self.root_node_id:
            raise NotImplementedError('Language boxes cannot be exported for version control purposes yet')
        try:
            buffer = self.node_id_to_buffer[node_id]
        except KeyError:
            # We haven't handled this node / language box yet; create a new buffer
            buffer = VersionControlBuffer(node, self)
            # Register it
            self.node_id_to_buffer[node_id] = buffer
            # Export its content
            tokens = buffer.pp(node)
        else:
            # Node already exported; just get the content
            tokens = buffer.content

        # Generate the control sequence for a reference to this node
        ref = self.node_ref_control_sequence(node_id)
        return ref, tokens


    def node_ref_control_sequence(self, node_id):
        return self.NODE_REF_START + str(node_id) + self.NODE_REF_END


def export_diff3(node):
    exporter = VersionControlExporter()
    exporter.export_document(node)

    # Get the root buffer (just for now)
    roof_buffer = exporter.node_id_to_buffer[exporter.root_node_id]
    if len(exporter.node_id_to_buffer) > 1:
            raise NotImplementedError('Language boxes cannot be exported for version control purposes yet')

    # Export each token as a repr on a separate line
    tokens_as_python_strings_on_lines = '\n'.join([repr(x) for x in roof_buffer.buf])

    return tokens_as_python_strings_on_lines
