from calibre_plugins.cover_backup.base import book_info,BackupStatus,BackupTask,session_base
from calibre_plugins.cover_backup.base.backup import session_backup
from calibre_plugins.cover_backup.ui.backup.workers import PromptRequest,PromptResponse
from calibre_plugins.cover_backup.ui.backup.helper import Helper
from qt.core import (Qt,sip,QObject,pyqtSignal,QMessageBox,QEventLoop,QCoreApplication,QEvent)
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
        #super(session_base,self).__init__(ids,db,backup_path)
        #super(QObject,self).__init__(parent)
        # Initialize member variables
        self.box = QMessageBox()
        self.box.setModal(True)
        self.current = None
        self.queue = Queue()
        # Connect Signals
        self.box.buttonClicked.connect(self.__finish_prompt)
        self.book_ready.connect(self.__make_prompt, Qt.ConnectionType.QueuedConnection)
        self.global_resolution.connect(self.early_exit)
        self.aborted.connect(self.early_exit)
        #self.destroyed.connect(self.printDestroyed)
    def printDestroyed(self):
        print('Session Object was destroyed!')
    #@pyqtSlot()
    def early_exit(self):
        print('Got early exit.')
        self.queue.shutdown(True)
        # early_exit is only called from signal emitted by __finish_prompt here. Therefore, getResolution will always be called after and handled.
    #@pyqtSlot()
    def allInitialized(self):
        self.queue.shutdown()
        self.getResolution()
    
    @override
    def check_conflict(self,book,*,processed=None,conflicts=None):
        '''
        Checks conflict; Triggers queued signal for gui if found.
        Run in worker thread, but queued signal run in main thread.
        '''
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
    #@pyqtSlot()
    def __make_prompt(self):
        question = f"{self.current.book.title}, by {', '.join(self.current.book.authors)} has existing backup(s). Replace them?"
        paths = "\t'" + "'\n\t'".join(self.current.book.ext_paths) + "'"
        self.box.setText(f'{question}\n{paths}')
        self.box.setWindowTitle(f'"{self.current.book.title}" Backup Conflict')
        #self.box.setText(f"Overwrite Existing Backup for {book_title} at {paths}?")
        BUTTONS = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        if (not self.current.is_last) and self.current.multi: BUTTONS |= QMessageBox.StandardButton.YesToAll | QMessageBox.StandardButton.NoToAll | QMessageBox.StandardButton.Cancel
        self.box.setStandardButtons(BUTTONS)
        self.box.open()
    # Slot to enqueue conflict request
    #@pyqtSlot(BackupTask|None)
    def getResolution(self,t=None):
        print("Getting next conflict with current =",self.current)
        try:
            # If current is none, try to get from queue.
            if self.current is None:
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
        if self.current is not None: self.book_ready.emit()
    #@pyqtSlot()
    def __finish_prompt(self,button):
        signal = self.reached_resolution
        response = 0
        try:  
            match(self.box.buttonRole(button)):
                case QMessageBox.ButtonRole.InvalidRole: raise ValueError("Reported button does not exist on dialog.")
                case QMessageBox.ButtonRole.YesRole:
                    response = PromptResponse(self.current.book.book_id,True)
                    if button == self.box.button(QMessageBox.StandardButton.YesToAll): signal = self.global_resolution
                case QMessageBox.ButtonRole.NoRole: 
                    response = PromptResponse(self.current.book.book_id,False)
                    if button == self.box.button(QMessageBox.StandardButton.NoToAll): signal = self.global_resolution
                case QMessageBox.ButtonRole.RejectRole: signal = self.aborted # Set abort event in thread here. raise GeneratorExit("Canceled.")
        except:
            # Set response to error code
            #self.__handle_error()
            raise
        finally:
            self.current = None
            signal.emit(response)
        print('Sent prompt response, calling getResolution()...')
        self.getResolution() 
    # Override of process
    @staticmethod
    def process(session,*,log=None,notifications=None,abort=None):
        '''
        Start event loop in seperate thread
        '''
        log.info(f'Processing Book(s) {",".join([str(i) for i in session.ids])}...')
        l = QEventLoop(None)
        h = Helper(session,l,notifications,log)
        h.books += session.get_books()
        #h.all_started.connect(lambda : print('t2:',int(QThread.currentThreadId())), Qt.ConnectionType.QueuedConnection)
        #h.done.connect(session.parent().exit,Qt.ConnectionType.QueuedConnection)
        #l.destroyed.connect(session.deleteLater,Qt.ConnectionType.QueuedConnection)
        h.prepare()
        # When h is complete, make the event loop exit.
        h.destroyed.connect(l.exit)
        #sleep(10)
        res = l.exec()
        # Queue and process deferred event loop deletion.
        l.deleteLater()
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
        # Warn if loop or helper still exists.
        if not sip.isdeleted(h): log.warn('Helper still exists!')
        if not sip.isdeleted(l): log.warn('Event loop still exists!')
        return res





