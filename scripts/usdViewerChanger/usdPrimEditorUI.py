from PySide2 import QtWidgets, QtCore, QtGui
from .usdTreeModel import UsdTreeModel
from .usdUtils import (
    PrimPurpose, set_prim_kind, set_prim_purpose, get_stage_as_text,
    update_stage_from_text, get_variant_sets, set_variant_selection,
    has_payload, load_payload, unload_payload
)
from pxr import Usd, Sdf, UsdGeom, Gf
import maya.cmds as cmds
import mayaUsd


class ColorCodedItemDelegate(QtWidgets.QStyledItemDelegate):
    def paint(self, painter, option, index):
        if option.state & QtWidgets.QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())

        item_data = index.data(QtCore.Qt.UserRole)
        color = item_data.get('color', QtGui.QColor(255, 255, 255)) if item_data else option.palette.text().color()
        painter.setPen(color)
        painter.drawText(option.rect, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, index.data())


class UsdPrimEditor(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(UsdPrimEditor, self).__init__(parent)
        self.stage = None
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("USD Prim Editor")
        self.setMinimumSize(800, 600)

        treeLayout = QtWidgets.QVBoxLayout()

        self.setup_tree_view()
        self.setup_property_editors(treeLayout)
        self.setup_buttons(treeLayout)
        self.setup_stage_text_editor(treeLayout)
        self.setup_variant_sets(treeLayout)
        self.setup_payload_controls(treeLayout)

        propertiesLayout = QtWidgets.QVBoxLayout()
        self.setup_attr_primvar_editor(propertiesLayout)
        self.setup_time_samples_editor(propertiesLayout)

        mainLayout = QtWidgets.QHBoxLayout(self)
        mainLayout.addLayout(treeLayout)
        mainLayout.addLayout(propertiesLayout)

        self.connect_signals()

    def setup_tree_view(self):
        self.tree_view = QtWidgets.QTreeView()
        self.tree_view.setAlternatingRowColors(True)
        self.tree_view.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tree_view.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

    def setup_property_editors(self, layout):
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

        layout.addWidget(self.tree_view)
        layout.addLayout(property_layout)

    def setup_buttons(self, layout):
        button_layout = QtWidgets.QHBoxLayout()
        self.refresh_button = QtWidgets.QPushButton("Refresh")
        self.apply_button = QtWidgets.QPushButton("Apply Changes")
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.apply_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)

    def setup_stage_text_editor(self, layout):
        self.stage_text_edit = QtWidgets.QPlainTextEdit()
        self.stage_text_edit.setReadOnly(True)
        self.update_stage_button = QtWidgets.QPushButton("Update Stage")
        layout.addWidget(self.stage_text_edit)
        layout.addWidget(self.update_stage_button)

    def setup_variant_sets(self, layout):
        self.variant_set_layout = QtWidgets.QVBoxLayout()
        self.variant_set_layout.addWidget(QtWidgets.QLabel("Variant Sets:"))
        self.variant_set_widget = QtWidgets.QWidget()
        self.variant_set_widget.setLayout(self.variant_set_layout)
        layout.addWidget(self.variant_set_widget)

    def setup_payload_controls(self, layout):
        payload_layout = QtWidgets.QHBoxLayout()
        self.load_payload_button = QtWidgets.QPushButton("Load")
        self.unload_payload_button = QtWidgets.QPushButton("Unload")
        payload_layout.addWidget(QtWidgets.QLabel("Payload:"))
        payload_layout.addWidget(self.load_payload_button)
        payload_layout.addWidget(self.unload_payload_button)
        layout.addLayout(payload_layout)

    def setup_attr_primvar_editor(self, layout):
        self.attr_primvar_tree = QtWidgets.QTreeWidget()
        self.attr_primvar_tree.setHeaderLabels(["Name", "Value"])
        self.attr_primvar_tree.setItemDelegate(ColorCodedItemDelegate())

        attr_primvar_layout = QtWidgets.QVBoxLayout()
        attr_primvar_layout.addWidget(QtWidgets.QLabel("Attributes and Primvars:"))
        attr_primvar_layout.addWidget(self.attr_primvar_tree)

        button_layout = QtWidgets.QHBoxLayout()
        self.add_attr_button = QtWidgets.QPushButton("Add Attribute")
        self.add_primvar_button = QtWidgets.QPushButton("Add Primvar")
        self.edit_button = QtWidgets.QPushButton("Edit")
        self.remove_button = QtWidgets.QPushButton("Remove")
        button_layout.addWidget(self.add_attr_button)
        button_layout.addWidget(self.add_primvar_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.remove_button)

        attr_primvar_layout.addLayout(button_layout)
        layout.addLayout(attr_primvar_layout)

    def setup_time_samples_editor(self, layout):
        self.time_samples_tree = QtWidgets.QTreeWidget()
        self.time_samples_tree.setHeaderLabels(["Attribute", "Time", "Value"])

        time_samples_layout = QtWidgets.QVBoxLayout()
        time_samples_layout.addWidget(QtWidgets.QLabel("Time Samples:"))
        time_samples_layout.addWidget(self.time_samples_tree)

        time_samples_group = QtWidgets.QGroupBox()
        time_samples_group.setLayout(time_samples_layout)
        layout.addWidget(time_samples_group)

    def connect_signals(self):
        self.refresh_button.clicked.connect(self.refresh_tree_view)
        self.apply_button.clicked.connect(self.apply_changes)
        self.update_stage_button.clicked.connect(self.update_stage_from_text)
        self.load_payload_button.clicked.connect(self.load_selected_payload)
        self.unload_payload_button.clicked.connect(self.unload_selected_payload)
        self.add_attr_button.clicked.connect(self.add_attribute)
        self.add_primvar_button.clicked.connect(self.add_primvar)
        self.edit_button.clicked.connect(self.edit_attr_primvar)
        self.remove_button.clicked.connect(self.remove_attr_primvar)
        self.time_samples_tree.itemDoubleClicked.connect(self.edit_time_sample)

    def update_property_editors(self):
        selected_indexes = self.tree_view.selectedIndexes()
        if not selected_indexes:
            self.clear_editors()
            return

        model = self.tree_view.model()
        row = selected_indexes[0].row()

        kind_item = model.item(row, 2)
        purpose_item = model.item(row, 3)

        self.kind_combo.setCurrentText(kind_item.text() if kind_item else "")
        self.purpose_combo.setCurrentText(purpose_item.text() if purpose_item else "")

        prim = self.get_selected_prim()
        if not prim:
            return

        self.update_variant_sets(prim)
        self.update_payload_controls(prim)
        self.update_attr_primvar_list(prim)
        self.update_time_samples(prim)

    def clear_editors(self):
        self.kind_combo.setCurrentText("")
        self.purpose_combo.setCurrentText("")
        self.attr_primvar_tree.clear()
        self.clear_variant_sets()
        self.load_payload_button.setEnabled(False)
        self.unload_payload_button.setEnabled(False)
        self.time_samples_tree.clear()

    def update_variant_sets(self, prim):
        self.clear_variant_sets()
        for vs_info in get_variant_sets(prim):
            vs_layout = QtWidgets.QHBoxLayout()
            vs_layout.addWidget(QtWidgets.QLabel(vs_info.name))
            vs_combo = QtWidgets.QComboBox()
            vs_combo.addItems(vs_info.variants)
            vs_combo.setCurrentText(vs_info.current_selection)
            vs_combo.currentTextChanged.connect(lambda text, name=vs_info.name: self.set_variant(prim, name, text))
            vs_layout.addWidget(vs_combo)
            self.variant_set_layout.addLayout(vs_layout)

    def clear_variant_sets(self):
        for i in reversed(range(1, self.variant_set_layout.count())):
            self.variant_set_layout.itemAt(i).widget().setParent(None)

    def update_payload_controls(self, prim):
        has_payload_value = has_payload(prim)
        self.load_payload_button.setEnabled(has_payload_value)
        self.unload_payload_button.setEnabled(has_payload_value)

    def update_attr_primvar_list(self, prim):
        self.attr_primvar_tree.clear()
        for attr in prim.GetAttributes():
            self.add_attribute_to_tree(attr)
        if prim.IsA(UsdGeom.Imageable):
            primvar_api = UsdGeom.PrimvarsAPI(prim)
            for primvar in primvar_api.GetPrimvars():
                self.add_primvar_to_tree(primvar)

    def update_time_samples(self, prim):
        self.time_samples_tree.clear()
        for attr in prim.GetAttributes():
            if attr.GetNumTimeSamples() > 0:
                parent_item = QtWidgets.QTreeWidgetItem(self.time_samples_tree)
                parent_item.setText(0, attr.GetName())
                for time in attr.GetTimeSamples():
                    child_item = QtWidgets.QTreeWidgetItem(parent_item)
                    child_item.setText(1, str(time))
                    child_item.setText(2, str(attr.Get(time)))
        self.time_samples_tree.expandAll()

    def add_attribute_to_tree(self, attr):
        item = QtWidgets.QTreeWidgetItem(self.attr_primvar_tree)
        item.setText(0, attr.GetName())
        item.setText(1, str(attr.Get()))

        color = self.get_attribute_color(attr)
        item.setData(0, QtCore.Qt.UserRole, {'color': color})
        item.setData(1, QtCore.Qt.UserRole, {'color': color})

    def get_attribute_color(self, attr):
        if attr.IsCustom():
            return QtGui.QColor(255, 255, 0)  # Yellow for custom attributes
        elif attr.GetName().startswith('xformOp:'):
            return QtGui.QColor(200, 200, 255)  # Light blue for transform attributes
        elif isinstance(attr.Get(), Usd.TimeCode):
            return QtGui.QColor(0, 255, 0)  # Green for time samples
        elif attr.GetTypeName() == 'token':
            return QtGui.QColor(217, 157, 52)  # Orange for tokens
        return QtGui.QColor(142, 211, 245)  # Default color

    def add_primvar_to_tree(self, primvar):
        item = QtWidgets.QTreeWidgetItem(self.attr_primvar_tree)
        item.setText(0, primvar.GetName())
        item.setText(1, str(primvar.Get()))

        color = QtGui.QColor(0, 255, 255)  # Cyan for primvars
        item.setData(0, QtCore.Qt.UserRole, {'color': color})
        item.setData(1, QtCore.Qt.UserRole, {'color': color})

    def edit_attr_primvar(self):
        item = self.attr_primvar_tree.currentItem()
        if not item:
            return

        prim = self.get_selected_prim()
        name = item.text(0)
        current_value = item.text(1)
        new_value, ok = QtWidgets.QInputDialog.getText(self, "Edit", f"Enter new value for {name}:", text=current_value)
        if not ok or not prim:
            return

        try:
            attr = UsdGeom.PrimvarsAPI(prim).GetPrimvar(name).GetAttr() if UsdGeom.Primvar.IsPrimvarName(
                name) else prim.GetAttribute(name)
            if not attr:
                print(f"Warning: Could not find attribute or primvar named {name}")
                return

            typed_value = self.convert_to_attr_type(new_value, attr.GetTypeName())
            attr.Set(typed_value)
            self.update_attr_primvar_list(prim)
        except Exception as e:
            print(f"Error setting value: {str(e)}")

    def convert_to_attr_type(self, value_str, type_name):
        type_converters = {
            Sdf.ValueTypeNames.Bool: lambda x: x.lower() in ('true', '1', 'yes', 'on'),
            Sdf.ValueTypeNames.Int: int,
            Sdf.ValueTypeNames.UInt: int,
            Sdf.ValueTypeNames.Float: float,
            Sdf.ValueTypeNames.Double: float,
            Sdf.ValueTypeNames.String: str,
            Sdf.ValueTypeNames.Token: str,
            Sdf.ValueTypeNames.Vector3f: lambda x: Gf.Vec3f(*[float(v) for v in x.strip('()').split(',')]),
            Sdf.ValueTypeNames.Vector3d: lambda x: Gf.Vec3d(*[float(v) for v in x.strip('()').split(',')]),
            Sdf.ValueTypeNames.Color3f: lambda x: Gf.Vec3f(*[float(v) for v in x.strip('()').split(',')])
        }

        converter = type_converters.get(type_name)
        if converter:
            return converter(value_str)
        else:
            print(f"Warning: Unsupported type {type_name}. Returning string value.")
            return value_str

    def add_attribute(self):
        prim = self.get_selected_prim()
        if not prim:
            return

        name, ok = QtWidgets.QInputDialog.getText(self, "Add Attribute", "Enter attribute name:")
        if not ok or not name:
            return

        value, ok = QtWidgets.QInputDialog.getText(self, "Add Attribute", f"Enter value for {name}:")
        if not ok:
            return

        prim.CreateAttribute(name, Sdf.ValueTypeNames.String).Set(value)
        self.update_attr_primvar_list(prim)

    def add_primvar(self):
        prim = self.get_selected_prim()
        if not prim:
            return

        name, ok = QtWidgets.QInputDialog.getText(self, "Add Primvar", "Enter primvar name:")
        if not ok or not name:
            return

        value, ok = QtWidgets.QInputDialog.getText(self, "Add Primvar", f"Enter value for {name}:")
        if not ok:
            return

        UsdGeom.PrimvarsAPI(prim).CreatePrimvar(name, Sdf.ValueTypeNames.String).Set(value)
        self.update_attr_primvar_list(prim)

    def remove_attr_primvar(self):
        item = self.attr_primvar_tree.currentItem()
        if not item:
            return

        prim = self.get_selected_prim()
        name = item.text(0)

        if UsdGeom.Primvar.IsPrimvarName(name):
            UsdGeom.PrimvarsAPI(prim).RemovePrimvar(name)
        else:
            prim.RemoveProperty(name)

        self.update_attr_primvar_list(prim)

    def edit_time_sample(self, item, column):
        if not item.parent():  # Ensure it's a child item (time sample)
            return

        prim = self.get_selected_prim()
        attr_name = item.parent().text(0)
        time = float(item.text(1))
        current_value = item.text(2)

        new_value, ok = QtWidgets.QInputDialog.getText(
            self, "Edit Time Sample",
            f"Enter new value for {attr_name} at time {time}:",
            text=current_value
        )

        if not ok or not prim:
            return

        try:
            attr = prim.GetAttribute(attr_name)
            if not attr:
                print(f"Warning: Could not find attribute named {attr_name}")
                return

            typed_value = self.convert_to_attr_type(new_value, attr.GetTypeName())
            attr.Set(typed_value, time)
            self.update_time_samples(prim)
        except Exception as e:
            print(f"Error setting time sample: {str(e)}")

    def get_selected_prim(self):
        selected_indexes = self.tree_view.selectedIndexes()
        if not selected_indexes:
            return None

        prim_path_str = selected_indexes[0].data(QtCore.Qt.UserRole)
        prim_path = Sdf.Path(prim_path_str)
        return self.stage.GetPrimAtPath(prim_path)

    def set_variant(self, prim, variant_set, variant):
        set_variant_selection(prim, variant_set, variant)
        self.refresh_tree_view()

    def load_selected_payload(self):
        prim = self.get_selected_prim()
        if prim:
            load_payload(prim)
            self.refresh_tree_view()

    def unload_selected_payload(self):
        prim = self.get_selected_prim()
        if prim:
            unload_payload(prim)
            self.refresh_tree_view()

    def refresh_tree_view(self):
        selected = cmds.ls(sl=1, ufe=1)
        if not selected:
            cmds.warning("No USD prim selected.")
            return

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

    def apply_changes(self):
        prim = self.get_selected_prim()
        if not prim or not self.stage:
            cmds.warning("No prim selected or stage not available.")
            return

        try:
            new_kind = self.kind_combo.currentText()
            if new_kind:
                set_prim_kind(prim, new_kind)

            new_purpose = self.purpose_combo.currentText()
            if new_purpose:
                set_prim_purpose(prim, PrimPurpose(new_purpose))

            self.refresh_tree_view()
        except Exception as e:
            print(f"Error applying changes: {str(e)}")

    def update_stage_text(self):
        if self.stage:
            self.stage_text_edit.setPlainText(get_stage_as_text(self.stage))

    def update_stage_from_text(self):
        if not self.stage:
            return

        try:
            update_stage_from_text(self.stage, self.stage_text_edit.toPlainText())
            self.refresh_tree_view()
        except Exception as e:
            print(f"Error updating stage: {str(e)}")

    def showEvent(self, event):
        if self.stage:
            self.refresh_tree_view()
        super().showEvent(event)


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
