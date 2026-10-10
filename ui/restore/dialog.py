from calibre_plugins.cover_backup.ui.cover_dialog.cover_view import CoverListView,BackupTask
from preview import PreviewWidget
from PyQt6.QtWidgets import QTreeView ,QGridLayout,QLabel,QWidget,QHeaderView,QHBoxLayout,QVBoxLayout,QDialog,QDialogButtonBox,QCheckBox
from PyQt6.QtGui import QPixmap,QIcon,QPainter
from PyQt6.QtCore import Qt
from cover_model import BookCoverItem,BookCoverItemModel,StyledBookCoverDelegate,CoverDataRole
from typing import override
from dataclasses import dataclass,field
from enum import IntEnum
from os import path
import glob
@dataclass
class PromptResult:
    result: QDialogButtonBox.ButtonRole
    image:tuple(PathLike,QImage)
    other_paths:list[PathLike]
    rm_others:bool
    @property
    def selected(self):
        return self.result == QDialogButtonBox.ButtonRole.AcceptRole
    @property
    def skipped(self):
        return self.result == QDialogButtonBox.ButtonRole.DestructiveRole
    @property
    def cancelled(self):
        return self.result == QDialogButtonBox.ButtonRole.RejectRole

def prepareCoverWidgets(db,book,model,viewer):
    pm = db.cover(book.book_id,as_pixmap=True)
    model.appendRow(base := BookCoverItem(pm))
    if pm is None: print('LOADED COVER WAS NULL!')
    elif not pm.isNull(): print('Pixmap is not valid!')
    #m.destroyed.connect(lambda: print(f"Model destruction for book {book} detected"))
    model.setHorizontalHeaderLabels(["Backup Filename"])
    for r in range(len(book.ext_paths)):
        base.setChild(r, BookCoverItem(book.ext_paths[r]))
    viewer.setRootIndex(base.index())
    viewer.setCurrentIndex(top := model.index(0,0,viewer.rootIndex()))
    rsize, rc = BookCoverItemModel.loadCover(model,viewer.rootIndex())
    viewer.rootCoverChanged.emit(rsize, rc.pixmap(rsize))
    csize, cc = BookCoverItemModel.loadCover(model, top)
    viewer.coverChanged.emit(csize, cc.pixmap(csize))
    #self.viewer.coverChanged.emit(BookCoverItemModel.loadCover())
    viewer.resizeColumnToContents(1)
	


class RestoreDialog(QDialog):
    def __init__(self,db_api,parent=None):
        QDialog.__init__(self,parent)
        self.db = db_api
        self.setLayout(layout := QGridLayout())
        self.book_msg = QLabel(f"")
        layout.addWidget(self.book_msg,0,0,1,1)
        self.select_msg = QLabel("Please select a backup to restore.")
        layout.addWidget(self.select_msg, 1,0,1,1)
        self.preview = PreviewWidget(self)
        self.viewer = CoverListView(self.preview, self)
        layout.addWidget(self.viewer,2,0,1,1)
        self.viewer.setItemDelegate(StyledBookCoverDelegate())
        #preview = QLabel("")
        layout.addWidget(self.preview, 0,1,3,-1)
        #model.setItemPrototype(BookCoverItem())
        layout.setColumnStretch(0,1)
        layout.setColumnStretch(1,1)
        self.viewer.coverChanged.connect(self.preview.updateBackup)
        self.viewer.rootCoverChanged.connect(self.preview.updateCurrent)
        self.rm_others = QCheckBox("Delete other backups")
        layout.addWidget(self.rm_others,3,0,1,1)
        self.button_box = QDialogButtonBox()
        self.ok = self.button_box.addButton(QDialogButtonBox.StandardButton.Ok)
        self.skip = self.button_box.addButton(QDialogButtonBox.StandardButton.Discard)
        self.skip.setText("Skip")
        self.skip.setIcon(QIcon.fromTheme(QIcon.ThemeIcon.MediaSeekForward))
        self.cancel = self.button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        self.button_box.clicked.connect(lambda b: self.done(self.button_box.buttonRole(b).value))
        layout.addWidget(self.button_box,3,1,1,1)
    '''
    @override
    def resizeEvent(self, event):
        if (curr := self.viewer.currentIndex()).isValid():
            self.viewer.currentChanged(curr,None)
            self.viewer.currentChanged(curr.parent(),None)
    '''
    @property
    def model(self):
        return self.viewer.model()
    @model.setter
    def model(self,m):
        sm = self.viewer.selectionModel() if (om := self.model) is not None else None
        m.setParent(self.viewer)
        self.viewer.setModel(m)
        if sm is not None:
            om.deleteLater()
            sm.deleteLater()

    def load_book_model(self,book):
        #print('Loading',book)
        self.book = book
        self.book_msg.setText(f"Multiple backups exist for {self.book.title} [{self.book.book_id}].")
        self.model = BookCoverItemModel()
		prepareCoverWidgets(self.db,self.book,self.model,self.viewer)
        self.show()

    @override
    def done(self,res):
        index = self.viewer.currentIndex()
        if not index.isValid(): return
        print(f'Selected Item: {self.model.itemData(index)}')
        root = self.model.item(0)
        item = root.takeChild(index.row())
        selected_path = item.data(CoverDataRole.PathRole)
        s, icn = BookCoverItemModel.loadCover(item)
        img = icn.pixmap(s).toImage()
        item.clearData()
        others = []
        for r in range(root.rowCount()):
            ch = root.child(r)
            if ch in [None,item] : continue
            print(f'Child {r}: {self.model.itemData(ch.index())}')
            others.append(ch.data(CoverDataRole.PathRole))
            ch.clearData()
            print('Path Check:',ch.data(CoverDataRole.PathRole))
            print('Size Check:',ch.data(CoverDataRole.SizeRole))
            
        print(root.rowCount())
        self.decision = PromptResult(res,(selected_path,img),others,self.rm_others.isChecked())
        print('DECISION:',self.decision)
        self.model.clear()
        QDialog.done(self,res)

