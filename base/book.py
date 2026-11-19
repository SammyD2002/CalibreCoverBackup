from enum import IntEnum
import glob
from os import PathLike,path,remove
from calibre.library import db as db_api
import logging
import re
class BookTemplate:
    '''
    # The target path
    backup_path: PathLike
    # Detected paths containing existing backups. Can be set later
    ext_paths: list[PathLike] = field(default_factory=list)
    # Task Status
    status: BackupStatus = BackupStatus.Initial
    unique: bool = True
    '''
    # Attribute containining db, should be set on startup to current_db.
    _db : db_api|None = None
    _tfield = None
    _afield = None
    _dir : str|None = None

    def __init__(self,book_id):
        self.book_id = book_id
        self.__title = self.__authors = self.__cover = self.__ext_paths = None

    @property
    def title(self)->str:
        '''
        Book title
        '''
        if (v := self.__title) is None: self.__title = v = self._db.fast_field_for(self._tfield,self.book_id)
        return v
 
    @property
    def authors(self)->tuple[str,...]:
        '''
        List of author(s) the book is attributed to.
        '''
        if (v := self.__authors) is None: self.__authors = v = self._db.fast_field_for(self._afield,self.book_id)
        return v

    @property
    def base_path(self)->PathLike:
        '''
        Path where the backup is written if not already present, used as base for unique path if path is present.
        '''
        DN = f'{self.book_id}_{self.title}' if any(self.authors == a for a in ['','Unknown']) else f'{self.book_id}_{self.title} [{', '.join(self.authors)}]'
        return path.abspath(path.join(self._dir, DN + '.jpg'))
    
    @property
    def ext_paths(self)->list[PathLike]:
        '''
        Path(s) to existing backups for <id> in the backup directory.
        '''
        if (v := self.__ext_paths) is None: self.__ext_paths = v = [path.join(self._dir,n) for n in glob.glob(f'{self.book_id}_*.jpg',root_dir=self._dir)]
        return v

    @property
    def unique_path(self)->PathLike:
        '''
        Path used to write a new backup if not replacing any existing backup(s).
        '''
        last_id = 0
        matching_paths = []
        # backup_path always has an extension, so we can use backup_path[:-4] to get prefix.
        prefix = self.base_path[:-4]
        expr = re.compile(r"%s\.(?:(?P<num>\d+)\.)?jpg" % re.escape(prefix), flags=re.MULTILINE)
        for p in self.ext_paths:
            m = expr.match(p)
            if m is None: continue
            matching_paths.append(p)
            if (nstr := m.groupdict()['num']) is not None:
                num = int(nstr)
                if num > last_id: last_id = num
            # If first char after '.' is a number, nums group will be populated. add it to nums, then
        if len(matching_paths) == 0: return prefix + '.jpg'
        else: return f'{prefix}.{last_id + 1}.jpg'

    @property
    def current_pixmap(self):
        '''
        Reads QPixmap of currently set book cover. Used in preview widget(s)
        '''
        try:
            if (v := self.__cover) is None: 
                #print('__cover is None, loading from file...')
                self.__cover = v = self._db.cover(self.book_id, as_pixmap=True)
            #else: print('__cover was not none, using it...')
            return v
        except Exception as e:
            print(f'Caught some error {e}')
            print(f'Type: {type(e)}')
            raise

    def write_cover(self,bpath=None):
        '''
        Writes cover to bpath or unique_path if bpath not specified.
        Returns the path the cover was written to.
        '''
        if bpath is None: bpath = self.unique_path
        self._db.copy_cover_to(self.book_id,bpath)
        return bpath

    def restore_cover(self,rpath=None):
        '''
        Restores cover at rpath to book.
        If rpath is not specified, restores base_path if it exists.
        If base_path does not exist, restore first path in self.ext_paths
        Returns the path that was restored.
        '''
        # If rpath is set, attempt to restore it and only it.
        if rpath is not None:
            with open(rpath,'rb') as cf:
                self._db.set_cover({self.book_id: cf})
            return rpath
        # Otherwise, try base_path then other existing paths.
        else:
            paths = self.ext_paths
            if (bp := self.base_path) not in paths: paths.insert(0,bp)
            for p in paths:                    
                try:
                    with open(p,'rb') as cf:
                        self._db.set_cover({self.book_id: cf})
                except FileNotFoundError:
                    if p != paths[-1]: continue
                    else: raise
                return p


class BookBase(BookTemplate):
    def __init_subclass__(cls, **kwargs):
        '''
        Prevent creation of subclass without _db, and _dir; initialize _tfield and _afield.
        ''' 
        assert (db := cls._db) is not None
        assert (cls._dir is not None)
        cls._tfield = db.fields['title']
        cls._afield = db.fields['authors']
        super().__init_subclass__(**kwargs)



'''
Initializes and returns Book class using db and backup_dir.
'''
def BookClassFactory(basecls, db, backup_dir):
    return type('Book',(basecls,),{'_db': db, '_dir': backup_dir})
