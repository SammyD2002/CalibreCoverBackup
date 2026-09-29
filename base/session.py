from dataclasses import dataclass
from typing import override
from calibre_plugins.cover_backup.base import session_base
from os import path,remove
from sys import stdout
import logging
def wrap_log(fn):
	class ndummy:
		def __init__(self,log):
			self.log = log
		def put(self,msg,block=True,timeout=None):
			self.log.info(f'[{msg[0] * 100}%]: {msg[1]}')
		def put_nowait(self,msg):
			self.put(msg,False,None)
	class adummy:
		def __init__(self,log):
			self.log = log
		def isSet(self):
			return False
		def set(self):
			raise RuntimeError('Abort set!')
	def wrapper(*args,**kwargs):
		l = kwargs.get('log')
		if l is None:
			logger = logging.getLogger(__name__)
			logging.basicConfig(level=logging.DEBUG)
			l = kwargs.setdefault('log',logger)
		if kwargs.get('notifications') is None: kwargs.setdefault('notifications',ndummy(l))
		if kwargs.get('abort') is None: kwargs.setdefault('abort',adummy(l))
		fn(*args,**kwargs)
	return wrapper

@dataclass
class session_noninteractive(session_base):
	ow_mode: bool
	@override
	def check_conflict(self, book, *, abort=None,log=None,notifications=None):
		'''
		Gets conflicting paths, then returns according to ow_mode.
		'''
		ok,paths = super().check_conflict(book)
		if not ok:
			msg = f'\t\tExisting backup(s) found at {paths} '
			if self.ow_mode: msg += 'WILL be replaced.'
			else: msg += 'will NOT be replaced.'
			log.info(msg)
		else: log.info(f'\t\tNo existing backup(s) were found.')
		return (self.ow_mode or ok),[p for p in paths if path.abspath(p) != book.backup_path]
			
			
	
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

