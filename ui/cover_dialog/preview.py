from qt.core import QTreeView ,QApplication,QGridLayout,QLabel,QMainWindow,QWidget,QSizeF,QButtonGroup,QRadioButton,QHeaderView,QHBoxLayout,QVBoxLayout,QDialog, QBoxLayout,QSizePolicy,QPixmap,QIcon,QPainter,pyqtSignal,QSize,Qt
from calibre_plugins.cover_backup.ui.cover_dialog.cover_model import BookCoverItem,BookCoverItemModel,StyledBookCoverDelegate
from sys import argv
from typing import override
from dataclasses import dataclass,field
from enum import IntEnum
from os import path
import glob
class LabeledImage(QWidget):
    class __internal_img(QLabel):
        def __init__(self,parent=None):
            QLabel.__init__(self,parent)
            self.pm = QPixmap()
            self.setMinimumSize(1,1)
            self.setScaledContents(False)
        def scaledPixmap(self):
            if self.pm.isNull(): return self.pm
            return self.pm.scaled(self.size(),Qt.AspectRatioMode.KeepAspectRatio)
        @override
        def resizeEvent(self,event):
            if not self.pm.isNull(): super().setPixmap(self.scaledPixmap())
        @override
        def sizeHint(self):
            w = self.width()
            return QSize(w,self.heightForWidth(w))
        @override
        def heightForWidth(self,width):
            if self.pm.isNull(): return width
            return int((self.pm.height() / self.pm.width()) * width)
        @override
        def clear(self):
            super().clear()
            self.img_size = None
        @override
        def setPixmap(self,pixmap):
            self.pm.swap(pixmap)
            del pixmap
            super().setPixmap(self.scaledPixmap())

    def __init__(self,txt,parent=None):
        QWidget.__init__(self,parent)
        self.setLayout(layout := QVBoxLayout())
        self.label = QLabel(txt)
        layout.addWidget(self.label)
        self.preview = LabeledImage.__internal_img(self)
        layout.addWidget(self.preview)
        layout.addStretch()
        self.img_bsize = QSize()
        layout.setStretchFactor(self.preview,1)

class PreviewWidget(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self,parent)
        self.setLayout(layout := QBoxLayout(QBoxLayout.Direction.TopToBottom))
        self.__ccover = LabeledImage("Current Cover Image",self)
        layout.addWidget(self.__ccover)
        self.__bcover = LabeledImage("Selected Backup Image",self)
        layout.addWidget(self.__bcover)
    @override
    def resizeEvent(self,event):
        event.accept()
        cd = self.layout().direction()
        s = event.size().toSizeF()
        b1 = QSizeF(self.__csize)
        b2 = QSizeF(self.__bsize)
        # Calculate space needed for scaled images in landscape orientation
        landscape = QSizeF(b1.width() + b2.width(),max(b1.height(),b2.height()))
        sl = landscape.scaled(s,Qt.AspectRatioMode.KeepAspectRatio)
        lsfactor = sl.width() / landscape.width()
        ls_avg = ((b1 * lsfactor) + (b2 * lsfactor)) / 2.0
        # Do the same for portrait orientation        
        portrait = QSizeF(max(b1.width(),b2.width()), b1.height() + b2.height())
        sp = portrait.scaled(s,Qt.AspectRatioMode.KeepAspectRatio)
        ptfactor = sp.width() / portrait.width()
        pt_avg = ((b1 * ptfactor) + (b2 * ptfactor)) / 2.0
        if (ls_avg.width() * ls_avg.height()) > (pt_avg.width() * pt_avg.height()): 
            if cd != QBoxLayout.Direction.LeftToRight: self.layout().setDirection(QBoxLayout.Direction.LeftToRight)
        else:
            if cd != QBoxLayout.Direction.TopToBottom: self.layout().setDirection(QBoxLayout.Direction.TopToBottom)
    def updateBackup(self,size,backup):
        #print('Preview Widget Size:',self.size())
        if backup is not None:
            self.__bcover.preview.setPixmap(backup)
            self.__bsize = size
            #self.__bcover.resize(size.scaled())
        else:
            self.__bcover.setImage()
            self.__bsize = None
    def updateCurrent(self,size,current):
        if current is not None: 
            self.__ccover.preview.setPixmap(current)
            self.__csize = size
        else:
            self.__ccover.setImage()
            self.__csize = None

