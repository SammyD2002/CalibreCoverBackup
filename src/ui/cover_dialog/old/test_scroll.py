from PyQt6.QtWidgets import QApplication,QWidget,QScrollArea,QMainWindow,QGridLayout,QHBoxLayout,QVBoxLayout,QLabel,QRadioButton,QLayout,QPushButton,QRadioButton,QButtonGroup,QFrame,QListWidgetItem
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap,QIcon
from sys import argv
class SelectionArea(QScrollArea):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWidget(w := QWidget())
        self.buttons = QButtonGroup(self)
        self.buttons.setExclusive(True)
        w.setLayout(pl := QGridLayout())
        pl.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        self.setWidgetResizable(True)
    @property
    def widgetLayout(self):
        return self.widget().layout()
    def addRow(self,txt):
        row = RowWidget(txt)
        self.buttons.addButton(row.button)
        self.widgetLayout.addWidget(row)
        

class RowWidget(QFrame):
    def __init__(self,txt,w=None,parent=None):
        QFrame.__init__(self,parent)
        self.setFrameShape(QFrame.Shape.Panel)
        self.setLayout(l := QHBoxLayout())
        self.button = QRadioButton(txt)
        l.addWidget(self.button)


app = QApplication(argv)
window = QMainWindow()
ui = QWidget()
window.setCentralWidget(ui)
ui.setLayout(layout := QGridLayout())
layout.addWidget(paths := SelectionArea(ui),0,0,1,-1)
for i in range(100):
    paths.addRow(f'r{i}')
window.show()
app.exec()
