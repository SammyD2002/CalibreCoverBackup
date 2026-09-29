from dataclasses import dataclass
from calibre_plugins.cover_backup.base import BackupTask
@dataclass
class PromptRequest:
    book: BackupTask
    is_last: bool
    multi: bool

@dataclass
class PromptResponse:
    book_id: int|None # The id of the book in question
    overwrite: bool # The result (whether to overwrite or not)
