from calibre_plugins.cover_backup.base import BackupStatus,Resolution,ABORT
#from calibre_plugins.cover_backup.base.backup import BackupResolution,BackupResult
from calibre_plugins.cover_backup.ui import LogPrefixWrapper
from calibre.utils.logging import GUILog
from qt.core import (Qt,QObject,pyqtSignal)
from queue import Queue,Empty,ShutDown
from threading import Event
class prompt_handler(QObject):
    # Emitted when prompt is closed and resolution is reached.
    resolutionReached = pyqtSignal(Resolution)
    # Emitted by __appExit, which is called if the app is exitting.
    appExit = pyqtSignal()
    # Emitted when prompt work is complete
    complete = pyqtSignal()
    def __init__(self,job,parent=None):
        QObject.__init__(self,parent)
        # Initialize var for current dialog
        self.current = None
        # job is an instance of ThreadedJob. Attributes to note:
        # job.args, job.kwargs: args and kwargs passed to the function.
        # job.log: GUILog instance used by the job. Is thread safe.
        # Set internal vars from job instance.
        self.last_id = job.args[0][-1]
        self.book_factory = job.args[1]
        self.log = LogPrefixWrapper(job.kwargs['log'],'PROMPT: ')
        # Add app_exit event and self to kwargs.
        self.exit_event = Event()
        self.id_queue = Queue()
        job.kwargs['prompt'] = self
        self.complete.connect(self.deleteLater)
    # Virtual Methods for subclass
    def _startPrompt(self,book)->QDialog:
        '''
        Initializes user prompt with data from paramater book.
        '''
        raise NotImplementedError('Must be implemented in subclass!')
    def _finishPrompt(self,result,prompt)->Resolution:
        '''
        Handle user prompt response
        '''
        raise NotImplementedError('Must be implemented in subclass!')
    def __prepare_dialog(self,book)->None:
        '''
        Create book object for book_id, pass book to _startPrompt, store and connect dialog signals/slots; show dialog.
        '''
        self.current = self._startPrompt(self.book_factory(book))
        # Connect Signals and Slots
        self.current.finished.connect(self.__resolutionReached)
        # Show dialog
        self.current.open()
    # Trigger and store prompt for t.
    def getResolution(self,book_id=None)->None:
        '''
        Enqueue book_id if it is not None; Start next task if current_dialog is None.
        '''
        try:
            # If current is none, try to get from queue.
            enqueued_id = self.id_queue.get_nowait() if self.current is None else None
            # If successful, or if current is set, put t into the queue if it is not None.
            if book_id is not None: self.id_queue.put(book_id)
            book_id = enqueued_id
        except Empty:
            print("Queue was empty")
            # If we caught empty queue, current was none but queue was empty. Return if book_id is none, continue otherwise.
            if book_id is None: return
        except ShutDown:
            print("Caught ShutDown")
            self.complete.emit()
            return
        if self.current is None: self.__prepare_dialog(book_id)

    # Handle prompt result.
    def __resolutionReached(self,result)->None:
        '''
        Unset stored prompt and pass both it and result to _finishPrompt; emit resolutionReached with _finishPrompt return value; Destroy prompt object and book.
        '''
        tmp_prompt = self.current
        self.current = None
        # Retrieve and emit resolution.
        res = self._finishPrompt(result,tmp_prompt)
        self.resolutionReached.emit(res)
        if res.action == ABORT or res.isGlobal() or res.book == self.last_id: self.id_queue.shutdown(True)
        tmp_prompt.deleteLater()
        self.getResolution()

    # Called if app exits.
    def __appExit(self)->None:
        '''
        Emit appExit signal (or set event); delete dialog; delete self. Do this IMMEDIATLY
        '''
        self.__exit_event.set()
        # Delete dialog
        self.__shutdown()
        # Delete self
        self.appExit.emit()
        self.deleteLater()
    def __shutdown(self):
        self.id_queue.shutdown(True)
        if self.current is not None:
            self.current.finished.disconnect()
            self.current.reject()
            self.current.deleteLater()

    # Called if job is aborted by user or in job dialog.
    def jobAbort(self)->None:
        '''
        Disconnect resolutionReached and dialog signals; shutdown queue; close dialog if exists; enqueue call to getResolution with t=None
        '''
        self.__shutdown()
        self.getResolution()

'''
class prompt_handler(QObject):
    __getNext = pyqtSignal()
    book_ready = pyqtSignal()
    reached_resolution = pyqtSignal(PromptResponse)
    global_resolution = pyqtSignal(PromptResponse)
    complete = pyqtSignal()
    aborted = pyqtSignal(int)
    def __init__(self,book_factory,last_id,prompt_cls,parent=None):
        # Run parent constructors
        QObject.__init__(self,parent)
        # Set helpers used to structure ui.
        self.last = last_id
        self.current = None
        self.queue = Queue()
        # Connect Signals
        self.book_ready.connect(self.__make_prompt, Qt.ConnectionType.QueuedConnection)
        self.global_resolution.connect(self.early_exit)
        self.reached_resolution.connect(self.__getNext)
        self.complete.connect(self.deleteLater,Qt.ConnectionType.QueuedConnection)
        self.complete.connect(lambda: print('Completed session!'))
        self.aborted.connect(lambda: print('EXITTED SESSION EARLY!'))
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
        # Set constructor args if depending on if viewing dialog for one or multiple existing backups.
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
'''
