#from calibre_plugins.cover_backup.base import book_info,BackupStatus,BackupTask,session_base
from calibre_plugins.cover_backup.base import BackupStatus,Resolution
from calibre_plugins.cover_backup.base.backup import BackupResolution
from calibre_plugins.cover_backup.ui.cover_dialog import BookCoverItemModel,CoverDataRole,BookCoverItem,CoverListView,PreviewWidget,StyledBookCoverDelegate,prepareCoverWidgets,swapViewerModel
from qt.core import (Qt,QCheckBox,QWidget,QComboBox,QHBoxLayout,QDialog,QDialogButtonBox,QPushButton,QVBoxLayout,QLabel,QButtonGroup,pyqtSignal)
from enum import IntEnum
from dataclasses import dataclass
from typing import override

# TODO: Implement selection dialog and multiple choice enum
class ChoiceBox(QWidget):
    def __init__(self,parent=None):
        QWidget.__init__(self,parent)
        self.setLayout(layout := QHBoxLayout())
        self.check = QCheckBox("")
        layout.addWidget(self.check)
        self.__init__ow_box()
        self.choices = QDialogButtonBox()
        self.choices.setStandardButtons(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(self.choices)
    def __init__ow_box(self):
        self.__l1 = QLabel('Do this for all books with')
        self.__l2 = QLabel("existing backup(s).")
        self.layout().addWidget(self.__l1)
        self.ow_choices = QComboBox()
        self.ow_choices.addItem('any',userData=Resolution.Scope.All)
        self.ow_choices.addItem('one',userData=Resolution.Scope.Single)
        self.ow_choices.addItem('multiple',userData=Resolution.Scope.Multi)
        self.ow_choices.setCurrentIndex(0)
        self.layout().addWidget(self.ow_choices)
        self.layout().addWidget(self.__l2)
    def setHasNext(self,hn):
        visible = not hn
        self.check.setHidden(visible)
        self.ow_choices.setHidden(visible)
        self.__l1.setHidden(visible)
        self.__l2.setHidden(visible)
    @property
    def ow_choice(self):
        return self.ow_choices.currentData() if self.check.isChecked() else None

class BackupDialog(QDialog):
    def __init__(self,book,hasNext,parent=None):
        QDialog.__init__(self,parent)
        book.setParent(self)
        self.book = book
        self.isLast = isLast
        self.setLayout(layout := QVBoxLayout())
        self.msg = QLabel()
        layout.addWidget(self.msg)
        self._init__choices()
        self._init__confirm()
    def _init__choices(self):
        self.conflict_buttons = QButtonGroup(self)
        self.conflict_buttons.setExclusive(True)
        self.create = self.__add_choice(BackupStatus.Write,"&Create New Backup, Keep Existing Backups")
        self.skip = self.__add_choice(BackupStatus.Skip,"&Skip Backup")
        self.ow_all = self.__add_choice(BackupStatus.Overwrite,"Create New Backup, &Delete Existing Backup(s)")
        self.create.setChecked(True)
    def _init__confirm(self):
        self.confirm_buttons = cb = ChoiceBox(self)
        cb.choices.accepted.connect(self.accept)
        cb.choices.rejected.connect(self.reject)
        self.layout().addWidget(self.confirm_buttons) 
    def __add_choice(self, std, label):
        b = QPushButton()
        b.setText(label)
        b.setCheckable(True)
        self.layout().addWidget(b)
        self.conflict_buttons.addButton(b,std.value)
        return b
    
    @override
    def open(self):
        self.setResult(0)
        # TODO: Get single path and display cover vs current cover
        self.msg.setText(f"{self.book.title}, by {', '.join(self.book.authors)} has existing backup(s).")
        self.setWindowTitle(f'"{self.book.title}" Backup Conflict')
        self.confirm_buttons.setHasNext(self.hasNext)
        super().open()
    
    def make_resolution(self):
        if (action := self.conflict_buttons.checkedId()) == -1: return None
        if (gl_scope := self.confirm_buttons.ow_choice) is None: return Resolution(Resolution.Scope.All,action,self.book.book_id)
        else: return Resolution(gl_scope,action)
    @override
    def accept(self):
        if self.conflict_buttons.checkedId() != -1: super().accept()

    @override
    def reject(self):
        #self.resolved.emit(QDialog.DialogCode.Rejected,ConflictChoice(BackupStatus.Abort,GlobalChoice.All))
        super().reject()

class MultiBackupDialog(BackupDialog):
    def __init__(self,book,isLast,parent=None):
        BackupDialog.__init__(self,book,parent)
    
    @override
    def _init__choices(self):
        super()._init__choices()
        self.preview = PreviewWidget(self)
        self.viewer = CoverListView(self.preview,self)
        self.viewer.setItemDelegate(StyledBookCoverDelegate())        
        self.layout().addWidget(self.viewer)
        self.layout().addWidget(self.preview)
        self.viewer.coverChanged.connect(self.preview.updateBackup)

    def clearModel(self):
        swapViewerModel(self.viewer,None)

    @override
    def make_resolution(self):
        res = super().make_resolution()
        if res is None or res.isGlobal(): return res
        # Set res.paths to selected paths.
        res.paths = self.viewer.currentIndex.
        return res

    @override
    def open(self)
        prepareCoverWidgets(self.book,self.viewer,self.preview)
        super().startPrompt()



