from cover_view import BackupTask
import init_calibre
from calibre.library import db
from PyQt6.QtWidgets import QApplication 
#from PyQt6.Core import Qt
from restore_dialog import RestoreDialog
from sys import argv
from os import path
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
ROOT = '/home/sam/Pictures/Covers/'
books = [BackupTask(1, 'Book Title', ['Author 1','Author 2'], ROOT,[path.join(ROOT,p) for p in glob.glob('1_*',root_dir=ROOT)]),BackupTask(2, 'Book 2 Title', ['Author 1','Author 2'], ROOT,[path.join(ROOT,p) for p in glob.glob('2_*',root_dir=ROOT)])]
window = RestoreDialog(db('/home/sam/Documents/LocalBooks').new_api)
window.load_book_model(books.pop(0))
window.finished.connect(lambda _: window.load_book_model(books.pop(0)) if (len(books) > 0) else app.exit())
window.show()
app.exec()
