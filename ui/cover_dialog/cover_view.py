from qt.core import pyqtSignal,QSize,Qt,QTreeView ,QApplication,QGridLayout,QLabel,QMainWindow,QWidget,QButtonGroup,QRadioButton,QHeaderView,QHBoxLayout,QVBoxLayout,QDialog, QBoxLayout,QSizePolicy,QPixmap,QIcon,QPainter
from calibre_plugins.cover_backup.base import book_info,BackupStatus,BackupTask
from calibre_plugins.cover_backup.ui.cover_dialog import BookCoverItem,BookCoverItemModel,StyledBookCoverDelegate
from sys import argv
from typing import override
from dataclasses import dataclass,field
from enum import IntEnum
from os import path,PathLike

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

class CoverListView(QTreeView):
    coverChanged = pyqtSignal(QSize,QPixmap)
    rootCoverChanged = pyqtSignal(QSize,QPixmap)
    def __init__(self,pw,parent=None):
        QTreeView.__init__(self,parent)
        self.preview_widget = pw
        #self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Preferred)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)
        self.setRootIsDecorated(False)
        #print('MODEL:',self.model())
        #self.buttons = QButtonGroup()
        #self.header().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
    def __set_index_checked(self, index, checked):
        if index is None: print('Index passed was None. Skipping...')
        elif not index.isValid(): print("Current is invalid")
        elif index.model() is None: print("Current model is None!")
        else: self.model().setData(index,Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
    def clearModel(self):
        model = self.model()
        index = self.currentIndex()
        self.setModel(None)
        root = model.item(0)
        item = root.takeChild(index.row())
        selected_path = item.data(CoverDataRole.PathRole)
        s, icn = BookCoverItemModel.loadCover(item)
        img = icn.pixmap(s).toImage()
        item.clearData()
        others = []
        for r in range(root.rowCount()):
            ch = root.child(r)
            if ch in [None,item] : continue
            print(f'Child {r}: {model.itemData(ch.index())}')
            others.append(ch.data(CoverDataRole.PathRole))
            ch.clearData()
            print('Path Check:',ch.data(CoverDataRole.PathRole))
            print('Size Check:',ch.data(CoverDataRole.SizeRole))
        #print(root.rowCount())
        model.clear()
        model.deleteLater()
        
    @override
    def currentChanged(self, current, previous):
        self.__set_index_checked(current,True)
        self.__set_index_checked(previous,False)
        if current is None: print('Current is None.')
        elif not current.isValid(): print("Current is invalid")
        elif current.model() is None: print("Current model is None!")
        else:
            m = current.model()
            #print(f'Creating thumbnail(s) for {parent_size}...')
            signal = self.coverChanged if current.parent().isValid() else self.rootCoverChanged
                #print(f"Loading thumbnail for child at row {current.row()} to parent row {current.parent().row()}")
            s, pm = BookCoverItemModel.loadCover(m, current)
            signal.emit(s,pm.pixmap(s))
        super().currentChanged(current,previous)
            #current = current.siblingAtColumn(0)
            #button = current.siblingAtColumn(1)
            #w = self.indexWidget(button)
            #w.setChecked(True)
            ##print(w.text())
    @override
    def rowsInserted(self,pindex,start,end):
        if pindex.isValid(): print(f"Added child at row {start} to parent row {pindex.row()}")
        else: print(f"Added non-child at row {start}")
        self.resizeColumnToContents(1)
        super().rowsInserted(pindex,start,end)

    '''
    @override
    def rowsInserted(self,pindex,start,end):
        for i in range(start,end+1):
            b = QRadioButton('')
            self.buttons.addButton(b)
            self.setIndexWidget(self.model().index(i,1,pindex),b)
            self.resizeColumnToContents(1)
            self.resizeColumnToContents(2)
    ''' 

