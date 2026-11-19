from enum import IntEnum
from typing import override
from os import path
from ..base import BackupStatus,Result

class BackupResult(Result):
    def __init_subclass__(cls, status: BackupStatus, **kwargs):
        '''
        Map status to subclass
        '''
        cls.status = status
        BackupResult.StatusResult[status] = cls
        super().__init_subclass__(**kwargs)

BackupResult.StatusResult = dict()

class UnprocessedBase(BackupResult, status=BackupStatus.Initial):    
    def __init__(self,book,changed=False,**kwargs):
        super().__init__(book,changed)

class ProcessedBase(UnprocessedBase, status=BackupStatus.Pending):
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
    LONG: Aborted Backup Creation at <TITLE> [ID]
    SHORT: <TITLE> [ID]: ABORTED
'''
class Aborted(UnprocessedBase, status=BackupStatus.Abort):
    def __init__(self,book,**kwargs):
        super().__init__(book)
    @override
    def summarize_full(self):
        return f"Aborted Backup Creation at '{self.header}'."
    @override
    def summarize_brief(self):
        return f"{self.header}: ABORTED"

'''
Skipped Format
LONG: 
    Skipped backup creation for <TITLE> [ID].
      Kept '/path/to/exsisting_backup1'
      Kept '/path/to/exsisting_backup2'
      ...
SHORT: <TITLE> [ID]: KEPT '<ext_1>','<ext_2>',...
'''
class Skipped(ProcessedBase, status=BackupStatus.Skip):
    def __init__(self,book,**kwargs):
        super().__init__(book,False)
    @ProcessedBase.long_header.getter
    def long_header(self):
        return f"Skipped backup creation for {self.header}."
    @override
    def summarize_brief(self):
        return f"{self.header}: Kept '{'\',\''.join([path.basename(p) for p in self.existing])}'"

'''
Written Format
LONG: 
    Created new backup for <TITLE> [ID]
      Wrote '/path/to/new_backup'
      Kept '/path/to/exsisting_backup1'
      Kept '/path/to/exsisting_backup2'
      ...
SHORT: <TITLE> [ID]: WROTE <BASENAME>, KEPT '<ext_1>','<ext_2>',...
SHORT V2: <TITLE> [ID]: WROTE <BASENAME>
'''
class Written(ProcessedBase, status=BackupStatus.Write):
    def __init__(self,book,wpath=None,**kwargs):
        super().__init__(book,True)
        self.location = wpath if wpath is not None else book.unique_path
    @ProcessedBase.long_header.getter
    def long_header(self):
        return f"Created new backup for {self.header}."
    @ProcessedBase.prefix_lines.getter
    def prefix_lines(self):
        return [self.long_header, f"  Wrote '{self.location}'"]
    @override
    def summarize_brief(self):
        return f"{self.header}: Wrote '{path.basename(self.location)}'"

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
'''
class Overwritten(Written, status=BackupStatus.Overwrite):
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
