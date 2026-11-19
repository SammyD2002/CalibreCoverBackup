# Initialize toplevel module items
from .cover_model import BookCoverItemModel,CoverDataRole,BookCoverItem,CheckProxyModel
from .cover_view import CoverListView
from .preview import PreviewWidget
from qt.core import (QDialog,QLabel,QDialogButtonBox,QVBoxLayout)
from typing import override

def destroyItem(item):
    if item.hasChildren():
        c = item.takeColumn(0)
        for ci in c:
            destroyItem(ci)
    item.clearData()    

def swapViewerModel(viewer,nmodel):
    model = viewer.model()
    smodel = viewer.selectionModel()
    viewer.setModel(nmodel)
    if model is None: return
    destroyItem(model.invisibleRootItem())
    model.clear()
    if smodel is not None: smodel.deleteLater()
    model.deleteLater()


def loadBookModel(book):
    #print(dir(book))
    #print(vars(book))
    model = BookCoverItemModel()
    #pm = db.cover(book.book_id,as_pixmap=True)
    pm = book.current_pixmap
    model.appendRow(base := BookCoverItem(pm))
    if pm is None: print('LOADED COVER WAS None!')
    elif pm.isNull(): print('Pixmap is not valid!')
    #m.destroyed.connect(lambda: print(f"Model destruction for book {book} detected"))
    model.setHorizontalHeaderLabels(["Backup Filename"])
    for r in range(len(book.ext_paths)):
        base.setChild(r, BookCoverItem(book.ext_paths[r]))
    return base,model

def prepareCoverWidgets(book,viewer,preview):
    omodel = viewer.model()
    if omodel is not None:
        omodel.clear()
        smodel = viewer.selectionModel()
        if smodel is not None: smodel.deleteLater()
        omodel.deleteLater()
    base,model = loadBookModel(book)
    viewer.setModel(pr := CheckProxyModel(None,model))
    #print('Finished setModel()')
    viewer.setRootIndex(root := pr.mapFromSource(base.index()))
    #print('ROOT VALIDITY:',root.isValid())
    viewer.setCurrentIndex(top := pr.index(0,0,root))
    rsize, rc = BookCoverItemModel.loadCover(pr,viewer.rootIndex())
    #viewer.rootCoverChanged.emit(rsize, rc.pixmap(rsize))
    preview.updateCurrent(rsize,rc.pixmap(rsize))
    csize, cc = BookCoverItemModel.loadCover(pr, top)
    #viewer.coverChanged.emit(csize, cc.pixmap(csize))
    preview.updateBackup(csize,cc.pixmap(csize))
    viewer.resizeColumnToContents(1)
    viewer.coverChanged.connect(preview.updateBackup)


class CoverSelectDialog(QDialog):
    default_prompt:str = 'Select cover image'
    default_prompt_m:str = 'Select cover image(s)'
    def __init__(self,book,parent=None,*,multi=False,prompt=None):
        QDialog.__init__(self,parent)
        # Set layout
        self.setLayout(lay := QVBoxLayout())
        # Intialize prompt message
        if prompt is not None: self.prompt = QLabel(prompt)
        elif multi: self.prompt = QLabel(self.default_prompt_m)
        else: self.prompt = QLabel(self.default_prompt)
        lay.addWidget(self.prompt)
        # Initialize viewer and preview widget.
        self.preview = PreviewWidget(self)
        self.viewer = CoverListView(self.preview,self)
        prepareCoverWidgets(book,self.viewer,self.preview)
        #self.viewer.setItemDelegate(StyledBookCoverDelegate())        
        lay.addWidget(self.viewer,3)
        lay.addWidget(self.preview,6)
        # Prepare the decision button box
        self.decision = QDialogButtonBox()
        self.decision.setStandardButtons(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.decision.accepted.connect(self.accept)
        self.decision.rejected.connect(self.reject)
        lay.addWidget(self.decision)
