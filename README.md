## Eco: An Editor for Language Composition ##

Eco is a prototype editor for editing composed languages. It is not feature
complete, it is not intended for production, and it does have bugs. Eco is
distributed under a BSD/MIT license.

### Install ###
At a minimum you will need to install:

* Python 3 https://www.python.org/download/
* PyQt5 http://www.riverbankcomputing.co.uk/software/pyqt/download5
* Py http://py.readthedocs.io/en/latest/install.html

On Unix machines, you can reasonably expect your distribution to have packages
for Python and PyQt. You may need to install Py using Pip or similar (see the
link above).

If you wish to see visualisations of parse trees, you may optionally install:

* GraphViz http://www.graphviz.org/Download.php
* PyDot https://code.google.com/p/pydot/
* Pygame https://www.pygame.org/

### Running Eco ###

To run Eco, use the bin/eco file:

  `$ bin/eco`

### Tutorial ###

A small tutorial to get you started with the basics of Eco can be found [here](tutorial/TUTORIAL.md).

### Troubleshooting ###

#### Windows Subsystem for Linux running Ubuntu ####

If you are having trouble running Eco on the Windows Subsystem running Ubuntu,
follow these instructions:

```
# Install Python3
sudo apt-get install python3 libxkbcommon-x11-0

# Install dependencies via pip
python3 -m pip install --user PyQt5 py

# Optional dependencies to visualise parse trees
sudo apt-get install graphviz
python3 -m pip install --user pydot pygame
```
