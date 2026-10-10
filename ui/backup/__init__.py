from calibre_plugins.cover_backup.base import book_info,BackupStatus,BackupTask,session_base
from calibre_plugins.cover_backup.base.backup import session_backup
from calibre_plugins.cover_backup.ui.backup.dialog import BackupDialog,MultiBackupDialog,GlobalChoice
from calibre_plugins.cover_backup.ui.backup.workers import PromptRequest,PromptResponse
from calibre_plugins.cover_backup.ui.backup.helper import Helper
import threading
from qt.core import (Qt,QCheckBox,QWidget,QComboBox,QHBoxLayout,sip,QObject,pyqtSignal,QDialog,QMessageBox,QDialogButtonBox,QEventLoop,QCoreApplication,QEvent,QPushButton,QVBoxLayout,QLabel,QButtonGroup)
from queue import Queue,Empty,ShutDown
from typing import override
# The session interactive object replaces the gui connector object.
class backup_interactive(session_backup,QObject):
    '''
    # Actual session info
    ids: list[int]
    db: db_api
    backup_path: PathLike
    def process(self,*,abort=None,log=None,notifications=None):
    def get_books(self):
        paths = self.db.all_field_for('path',self.ids)
        titles = self.db.all_field_for('title',self.ids)
        authors = self.db.all_field_for('authors',self.ids)
        return [book_info(bid,titles[bid],authors[bid],self.backup_path) for bid in self.ids]
    def check_conflict(self,book)
    def write_backup(self,book,path,existing=[])
    '''
    __getNext = pyqtSignal()
    book_ready = pyqtSignal()
    reached_resolution = pyqtSignal(PromptResponse)
    global_resolution = pyqtSignal(PromptResponse)
    complete = pyqtSignal()
    aborted = pyqtSignal(int)
    def __init__(self,ids,db,backup_path,parent=None):
        # Run parent constructors
        session_backup.__init__(self,ids,db,backup_path)
        QObject.__init__(self,parent)
        # Set helpers used to structure ui.
        self.multi = len(ids) > 0
        self.last = ids[-1]
        self.current = None
        self.queue = Queue()
        # Connect Signals
        self.book_ready.connect(self.__make_prompt, Qt.ConnectionType.QueuedConnection)
        self.global_resolution.connect(self.early_exit)
        self.reached_resolution.connect(self.__getNext)
        self.complete.connect(self.deleteLater,Qt.ConnectionType.QueuedConnection)
        self.complete.connect(lambda: print('Completed session!'))
        self.aborted.connect(lambda: print('EXITTED SESSION EARLY!'))
    def printDestroyed(self):
        print('Session Object was destroyed!')
    def abort(self):
        self.early_exit()
        self.aborted.emit(0)
    #@pyqtSlot()
    def early_exit(self):
        print('Got early exit.')
        #self.aborted.emit(0)
        self.queue.shutdown(True)
        self.__getNext.emit()
    #@pyqtSlot()
    def allInitialized(self):
        self.queue.shutdown()
        self.getResolution()
    
    @override
    def check_conflict(self,book,*,processed=None,conflicts=None):
        print('Calling super...')
        book.unique,book.ext_paths = session_base.check_conflict(self,book)
        book.unique = not book.unique
        print('Setting status if ok...')
        book.status = BackupStatus.Overwrite if book.unique else BackupStatus.Pending
        #print(f'Checked conflict, got {ok},{paths}')
        #req.book.ext_paths += paths
        if processed is not None: processed.emit(book)
        if not book.unique and conflicts is not None: conflicts.emit(PromptRequest(book,book.book_id == self.last,self.multi))
        return book.unique,book.ext_paths
    # Slot to enqueue conflict request
    def getResolution(self,t=None):
        print("Getting next conflict with current =",self.current)
        was_free = self.current is None
        try:
            # If current is none, try to get from queue.
            if was_free:
                self.current = self.queue.get_nowait()
            # If successful, or if current is set, put t into the queue if it is not None.
            if t is not None: self.queue.put(t)
        except Empty:
            print("Queue was empty")
            # If we caught empty queue, current was none but queue was empty. set current to t and return.
            self.current = t
        except ShutDown:
            print("Caught ShutDown")
            self.complete.emit()
            return
        if was_free: self.book_ready.emit()
    def __make_prompt(self):
        d = MultiBackupDialog(self.parent()) if (multi := (len(self.current.book.ext_paths)) > 1) else BackupDialog(self.parent())
        if multi: args = (self.db, self.current, (not self.current.is_last) and self.current.multi)
        else: args = (self.current, (not self.current.is_last) and self.current.multi)
        d.resolved.connect(self.__finish_prompt)
        self.aborted.connect(d.reject)
        d.finished.connect(d.deleteLater)
        self.destroyed.connect(d.deleteLater)
        d.startPrompt(*args)
    def __finish_prompt(self,result,resolution=None):
        signal = self.reached_resolution
        response = 0
        try:
            response = PromptResponse(self.current.book.book_id,resolution.action)
            if result == QDialog.DialogCode.Rejected: self.queue.shutdown(True)
            elif resolution.scope != GlobalChoice.NoGlobal: signal = self.global_resolution
            signal.emit(response)
        except:
            # Set response to error code
            #self.__handle_error()
            raise
        print('Sent prompt response, calling getResolution()...')
        self.current = None
        self.getResolution() 
    # Override of process
    @staticmethod
    def process(session,*,log=None,notifications=None,abort=None):
        '''
        Start event loop in seperate thread
        '''
        log.debug(f'Running job on thread{threading.get_ident()},{threading.get_native_id()}...')
        log.info(f'Processing Book(s) {",".join([str(i) for i in session.ids])}...')
        l = QEventLoop(None)
        h = Helper(session,l,notifications,log,abort)
        wr = h.writer
        ch = h.handler
        h.books += session.get_books()
        h.prepare()
        # When h is complete, or when early exit, make the event loop exit.
        h.destroyed.connect(l.exit)
        #session.aborted.connect(l.exit)
        #sleep(10)
        print('Loop STARTED!')
        res = l.exec()
        print('Loop FINISHED!')
        # Queue and process deferred event loop deletion.
        l.deleteLater()
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
        # Warn if loop or helper still exists.
        if not sip.isdeleted(wr): log.warn('BackupWriter still exists!')
        if not sip.isdeleted(ch): log.warn('ConflictHandler still exists!')
        if not sip.isdeleted(h): log.warn('Helper still exists!')
        if not sip.isdeleted(l): log.warn('Event loop still exists!')
        log.info('Reached end of worker thread!')
        return res





