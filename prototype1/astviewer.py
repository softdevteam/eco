import sys
import simpleast
from PyQt4 import QtGui

class AstViewer(QtGui.QWidget):

    def __init__(self, parent=None, ast):
        QtGui.QWidget.__init__(self, parent)

        self.setGeometry(300, 300, 250, 250)

    def paintEvent(self, event):
        paint = QtGui.QPainter()
        paint.begin(self)
        paint.drawLine(0,0,100,100)
        paint.drawArc(0,0,100,50,0,16*360)

        drawProgram()

        paint.end()

    def drawProgram():
        paint.drawArc()



def embed_ipython(w):
    from IPython.Shell import IPShellEmbed
    ipshell = IPShellEmbed(user_ns = dict(w = w))
    ipshell()


# load program

p = simpleast.createTestProgram()

app = QtGui.QApplication(sys.argv)
av = AstViewer(p)
av.show()
embed_ipython(av)
sys.exit(app.exec_()) # important, else wm crashes
