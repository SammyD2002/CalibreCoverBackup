from calibre_plugins.cover_backup.base import BackupStatus,Resolution
from calibre_plugins.cover_backup.backup import BackupResolution,BackupResult
from calibre_plugins.cover_backup.base.prompt_handler import prompt_handler
from calibre_plugins.cover_backup.ui import ActionButtonMixin,CustomPushButton
from calibre_plugins.cover_backup.ui.cover_dialog import CoverListView,PreviewWidget,prepareCoverWidgets,swapViewerModel,CoverSelectDialog
from typing import override
from queue import Queue,Empty,ShutDown
from qt.core import (Qt,QObject,QWidget,QCheckBox,QComboBox,QDialog,QDialogButtonBox,QPushButton,QHBoxLayout,QVBoxLayout,QLabel,QButtonGroup,pyqtSignal,QSizePolicy)
# Test prompt and handler. Will always skip backups with conflicts.
class DummyPrompt(QObject):
    finished = pyqtSignal(int)
    def __init__(self,book,parent=None):
        super().__init__(parent)
        self.book = book
    def open(self):
        self.finished.emit(BackupStatus.Skip)

class DummyHandler(prompt_handler):
    @override
    def _startPrompt(self,book):
        self.log.debug('Starting prompt with book',book)
        return DummyPrompt(book)
    @override
    def _finishPrompt(self,result,prompt):
        self.log.debug('CALLED __finishPrompt for book_id', int(prompt.book.book_id))
        br = BackupResolution(Resolution.Scope.All,BackupStatus.Skip,book=prompt.book.book_id)
        self.log.debug('Finished prompt with result', result, 'with resolution settings', f'SCOPE={br.scope},ACTION={br.action},BOOK={br.book},PATHS={br.paths}')
        return br

    '''
class ChoiceBox(QWidget):
    def __init__(self,parent=None):
        QWidget.__init__(self,parent)
        self.setLayout(layout := QHBoxLayout())
        #self.__init__ow_box()
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
    '''

class BackupButtonMixin(ActionButtonMixin):
    @override
    def make_resolution(self):
        return BackupResolution(Resolution.Scope.All,self.group().id(self),book=self.parent().book.book_id) 

ActionButton = type('ActionButton',(BackupButtonMixin,QPushButton),{})

class BuddyLabel(QLabel):
    @override
    def mousePressEvent(self,event):
        if self.buddy() is not None: self.buddy().toggle()
        super().mousePressEvent(event)
class BoxButton(BackupButtonMixin,CustomPushButton):
    '''
    Used if there are more books to be handled; does this by adding the checkbox and combo box.
    '''
    def __init__(self,label:str,*gl_opts:*tuple[opt_text,opt_role],parent=None):
        if len(gl_opts) % 2 != 0: raise ValueError('Passed odd number of options for gl_opts.')
        CustomPushButton.__init__(self,label,parent)
        lay = self.layout()
        lay.addWidget(ow := QWidget())
        ow.setLayout(l2 := QHBoxLayout())
        l2.addWidget(cb := QCheckBox(""))
        cb.setEnabled(False)
        self.__gl_box = cb
        l2.addWidget(lb1 := BuddyLabel('Do this for all titles with'))
        lb1.setBuddy(cb)
        l2.addWidget(cc := QComboBox())
        l2.addWidget(QLabel("existing backup(s)."))
        l2.addStretch()
        cc.setEnabled(False)
        self.__ch_box = cc
        self.gl_choices = cc
        self.toggled.connect(cb.setEnabled)
        self.toggled.connect(cc.setEnabled) 
        for ib in range(0,len(gl_opts),2): self.gl_choices.addItem(gl_opts[ib],userData=gl_opts[ib+1])
    
    @ActionButtonMixin.gl_scope.getter
    def gl_scope(self):
        return self.__ch_box.currentData() if self.__gl_box.isChecked() else None
    
    @override
    def make_resolution(self):
        # Get button id
        return BackupResolution(Resolution.Scope.All,self.group().id(self),book=self.parent().book.book_id) if (gl := self.gl_scope) is None else BackupResolution(gl, self.group().id(self))

class CoverSelectButton(ActionButtonMixin,CustomPushButton):
    def __init__(self,label,parent=None,*,select_label="Select Backups"): 
        super().__init__(label,parent)
        self.cs_dialog = None
        clay = self.layout()
        self.cs_button = QPushButton()
        clay.addWidget(cs := self.cs_button)
        cs.pressed.connect(self.show_cover_select)
        self.__paths = []
        self.updateSelectLabel(select_label)
        cs.setEnabled(False)
        self.toggled.connect(cs.setEnabled)
    
    def show_cover_select(self):
        #print('Opening cover dialog')
        if self.cs_dialog is None:
            self.cs_dialog = CoverSelectDialog(self.parent().book,self.parent(),multi=True)
            self.cs_dialog.finished.connect(self.cover_dialog_finished)
        self.cs_dialog.setResult(QDialog.DialogCode.Rejected)
        self.cs_dialog.open()

    def cover_dialog_finished(self,result):
        #print('Cover select dialog finished with result',result)
        if result == QDialog.DialogCode.Rejected: self.cs_dialog.viewer.model().revert()
        else: 
            if self.cs_dialog.viewer.model().submit(): self.paths = self.cs_dialog.viewer.selectedPaths()
    
    def updateSelectLabel(self,base=None):
        if base is not None: self.__cs_base = base
        self.cs_button.setText(self.tr(f'{self.__cs_base} ({len(self.__paths)} selected currently)...'))

    @property
    def paths(self):
        return self.__paths

    @paths.setter
    def paths(self,paths:list[str]):
        self.__paths = paths
        self.updateSelectLabel()

    @override
    def inputValid(self):
        return len(self.__paths) > 0

    @override
    def make_resolution(self):
        return BackupResolution(Resolution.Scope.All,self.group().id(self),book=self.parent().book.book_id,paths=self.__paths)

class BackupDialog(QDialog):
    def __init__(self,book,hasNext,parent=None):
        QDialog.__init__(self,parent)
        self.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Minimum)
        self.setModal(True)
        book.setParent(self)
        self.book = book
        self.hasNext = hasNext
        self.setLayout(layout := QVBoxLayout())
        self.msg = QLabel()
        layout.addWidget(self.msg)
        self._init__choices()
        self._init__confirm()
        self.layout().addStretch()
    def _init__choices(self):
        self.conflict_buttons = QButtonGroup(self)
        self.conflict_buttons.setExclusive(True)
        self.create = self.__add_choice(BackupStatus.Write,"&Create New Backup, Keep Existing Backups")
        self.skip = self.__add_choice(BackupStatus.Skip,"&Skip Backup")
        self.ow_all = self.__add_choice(BackupStatus.Overwrite,"Create New Backup, &Delete Existing Backup(s)")
        self.create.setChecked(True)
    def _init__confirm(self):
        self.confirm_buttons = cb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        cb.accepted.connect(self.accept)
        cb.rejected.connect(self.reject)
        self.layout().addWidget(self.confirm_buttons) 
    def __add_choice(self, std, label):
        b = BoxButton(label,'any',Resolution.Scope.All,'one',Resolution.Scope.Single,'multiple',Resolution.Scope.Multi) if self.hasNext else ActionButton(label)
        b.setCheckable(True)
        self.layout().addWidget(b)
        self.conflict_buttons.addButton(b,std.value)
        return b
    @override
    def accept(self):
        if self.conflict_buttons.checkedId() != -1 and self.conflict_buttons.checkedButton().inputValid(): super().accept()
    @override
    def open(self):
        self.setResult(0)
        # TODO: Get single path and display cover vs current cover
        self.msg.setText(f"{self.book.title}, by {', '.join(self.book.authors)} has existing backup(s).")
        self.setWindowTitle(f'"{self.book.title}" Backup Conflict')
        #self.confirm_buttons.setHasNext(self.hasNext)
        super().open()
    
    def make_resolution(self):
        if self.result() == QDialog.DialogCode.Rejected: return BackupResolution(Resolution.Scope.All,BackupStatus.Abort,book=self.book.book_id)
        elif (action := self.conflict_buttons.checkedId()) == -1: return None
        else: return self.conflict_buttons.checkedButton().make_resolution()
        #elif (gl_scope := self.confirm_buttons.ow_choice) is None: return BackupResolution(Resolution.Scope.All,action,book=self.book.book_id)
        #else: return Resolution(gl_scope,action)

    @override
    def reject(self):
        #self.resolved.emit(QDialog.DialogCode.Rejected,ConflictChoice(BackupStatus.Abort,GlobalChoice.All))
        super().reject()

class MultiBackupDialog(BackupDialog):
    @override
    def _init__choices(self):
        super()._init__choices()
        self.layout().addWidget(cs_button := CoverSelectButton("Create new backup, &replace selected backup(s)",self))
        cs_button.setCheckable(True)
        self.conflict_buttons.addButton(cs_button,BackupStatus.Overwrite)
    def clearModel(self):
        swapViewerModel(self.viewer,None)

 
class BackupPromptHandler(prompt_handler):
    @override
    def _startPrompt(self,book):
        args = (book,book.book_id != self.last_id,self.parent())
        d = MultiBackupDialog(*args) if (multi := (len(book.ext_paths)) > 1) else BackupDialog(*args)
        # Set constructor args if depending on if viewing dialog for one or multiple existing backups.
        return d

    @override
    def _finishPrompt(self,result,prompt):
        return prompt.make_resolution()
