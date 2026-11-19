from qt.core import (pyqtSignal,QSize,Qt,QTreeView,QApplication,QGridLayout,QLabel,QMainWindow,QWidget,QButtonGroup,
                    QRadioButton,QHeaderView,QHBoxLayout,QVBoxLayout,QDialog,QBoxLayout,QSizePolicy,QPixmap,QIcon,QPainter)
#from calibre_plugins.cover_backup.base import book_info,BackupStatus,BackupTask
from calibre_plugins.cover_backup.ui.cover_dialog import BookCoverItem,BookCoverItemModel,CheckProxyModel
from sys import argv
from typing import override
from dataclasses import dataclass,field
from enum import IntEnum
from os import path,PathLike
class CoverListView(QTreeView):
    coverChanged = pyqtSignal(QSize,QPixmap)
    rootCoverChanged = pyqtSignal(QSize,QPixmap)
    def __init__(self,pw,parent=None):
        QTreeView.__init__(self,parent)
        '''
        New behavoir: Select on double-click or checkbox pressed, preview on selectionChanged.
        '''
        self.preview_widget = pw
        self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)
        self.setRootIsDecorated(False)
        self.doubleClicked.connect(self.toggleIndex)
    def __index_issue(self,index):
        # Returns int depending on the issue at hand.
        if index is None: return 1
        elif not index.isValid(): return 2
        elif index.model() is None: return 3
        else: return 0
    def __print_index_issue(self,code,index,prefix='Specified Index'):
        match(code):
            case 1: print(prefix,'was None. Skipping...')
            case 2: print(prefix,"is invalid")
            case 3: print(prefix," had model of None!")
    def toggleIndex(self,index):
        if (iss := self.__index_issue(index)) == 0:
            if index.data(Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Unchecked: self.model().setData(index,Qt.CheckState.Checked,Qt.ItemDataRole.CheckStateRole)
            else: self.model().setData(index,Qt.CheckState.Unchecked,Qt.ItemDataRole.CheckStateRole)
        else: self.__print_index_issue(iss,index,'Index passed to toggleIndex')
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
        model.clear()
        model.deleteLater()    

    def selectedPaths(self):
        r = self.model().sourceModel().item(0)
        paths = []
        if r.hasChildren():
            #print(f'root has {r.rowCount()} Children')
            for ci in range(r.rowCount()):
                c = r.child(ci)
                if c is not None and Qt.CheckState(c.checkState()) == Qt.CheckState.Checked:
                    paths.append(c.cover_path)
        return paths
 
    @override
    def currentChanged(self, current, previous):
        if (iss := self.__index_issue(current)) == 0:
            m = current.model()
            #print(f'Creating thumbnail(s) for {parent_size}...')
            signal = self.coverChanged if current.parent().isValid() else self.rootCoverChanged
            #print(f"Loading thumbnail for child at row {current.row()} to parent row {current.parent().row()}")
            s, pm = BookCoverItemModel.loadCover(m, current)
            signal.emit(s,pm.pixmap(s))
        elif iss != 2: self.__print_index_issue(iss,current,'currentChanged arg for current index')
        super().currentChanged(current,previous)

    @override
    def rowsInserted(self,pindex,start,end):
        self.resizeColumnToContents(1)
        super().rowsInserted(pindex,start,end)

