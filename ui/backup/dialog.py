from calibre_plugins.cover_backup.base import book_info,BackupStatus,BackupTask,session_base
from calibre_plugins.cover_backup.ui.cover_dialog import BookCoverItemModel,CoverDataRole,BookCoverItem,CoverListView,PreviewWidget,StyledBookCoverDelegate,prepareCoverWidgets,swapViewerModel
from qt.core import (Qt,QCheckBox,QWidget,QComboBox,QHBoxLayout,QDialog,QDialogButtonBox,QPushButton,QVBoxLayout,QLabel,QButtonGroup,pyqtSignal)
from enum import IntEnum
from dataclasses import dataclass
from typing import override
# TODO: Implement selection dialog and multiple choice enum
'''
class ResolutionChoice(IntEnum):
    Skip = 1
    Create = 2
    Overwrite = 3
''' 
class GlobalChoice(IntEnum):
    NoGlobal = 1
    Single = 2
    Multi = 3
    All = 4

@dataclass
class ConflictChoice:
    #action: ResolutionChoice
    action: BackupStatus
    scope: GlobalChoice


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
        self.ow_choices.addItem('any',userData=GlobalChoice.All)
        self.ow_choices.addItem('one',userData=GlobalChoice.Single)
        self.ow_choices.addItem('multiple',userData=GlobalChoice.Multi)
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
        return self.ow_choices.currentData() if self.check.isChecked() else GlobalChoice.NoGlobal

class BackupDialog(QDialog):
    resolved = pyqtSignal(QDialog.DialogCode, ConflictChoice)
    def __init__(self,parent=None):
        QDialog.__init__(self,parent)
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
        #setattr(self,name,b := QPushButton())
        b = QPushButton()
        b.setText(label)
        b.setCheckable(True)
        self.layout().addWidget(b)
        self.conflict_buttons.addButton(b,std.value)
        return b
    def startPrompt(self,prompt,hasNext):
        self.setResult(0)
        book = prompt.book
        self.msg.setText(f"{book.title}, by {', '.join(book.authors)} has existing backup(s).")
        self.setWindowTitle(f'"{book.title}" Backup Conflict')
        self.confirm_buttons.setHasNext(hasNext)
        self.open()

    @property
    def decision(self):
        d = self.conflict_buttons.checkedId()
        # No action taken, return None
        if d == -1: return None
        return ConflictChoice(d,self.confirm_buttons.ow_choice)

    @override
    def accept(self):
        if (d := self.decision) is not None:
            self.resolved.emit(QDialog.DialogCode.Accepted,d)
            super().accept()

    @override
    def reject(self):
        self.resolved.emit(QDialog.DialogCode.Rejected,ConflictChoice(BackupStatus.Abort,GlobalChoice.All))
        super().reject()

class MultiBackupDialog(BackupDialog):
    def __init__(self,parent=None):
        BackupDialog.__init__(self,parent)
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
    def startPrompt(self,db,prompt,hasNext):
        prepareCoverWidgets(db,prompt.book,self.viewer,self.preview)
        super().startPrompt(prompt,hasNext)



