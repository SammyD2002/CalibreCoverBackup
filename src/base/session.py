from dataclasses import dataclass
from typing import override
#from calibre_plugins.cover_backup.base import wrap_log
from os import path,remove
class Result:
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
