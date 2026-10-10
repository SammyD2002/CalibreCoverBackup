import init_calibre
from calibre.library import db
from PyQt6.QtWidgets import QDialog,QApplication,QLabel
lib = db('/home/sam/Documents/LocalBooks').new_api
app = QApplication([])
d = QDialog()
l = QLabel('',d)
l.setPixmap(lib.cover(5,as_pixmap=True))
d.show()
app.exec()
