from calibre.gui2.actions import InterfaceAction
from calibre_plugins.cover_backup.ui.backup import backup_interactive
from calibre_plugins.cover_backup.base.restore import restore_noninteractive
from calibre.gui2.threaded_jobs import ThreadedJob
from PyQt6.QtCore import QThread
import traceback
# Suppresses exceptions and prints them to log.
def suppress(fn,abort=None,log=None,notifications=None):
    def nfn(*args,**kwargs):
        try:
            return fn(*args,**kwargs)
        except:
            #kwargs['log'].error(f'Suppressed Exception {e}!')
            kwargs['log'].error(traceback.format_exc())
            kwargs['notifications'].put_nowait((1,'ERROR!'))
    return nfn
class CoverBackupPlugin(InterfaceAction):
    name = 'Cover Backup Plugin'
    # Declare the main action associated with this plugin
    # The keyboard shortcut can be None if you don't want to use a keyboard
    # shortcut. Remember that currently calibre has no central management for
    # keyboard shortcuts, so try to use an unusual/unused shortcut.
    action_spec = ('Backup Cover(s)', None, "Create a backup of each book's cover", None)
    action_add_menu = True
    action_menu_clone_qaction = 'Backup Selected Cover(s)'
    def genesis(self):
        # Read backup_path from prefs
        from calibre_plugins.cover_backup.config import prefs
        self.backup_path = prefs['backup_path']
        # This method is called once per plugin, do initial setup here
        # Connect backup action to start_backup()
        self.qaction.triggered.connect(self.start_backup)
        # Create and connect restore action to start_restore()
        self.restore = self.create_menu_action(self.qaction.menu(),'smfincher.cover_restore', 'Restore Cover(s)',triggered=self.start_restore)
        # Connect configure action to configure()
    def __job_finished(self,j,ids,prev):
        print(f'Finished restoring {ids}')
        current = self.gui.library_view.currentIndex()
        self.gui.library_view.model().refresh_ids(ids)
        if self.gui.cover_flow: self.gui.cover_flow.dataChanged()
        self.gui.library_view.model().current_changed(current, prev)

    def start_backup(self):
        ids = self.gui.library_view.get_selected_ids()
        db = self.gui.current_db.new_api # Get current db
        print('t1:',int(QThread.currentThreadId()))
        session = backup_interactive(ids,db, self.backup_path, self.gui) # Create session object
        session.destroyed.connect(self.db_session_destroyed) # Debug that ensured a session object is actually destroyed.
        job = ThreadedJob('cover_backup','Back up the covers of the selected books.',
            suppress(backup_interactive.process),
            [session],
            dict(), lambda j:j) # Create job object
        self.gui.job_manager.run_threaded_job(job) # Start job

    def db_session_destroyed(self):
        print('Detected a session was destroyed.')

    def start_restore(self):
        ids = self.gui.library_view.get_selected_ids()
        api = self.gui.current_db.new_api
        session = restore_noninteractive(db=api,ids=ids,ow_mode=False,backup_path=self.backup_path) 
        job = ThreadedJob('cover_backup','Back up the covers of the selected books.',
            suppress(restore_noninteractive.process),
            [session],
            dict(), lambda j,prev=self.gui.library_view.currentIndex():self.__job_finished(j,ids,prev)) # Create job object
        self.gui.job_manager.run_threaded_job(job) # Start job

    def apply_settings(self):
        from calibre_plugins.cover_backup.config import prefs

        # In an actual non trivial plugin, you would probably need to
        # do something based on the settings in prefs
        self.backup_path = prefs['backup_path']
