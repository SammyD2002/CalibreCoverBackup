from calibre_plugins.cover_backup.base import book_info,BackupStatus,BackupTask
from qt.core import QStyleOptionViewItem,QStyledItemDelegate,QStyle,QStyleOptionButton,Qt,QVariant,QIcon,QStandardItem, QStandardItemModel, QPixmap
from enum import IntEnum
from os import path
from typing import override
def pigeon_pairing(i,j):
    pl = 0
    num = 0
    while i != 0 or j != 0:
        if i % 2: num += 2 ** pl
        if j % 2: num += 2 ** (pl + 1)
        i = i // 2
        j = j // 2
        pl += 2
    return num
class StyledBookCoverDelegate(QStyledItemDelegate):
    '''
    def __init__(self,parent=None):
        QStyledItemDelegate.__init__(self,parent)
    @override
    def paint(self,painter,option,index):
        #print(type(d))
        self.initStyleOption(option,index)
        #if isinstance(d,QVariant)
        #if option.features
        print(option.features)
        option.features &= ~QStyleOptionViewItem.ViewItemFeature.HasCheckIndicator
        super().paint(painter,option,index)
        # Button style
        button = QStyleOptionButton()
        style = option.widget.style()
        button.rect = style.subElementRect(QStyle.SubElement.SE_ItemViewItemCheckIndicator,option,option.widget)
        button.state = option.state | (QStyle.StateFlag.State_On if option.showDecorationSelected else QStyle.StateFlag.State_Off)
        #txt_rect = style.subElementRect(QStyle.SubElement.SE_ItemViewItemText,option,option.widget)
        #print(style)
        #painter.drawText(txt_rect,Qt.AlignmentFlag.AlignLeft,f'Hello {index.row()},{index.column()}')
        style.drawControl(QStyle.ControlElement.CE_RadioButton,button,painter,option.widget)
    '''
    @override
    def initStyleOption(self,option, index):
        super().initStyleOption(option,index)
        #print(option)
        #print(option.features)
        #print(option.showDecorationSelected)
        #option.state |= QStyle.StateFlag.State_On if option.showDecorationSelected else QStyle.StateFlag.State_Off
        option.checkState  = Qt.CheckState.Unchecked if (cs := index.data(Qt.ItemDataRole.CheckStateRole)) is None else cs
        #option.state |= QStyle.StateFlag.State_Enabled
        



class BookCoverItemModel(QStandardItemModel):
    def __init__(self,parent=None):
        QStandardItemModel.__init__(self,parent)
    # src.data(args,role)
    # src.setData(args,data,role)
    @staticmethod
    def loadCover(src,*args,pm = None):
        s = None
        icn = src.data(*args,Qt.ItemDataRole.DecorationRole)
        if icn.isNull():
            if pm is None: 
                pm = QPixmap(f := src.data(*args,CoverDataRole.PathRole))
                print(f'Loading Pixmap from {f}...')
            else:
                print(f'Loading icon directly from provided pixmap...')
            icn.addPixmap(pm)
            src.setData(*args,s := pm.size(),CoverDataRole.SizeRole)
            print(f'loadCover: Initialized cover of size {s}') 
            src.setData(*args,icn,Qt.ItemDataRole.DecorationRole)
        else: s = src.data(*args,CoverDataRole.SizeRole)
        return s,icn
    '''
    @staticmethod 
    def loadThumbnail(src,*args,target):
        print(f'Loading Thumbnail for size {target}')
        base,icn = BookCoverItemModel.loadCover(src,*args)
        print(f'Loaded cover size {base}')
        icn_size = base.scaled(target,Qt.AspectRatioMode.KeepAspectRatio)
        print(f'Scaling to {icn_size}')
        if icn_size not in icn.availableSizes():
            icn.addPixmap(pm := icn.pixmap(base).scaled(icn_size))
            src.setData(*args,icn,Qt.ItemDataRole.DecorationRole)
            #icn.addPixmap(pm := icn.pixmap(base).scaled(icn_size,Qt.AspectRatioMode.IgnoreAspectRatio))
            return pm
        else: return icn.pixmap(icn_size)
    '''


class CoverDataRole(IntEnum):
    PathRole = Qt.ItemDataRole.UserRole.value + 1
    SizeRole = Qt.ItemDataRole.UserRole.value + 2

class BookCoverItem(QStandardItem):
    def __init__(self,cv_path=None):
        QStandardItem.__init__(self)
        print(f"Making book cover from {type(cv_path)}")
        self.setCheckable(True)
        self.setData(Qt.CheckState.Unchecked,Qt.ItemDataRole.CheckStateRole) 
        self.setData(ic := QIcon(), Qt.ItemDataRole.DecorationRole)
        if cv_path is not None:
            if isinstance(cv_path,QPixmap):
                print(f"Adding pixmap...")
                #ic.addPixmap(cv_path)
                s, icn = BookCoverItemModel.loadCover(self,pm=cv_path)
                self.setData(None, CoverDataRole.PathRole)
                print('Initialized from pixmap to sizes',ic.availableSizes())
                if ic.isNull(): print(f'NOTE: Icon is still invalid!')
            else:
                self.setData(cv_path, CoverDataRole.PathRole)
                self.setData(path.basename(cv_path),Qt.ItemDataRole.DisplayRole)


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

