import abc

from PyQt4 import QtCore

class Plugin(QtCore.QThread):
    """Base class for Eco plugins.
    Every Plugin subclass must have a 'name' field which described the Plugin
    and a 'language' field which describes which language the plugin can be
    applied to.
    """

    def __init__(self, language, name):
        super(Plugin, self).__init__(parent=None)
        self.language = language
        self.name = name
        self._activated = True
        self._tm = None  # TreeManager must be set (per document) by the GUI.

    @abc.abstractmethod
    def run_tool(self):
        """Run an external tool and annotate nodes.
        """
        raise NotImplementedError("Must be overridden in subclass.")

    def run(self):
        self.run_tool()
        self.tm.tool_data_is_dirty = False

    def export(self, path=None):
        return self._tm.export(path)

    def export_as_text(self, path=None):
        return self._tm.export_as_text(path)

    def get_node_at_pos(self, lineno, charno=0):
        """Get the node at a given position.
        If charno is not given, this method returns the first non-whitespace
        node on the given line.
        """
        temp_cursor = self.tm.cursor.copy()
        temp_cursor.line = lineno - 1
        temp_cursor.move_to_x(charno, self.tm.lines)
        node = temp_cursor.find_next_visible(temp_cursor.node)
        if node.lookup == "<ws>":
            node = node.next_term
        return temp_cursor.find_next_visible(temp_cursor.node)

    @property
    def tm(self):
        """The TreeManager object needs to be set by external code.
        Ideally we want to hide the TreeManager and other Eco internals
        from plugins.
        """
        return self._tm

    @tm.setter
    def tm(self, tm):
        self._tm = tm

    @property
    def activated(self):
        return self._activated

    def activate(self):
        """Activate this plugin.
        i.e. show it as checked in the GUI and run the external tool for
        which this plugin is a proxy.
        """
        self._activated = True

    def deactivate(self):
        """Deactivate this plugin.
        i.e. show it as unchecked in the GUI and do not run the external tool
        for which this plugin is a proxy.
        """
        self._activated = False
