from calibre_plugins.cover_backup.base import BackupStatus,BackupTask
from calibre_plugins.cover_backup.ui.backup.workers import ConflictHandler,BackupWriter,PromptRequest,PromptResponse
from calibre.constants import DEBUG
from os import path,remove
from qt.core import (Qt,QObject,pyqtSignal)
import traceback
# Suppress wrapper for member functions
def msuppress(fn):
    def nfn(self,*args,**kwargs):
        try:
            return fn(self,*args,**kwargs)
        except:
            self.log.error(traceback.format_exc())
    return nfn
class Helper(QObject):
    start_book = pyqtSignal(BackupTask)
    all_started = pyqtSignal()
    destroySession = pyqtSignal()
    done = pyqtSignal()
    def __init__(self,session,loop,notifications,log):
        QObject.__init__(self,loop)
        self.log = log
        self.notifications = notifications
        self.session = session
        self.deleted_session = False
        self.handler = ConflictHandler(session,loop)
        self.deleted_handler = False
        self.writer = BackupWriter(session,loop)
        self.deleted_writer = False
        self.start_book.connect(self.handler.processTask,Qt.ConnectionType.QueuedConnection)
        self.all_started.connect(self.handler.processedAll,Qt.ConnectionType.QueuedConnection)
        self.handler.taskProcessed.connect(self.printStarted)
        self.handler.destroyed.connect(self.ch_destroyed)
        self.session.complete.connect(self.s_complete,Qt.ConnectionType.QueuedConnection)
        self.destroySession.connect(self.session.deleteLater, Qt.ConnectionType.QueuedConnection)
        self.session.destroyed.connect(self.log_s_destroyed,Qt.ConnectionType.DirectConnection)
        self.writer.destroyed.connect(self.bw_destroyed)
        #self.destroyed.connect(self.h_destroyed)
        #self.destroyed.connect(self.quit)
        self.hasPrompt = False
        self.books = []
        self.written = []
        self.skipped = []
    def prepare_signals(self):
        self.__prepareHelperSignals()
        self.__prepareHandlerSessionSignals()
        self.__prepareHandlerWriterSignals()
        self.__prepareSessionWriterSignals()
    
    def __prepareHelperSignals(self):
        self.writer.skipped.connect(self.printSkipped)
        self.writer.written.connect(self.printWritten)
        self.writer.complete.connect(self.writer.deleteLater)
        self.handler.processedAll.connect(self.handler.deleteLater)
        self.session.aborted.connect(self.printAborted,Qt.ConnectionType.QueuedConnection)
        #self.writer.complete.connect(self.quit,Qt.ConnectionType.QueuedConnection)
        self.session.book_ready.connect(self.printPrompt,Qt.ConnectionType.QueuedConnection)
        self.session.reached_resolution.connect(self.promptDone,Qt.ConnectionType.QueuedConnection)
        self.session.global_resolution.connect(self.promptDone,Qt.ConnectionType.QueuedConnection)
        self.session.aborted.connect(self.promptDone,Qt.ConnectionType.QueuedConnection)
    
    def __prepareHandlerSessionSignals(self):
        self.handler.needsResolution.connect(self.session.getResolution,Qt.ConnectionType.QueuedConnection)
        self.handler.processedAll.connect(self.session.allInitialized,Qt.ConnectionType.QueuedConnection)
    
    def __prepareHandlerWriterSignals(self):
        self.handler.taskProcessed.connect(self.writer.enqueue_book,Qt.ConnectionType.QueuedConnection)
        self.handler.processedAll.connect(self.writer.closeQueue,Qt.ConnectionType.QueuedConnection)
    
    def __prepareSessionWriterSignals(self):
        self.session.aborted.connect(self.writer.exitEarly,Qt.ConnectionType.QueuedConnection)
        self.session.reached_resolution.connect(self.writer.update_book,Qt.ConnectionType.QueuedConnection)
        self.session.global_resolution.connect(self.writer.update_global,Qt.ConnectionType.QueuedConnection)
    def ch_destroyed(self):
        self.log.debug('Destroyed Conflict Handler.')
        self.deleted_handler = True
        self.__check_del()
    def bw_destroyed(self):
        self.log.debug('Destroyed backup writer')
        self.deleted_writer = True
        self.__check_del()
    def s_complete(self):
        self.log.debug('Completed session object')
        self.deleted_session = True
        self.destroySession.emit()
        self.__check_del()
    def log_s_destroyed(self):
        self.log.debug('Destroyed session object')
    def __check_del(self):
        if self.deleted_handler and self.deleted_writer and self.deleted_session: self.quit()
    def make_samples(self,size):
        for i in range(250,250+size):
            b = BackupTask(i,f'Title {i}',[f'Author(s) {i}'],self.session.backup_path)
            self.books.append(b)
        self.last = size - 1

    def quit(self):
        self.log.debug('Quitting helper...')
        self.done.emit()
        self.logSummary()
        self.deleteLater()
        #self.parent().exit()

    def prepare(self):
        self.prepare_signals()
        self.total = len(self.books)
        self.count = 0
        for b in self.books:
            self.start_book.emit(b)
        self.all_started.emit()
    
    def __update_progress(self):
        if self.hasPrompt or self.count == self.total: return
        msg = f'Processing Book {self.count + 1}/{self.total}'
        prog = (self.count / self.total) + 0.01
        self.notifications.put_nowait((prog,msg))
    
    def printPrompt(self):
        self.hasPrompt = True
        self.notifications.put_nowait((0,'Waiting for response to prompt...'))
    
    def promptDone(self,res):
        self.hasPrompt = False
        self.__update_progress()
    
    def printStarted(self,task):
        self.log.debug('Started',self.__summarize_book(task,processed=False))
    
    def printWritten(self,task):
        self.log.debug('Wrote',self.__summarize_book(task,processed=False))
        self.count += 1
        self.written.append(task)
        self.__update_progress()
    
    def printSkipped(self,res):
        self.log.debug('Skipped:',self.__summarize_book(res,processed=False))
        self.count += 1
        self.skipped.append(res)
        self.__update_progress()

    
    def printAborted(self,res):
        self.log.info('Aborted:',res)
        self.quit()
        
    def __summarize_book(self,b,*,processed=True,written=True):
        HEADER = f'{b.title} [{b.book_id}]'
        if not processed: return HEADER
        if written: return f"{HEADER}: Wrote '{b.backup_path}'" + (f", Replaced '{','.join(b.ext_paths)}'" if len(b.ext_paths) > 0 else "")
        else: return f"{HEADER}: 'Skipped {b.backup_path}', Kept '{','.join(b.ext_paths)}'"

                
    def logSummary(self):
        '''
        SUMMARY: X/Y Books Processed, Z Covers Written
        UNPROCESSED: U/Y
            TITLE [ID]
            ...
        WRITTEN: W/Y
            TITLE [ID]: Wrote <PATH>, Replaced <PATHS>
            ...
        SKIPPED: S/Y
            TITLE [ID]: Skipped <PATH>, Kept <PATHS>
            ...
        X/Y Books Written, Z/Y Books Skipped, W/Y Books Unprocessed
        '''        
        wc = len(self.written)
        sc = len(self.skipped)
        self.log.info(f'BACKUP SUMMARY: {wc + sc}/{self.total} book(s) processed, {wc} backup(s) created.')
        if (uc := self.total - (wc + sc)) != 0:
            self.log.info(f'UNPROCESSED: {uc}/{self.total}')
            for b in self.books:
                self.log.info(f'\t{self.__summarize_book(b,processed=False)}')
        if wc != 0:
            self.log.info(f'WRITTEN: {wc}/{self.total}')
            for b in self.written:
                self.log.info(f'\t{self.__summarize_book(b)}')
        if sc != 0:
            self.log.info(f'SKIPPED: {sc}/{self.total}')
            for b in self.skipped:
                self.log.info(f'\t{self.__summarize_book(b,written=False)}')


        
'''
class InteractiveBackup(ChainAction):
    # replace with the name of your action
    name = 'Interactive Cover Backup'
    support_scopes = True
    def run(self, gui, settings, chain):
        ids = chain.scope().get_book_ids()
        db = gui.current_db.new_api
        session = session_interactive(ids,db,'/home/sam/Pictures/Covers',gui)
        job = ThreadedJob('cover_backup','Back up the covers of the selected books.',
            suppress(session_interactive.process),
            [session],
            dict(), lambda j:j)
        gui.job_manager.run_threaded_job(job)

'''
