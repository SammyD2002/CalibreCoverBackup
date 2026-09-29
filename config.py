#from qt.core import QHBoxLayout, QLabel, QLineEdit, QWidget, QStandardPaths, QUrl
from qt.core import Qt, QWidget, QGridLayout, QLabel, QPushButton,  QFileDialog, QUrl, QStandardPaths, QCheckBox, QMessageBox
from os import path
from calibre.utils.config import JSONConfig

# This is where all preferences for this plugin will be stored
# Remember that this name (i.e. plugins/interface_demo) is also
# in a global namespace, so make it as unique as possible.
# You should always prefix your config file name with plugins/,
# so as to ensure you don't accidentally clobber a calibre config file
prefs = JSONConfig('plugins/cover_backup')

# Set defaults
#prefs.defaults['hello_world_msg'] = 'Hello, World!'
prefs.defaults['backup_path'] = path.join(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation),'Covers')
class ConfigWidget(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self.layout = QGridLayout(self)
        self.make_widgets()
        self.load_settings()

    def make_widgets(self):
        # Make File Select and Button Label widgets
        l = QLabel("Backup Directory")
        l.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.file_button = QPushButton("Choose Directory...")
        self.file_button.clicked.connect(self.file_button_clicked)
        self.layout.addWidget(l,0,0,1,2)
        self.layout.addWidget(self.file_button,1,0,1,2)

    def file_button_clicked(self):
        self.path = QFileDialog.getExistingDirectoryUrl(self,
                                                    'Select Cover Backup Directory...',
                                                    self.path)
    @property
    def path(self):
        return self.__path
    @path.setter
    def path(self,npath):
        if npath is None or len(npath.toLocalFile()) == 0: return
        self.__path = npath
        self.file_button.setText(' ' + npath.toLocalFile() + ' ')
    def load_default_path(self):
        return prefs['backup_path']
    def load_settings(self):
        self.path = QUrl.fromLocalFile(prefs['backup_path'])
    def save_settings(self):
        prefs['backup_path'] = self.path.toLocalFile()
'''
class CoverBackupSettings(CoverRestoreSettings):
    def __init__(self):
        CoverRestoreSettings.__init__(self)
    @override
    def make_widgets(self):
        super().make_widgets()
        self.overwrite_box = QCheckBox('Overwrite Existing Backups?')
        self.overwrite_box.setTristate(True)
        self.layout.addWidget(self.overwrite_box, 2,0,1,2)
    @property
    def overwrite(self):
        state = self.overwrite_box.checkState()
        if state == Qt.CheckState.Unchecked: return False
        elif state == Qt.CheckState.Checked: return True
        else: return None
    @overwrite.setter
    def overwrite(self,state):
        if state is False: self.overwrite_box.setCheckState(Qt.CheckState.Unchecked)
        elif state is True: self.overwrite_box.setCheckState(Qt.CheckState.Checked)
        else: self.overwrite_box.setCheckState(Qt.CheckState.PartiallyChecked)
    @override
    def save_settings(self):
        settings = super().save_settings()
        settings['Overwrite'] = self.overwrite
        return settings
    @override
    def load_settings(self, settings):
        super().load_settings(settings)
        self.overwrite = settings.get('Overwrite', CoverBackupSettings.DEFAULTS['Overwrite'])

CoverBackupSettings.DEFAULTS = dict(**CoverRestoreSettings.DEFAULTS, Overwrite=None)
'''
