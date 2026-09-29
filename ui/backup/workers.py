'''
ConflictHandler: Validates tasks and triggers conflict dialogs before forwarding them.
BackupWriter: Write/Skip covers.
'''
from calibre_plugins.cover_backup.base import BackupStatus,BackupTask
from dataclasses import dataclass
from qt.core import (QObject,pyqtSignal)
from queue import Queue,Empty,ShutDown
from os import path

@dataclass
class PromptRequest:
    book: BackupTask
    is_last: bool
    multi: bool

@dataclass
class PromptResponse:
    book_id: int|None # The id of the book in question
    overwrite: bool # The result (whether to overwrite or not)


# Checks for path conflicts before forwarding book to BackupWriter.
# If conflict is found, mark as in progress and allow BackupWriter to recieve resolved signal.
class ConflictHandler(QObject):
    taskProcessed = pyqtSignal(BackupTask)
    processedAll = pyqtSignal()
    needsResolution = pyqtSignal(PromptRequest)
    def __init__(self, session, parent=None):
        QObject.__init__(self,parent)
        self.session = session
    def processTask(self, task):
        '''
        Used to check existing paths, sending them to gui as needed. 
        '''
        print(f'Processing {task}')
        ok,paths = self.session.check_conflict(task,processed=self.taskProcessed,conflicts=self.needsResolution)
        #if ok: task.status = BackupStatus.Overwrite
        #self.taskProcessed.emit(task)
        

class BackupWriter(QObject):
    skipped = pyqtSignal(BackupTask)
    written = pyqtSignal(BackupTask)
    complete = pyqtSignal()
    def __init__(self,session,parent=None):
        QObject.__init__(self,parent)
        self.session = session
        self.tasks = Queue()
        # A list of ids to overwrite
        self.overwrite = []
        # A list of ids to skip
        self.skip = []
        self.glr = None
        # Current Task. Used to check if a task is running.
        self.current = None
        self.written.connect(self.do_write)
    def do_write(self,task):
            rm_paths = [p for p in task.ext_paths if path.abspath(p) != path.abspath(task.backup_path)]
            self.session.write_backup(task,rm_paths)
    def enqueue_book(self,task):
        #print(f'WRITER: Enquing {task}')
        was_empty = self.tasks.empty()
        self.tasks.put(task)
        if was_empty: self.process_tasks()
    def update_book(self,res):
        if res.overwrite: self.overwrite.append(res.book_id)
        else: self.skip.append(res.book_id)
        self.process_tasks()
    def update_global(self,res):
        if res.overwrite: self.glr = BackupStatus.Overwrite
        else: self.glr = BackupStatus.Skip
        self.process_tasks()
    def closeQueue(self):
        self.tasks.shutdown()
        self.process_tasks()
    def exitEarly(self):
        self.tasks.shutdown(True)
        self.process_tasks()
    def findStatus(self,task):
        if task.status != BackupStatus.Pending: return task.status
        elif task.book_id in self.overwrite: return BackupStatus.Overwrite
        elif task.book_id in self.skip: return BackupStatus.Skip
        elif self.glr is not None: return self.glr
        else: return BackupStatus.Pending
    # Trigger event to process tasks if new task added or resolution marked.
    def process_tasks(self):
        #print('WRITER: Processing Tasks...')
        try:
            # If we do not have a current task set, get the next task in the queue.
            if self.current is None: self.current = self.tasks.get_nowait()
            while self.current is not None:
                #print(f'Handling {self.current}')
                # Get updated status
                s = self.current.status = self.findStatus(self.current)
                # Check status.
                # Break out of the loop if still pending
                if s == BackupStatus.Pending: break
                # Write backup if set to overwrite
                elif s == BackupStatus.Overwrite: self.written.emit(self.current)
                # Skip if set to skip
                elif s == BackupStatus.Skip: self.skipped.emit(self.current)
                # Update the current task.
                self.current = self.tasks.get_nowait()

        except Empty:
            self.current = None

        except ShutDown:
            # Exit the event loop, as all books have been processed.
            self.complete.emit()


