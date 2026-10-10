# Initialize toplevel module items
from .cover_model import StyledBookCoverDelegate,BookCoverItemModel,CoverDataRole,BookCoverItem
from .cover_view import CoverListView
from .preview import PreviewWidget

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


def loadBookModel(db,book):
    model = BookCoverItemModel()
    pm = db.cover(book.book_id,as_pixmap=True)
    model.appendRow(base := BookCoverItem(pm))
    if pm is None: print('LOADED COVER WAS NULL!')
    elif not pm.isNull(): print('Pixmap is not valid!')
    #m.destroyed.connect(lambda: print(f"Model destruction for book {book} detected"))
    model.setHorizontalHeaderLabels(["Backup Filename"])
    for r in range(len(book.ext_paths)):
        base.setChild(r, BookCoverItem(book.ext_paths[r]))
    return base,model

def prepareCoverWidgets(db,book,viewer,preview):
    omodel = viewer.model()
    if omodel is not None:
        omodel.clear()
        smodel = viewer.selectionModel()
        if smodel is not None: smodel.deleteLater()
        omodel.deleteLater()
    base,model = loadBookModel(db,book)
    viewer.setModel(model)
    viewer.setRootIndex(base.index())
    viewer.setCurrentIndex(top := model.index(0,0,viewer.rootIndex()))
    rsize, rc = BookCoverItemModel.loadCover(model,viewer.rootIndex())
    #viewer.rootCoverChanged.emit(rsize, rc.pixmap(rsize))
    preview.updateCurrent(rsize,rc.pixmap(rsize))
    csize, cc = BookCoverItemModel.loadCover(model, top)
    #viewer.coverChanged.emit(csize, cc.pixmap(csize))
    preview.updateBackup(csize,cc.pixmap(csize))
    viewer.resizeColumnToContents(1)
