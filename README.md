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

#### On Ubuntu (including Windows Subsysten for Linux) ####

The above dependencies can be installed as follows on command line:

```
# Get Python3 if you haven't already
sudo apt-get install python3

python3 -m pip install --user PyQt5 py

# I couldn't run Eco without it because Qt couldn't find a platform plugin
# Solution from https://forum.qt.io/topic/99562/qt-5-12-1-cannot-load-library-opt-qt-5-12-1-gcc_64-plugins-platforms-libqxcb-so-libxkbcommon-x11-so-0-cannot-open-shared-object-file-no-such-file-or-directory
sudo apt-get install libxkbcommon-x11-0

# Optional dependencies if you want to visualize parse trees
sudo apt-get install graphviz 
python3 -m pip install --user pydot pygame
```

### Running Eco ###

To run Eco, use the bin/eco file:

  `$ bin/eco`
  
### Tutorial ###

A small tutorial to get you started with the basics of Eco can be found [here](tutorial/TUTORIAL.md).
