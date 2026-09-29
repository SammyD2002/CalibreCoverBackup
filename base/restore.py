from dataclasses import dataclass
from typing import override
from calibre_plugins.cover_backup.base import session_base,wrap_log
from os import path
from sys import stdout
import logging
@dataclass
class session_restore(session_base):
	@override
	def check_conflict(self, book, *, abort=None,log=None,notifications=None):
		'''
		If only one backup exists, we are okay and can return. Otherwise, we are not okay and must return False.
		'''
		cfl,paths = super().check_conflict(book)
		if len(paths) == 1:
			msg = f"\t\tExisting backup found at '{paths[0]}' will be restored"
			if self.ow_mode: msg += 'WILL be replaced.'
			log.info(msg)
		elif not cfl: log.info(f'\t\tNo existing backup(s) were found.')
		else: log.info('Multiple existing backups were found.')
		return (len(paths) == 1),paths


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


