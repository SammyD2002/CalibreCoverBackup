import init_calibre
from calibre.library import db
api = db('/home/sam/Documents/LocalBooks').new_api
from base.backup_result import *
from base.book import BookBase,BookClassFactory
Book = BookClassFactory(BookBase,api,'/home/sam/Pictures/Covers')
Samples = [Book(1),Book(2),Book(3),Book(4)]
