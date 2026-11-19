#from calibre.customize import Plugin
from calibre.customize import InterfaceActionBase
from qt.core import (QDialog)
from calibre.utils.config import prefs
from calibre.library import db,current_library_path
from calibre_plugins.cover_backup.config import prefs as plugin_prefs
from calibre_plugins.cover_backup.base import BackupStatus,Resolution
from calibre_plugins.cover_backup.base.backup import session_backup,BackupResolution
from calibre_plugins.cover_backup.base.book import BookClassFactory,BookBase
from calibre_plugins.cover_backup.base.restore import session_restore
from typing import override
import argparse as argp
from os import path
class DemoPlugin(InterfaceActionBase):
    name = 'Cover Backup Plugin'  # Name of the plugin
    description = 'Creates and restores backups of book cover images.'
    supported_platforms = ['windows', 'osx', 'linux']  # Platforms this plugin will run on
    author = 'Samuel Fincher'  # The author of this plugin
    version = (0, 1, 0)  # The version number of this plugin
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
        parser = argp.ArgumentParser(prog='Cover Backup Plugin', description='Creates and restores book cover image backups.',allow_abbrev=True)
        parser.add_argument('-l','--library',help='Path to library folder. Set to last used library by default', action='store', default=prefs.get("library_path"))
        parser.add_argument('-p', '--backup-path', help='Path where backups are stored', default=plugin_prefs['backup_path'])
        sp = parser.add_subparsers(help='subcommand help', dest='mode', metavar='{b[ackup],r[estore]}',required=True)
        make_aliases = lambda s: [] if len(s) <= 1 else [s[:-1]] + make_aliases(s[:-1])
        # Configure backup subparser
        backup = sp.add_parser('backup',aliases=make_aliases('backup'),help='backup help')
        #parser.add_argument('ids',help='The ID(s) of books we are operating on.', type=int, action='extend',nargs=1)
        #parser.add_argument('mode',help='Create or Restore Backup(s)',choices=['backup','restore'])
        #backup.add_argument('-o', '--overwrite-single', help='Overwrite the existing backup of book(s) with one existing backup instead of skipping them.', action='store_true')
        # Change to -s (single existing), -S (single existing global), -m (multi existing), -M (multi existing global), -e (any existing), -E (any existing GLOBAL)
        # Format: -[s/m/e] <id>[,<id2>,...,<idn>];[skip/new/replace]
        # custom OverwriteMode subclass to parse and handle arg.
        def get_action(arg):
            if arg is not None:
                match(str(arg).lower()):
                    case 'skip': return BackupStatus.Skip
                    case 'new': return BackupStatus.Write
                    case 'replace': return BackupStatus.Overwrite
                    case _: print(f"'{arg} is not a valid action, will skip instead...")
            return BackupStatus.Skip
        class Handler(argp.Action):
            def _make_resolution(self,arg):
                return BackupResolution(self.scope, get_action(arg))
            def _update_namespace(self,namespace,res):
                setattr(namespace,self.dest,res)
                return namespace
            @override
            def __call__(self, parser, namespace, values, option_string=None):
                # Create BackupResolution Object for passed action
                res = self._make_resolution(values)
                # Append it to the list of Resolutions (Single Book Handlers should PREPEND)
                return self._update_namespace(namespace,res)
        
        class GlobalHandler(Handler):
            @override
            def _update_namespace(self,namespace,res):
                setattr(namespace,self.dest,cl + [res] if (cl := getattr(namespace,self.dest,None)) is not None else [res])
                return namespace

                
        class IndividualHandler(GlobalHandler):
            @override
            def _update_namespace(self,namespace,res):
                setattr(namespace,self.dest,res + cl if (cl := getattr(namespace,self.dest,None)) is not None else res)
                return namespace
            @override
            def _make_resolution(self,arg):
                argv = arg.split(':')
                ids = [int(s.strip()) for s in argv[0].split(',')]
                res = []
                for i in ids:
                    cr = super()._make_resolution(argv[1])
                    cr.book = i
                    res.append(cr)
                return res
        # Local and global args for single existing 
        backup.add_argument('-s','--single-existing',dest='indv_res',action=type('SingleExisting',(IndividualHandler,),{'scope': Resolution.Scope.Single}))
        backup.add_argument('-S','--single-existing-global',dest='indv_res',action=type('GSingleExisting',(GlobalHandler,),{'scope': Resolution.Scope.Single}))
        # Local and global args for multi existing 
        backup.add_argument('-m','--multi-existing',dest='indv_res',action=type('MultiExisting',(IndividualHandler,),{'scope': Resolution.Scope.Multi}))
        backup.add_argument('-M','--multi-existing-global',dest='indv_res',action=type('GMultiExisting',(GlobalHandler,),{'scope': Resolution.Scope.Multi}))
        # Local and global args for any # existing
        backup.add_argument('-e','--any-existing',dest='indv_res',action=type('AnyExisting',(IndividualHandler,),{'scope': Resolution.Scope.All}))
        backup.add_argument('-E','--any-existing-global',dest='all_res',default=BackupResolution(Resolution.Scope.All,BackupStatus.Skip),action=type('GAnyExisting',(Handler,),{'scope': Resolution.Scope.All}))
        '''
        backup.add_argument('-o', '--overwrite-single', help='Set how book(s) with one existing backup are handled (skip backup|new backup|replace backup).', default=None)
        #backup.add_argument('--overwrite-multi', help='Overwrite ALL existing backups of book(s) with multiple existing backups instead of skipping them.', action='store_true')
        backup.add_argument('--overwrite-multi', help='Set how book(s) with multiple existing backups are handled (skip backup|new backup|replace ALL backups).', default=None)
        # Equivalent to -o and --overwrite-multi
        #backup.add_argument('-O', '--overwrite-all', help='Overwrite ALL existing backups of book(s) with any number of backups instead of skipping them.', action='store_true')
        backup.add_argument('-O', '--overwrite-all', help='Set how book(s) with any number of backups are handled (skip backup|new backup|replace ALL backups).', default='skip')
        backup.add_argument('--overwrite-individual', help='Set how the books with the specified id(s) are handled if they have existing backups (Format: <ID>,<# EXIST>,<ACTION>;<ID>...', action='store')
        '''
        backup.add_argument('ids',help='The ID(s) of books we are creating backup(s) for.', type=int, action='extend',nargs='+',metavar=('id','ids'))
        # Configure restore subparser
        restore = sp.add_parser('restore',aliases=make_aliases('restore'),help='restore help')
        #restore.add_argument('-d','--delete',help='Delete backups after they are restored.', action='store_true',dest='ow_mode')
        restore.add_argument('-f','--from-base',help='Restore from base path if multiple backups exist instead of skipping.', action='store_true', dest='br_mode')
        restore.add_argument('ids',help='The ID(s) of books we are restoring backup(s) for.', type=int, action='extend',nargs='+',metavar=('id','ids'))
        #print(f'Called with {args}') 
        argv = parser.parse_args(args[1:])
        #leg = db(argv.library)
        #print(leg)
        api = db(argv.library).new_api
        #print(api)
        api.init()
        api.reload_from_db()
        Book = BookClassFactory(BookBase,api,argv.backup_path)
        session = None
        if argv.mode[0] == 'b':
            argv.ow_modes = (argv.indv_res if argv.indv_res is not None else []) + [argv.all_res]
            #if argv.overwrite_single is not None: argv.ow_modes.append(OverwriteMode(OverwriteMode.Scope.Single,get_action(argv.overwrite_single)))
            #if argv.overwrite_multi is not None: argv.ow_modes.append(OverwriteMode(OverwriteMode.Scope.Multi,get_action(argv.overwrite_multi)))
            #argv.ow_modes.append(OverwriteMode(OverwriteMode.Scope.All,get_action(argv.overwrite_all)))
            '''
            if argv.overwrite_all or (argv.overwrite_single and argv.overwrite_multi): argv.ow_mode = OverwriteMode.All
            else:
                if argv.overwrite_single: argv.ow_mode = OverwriteMode.Single
                if argv.overwrite_multi: argv.ow_mode = OverwriteMode.Multi
            '''
            session = session_backup(argv.ow_modes,Book)
        else:
            session = session_restore(argv.br_mode,Book)
        for b in argv.ids:
            session.do_book(b)
        session.summarize_results()
        #cs = backup_noninteractive if argv.mode == 'backup' else restore_noninteractive
        #s = cs(db=api,ids=argv.ids,ow_mode=argv.ow_mode,backup_path=argv.backup_path) 
        #cs.process(s)
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
