import os
import os.path

from api import Plugin

from PyQt4 import QtCore
from PyQt4.QtGui import *


class PluginManager(object):
    """This object loads and manages Eco plugins.

    The object constructs the Tools menu in the Eco GUI and connects
    menu actions to plugins.

    Plugins are stored in ~/.eco and must be subclasses of plugins.api.Plugin.
    """

    def __init__(self, main_window, tool_plugin_menu):
        self._plugins = dict()
        self._actions = dict()
        self._main_window = main_window
        self._plugin_menu = tool_plugin_menu
        self._plugin_dir = os.path.join(os.path.expanduser("~"), ".eco")

        # Load all plugins that can be found on disk.
        name_space = dict(locals(), **globals())
        for root, dirs, files in os.walk(self._plugin_dir):
            for file_ in files:
                execfile(os.path.join(root, file_), name_space, name_space)

        # Store references to plugins to this object.
        for obj_name in name_space:
            if isinstance(name_space[obj_name], Plugin):
                self._add_plugin(name_space[obj_name])

        # Construct the Tools menu.
        for language in self._plugins:
            lang_menu = self._plugin_menu.addMenu(language)
            self._actions[language] = dict()
            for plugin in self._plugins[language]:
                action = lang_menu.addAction(plugin.name)
                action.setCheckable(True)
                self._actions[language][plugin.name] = action
                self._main_window.connect(action,
                                          QtCore.SIGNAL('triggered()'),
                                          lambda plugin=plugin: self.toggle_plugin(plugin))

        # Start with all plugins activated.
        for language in self._plugins:
            for plugin in self._plugins[language]:
                plugin.activate()
                self._set_checked(plugin, True)

    def _add_plugin(self, plugin):
        if plugin.language in self._plugins:
            self._plugins[plugin.language].append(plugin)
        else:
            self._plugins[plugin.language] = [plugin]

    def _set_checked(self, plugin, is_checked):
        action = self._actions[plugin.language][plugin.name]
        action.setChecked(is_checked)

    def toggle_plugin(self, plugin):
        if not plugin.activated:
            self._set_checked(plugin, True)
            plugin.activate()
        else:
            self._set_checked(plugin, False)
            plugin.deactivate()

    def run_plugins_by_language(self, language):
        for plugins in self._plugins[lang]:
            if plugin.activated():
                plugin.run_tool()
