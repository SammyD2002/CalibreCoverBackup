from PyQt6.QtWidgets import QDialog,QLabel,QWidget,QFrame,QGridLayout,QHBoxLayout,QListWidget,QListWidgetItem,QRadioButton,QListView,QStyledItemDelegate,QButtonGroup,QAbstractItemView,QCheckBox,QToolButton,QDialogButtonBox
from PyQt6.QtCore import Qt,QBuffer,QByteArray,QIODevice,pyqtSignal
from PyQt6.QtGui import QImage,QPixmap,QImage,QIcon,QPixmapCache
from PyQt6 import sip 
from gc import get_referrers
from dataclasses import dataclass,field
from enum import IntEnum
from typing import override
from os import path
from sys import getrefcount
@dataclass
class book_info:
    book_id:int
    title:str
    authors:list[str]

class BackupStatus(IntEnum):
    Initial = 0
    Pending = 1
    Write = 3
    Overwrite = 4
    Skip = 5

@dataclass
class BackupTask(book_info):
    # The target path
    backup_path: PathLike
    # Detected paths containing existing backups. Can be set later
    ext_paths: list[PathLike] = field(default_factory=list)
    # Task Status
    status: BackupStatus = BackupStatus.Initial
    unique: bool = True
    def __post_init__(self):
        DN = f'{self.book_id}_{self.title}' if any(self.authors == a for a in ['','Unknown']) else f'{self.book_id}_{self.title} [{', '.join(self.authors)}]'
        self.backup_path = path.abspath(path.join(self.backup_path, DN + '.jpg'))

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

class LinkedButton(QRadioButton):
    def __init__(self,item,text=None,parent=None):
        QRadioButton.__init__(self,text,parent)
        self.item = item


class ModelRow(QListWidgetItem):
    def __cleanup(self):
        # Ensure that references are cleared. 
        self.__image = self.__pixmap = None
    def __init__(self,p,parent_list):
        QListWidgetItem.__init__(self,parent_list)
        self.setData(Qt.ItemDataRole.UserRole,p)
        #lw.setText(path.basename(p))
        self.button = LinkedButton(self,path.basename(p)) 
        parent_list.setItemWidget(self,self.button)
        self.ipath = p
        #self.__picture = QPicture()
        self.__image = QImage()
        self.__pixmap = None
        self.__thumbnails = dict()
        parent_list.destroyed.connect(lambda: print('parent_list destroyed'))
        parent_list.destroyed.connect(self.__cleanup)
    @property
    def image(self):
        if self.__image.isNull():
            loaded = self.__image.load(self.data(Qt.ItemDataRole.UserRole),format=None) 
            print(f'Loaded QImage {self.ipath}:', loaded)
        return self.__image
    @property
    def pixmap(self):
        if self.__pixmap is None:
            img = self.image
            if not img.isNull(): self.__pixmap = QPixmap.fromImage(img)
        return self.__pixmap
    @override
    def setCheckState(self,state):
        self.button.setChecked(state == Qt.CheckState.Checked)
    def loadThumbnail(self, size):
        h,w = (size.height(),size.width())
        hdict = self.__thumbnails.setdefault(h,dict())
        if (pm := hdict.get(w)) is None: hdict[w] = pm = self.pixmap.scaled(size,Qt.AspectRatioMode.KeepAspectRatio)
        else: print('Loaded from cache')
        print(f'Loaded pixmap of size : {pm.size()}')
        return pm

class ImageSelect(QDialog): 
    book_loaded = pyqtSignal()
    def __init__(self,book=None,parent=None):
        QWidget.__init__(self,parent)
        self.book = book
        #self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        #self.frame = layout.addWidget(QFrame(),2,0,-1,2)
        #self.list = QListWidget(self.frame)
        self.__init__widgets()
        if book is not None: self.loadBook(book)
    def __init__widgets(self):
        layout = QGridLayout()
        self.book_msg = QLabel(f"")
        layout.addWidget(self.book_msg,0,0,1,1)
        self.select_msg = QLabel("Please select a backup to restore.")
        layout.addWidget(self.select_msg, 1,0,1,1)
        self.button_box = QDialogButtonBox()
        self.ok = self.button_box.addButton(QDialogButtonBox.StandardButton.Ok)
        self.skip = self.button_box.addButton(QDialogButtonBox.StandardButton.Discard)
        self.skip.setText("Skip")
        self.skip.setIcon(QIcon.fromTheme(QIcon.ThemeIcon.MediaSeekForward))
        self.cancel = self.button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        self.button_box.clicked.connect(lambda b: self.done(self.button_box.buttonRole(b).value))
        layout.addWidget(self.button_box,3,1,1,1)
        self.list = QListWidget() 
        layout.addWidget(self.list,2,0,1,1)
        self.preview = QLabel("Image Preview")
        layout.addWidget(self.preview,2,1,1,1)
        self.rm_others = QCheckBox("Delete other backups")
        layout.addWidget(self.rm_others,3,0,1,1)
        self.setLayout(layout)
        self.book_loaded.connect(lambda: self.list.setCurrentRow(0))
        self.book_loaded.connect(self.show,Qt.ConnectionType.QueuedConnection)
        print('Initial size:',self.size())

    def loadBook(self,book):
        self.book = book
        self.book_msg.setText(f"Multiple backups exist for {self.book.title} [{self.book.book_id}].")
        self.buttons = QButtonGroup(self)
        self.buttons.setExclusive(True)
        for p in self.book.ext_paths:
            lw = ModelRow(p,self.list)
            self.buttons.addButton(lw.button)
            self.list.addItem(lw)
        self.__update_connection = self.list.currentItemChanged.connect(self.update_selected,Qt.ConnectionType.QueuedConnection)
        self.book_loaded.emit()

    def update_selected(self,curr,prev):
        curr.setCheckState(Qt.CheckState.Checked)
        print(self.size())
        self.preview.setPixmap(curr.loadThumbnail(self.size() / 2))

    def reset(self):
        self.decision = None
        self.preview.clear()
        self.list.currentItemChanged.disconnect(self.__update_connection)
        self.list.clear()
        bts = self.buttons
        self.buttons = None
        bts.deleteLater()
        #if self.__update_connection is not None: self.__update_connection.disconnect()

    @override
    def resizeEvent(self, event):
        if (curr := self.list.currentItem()) is not None:
            self.preview.setPixmap(curr.loadThumbnail(event.size()/2))


    @override
    def done(self,res):
        cb = self.buttons.checkedButton()
        #img = QByteArray()
        #writer = QBuffer(img)
        #writer.open(QIODevice.OpenModeFlag.ReadWrite)
        #img_pixmap = cb.item.pixmap
        #print('NULL:',img_pixmap.isNull())
        #print('VALID',img_pixmap.isValid())
        #img_pixmap.save(writer) 
        #print(writer.data())
        #writer.close()
        #print(img)
        self.decision = PromptResult(res,(cb.item.data(Qt.ItemDataRole.UserRole),cb.item.image.copy()), [p.item.data(Qt.ItemDataRole.UserRole) for p in self.buttons.buttons() if p != cb],self.rm_others.isChecked())
        QDialog.done(self,res)
