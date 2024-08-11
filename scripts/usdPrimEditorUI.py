from PySide2 import QtWidgets, QtCore
from .usdTreeModel import UsdTreeModel
from .usdUtils import PrimPurpose, set_prim_kind, set_prim_purpose, get_stage_as_text, update_stage_from_text
from pxr import Usd, Sdf
import maya.cmds as cmds
import mayaUsd


class UsdPrimEditor(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(UsdPrimEditor, self).__init__(parent)
        self.stage = None
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("USD Prim Editor")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)

        layout = QtWidgets.QVBoxLayout(self)

        # Tree view
        self.tree_view = QtWidgets.QTreeView()
        self.tree_view.setAlternatingRowColors(True)
        self.tree_view.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tree_view.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        # Property editors
        property_layout = QtWidgets.QHBoxLayout()
        self.kind_combo = QtWidgets.QComboBox()
        self.kind_combo.addItems(["", "component", "subcomponent", "assembly", "group"])
        self.purpose_combo = QtWidgets.QComboBox()
        self.purpose_combo.addItems([p.value for p in PrimPurpose])

        property_layout.addWidget(QtWidgets.QLabel("Kind:"))
        property_layout.addWidget(self.kind_combo)
        property_layout.addWidget(QtWidgets.QLabel("Purpose:"))
        property_layout.addWidget(self.purpose_combo)
        property_layout.addStretch()

        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        self.refresh_button = QtWidgets.QPushButton("Refresh")
        self.apply_button = QtWidgets.QPushButton("Apply Changes")
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.apply_button)
        button_layout.addStretch()

        # Stage text editor
        self.stage_text_edit = QtWidgets.QPlainTextEdit()
        self.stage_text_edit.setReadOnly(True)
        self.update_stage_button = QtWidgets.QPushButton("Update Stage")

        # Add widgets to layout
        layout.addWidget(self.tree_view)
        layout.addLayout(property_layout)
        layout.addLayout(button_layout)
        layout.addWidget(self.stage_text_edit)
        layout.addWidget(self.update_stage_button)

        # Connect signals
        self.refresh_button.clicked.connect(self.refresh_tree_view)
        self.apply_button.clicked.connect(self.apply_changes)
        self.update_stage_button.clicked.connect(self.update_stage_from_text)

        # We'll connect the tree_view selection signal in refresh_tree_view

    def refresh_tree_view(self):
        selected = cmds.ls(sl=1, ufe=1)
        if selected:
            try:
                proxy_shape, _ = selected[0].split(',')
                self.stage = mayaUsd.ufe.getStage(proxy_shape)
                model = UsdTreeModel(self.stage)
                self.tree_view.setModel(model)
                self.tree_view.expandAll()

                # Connect the selection changed signal after setting the model
                self.tree_view.selectionModel().selectionChanged.connect(self.update_property_editors)

                self.update_stage_text()
            except Exception as e:
                print(f"Error refreshing tree view: {str(e)}")
        else:
            cmds.warning("No USD prim selected.")

    def update_property_editors(self):
        selected_indexes = self.tree_view.selectedIndexes()
        if selected_indexes:
            kind = self.tree_view.model().item(selected_indexes[0].row(), 2).text()
            purpose = self.tree_view.model().item(selected_indexes[0].row(), 3).text()
            self.kind_combo.setCurrentText(kind)
            self.purpose_combo.setCurrentText(purpose)

    def apply_changes(self):
        selected_indexes = self.tree_view.selectedIndexes()
        if selected_indexes and self.stage:
            prim_path_str = selected_indexes[0].data(QtCore.Qt.UserRole)
            try:
                prim_path = Sdf.Path(prim_path_str)
                prim = self.stage.GetPrimAtPath(prim_path)

                if prim.IsValid():
                    new_kind = self.kind_combo.currentText()
                    if new_kind:
                        set_prim_kind(prim, new_kind)

                    new_purpose = self.purpose_combo.currentText()
                    if new_purpose:
                        set_prim_purpose(prim, PrimPurpose(new_purpose))

                    self.refresh_tree_view()
                else:
                    print(f"Invalid prim path: {prim_path_str}")
            except Exception as e:
                print(f"Error applying changes: {str(e)}")
        else:
            cmds.warning("No prim selected or stage not available.")

    def update_stage_text(self):
        if self.stage:
            self.stage_text_edit.setPlainText(get_stage_as_text(self.stage))

    def update_stage_from_text(self):
        if self.stage:
            try:
                update_stage_from_text(self.stage, self.stage_text_edit.toPlainText())
                self.refresh_tree_view()
            except Exception as e:
                print(f"Error updating stage: {str(e)}")


class UsdPrimEditorWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCentralWidget(UsdPrimEditor())


def show_usd_prim_editor():
    global usd_prim_editor
    try:
        usd_prim_editor.close()
        usd_prim_editor.deleteLater()
    except:
        pass
    usd_prim_editor = UsdPrimEditorWindow()
    usd_prim_editor.show()


# Run the tool
if __name__ == "__main__":
    show_usd_prim_editor()