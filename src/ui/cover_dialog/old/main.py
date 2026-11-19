from PyQt6.QtWidgets import QApplication,QDialogButtonBox
from PyQt6.QtCore import QObject,QIODevice,QFile,QDataStream,QMetaObject
from PyQt6.QtGui import QPixmap
from dialog import BackupTask,ImageSelect
import glob
from sys import argv
from PyQt6 import sip
from os import path
class ResultPrinter(QObject):
    def __init__(self,books,parent=None):
        QObject.__init__(self,parent)
        parent.finished.connect(self.print_result)
        self.books = books
    def do_book(self):
        self.parent().loadBook(self.books.pop(0))
        self.parent().show()
    def print_result(self,res):
        print(res)
        d = self.parent().decision
        print(d)
        out_f = QFile('out.jpg')
        if not out_f.open(QIODevice.OpenModeFlag.WriteOnly): print("Failed to open file!")
        #out = QDataStream(out_f)
        d.image[1].save(out_f)
        out_f.close()
        if len(self.books) > 0:
            self.parent().reset()
            self.do_book()
        else: self.parent().deleteLater()
        
        
app = QApplication(argv)
ROOT = path.expanduser('~/Pictures/Covers')
books = [BackupTask(1, 'Book Title', ['Author 1','Author 2'], ROOT,[path.join(ROOT,p) for p in glob.glob('1_*',root_dir=ROOT)]),BackupTask(2, 'Book 2 Title', ['Author 1','Author 2'], ROOT,[path.join(ROOT,p) for p in glob.glob('2_*',root_dir=ROOT)])]
isel = ImageSelect()
rp = ResultPrinter(books,isel)
#isel.finished.connect(rp.print_result)
isel.destroyed.connect(app.exit)
#isel.show()
rp.do_book()
app.exec()
