from calibre_plugins.cover_backup.ui import LogPrefixWrapper
from calibre_plugins.cover_backup.base import BackupStatus,Resolution
from calibre_plugins.cover_backup.backup import BackupResolution,BackupResult,session_backup,BackupTask
from typing import override
from qt.core import (Qt,QObject,pyqtSignal,QEventLoop)
from dataclasses import dataclass,field
from collections import deque

@dataclass
class BackupResolutionRequest:
    book_id: int
    title: str
    authors: tuple[str,...]

@dataclass
class QBackupTask(BackupTask,QObject):
    sentPrompt: bool = field(kw_only=True,default=False)
    def __init__(self,book,parent=None):
        BackupTask.__init__(self,book)
        QObject.__init__(self,parent)
        book.setParent(self)

class ui_backup(session_backup,QObject):
    doBook = pyqtSignal(int) # Emitted to tell us to process a book by connecting it to do_book.
    needsResolution = pyqtSignal(int) # Connected to QObject on main thread used to trigger prompts. (id)
    processingComplete = pyqtSignal() # Emitted when processing is complete or aborted by user dialog response, will print final summary to log.
    jobComplete = pyqtSignal() # Emitted after final summary is printed, will initiate teardown.
    initialized: bool = False
    def __init__(self,*args,**kwargs):
        parent = kwargs.pop('parent',None)
        ph = kwargs.pop('prompt')
        if len(args) == 1: args.insert(0,[])
        session_backup.__init__(self,*args,**kwargs)
        self.base_log = self.log
        self.log = LogPrefixWrapper(self.log,'WORKER: ',base_interval=ph.log._interval)
        QObject.__init__(self,parent)
        # Turn ow_modes into a deque
        self.ow_modes = deque(self.ow_modes)
        self.task_queue = deque()
        # Used to store task where user aborted via dialog, and allows us to know when to QUIT.
        self.last_id = None
        self.abortedAt = None
        self.doBook.connect(self.do_book,Qt.ConnectionType.QueuedConnection)
        self.processingComplete.connect(self.finishSession)
        self.jobComplete.connect(self.deleteLater, Qt.ConnectionType.QueuedConnection)
        self.prompt_handler = ph

    @property
    def prompt_handler(self):
        return self.__phandler

    @prompt_handler.setter
    def prompt_handler(self,ph):
        assert ph is not None
        self.__phandler = ph
        self.needsResolution.connect(ph.getResolution,Qt.ConnectionType.QueuedConnection)
        self.destroyed.connect(ph.deleteLater,Qt.ConnectionType.DirectConnection)
        self.app_exit = ph.exit_event
        ph.appExit.connect(self.terminateSession)
        ph.resolutionReached.connect(self.recieveResolution,Qt.ConnectionType.QueuedConnection)

    def recieveResolution(self, br):
        #br = BackupResolution(scope,action,book_id=book_id,paths=paths)
        self.log.debug('Recieved Resolution',br)
        if br.isGlobal(): self.ow_modes.append(br)
        else: self.ow_modes.insert(0,br)
        self.do_book()

    def handleDialogAbort(self, t):
        self.abortedAt = t
    
    def finishSession(self):
        c,b,results = self.summarize_results()
        self.base_log.info('\n'.join(['SUMMARY:'] + results))
        self.jobComplete.emit()

    def terminateSession(self):
        self.deleteLater()
    
    @override
    def do_book(self,book_id=None):
        last_book = None
        self.log.debug(f'Starting book {book_id}')
        while last_book != self.last_id:
            if self.abort.isSet(): break
            t = super().do_book(book_id)
            if t is None:
                self.finishProcessing.emit()
                return
            last_book = t.book.book_id
            if t.status == BackupStatus.Pending: 
                self.log.debug('\tDid not get resolution, will return and wait for resolution...')
                self.task_queue.appendleft(t)
                return
            elif t.status == BackupStatus.Abort:
                self.log.debug('\tAborted!')
                self.abortedAt = t
            else:
                self.log.info(t.result_summary.summarize_full())
                if len(self.task_queue) > 0: continue
            break
        if last_book == self.last_id or self.abortedAt is not None or self.abort.isSet(): self.processingComplete.emit()

    @override
    def summarize_results(self):
        count, base = super().summarize_results()
        # Add appropriate header.
        if (a1 := self.abortedAt is not None): base.insert(0, f'Aborted via backup conflict dialog ({count}/{(total := len(self.task_queue) + 1 + count)} Title(s) Processed)')
        elif (a2 := self.abort.isSet()): base.insert(0, f'Aborted via job manager ({count}/{(total := len(self.task_queue) + count)} Title(s) Processed)') # No + 1, as the task should be re-enqueued if abort is set
        else: base.insert(0,f'{(total := count)} Title(s) Processed')
        if a1 or a2:
            base.append(f'UNPROCESSED:{("\n\t" + "\n\t".join([r.result_summary.summarize_brief() for r in self.task_queue])) if len(self.task_queue) > 0 else " NONE!"}')
            self.task_queue.clear()
        return count,total,base

    @override
    def _find_resolution(self, task):
        super()._find_resolution(task)
        if task.status == BackupStatus.Pending and not task.sentPrompt:
            self.needsResolution.emit(task.book.book_id) # Send signal to trigger prompt
            task.sentPrompt = True
        return task

    @override
    def _make_task(self,book_id):
        '''
        If book_id is valid but a task is enqueued, put the book_id to the back of the queue and return the task at the front of the queue.
        If book_id is NOT valid and a task is enqueued, pop and return the enqueued task.
        If book_id is valid and no task is enqueued, create and return a task for the book.
        If book_id is not valid and no task is enqueued, we are done here.
        '''
        tsk = None if book_id is None else QBackupTask(self.book_factory(book_id),parent=self)
        if len(self.task_queue) == 0: return tsk # Returns the new task or None if the book id was not valid.
        if tsk is not None: self.task_queue.append(tsk) # Push the new task if created from valid book id.
        return self.task_queue.popleft()


def execute_session(ids, book_factory,ow_modes=[],*,log,notifications,abort,prompt):
    l = QEventLoop(None)
    # Modes, Factory, KWARGS
    # Skip by default for now.
    log.debug('WORKER: Initializing ui_backup instance...')
    s = ui_backup(ow_modes,book_factory,log=log,notifications=notifications,abort=abort,parent=l,prompt=prompt)
    s.log.debug('Setting prompt handler in ui_backup instance...')
    #s.prompt_handler = prompt
    s.destroyed.connect(l.exit)
    s.last_id = ids[-1]
    s.log.debug('Emitting signals for ui_backup queue')
    for i in ids: s.doBook.emit(i)
    s.log.debug('Starting event loop...')
    l.exec()
    s.log.debug('Finished event loop...')
