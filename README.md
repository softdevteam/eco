## Eco: An Editor for Language Composition ##

Eco is a prototype editor for editing composed languages. It is not feature
complete, it is not intended for production, and it does have bugs. Eco is
distributed under a BSD/MIT license.

### Install ###
At a minimum you will need to install:

* Python 2.7 https://www.python.org/download/
* PyQT4 http://www.riverbankcomputing.co.uk/software/pyqt/download
* Py http://pylib.readthedocs.org/en/latest/install.html

On Unix machines, you can reasonably expect your distribution to have packages
for Python and PyQT4. You may need to install Py using Pip or similar (see the
link above).

If you wish to see visualisations of parse trees, you may optionally install:

* GraphViz http://www.graphviz.org/Download.php
* PyDot https://code.google.com/p/pydot/

### Using plugins ###

Eco can visualise data from external tools such as profilers.
To make use of this feature, you need to create a plugin directory:

  `mkdir ~/.eco`

To make use of the example plugins that come with Eco, copy them into your
new plugin directory:

  `cp plugins/*.py ~/.eco/`

To create your own plugins, see the documentation in `plugins/README.md`.

### Running Eco ###

To run Eco, use the bin/eco file:

  `$ bin/eco`
