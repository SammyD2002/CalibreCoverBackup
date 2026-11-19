import init_calibre
from calibre.library import db
from PyQt6.QtWidgets import QApplication,QMainWindow
from PyQt6.QtCore import Qt,QObject,QMetaObject,pyqtSlot
from sys import argv
from os import path
from calibre_plugins.cover_backup.ui import QBookBase,BookClassFactory
from calibre_plugins.cover_backup.ui.cover_dialog import CoverSelectDialog
from calibre_plugins.cover_backup.ui.backup_resolver import MultiBackupDialog
import glob
app = QApplication(argv)
'''
window = QMainWindow()
widget = QWidget(window)
window.setCentralWidget(widget)
widget.setLayout(layout := QGridLayout())
viewer = CoverListView(widget)
layout.addWidget(viewer,0,0,2,1)
#preview = QLabel("")
layout.addWidget(preview := PreviewWidget('/home/sam/Pictures/Covers/3_Terra Incognita [TimeCloneMike].jpg'),0,1,1,1)
#layout.addWidget(preview,1,1,1,1)
model = BookCoverItemModel(viewer)
#model.setColumnCount(2)
model.setHorizontalHeaderLabels(["Backup Filename"])
viewer.setModel(model)
viewer.setItemDelegate(StyledBookCoverDelegate())
model.setItemPrototype(BookCoverItem())
covers = [BookCoverItem('/home/sam/Pictures/Covers/3_Terra Incognita [TimeCloneMike].jpg'),BookCoverItem('/home/sam/Pictures/Covers/1_Ebott\'s Wake [TimeCloneMike].jpg'),BookCoverItem('/home/sam/Pictures/Covers/1_Quick Start Guide [John Schember].jpg')]
for b in covers:
    model.appendRow(b)
viewer.coverChanged.connect(lambda bc: preview.updatePreview(bc))
'''
'''
books = [BackupTask(1, 'Book Title', ['Author 1','Author 2'], ROOT,[path.join(ROOT,p) for p in glob.glob('1_*',root_dir=ROOT)]),BackupTask(2, 'Book 2 Title', ['Author 1','Author 2'], ROOT,[path.join(ROOT,p) for p in glob.glob('2_*',root_dir=ROOT)])]'''
class Tester(QObject):
    def __init__(self,Book,ids,parent=None):
        QObject.__init__(self,parent)
        self.book_cls = Book
        self.books = [Book(i) for i in ids]
    @pyqtSlot()
    def doDialog(self):
        if len(self.books) == 0: 
            self.deleteLater()
            return
        self.d = MultiBackupDialog(self.books.pop(),len(self.books) > 0,self.parent())
        self.d.finished.connect(self.finishDialog)
        self.d.open()
        
    def finishDialog(self,result):
        print('Dialog result code:',result)
        tmp = self.d
        self.d = None
        rs = tmp.make_resolution()
        print('RESOLUTION:',rs)
        tmp.deleteLater()
        self.doDialog()

window = QMainWindow()
window.show()
test_mgr =  Tester(BookClassFactory(QBookBase,db('/home/sam/Documents/LocalBooks').new_api,'/home/sam/Pictures/Covers/'),[1,2],window)
QMetaObject.invokeMethod(test_mgr,'doDialog',Qt.ConnectionType.QueuedConnection)
test_mgr.destroyed.connect(app.exit)
'''
window.load_book_model(books.pop(0))
window.finished.connect(lambda _: window.load_book_model(books.pop(0)) if (len(books) > 0) else app.exit())
'''
app.exec()
