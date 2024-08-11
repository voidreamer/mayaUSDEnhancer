# Model
from PySide2 import QtGui, QtCore
from pxr import Usd
from .usdUtils import get_prim_info, get_child_prims, PrimInfo


class UsdTreeModel(QtGui.QStandardItemModel):
    def __init__(self, stage: Usd.Stage):
        super().__init__()
        self.stage = stage
        self.setHorizontalHeaderLabels(['Prim Name', 'Type', 'Kind', 'Purpose'])
        self.populate_model()

    def populate_model(self):
        root_prim = self.stage.GetPseudoRoot()
        self.populate_prim(root_prim, self.invisibleRootItem())

    def populate_prim(self, prim: Usd.Prim, parent_item: QtGui.QStandardItem):
        prim_info = get_prim_info(prim)
        items = self.create_row(prim_info)
        parent_item.appendRow(items)

        for child_prim in get_child_prims(prim):
            self.populate_prim(child_prim, items[0])

    def create_row(self, prim_info: PrimInfo) -> List[QtGui.QStandardItem]:
        name_item = QtGui.QStandardItem(prim_info.name)
        name_item.setData(str(prim_info.path), QtCore.Qt.UserRole)
        return [
            name_item,
            QtGui.QStandardItem(prim_info.type_name),
            QtGui.QStandardItem(prim_info.kind),
            QtGui.QStandardItem(prim_info.purpose)
        ]
