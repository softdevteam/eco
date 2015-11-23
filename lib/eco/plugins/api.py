import abc

class Plugin(object):
    """Base class for Eco plugins.
    Every Plugin subclass must have a 'name' field which described the Plugin
    and a 'language' field which describes which language the plugin can be
    applied to.
    """

    def __init__(self, language, name):
        self.language = language
        self.name = name
        self._activated = True

    @property
    def activated(self):
        return self._activated

    def activate(self):
        """Activate this plugin.
        """
        self._activated = True

    def deactivate(self):
        """Deactivate this plugin.
        """
        self._activated = False

    @abc.abstractmethod
    def run_tool(self):
        """Run an external tool and annotate nodes.
        """
        raise NotImplementedError("Must be overridden in subclass.")
