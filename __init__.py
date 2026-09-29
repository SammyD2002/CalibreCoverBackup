#from calibre.customize import Plugin
from calibre.customize import InterfaceActionBase
from calibre.utils.config import prefs
from calibre.library import db,current_library_path
from calibre_plugins.cover_backup.base.session import session_noninteractive
from os import path
import argparse as argp
class DemoPlugin(InterfaceActionBase):
    name = 'Cover Backup Plugin'  # Name of the plugin
    description = 'Creates and restores backups of book cover images.'
    supported_platforms = ['windows', 'osx', 'linux']  # Platforms this plugin will run on
    author = 'Samuel Fincher'  # The author of this plugin
    version = (1, 0, 0)  # The version number of this plugin
    minimum_calibre_version = (0, 7, 53)
    actual_plugin = 'calibre_plugins.cover_backup.interface:CoverBackupPlugin'
    def __print_metadata(self,api,i):
        if not api.has_id(i): raise FileNotFoundError(f"Book {i} doesn't exist!")
        meta = api.get_proxy_metadata(i)
        title = meta.get("title")
        #title = api.field_for("title",i)
        authors = meta.get("authors")
        #authors = api.field_for("authors",i)
        print(f'BOOK {i}:')
        print(f' TITLE: {title}')
        print(f' AUTHOR: {authors}')
    def __print_titles(self,api,ids):
        titles = api.all_field_for("title",ids)
        real_titles = [f'{i}: {t}' for i,t in titles.items() if t is not None]
        if len(real_titles) == 0: print(f'DB contains no titles.')
        else: print(f'DB does contain titles')
        for s in real_titles:
            print(s)

    def __print_all_titles(self,api):
        ids = api.all_book_ids()
        self.__print_titles(api,ids)

    # Properties that return classes from data_structs.
    @property
    def book_info(self):
        return self.__class__.book_info
    @property
    def session_base(self):
        return self.__class__.session_base

    @property
    def BackupTask(self):
        return self.__class__.BackupTask

    def BackupStatus(self):
        return self.__class__.BackupStatus

    def cli_main(self,args):
        parser = argp.ArgumentParser(prog='Hello world plugin', description='Hellos your world')
        parser.add_argument('-l','--library',help='Path to library folder. Set to last used library by default', action='store',default=prefs.get("library_path"))
        parser.add_argument('mode',help='Create or Restore Backup(s)',choices=['backup','restore'])
        parser.add_argument('ids',help='The ID(s) of books we are operating on.',nargs='+',type=int)
        parser.add_argument('-o', '--overwrite', help='Overwrite existing backups instead of skipping them.', action='store_true',dest='ow_mode')
        parser.add_argument('-p', '--backup-path', help='Path where backups are stored', default=path.expanduser('~/Pictures/Covers'))
        print(f'Called with {args}') 
        argv = parser.parse_args(args[1:])
        #leg = db(argv.library)
        #print(leg)
        api = db(argv.library).new_api
        #print(api)
        api.init()
        api.reload_from_db()
        s = session_noninteractive(db=api,ids=argv.ids,ow_mode=argv.ow_mode,backup_path=argv.backup_path)
        session_noninteractive.process(s)
        '''
        with api.safe_read_lock as l:
            print(f'Library Path: {argv.library}')
            print(f'DB Path: {api.dbpath}')
            for i in argv.ids:
                self.__print_metadata(api,i)
        '''
    def is_customizable(self):
        """
        This method must return True to enable customization via
        Preferences->Plugins
        """
        return True

    def config_widget(self):
        """
        Implement this method and :meth:`save_settings` in your plugin to
        use a custom configuration dialog.

        This method, if implemented, must return a QWidget. The widget can have
        an optional method validate() that takes no arguments and is called
        immediately after the user clicks OK. Changes are applied if and only
        if the method returns True.

        If for some reason you cannot perform the configuration at this time,
        return a tuple of two strings (message, details), these will be
        displayed as a warning dialog to the user and the process will be
        aborted.

        The base class implementation of this method raises NotImplementedError
        so by default no user configuration is possible.
        """
        # It is important to put this import statement here rather than at the
        # top of the module as importing the config class will also cause the
        # GUI libraries to be loaded, which we do not want when using calibre
        # from the command line
        from calibre_plugins.cover_backup.config import ConfigWidget

        return ConfigWidget()

    def save_settings(self, config_widget):
        """
        Save the settings specified by the user with config_widget.

        :param config_widget: The widget returned by :meth:`config_widget`.
        """
        config_widget.save_settings()

        # Apply the changes
        ac = self.actual_plugin_
        if ac is not None:
            ac.apply_settings()
