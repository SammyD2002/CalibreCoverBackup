from qt.core import (Qt,QObject,QVBoxLayout,QPushButton,pyqtSignal,QLabel)
from ..base.book import BookTemplate,BookClassFactory
from ..base import WorkerMixin
#from calibre_plugins.cover_backup.base.book import BookTemplate,BookClassFactory
#from calibre_plugins.cover_backup.base import WorkerMixin
from calibre.utils.logging import GUILog,Log
from calibre.constants import DEBUG
from typing import override
from time import perf_counter_ns
from threading import Lock
class UnsafeLogWrapper(Log):
    def __init__(self, other_log: Log) -> None:    
        Log.__init__(self, level=other_log.filter_level)
        self.outputs = list(other_log.outputs)

def protect(fn):
    def guarded(self,*args,**kwargs):
        with self._lock:
            return fn(self,*args,**kwargs)
    return guarded

class interval:
    def __init__(self,stime=perf_counter_ns(),presep='(',postsep=')'):
        self._lock = Lock()
        with self._lock:
            self._time = stime
            self._fmt = f'{presep}%i{postsep}'
    @property
    @protect
    def time(self):
        return self._time
    @time.setter
    @protect
    def time(self,tm):
        self._time = tm
    @property
    @protect
    def fmt(self):
        return self._fmt
    @fmt.setter
    @protect
    def fmt(self,fmt):
        self._fmt = fmt
    @protect
    def clone(self):
        nt = interval(self._time)
        nt._fmt = self._fmt
        return nt


    @protect
    def __str__(self):
        return self._fmt%((perf_counter_ns() - self._time) // 1000) # Give time in microseconds
    def __call__(self):
        return self.__str__()

class LogPrefixWrapper(UnsafeLogWrapper,GUILog):
    '''
    Adapted from ThreadSafeWrapper, creates log instance that writes to same outputs as a GUILog object, but adds a prefix.
    Copies _lock from other_log.
    '''
    def __init__(self,other_log,*prefix,base_interval=None):
        super().__init__(other_log)
        self._lock = other_log._lock
        if DEBUG:
            if base_interval is None: self._interval = interval(postsep=' usec)')
            else: self._interval = base_interval.clone()
            prefix = (self._interval, *prefix)
        else: self._interval = None
        self.prefix = prefix
    def __prepare_args(self,args):
        print('length of args:', len(args))
        print('\t',args)
        #print('length of kwargs:',len(kwargs))
        #print('\t',kwargs)
        return args[:1] + self.prefix + args[1:]
    @override
    def prints(self,*args,**kwargs):
        super().prints(*self.__prepare_args(args),**kwargs)
    @override
    def print_with_flush(self, *args,**kwargs):
        super().print_with_flush(*self.__prepare_args(args),**kwargs)

class QBookBase(BookTemplate,QObject):
    def __init__(self,book_id,parent=None):
        QObject.__init__(self,parent)
        BookTemplate.__init__(self,book_id)
    def __init_subclass__(cls, **kwargs):
        '''
        Prevent creation of subclass without _db, and _dir; initialize _tfield and _afield.
        ''' 
        assert (db := cls._db) is not None
        assert (cls._dir is not None)
        cls._tfield = db.fields['title']
        cls._afield = db.fields['authors']
        super().__init_subclass__(**kwargs)

class QSession(QObject, WorkerMixin):
    def __init__(self, book_factory, **kwargs):
        QObject.__init__(self,kwargs.pop('parent',None))
        WorkerMixin.__init__(self,book_factory,**kwargs)

# Base classes useful for creating dialogs.
class ActionButtonMixin:
    def inputValid(self):
        '''
        Returns whether or not user input on the button(s) widgets is valid.
            By default, returns true
        '''
        return True

    @property
    def gl_scope(self):
        return None

    def make_resolution(self):
        raise NotImplementedError('Must be implemented in subclass!')

class CustomPushButton(QPushButton):
    def __init__(self,label,parent=None,*,layout_cls=QVBoxLayout):
        QPushButton.__init__(self,parent)
        self.setLayout(lay := layout_cls())
        lay.addWidget(lb := QLabel(self.tr(label)))
        lb.setBuddy(self)

    @override
    def sizeHint(self):
        if self.layout():
            # the button now has a layout, return its size hint
            return self.layout().sizeHint()
        # no layout set, return the result of the default implementation
        return super().sizeHint()


