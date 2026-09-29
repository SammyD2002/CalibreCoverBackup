from dataclasses import dataclass,field
from enum import IntEnum
import glob
from os import PathLike,path,remove
from calibre.library import db as db_api
import logging
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
    def write_backup(self,book,path,existing=[]):
        self.db.copy_cover_to(book.book_id,book.backup_path)
        for p in existing: 
            remove(p)
    def restore_backup(self,book,paths):
        # Set the book cover
        with open(paths[0],'rb') as src: self.db.set_cover({book.book_id: src})
        if self.ow_mode == True: remove(paths[0])
