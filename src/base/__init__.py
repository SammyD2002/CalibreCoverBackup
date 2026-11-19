from dataclasses import dataclass,field,KW_ONLY
from typing import override
from enum import IntEnum,auto
from os import PathLike,path,remove
import glob
from calibre.library import db as db_api
import logging
#from calibre_plugins.cover_backup.base.session import WorkerMixin
import re
from qt.core import (QDialog)
ABORT = QDialog.DialogCode.Rejected
INIT = QDialog.DialogCode.Accepted
def StatusBase(ec): # Create enum with normalized abort value.
    mbrs = ec._member_map_
    mbrs.pop('Abort',None)
    vals = [(k,auto() if v == ABORT else v) for k,v in ec._member_map_.items()]
    #mbrs['Abort',QDialog.DialogCode.Rejected 
    ne = IntEnum(ec.__name__, [('Abort',ABORT)] + vals)
    del ec
    return ne
    
'''
Status Enums
'''
class BackupStatus(IntEnum):
    Initial = INIT
    Pending = 1
    Write = 2
    Overwrite = 3
    Skip = 4
    Abort = ABORT

class RestoreStatus(IntEnum):
    Initial = INIT
    Pending = 1
    Skip = 2 # No backups or multiple backups exist
    Restore = 3 # At least one backup existed
    Abort = ABORT

@dataclass
class Resolution:
    '''
    Action Conflict Resolution Base Class
    '''
    class Scope(IntEnum):
        NotFound = 0 # No Backups exist
        Single = 1 # One Backup exists
        Multi = 2 # 2+ Backups Exist
        All = 3 # Any # Of backups exist
    scope: Resolution.Scope
    book: int|None = field(kw_only=True,default=None)
    def isGlobal(self): # True if the resolution applies globally
        return self.book is None
    def match_scope(self,book): # Return True if book passed in parameters matches scope
        return self.scope != self.Scope.Single if len(book.ext_paths) > 1 else self.scope != self.Scope.Multi
    def match_id(self,book): # Return True if scope is global or the id of the book matches.
        return self.isGlobal() or book.book_id == self.book

class Result:
    '''
    Action result base class
    '''
    header: str|None = None
    def __init__(self, book,changed):
        '''
        changed is a bool used to dictate whether a backup/book was altered.
        '''
        self.header = f'{book.title} [{book.book_id}]'
        self.changed = changed
    def summarize_full(self):
        raise NotImplementedError()
    def summarize_brief(self):
        raise NotImplementedError()

class WorkerMixin:
    def __init__(self, book_factory, *, abort=None,log=None,notifications=None):
        '''
        Create class and set internal variables
        '''
        self.book_factory = book_factory
        self.abort = abort
        self.log = log
        self.notifications = notifications

    def summarize_results(self):
        '''
        Returns string containing result summary.
        Implement in subclass
        '''
        raise NotImplementedError()
    def do_book(self,book_id):
        '''
        Process book <book_id>. Implement in subclass
        '''
        raise NotImplementedError()



'''
Helper used to wrap log for testing.
'''
def wrap_log(fn):
	class ndummy:
		def __init__(self,log):
			self.log = log
		def put(self,msg,block=True,timeout=None):
			self.log.info(f'[{msg[0] * 100}%]: {msg[1]}')
		def put_nowait(self,msg):
			self.put(msg,False,None)
	class adummy:
		def __init__(self,log):
			self.log = log
		def isSet(self):
			return False
		def set(self):
			raise RuntimeError('Abort set!')
	def wrapper(*args,**kwargs):
		l = kwargs.get('log')
		if l is None:
			logger = logging.getLogger(__name__)
			logging.basicConfig(level=logging.DEBUG)
			l = kwargs.setdefault('log',logger)
		if kwargs.get('notifications') is None: kwargs.setdefault('notifications',ndummy(l))
		if kwargs.get('abort') is None: kwargs.setdefault('abort',adummy(l))
		fn(*args,**kwargs)
	return wrapper

class session_base(WorkerMixin):
    @override
    def do_book(self,book_id):
        return self.book_factory(book_id)
'''
@dataclass
class session_base:
    # Actual session info
    ids: list[int]
    db: db_api
    backup_path: PathLike
    ow_mode: bool|None = None
    # Returns dict of {id: [library_path,backup_file,title,authors]}
    def process(self,*,abort=None,log=None,notifications=None):
        raise NotImplemented('Must be implemented in subclass!')
    
    def get_books(self):
        #paths = self.db.all_field_for('path',self.ids)
        #titles = self.db.all_field_for('title',self.ids)
        #authors = self.db.all_field_for('authors',self.ids)
        #return [BackupTask(bid,titles[bid],authors[bid],self.backup_path) for bid in self.ids]
        return B
    def check_conflict(self,book):
        #Conflicts to handle:
            #i) A backup cover of the same filename exists
            #ii) A backup cover of the same id but different filename exists
        #Subclasses should override this method, call super().check_conflict(), and execute based on its result.
        #Returns isConflicting,[Conflicting Paths]
        existing_paths = glob.glob(f'{book.book_id}_*.jpg',root_dir=self.backup_path)
        return len(existing_paths) > 0, [path.join(self.backup_path,p) for p in existing_paths]
    def write_backup(self,book,existing=[]):
        print(f'Book Mode: {book.status}')
        if book.status == BackupStatus.Write: book.backup_path = book.make_new_path()
        print(f'Creating backup {book.backup_path}')
        self.db.copy_cover_to(book.book_id,book.backup_path)
        if book.status == BackupStatus.Overwrite:
            print(f'Removing {existing}')
            for p in existing: remove(p)


    def restore_backup(self,book,paths):
        # Set the book cover
        with open(paths[0],'rb') as src: self.db.set_cover({book.book_id: src})
        if self.ow_mode == True: remove(paths[0])
'''
