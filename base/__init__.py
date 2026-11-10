from dataclasses import dataclass,field
from enum import IntEnum
import glob
from os import PathLike,path,remove
from calibre.library import db as db_api
import logging
import re
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
        paths = self.db.all_field_for('path',self.ids)
        titles = self.db.all_field_for('title',self.ids)
        authors = self.db.all_field_for('authors',self.ids)
        return [BackupTask(bid,titles[bid],authors[bid],self.backup_path) for bid in self.ids]
    def check_conflict(self,book):
        '''
        Conflicts to handle:
            i) A backup cover of the same filename exists
            ii) A backup cover of the same id but different filename exists
        Subclasses should override this method, call super().check_conflict(), and execute based on its result.
        Returns isConflicting,[Conflicting Paths]
        '''
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
