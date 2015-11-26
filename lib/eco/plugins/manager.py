import os
import os.path

from api import Plugin

from PyQt4.QtCore import QObject, QTimer, SIGNAL

class PluginManager(QObject):
    """This object loads and manages Eco plugins.

    The object constructs the Tools menu in the Eco GUI and connects
    menu actions to plugins.

    Plugins should be stored in ~/.eco and must be subclasses of
    eco.plugins.api.Plugin.
    """

    def __init__(self, main_window, tool_plugin_menu):
        super(PluginManager, self).__init__(parent=None)
        self._plugins = dict()
        self._actions = dict()
        self._main_window = main_window
        self._plugin_menu = tool_plugin_menu
        self._plugin_dir = os.path.join(os.path.expanduser("~"), ".eco")
        self._current_language = None  # Set by self.set_tms()

        # Load plugins and construct UI.
        self._load_plugins()

        # Use a single shot timer to run external tools, in case the plugins
        # take a long time to run (i.e. we do not want to restart the timer
        # while tools are still running in the background). The default
        # timeout is quite long, because most of the time the user is typing
        # the code will be syntactically incorrect, and the tools will not
        # be able to run.
        self._default_timeout = 2500
        self.timer = QTimer()
        self.timer.timeout.connect(self._run_plugins)
        self.timer.setSingleShot(True)
        self.timer.start(self._default_timeout)

        # Number of plugins currently running.
        self._plugins_running = 0

    def _load_plugins(self):
        """Load plugins and construct GUI elements.
        """
        # Load all plugins that can be found on disk.
        name_space = dict(locals(), **globals())
        for root, dirs, files in os.walk(self._plugin_dir):
            for file_ in files:
                if file_.endswith(".py"):
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
                                          SIGNAL("triggered()"),
                                          lambda plugin=plugin: self.toggle_plugin(plugin))
                self.connect(plugin, SIGNAL("finished()"), self._plugin_finished)

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

    def _is_document_exportable(self, plugin):
        """Returns True if the current document can be exported.
        Eco cannot export a document that is syntactically incorrect.
        """
        for p, _, _, _ in plugin._tm.parsers:
            if p.last_status == False:
                return False
        return True

    def _plugin_finished(self):
        self._plugins_running -= 1
        if self._plugins_running == 0:
            self.timer.start(self._default_timeout)

    def _run_plugins(self):
        if self._current_language is None:
            # Eco does not have an open document.
            # Wait a little longer before trying again.
            self.timer.start(2 * self._default_timeout)
            return
        # Run plugins if they are activated and the current document is
        # syntactically correct.
        for plugin in self._plugins[self._current_language]:
            if not (plugin.activated and self._is_document_exportable(plugin)):
                continue
            self._plugins_running += 1
            plugin.start()

    def set_tms(self, tm):
        """Give all plugins access to the current TreeManager object.
        """
        self._current_language = None if tm is None else tm.parsers[0][2]
        for language in self._plugins:
            for plugin in self._plugins[language]:
                plugin.tm = tm
