from dataclasses import dataclass,field
from typing import override
from calibre_plugins.cover_backup.base import session_base,WorkerMixin,BackupStatus,Resolution#,wrap_log
from .book import BookBase
from .backup_result import BackupResult
from os import path,remove
from sys import stdout
from enum import IntEnum

@dataclass
class BackupTask:
    book: BookBase
    status: BackupStatus = BackupStatus.Initial
    w_path: str|None = None
    rm_paths: list[str]|None = None
    def __post_init__(self):
        if len(self.book.ext_paths) > 0: self.status = BackupStatus.Pending
        else: self.status = BackupStatus.Write
    @property
    def result_summary(self):
        return BackupResult.StatusResult[self.status](self.book,wpath=self.w_path,removed=self.rm_paths)

@dataclass
class BackupResolution(Resolution):
    '''
    Stores resolution of conflict due to existing backups
    '''
    action: BackupStatus
    paths: list[str]|None = field(kw_only=True,default=None) # If global, this will not be set, and all paths will be replaced.
    def checkMatch(self,task):
        # Check if the passed book matches this OverwriteMode. If it does, set task variables accordingly and return True. Otherwise, return False
        if self.match_scope(task.book) and self.match_id(task.book):
            task.status = self.action
            if self.action == BackupStatus.Overwrite:
                if self.isGlobal() or self.paths is None: task.rm_paths = book.ext_paths
                else: task.rm_paths = self.paths
                task.rm_paths.sort()
            return True
        return False
'''
@dataclass
class session_backup(session_base):
	@override
	def check_conflict(self, book, *, abort=None,log=None,notifications=None):
		#Gets conflicting paths, then returns according to ow_mode.
		cfl,paths = super().check_conflict(book)
		if cfl:
			msg = f'\t\tExisting backup(s) found at {paths} '
			if self.ow_mode: msg += 'WILL be replaced.'
			else: msg += 'will NOT be replaced.'
			log.info(msg)
		else: log.info(f'\t\tNo existing backup(s) were found.')
		return (self.ow_mode or not cfl),[p for p in paths if path.abspath(p) != book.backup_path]
'''
class session_backup(session_base):
    def __init__(self,ow_modes,*args,**kwargs):
        super().__init__(*args,**kwargs)
        '''
        self.ow_global = []
        self.ow_single = []
        for ow in ow_modes:
            if ow.isGlobal(): self.ow_global.append(ow)
            else: self.ow_single.append(ow)
        '''
        self.ow_modes = ow_modes
        print(f'Starting session with overwrite mode "{ow_modes}"...')
        self.written = []
        self.skipped = []
        self.overwritten = []
    def _make_task(self,book_id):
        return BackupTask(super().do_book(book_id))
    def _find_resolution(self, t):
        '''
        Override in UI to do prompt and return pending if no ow_modes match.
        '''
        if t.status == BackupStatus.Pending: # If status is pending, handle conflict
            #marr = [(OverwriteMode.Scope.Multi if len(t.book.ext_paths) > 1 else OverwriteMode.Scope.Single),OverwriteMode.Scope.All]
            #print(f'Detected Scope: {marr[0]}')
            #mode = OverwriteMode.Scope.Multi if len(t.book.ext_paths) > 1 else OverwriteMode.Scope.Single
            for m in self.ow_modes:
                if m.checkMatch(t): break
                '''
                if m.scope == mode or m.scope == OverwriteMode.Scope.All:
                    print(f'Setting from mode {m.scope} to action {m.action}')
                    t.status = m.action
                    break
                elif m.scope * -1 == t.book.book_id: 
                    t.status = m.action
                    t.rm_paths = m.paths.sort()
                    break
                '''
            if t.status == BackupStatus.Pending:
                print(f'WARNING: Conflict not resolved, skipping {t.book.book_id}...')

    def _process_task(self, t):
        '''
        Check task status and work accordingly.
        '''
        if t.status == BackupStatus.Skip: self.skipped.append(t)
        elif t.status == BackupStatus.Write:
            t.rm_paths = t.book.ext_paths
            t.w_path = t.book.write_cover()
            self.written.append(t) 
        elif t.status == BackupStatus.Overwrite:
            # Write to BasePath, then remove all files that are not base path.
            if t.rm_paths is None:
                t.w_path = t.book.write_cover(t.book.base_path)
                t.rm_paths = [p for p in t.book.ext_paths if p != t.w_path]
            else:
                t.w_path = t.book.write_cover(t.rm_paths.pop(0))
            for op in t.rm_paths: # Accounts for duplicates of the written path by ensuring we don't remove the path we just wrote.
                if op != t.w_path: remove(op)
            self.overwritten.append(t)
        #print(t.result_summary.summarize_full())
        return t

    @override
    def do_book(self,book_id):
        '''
        Process book <book_id>.
        '''
        #print('Doing id',book_id)
        t = self._make_task(book_id)
        if t is None: return
        # Handle conflict based on configured modes.
        self._find_resolution(t)
        return self._process_task(t)
        #print(t)
    @override
    def summarize_results(self):
        return len(self.skipped) + len(self.written) + len(self.overwritten), [f'SKIPPED:{("\n\t" + "\n\t".join([r.result_summary.summarize_brief() for r in self.skipped])) if len(self.skipped) > 0 else " NONE!"}',
        f'WRITTEN:{("\n\t" + "\n\t".join([r.result_summary.summarize_brief() for r in self.written])) if len(self.written) > 0 else " NONE!"}',
        f'OVERWRITTEN:{("\n\t" + "\n\t".join([r.result_summary.summarize_brief() for r in self.overwritten])) if len(self.overwritten) > 0 else " NONE!"}']
'''
@dataclass
class backup_noninteractive(session_backup):
	@staticmethod
	def process(this,*,abort=None,log=None,notifications=None):
		skipped = []
		written = []
		notifications.put_nowait((0.01,'Retrieving title metadata...'))
		books = this.get_books()
		bc = len(books)
		pc = 0
		for b in books:
			if abort.isSet(): break
			notifications.put(((pc/bc) + 0.01,f'Processing {b.title} [{pc+1}/{bc}]'))
			log.info(f'Starting {b.title} ({b.book_id}):')
			log.info(f'\tFinding existing backups for {b.book_id}...')
			ok,ext_paths = this.check_conflict(b,abort=abort,log=log,notifications=notifications)
			if ok:
				log.info(f"\tWriting Backup File...")
				this.write_backup(b,ext_paths)
				log.info(f"\t\tWRITTEN: {b.backup_path}")
				if len(ext_paths) > 0: log.info(f"\t\tREMOVED: '{'\', \''.join(ext_paths)}'")
				written.append(f'  {b.title} -> {b.backup_path}')
			else:
				if len(ext_paths) == 0: ext_paths.append(b.backup_path)
				skipped.append(f'  {b.title}: {"\',\'".join(ext_paths)}\'')
			pc += 1
			log.info(f'Completed {b.title} ({b.book_id}).')
		if abort.isSet(): log.error(f'Aborted after {pc}/{bc} books processed.')
		log.info('Job complete!')
		log.info(f'{len(written)} COVER(S) WRITTEN')
		log.info('\n'.join(written))
		log.info(f'{len(skipped)} COVER(S) SKIPPED')
		log.info('\n'.join(skipped))
'''
