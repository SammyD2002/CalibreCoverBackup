from qt.core import (QStyleOptionViewItem,QStyledItemDelegate,QStyle,QStyleOptionButton,Qt,QVariant,QIcon,QLoggingCategory,
                     QStandardItem,QStandardItemModel,QPixmap,QIdentityProxyModel,QModelIndex,QAbstractItemModel,QMessageLogger)
from enum import IntEnum
from os import path
from typing import override
from sys import _getframe

class CoverDataRole(IntEnum):
    PathRole = Qt.ItemDataRole.UserRole.value + 1
    SizeRole = Qt.ItemDataRole.UserRole.value + 2

class BookCoverItemModel(QStandardItemModel):
    def __init__(self,parent=None):
        QStandardItemModel.__init__(self,parent)
    # src.data(args,role)
    # src.setData(args,data,role)
    '''
    @override
    def checkIndex(self,index,opts=QAbstractItemModel.CheckIndexOption.IndexIsValid):
        print('Checking model index',index)
        if index is None:
            if (lc := QLoggingCategory('qt.core.qabstractitemmodel',Qt.MsgType.QtWarningMessage)).isWarningEnabled(): QMessageLogger(__file__,_getframe().f_lineno,'checkIndex',lc).warning('Index is None')
            return False
        return super().checkIndex(index,opts)
    '''         
    @override
    def data(self,index,role=Qt.ItemDataRole.UserRole+1):
        icn = super().data(index,role)
        if role == Qt.ItemDataRole.DecorationRole and icn.isNull() and super().data(index,CoverDataRole.PathRole) is not None:
            pm = QPixmap(f := super().data(index,CoverDataRole.PathRole))
            #print(f'Loading Pixmap from {f}...')
            icn.addPixmap(pm)
            super().setData(index,s := pm.size(),CoverDataRole.SizeRole)
            #print(f'loadCover: Initialized cover of size {s}') 
            super().setData(index,icn,Qt.ItemDataRole.DecorationRole)
        return icn
    @staticmethod
    def loadCover(src,*args,pm = None):
        # TODO: Add kwargs to overidden item data() fn
        s = None
        icn = src.data(*args,Qt.ItemDataRole.DecorationRole)
        if icn.isNull() and pm is not None:
            #print(f'Loading icon directly from provided pixmap...')
            icn.addPixmap(pm)
            src.setData(*args,s := pm.size(),CoverDataRole.SizeRole)
            #print(f'loadCover: Initialized cover of size {s}') 
            src.setData(*args,icn,Qt.ItemDataRole.DecorationRole)
        else: s = src.data(*args,CoverDataRole.SizeRole)
        return s,icn

class CheckProxyModel(QIdentityProxyModel):
    '''
    This model proxies another model and stores changes to an items checkstate in a local dict until they are comitted.
    '''
    def __init__(self,parent=None,src=None):
        super().__init__(parent)
        self.changes = dict()
        if src is not None: super().setSourceModel(src)
    @override
    def setSourceModel(self,model):
        '''
        Clear set changes and load new model.
        '''
        self.changes.clear()
        super().setSourceModel(model) 
    @override
    def data(self,index,role=Qt.ItemDataRole.DisplayRole):
        if self.sourceModel() is None or not index.isValid(): return
        #print(f'Getting data from index {index.row()},{index.column()} for role {role}, with {len(self.checks)} values in checks')
        if role == Qt.ItemDataRole.CheckStateRole and index in self.changes: return self.changes[index]
        return super().data(index,role)
   
    @override
    def setData(self,index,value,role=Qt.ItemDataRole.DisplayRole):
        if self.sourceModel() is None: return False
        #print('Setting data from index',f'{index.row()},{index.column()}','for role',role,'to',value)
        if role == Qt.ItemDataRole.CheckStateRole: 
            #print('Its a check state, so we will be checking it out.')
            self.changes[index] = value
            self.dataChanged.emit(index,index,[Qt.ItemDataRole.CheckStateRole])
        else: super().setData(index,value,role)
        return True

    def submit(self):
        '''
        Returns false if no changes were made or no sourceModel exists to submit changes to.
        '''
        if (m := self.sourceModel()) is None or len(self.changes) == 0: return False
        #print('Current model is not none. Overlay has',len(self.changes),'updates.')
        for pdx,state in self.changes.items():
            idx = self.mapToSource(pdx)
            #print(f'Setting index {idx.row()},{idx.column()} to {state}')
            m.setData(idx,state,Qt.ItemDataRole.CheckStateRole)
        self.changes.clear()
        return True

    def revert(self):
        #print('Reverting Changes...')
        ids = self.changes.keys()
        self.changes.clear()
        # TODO: Replace with version that clumps adjacent changes together and emits all at once.
        for i in ids: self.dataChanged.emit(i,i,[Qt.ItemDataRole.CheckStateRole])

class BookCoverItem(QStandardItem):
    def __init__(self,cv_path=None):
        QStandardItem.__init__(self)
        #print(f"Making book cover from {type(cv_path)}")
        self.setCheckable(True)
        self.setEditable(False)
        self.setData(Qt.CheckState.Unchecked,Qt.ItemDataRole.CheckStateRole) 
        self.setData(ic := QIcon(), Qt.ItemDataRole.DecorationRole)
        if cv_path is not None:
            if isinstance(cv_path,QPixmap):
                #print(f"Adding pixmap...")
                #ic.addPixmap(cv_path)
                s, icn = BookCoverItemModel.loadCover(self,pm=cv_path)
                self.setData(None, CoverDataRole.PathRole)
                #print('Initialized from pixmap to sizes',ic.availableSizes())
                #if ic.isNull(): print(f'NOTE: Icon is still invalid!')
            else:
                self.setData(cv_path, CoverDataRole.PathRole)
                self.setData(path.basename(cv_path),Qt.ItemDataRole.DisplayRole)
                #BookCoverItemModel.loadCover(self) # Load cover into the Item. Comment this line out to skip.
    @property
    def cover_path(self):
        return self.data(CoverDataRole.PathRole)
    @cover_path.setter
    def cover_path(self,p):
        self.setData(p,CoverDataRole.PathRole)
    @property
    def cover_icon(self):
        return BookCoverItemModel.loadCover(self)[1]
    @property
    def base_cover(self):
        size,icn = BookCoverItemModel.loadCover(self)[1]
        return icn.pixmap(size)
    @property
    def base_size(self):
        return BookCoverItemModel.loadCover(self)[0]
    def loadThumbnail(self,target):
        return BookCoverItemModel.loadCover(self,target=target)
    def clone(self):
        return BookCoverItem(self.cover_path)
    @override
    def type(self):
        return QStandardItem.ItemType.UserType + 1


