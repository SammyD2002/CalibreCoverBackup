from dataclasses import dataclass
from typing import override
from calibre_plugins.cover_backup.base import session_base,wrap_log,RestoreStatus
from calibre_plugins.cover_backup.base.restore_result import RestoreResult
from .book import BookBase
from os import path
from sys import stdout
import logging
'''
@dataclass
class session_restore(session_base):
	@override
	def check_conflict(self, book, *, abort=None,log=None,notifications=None):
		#If only one backup exists, we are okay and can return. Otherwise, we are not okay and must return False.
		cfl,paths = super().check_conflict(book)
		if len(paths) == 1:
			msg = f"\t\tExisting backup found at '{paths[0]}' will be restored"
			if self.ow_mode: msg += 'WILL be replaced.'
			log.info(msg)
		elif not cfl: log.info(f'\t\tNo existing backup(s) were found.')
		else: log.info('Multiple existing backups were found.')
		return (len(paths) == 1),paths
'''
@dataclass
class RestoreTask:
    book: BookBase
    status: RestoreStatus = RestoreStatus.Initial
    r_path: str|None = None
    def __post_init__(self):
        if len(self.book.ext_paths) == 1: self.status = RestoreStatus.Restore
        else: self.status = RestoreStatus.Pending
        
    @property
    def result_summary(self):
        return RestoreResult.StatusResult[self.status](self.book,rpath=self.r_path)


class session_restore(session_base):
    def __init__(self,br_mode,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.br_mode = br_mode
        self.skipped = []
        self.restored = []

    def do_book(self,book_id):
        t = RestoreTask(super().do_book(book_id),RestoreStatus.Initial)
        # Handle pending here.
        if t.status == RestoreStatus.Pending: t.status = RestoreStatus.Restore if self.br_mode else RestoreStatus.Skip
        # Restore if possible, otherwise skip.
        if t.status == RestoreStatus.Restore:
            t.r_path = t.book.restore_cover()
            self.restored.append(t)
        else: self.skipped.append(t)

    @override
    def summarize_results(self):
        print(f'SKIPPED:{("\n\t" + "\n\t".join([r.result_summary.summarize_brief() for r in self.skipped])) if len(self.skipped) > 0 else " NONE!"}')
        print(f'RESTORED:{("\n\t" + "\n\t".join([r.result_summary.summarize_brief() for r in self.restored])) if len(self.restored) > 0 else " NONE!"}')

'''
@dataclass
class restore_noninteractive(session_restore):
	@staticmethod
	@wrap_log
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
				log.info(f"\tRestoring Backup File...")
				this.restore_backup(b,ext_paths)
				log.info(f"\t\tRESTORED: {ext_paths[0]}")
				if this.ow_mode: log.info(f"\t\tREMOVED: '{'\', \''.join(ext_paths)}'")
				written.append(f'  {b.backup_path} -> {b.title}')
			else:
				if len(ext_paths) == 0: ext_paths.append('<BACKUP NOT FOUND>')
				skipped.append(f'  {b.title}: {"\',\'".join(ext_paths)}\'')
			pc += 1
			log.info(f'Completed {b.title} ({b.book_id}).')
		if abort.isSet(): log.error(f'Aborted after {pc}/{bc} books processed.')
		log.info('Job complete!')
		log.info(f'{len(written)} COVER(S) RESTORED')
		log.info('\n'.join(written))
		log.info(f'{len(skipped)} COVER(S) SKIPPED')
		log.info('\n'.join(skipped))

'''
