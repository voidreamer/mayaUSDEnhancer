from typing import List

from PySide2 import QtGui, QtCore
from pxr import Usd
from .usdUtils import get_prim_info, get_child_prims, PrimInfo, get_variant_sets, has_payload


class UsdTreeModel(QtGui.QStandardItemModel):
    def __init__(self, stage: Usd.Stage):
        super().__init__()
        self.stage = stage
        self.setHorizontalHeaderLabels(['Prim Name', 'Type', 'Kind', 'Purpose', 'Variant Sets', 'Has Payload'])
        self.populate_model()

    def populate_model(self):
        root_prim = self.stage.GetPseudoRoot()
        self.populate_prim(root_prim, self.invisibleRootItem())

    def populate_prim(self, prim: Usd.Prim, parent_item: QtGui.QStandardItem):
        prim_info = get_prim_info(prim)
        items = self.create_row(prim_info, prim)
        parent_item.appendRow(items)

        for child_prim in get_child_prims(prim):
            self.populate_prim(child_prim, items[0])

    def create_row(self, prim_info: PrimInfo, prim: Usd.Prim) -> List[QtGui.QStandardItem]:
        name_item = QtGui.QStandardItem(prim_info.name)
        name_item.setData(str(prim_info.path), QtCore.Qt.UserRole)

        variant_sets = get_variant_sets(prim)
        variant_sets_str = ", ".join([f"{vs.name}: {vs.current_selection}" for vs in variant_sets])

        has_payload_str = "Yes" if has_payload(prim) else "No"

        return [
            name_item,
            QtGui.QStandardItem(prim_info.type_name),
            QtGui.QStandardItem(prim_info.kind),
            QtGui.QStandardItem(prim_info.purpose),
            QtGui.QStandardItem(variant_sets_str),
            QtGui.QStandardItem(has_payload_str)
        ]
