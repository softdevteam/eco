# Eco plugin API

A *plugin* in Eco is a proxy to an external tool, which can provide useful
information that can provide feedback to the user. Example tools include
profilers, lints, etc.

This directory contains some example plugins, and at the end of this file
you can find a template for creating a new plugin.

To create a plugin you need to provide at least two classes: an
`Annotation` class, instances of which will be stored on AST nodes at runtime.
Secondly, you need to provide the `Plugin` class itself.

### Annotations

An `Annotation` should be a subclass of `incparser.annotation.Annotation`.
It should provide a single method called `get_hints()` which should
return a list of objects, each of which should be a subclass of
`incparser.annotation.Hint`. Hints tell Eco how you wish your annotations
to be visualised at runtime. Currently available hints are:

  * `Heatmap`
  * `ToolTip`
  * `Footnote` (text displayed underneath a node)

### Plugins

A plugin should be a subclass of `incparser.annotation.Plugin`. Every plugin
should have a `name` field (which will be displayed in the **Tools** menu
of the GUI) and a `language` field. The `language` field tells Eco which
lanuages your plugin is applicable to.

The following languages are currently available in Eco:

  * Basic Calculator
  * HTML
  * HTML + Python + SQL
  * Java 1.5
  * Java + SQL + Chemical
  * PHP
  * PHP + Python
  * Prolog
  * Python 2.7.5
  * Python + HTML + SQL
  * Python + Prolog
  * Python + IPython
  * Ruby
  * Ruby + SimpleLanguage
  * SimpleLanugage
  * SQL

Finally, your plugin must expose a method called `run_tool()` which
does the work of the plugin -- i.e. it runs an external tool and annotates
the relevant nodes of the AST.

To help you, plugin objects implement the following methods:

  * `export(self, path=None)` -- export the current document and save in a file
    called `path`
  * `export_as_text(self, path=None)` -- export the current document as plain
    text (i.e. ignore language boxes)
  * `get_node_at_pos(self, lineno, charno=0)` -- return the node at a given
    line number and character in the original document.

## Plugin template

```python
from plugins.api import Plugin
from incparser.annotation import Annotation, Heatmap, Footnote, ToolTip


class MyPluginTextAnnotation(Annotation):
    def __init__(self, annotation):
        self._hints = [ToolTip(), Footnote()]
        super(MyPluginAnnotation, self).__init__(annotation)

    def get_hints(self):
        return self._hints


class MyPluginFloatAnnotation(Annotation):
    def __init__(self, annotation):
        self._hints = [Heatmap()]
        super(MyPluginAnnotation, self).__init__(annotation)

    def get_hints(self):
        return self._hints


class MyPlugin(Plugin):
    """Example Eco plugin.
    """

    def __init__(self):
        super(MyPlugin, self).__init__("Python 2.7.5",
                                       "Example Python plugin")

    def run_tool(self):
        """Run an external tool and annotate nodes."""

        tfile = tempfile.mkstemp(suffix=".py")
        self.export(tfile[1])

        # Run an external command
        proc = subprocess.Popen(["...",  # Command
                                tfile[1]],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                bufsize=0)
        stdout_value, stderr_value = proc.communicate()

        # Lex or parse the result of the external tool.
        for line in stdout_value.split('\n'):
            tokens = line.strip().split()
            if not tokens:
                continue
            if ... :
                line_no = ...  # Location of node we wish to annotate
                char_no = ...
                node = self.get_node_at_pos(line_no, char_no)
                # Remove old annotations
                node.remove_annotations_by_class(MyPluginTextAnnotation)
                node.remove_annotations_by_class(MyPluginFloatAnnotation)
                # Add new annotation
                text_msg = ...
                float_val = ...
                node.add_annotation(MyPluginTextAnnotation(text_msg))
                node.add_annotation(MyPluginFloatAnnotation(float_val))

# Create the plugin object that will be loaded by Eco.
my_plugin = MyPlugin()
```
