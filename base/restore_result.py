from typing import override
from os import path
from . import Result,RestoreStatus
# Possible Outcomes: Do not restore (no book), Do not restore (multiple candidates), Restore (retain backups), Restore (remove backups)

class RestoreResult(Result):
    def __init_subclass__(cls, status: RestoreStatus, **kwargs):
        '''
        Map status to subclass
        '''
        cls.status = status
        RestoreResult.StatusResult[status] = cls
        super().__init_subclass__(**kwargs)

RestoreResult.StatusResult = dict()

class UnprocessedBase(RestoreResult, status=RestoreStatus.Initial):    
    def __init__(self,book,changed=False,**kwargs):
        super().__init__(book,changed)

class ProcessedBase(UnprocessedBase, status=RestoreStatus.Pending):
    def __init__(self,book,changed=True):
        super().__init__(book,changed)
        self.existing = set(book.ext_paths)
    @property
    def long_header(self):
        return self.header
    @property
    def prefix_lines(self):
        return [self.long_header]
    @property
    def suffix_lines(self):
        return self._make_suffix_lines()
    
    def _make_suffix_lines(self, prefix='  Kept ', src=None):
        if src is None: src = self.existing
        return list([f"{prefix}'{p}'" for p in src])
    
    @override
    def summarize_full(self):
        return '\n'.join(self.prefix_lines + self.suffix_lines)
'''
Aborted Format:
    LONG: Aborted Restoration at <TITLE> [ID]
    SHORT: <TITLE> [ID]: ABORTED
'''
class Aborted(UnprocessedBase, status=RestoreStatus.Abort):
    def __init__(self,book,**kwargs):
        super().__init__(book)
    @override
    def summarize_full(self):
        return f"Aborted Backup Restoration at '{self.header}'."
    @override
    def summarize_brief(self):
        return f"{self.header}: ABORTED"

'''
Written Format
LONG: 
    Restored backup for <TITLE> [ID]
      Restored '/path/to/new_backup'
      Left '/path/to/exsisting_backup1'
      Left '/path/to/exsisting_backup2'
      ...
SHORT: <TITLE> [ID]: WROTE <BASENAME>, KEPT '<ext_1>','<ext_2>',...
SHORT V2: <TITLE> [ID]: WROTE <BASENAME>
'''
class Restored(ProcessedBase, status=RestoreStatus.Restore):
    def __init__(self,book,rpath=None,**kwargs):
        super().__init__(book,True)
        self.location = rpath if rpath is not None else book.base_path
    @ProcessedBase.long_header.getter
    def long_header(self):
        return f"Restored backup for {self.header}."
    @ProcessedBase.prefix_lines.getter
    def prefix_lines(self):
        return [self.long_header, f"  Restored '{self.location}'"]
    @override
    def _make_suffix_lines(self):
        if len(self.existing) == 1: return []
        else: return super()._make_suffix_lines(prefix='  Left ',src=[p for p in self.existing if p != self.location])
    @override
    def summarize_brief(self):
        return f"{self.header}: Restored '{path.basename(self.location) + (f' Left \'{'\',\''.join([path.basename(p) for p in self.existing])}\'' if len(self.existing) > 1 else '')}'"

'''
Skipped Format
LONG (NO BACKUPS): 
    Skipped backup restoration for <TITLE> [ID] (No backups found)
LONG (MULTIPLE BACKUPS)
    Skipped backup restoration for <TITLE> [ID].
      Kept '/path/to/exsisting_backup1'
      Kept '/path/to/exsisting_backup2'
      ...
SHORT (NO BACKUPS): <TITLE> [ID]: HAD NO BACKUPS
SHORT (MULTIPLE BACKUPS): <TITLE> [ID]: HAD BACKUPS LEFT '<ext_1>','<ext_2>',...
'''
class Skipped(ProcessedBase, status=RestoreStatus.Skip):
    def __init__(self,book,**kwargs):
        super().__init__(book,False)
    @ProcessedBase.long_header.getter
    def long_header(self): 
        return f"Skipped backup restoration for {self.header} ({('No backups found' if len(self.existing) > 1 else 'Multiple backups found')})."
    @override
    def _make_suffix_lines(self):
        if len(self.existing) > 1: return super()._make_suffix_lines(prefix='  At ')
        else: return []
    @override
    def summarize_brief(self):
        return f"{self.header}: {f'HAD BACKUPS AT \'{'\',\''.join([path.basename(p) for p in self.existing])}\'' if len(self.existing) > 1 else 'HAD NO BACKUPS'}"

'''
Overwritten Format
LONG: 
Updated backup(s) for <TITLE> [ID]
  Wrote '/path/to/new_backup'
  Replaced '/path/to/removed_backup1'
  Replaced '/path/to/removed_backup2'
  ...
  Kept '/path/to/exsisting_backup1'
  Kept '/path/to/exsisting_backup2'
  ...
SHORT V1: <TITLE> [ID]: WROTE <BASENAME>, REPLACED '<rm_1>','<rm_2>',..., KEPT '<ext_1>','<ext_2>',...
SHORT V2: <TITLE> [ID]: WROTE <BASENAME>, REPLACED '<rm_1>','<rm_2>',...
class Overwritten(Written, status=RestoreStatus.Overwrite):
    def __init__(self,book,*,wpath,removed):
        super().__init__(book,wpath)
        if wpath in self.existing: self.existing.remove(wpath)
        self.removed = set(p for p in removed if p != wpath)
        self.existing -= self.removed
        
    @ProcessedBase.long_header.getter
    def long_header(self):
        return f"Updated backup(s) for {self.header}."
    @override
    def _make_suffix_lines(self):
        return super()._make_suffix_lines('  Replaced ', self.removed) + super()._make_suffix_lines()
    @override
    def summarize_brief(self):
        base = super().summarize_brief()
        suffix = '' if len(self.removed) > 0 else "','".join(self.removed)
        return base + suffix 
'''
