from PyQt6.QtGui import QIcon,QPixmap,QGuiApplication
from pathlib import Path
from sys import argv
app = QGuiApplication(argv)
#pm = QPixmap('/home/sam/Pictures/Covers/3_Terra Incognita [TimeCloneMike].jpg')
icn = QIcon()
icn.addFile('/home/sam/Pictures/Covers/3_Terra Incognita [TimeCloneMike].jpg')
pm = icn.pixmap(icn.availableSizes()[0])
icn.addPixmap(pm.scaled(500,500))

icn.addPixmap(pm.scaled(400,400))

print(icn.availableSizes())
