from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from qgis._core import QgsProject
from typing import List
from .form import Ui_Dialog
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
import importlib.resources
from .modules.FieldGraphs import FieldGraphs
from .modules.FieldCalculator import FieldCalculator
from .modules.ErrosMessage import ErrorMessage
from .modules.AreaConverter import AreaConverter
from .modules.WidgetActivator import WidgetActivator
from .modules.WidgetChanger import WidgetChanger

# load icon
with importlib.resources.path("FieldsClassifier", "iconPlugin.png") as data_path:
    icon_path = str(data_path.absolute())


class FieldsClassifier:

    def __init__(self, iface):
        self.iface = iface
        self._sumArea: float = 0.0
        self._mean: float = 0.0
        self._unit: str = "m2"  # default value 'm2'
        self._areaFeat: List[int] = []  # default value empty list
        self._selectedFeat: list = []  # default  empty list for feats
        self._uniqueClasses: set = {}  # deafult empty set for classes
        self._numberOfUniqueClasses: int = 0  # deafult 0 number of classes
        self._classesArea: dict[int: list] = {}  # deafult empty dict for area
        self._crs = None

    def initGui(self) -> None:
        self.action, self.menu = self._add_action(icon_path, "Field's Stats", "Fields Classifier", )

    def _add_action(self, pathIcon: str, pluginTitle: str, menuTitle: str):

        icon = QIcon(pathIcon)
        action = QAction(icon, pluginTitle, self.iface.mainWindow())
        menu = QMenu(self.iface.mainWindow())
        menu.setTitle(menuTitle)
        menu.addAction(action)
        menuBar = self.iface.mainWindow().menuBar()
        menuBar.addAction(menu.menuAction())
        action.triggered.connect(self.run)
        return action, menu

    def unload(self) -> None:
        self.menu.deleteLater()
        del self.action

    def _open(self) -> None:
        self._check_and_return_crs()
        path: tuple = QFileDialog.getOpenFileName(self.window, 'Otworz', "C:\\", '*.shp')
        if QFileDialog.accepted:
            self._check_path(path, self.form.lineEdit_5, self._crs)

    def _check_path(self, path: tuple, lineEdit, crs) -> None:
        if path[0]:
            lineEdit.setText(path[0])
            self.iface.addVectorLayer(path[0], '', 'ogr').setCrs(crs)
            ErrorMessage(self.iface, 3, f"Wgrano poprawnie plik", 5, 3)
        else:
            lineEdit.setText('Nie wybrano pliku')
            ErrorMessage(self.iface, 2, "Nie wybrano pliku", 5, 2)

    def _select(self) -> None:
        noLayers: bool = self._check_is_any_active_layer()
        if not noLayers:
            self._clean_object()
            self.iface.actionSelectFreehand().trigger()
            self._check_is_any_selected_feat()
            self.window.hide()
            layer = self.iface.activeLayer()
            layer.selectionChanged.connect(self._end_select)

    def _end_select(self) -> None:
        form = self.form
        layer = self.iface.activeLayer()
        layer.selectionChanged.disconnect(self._end_select)

        # create list of features
        self._create_selected_list_of_feat()

        # set unit for selected objects
        unitName: str = form.unitBox.currentText()
        labels: list = [form.unitText, form.unitText_2]
        changeUnit = WidgetChanger(form)
        changeUnit.set_value_in_widgets(labels, unitName)

        # init class to count all vars
        calculator = FieldCalculator(self._selectedFeat)
        calculator.count_all_values()
        self._sumArea = calculator.sumArea
        self._mean = calculator.mean
        self._uniqueClasses = calculator._uniqueClasses
        self._numberOfUniqueClasses = calculator.numberOfUniqueClasses
        self._classesArea = calculator._classesArea

        # set values in form
        fields = [(form.numberOfFieldLine, 0), (form.sumLine, 5), (form.meanLine, 5), (form.classLine, 0)]
        calculator.set_text_for_fields(fields)

        # active widgets
        activeWidgets = WidgetActivator(self.form, self._uniqueClasses)
        activeWidgets.change_visibility(True)
        self.window.show()

    def _create_selected_list_of_feat(self) -> None:
        self._check_is_any_active_layer()
        layer = self.iface.activeLayer()
        self._selectedFeat: list = [feat for feat in layer.selectedFeatures()]

    def _clean_object(self) -> None:
        form = self.form
        listsToDelete: list = [self._areaFeat, self._selectedFeat]
        floatListToClean = [self._sumArea, self._mean]
        linesToClean = [form.sumLine, form.meanLine, form.classLine]
        cleaner = WidgetChanger(form)
        cleaner.clean_scene()
        cleaner.reset_widget(form.numberOfFieldLine, '0')
        cleaner.set_value_in_widgets(linesToClean, "")
        self._unit = "m2"
        unitsToReset = [form.unitText,form.unitText_2]
        cleaner.set_value_in_widgets(unitsToReset,self._unit)
        form.unitBox.setCurrentText(self._unit)
        cleaner.deactivate_widgets(self._uniqueClasses)
        self._areaFeat, self._selectedFeat = cleaner.list_drainer(listsToDelete)
        self._sumArea, self._mean = cleaner.deafult_float_values(floatListToClean)
        self._classesArea.clear()
        self._uniqueClasses = {}
        self._check_is_any_selected_feat()

    def _convert(self) -> None:
        form = self.form
        unitLabels: list = [form.unitText, form.unitText_2]
        valuesLabels: list = [form.sumLine, form.meanLine]

        converter = AreaConverter(self.iface,
                                  form,
                                  form.unitBox,
                                  form.unitText,
                                  self._mean,
                                  self._sumArea,
                                  unitLabels,
                                  valuesLabels)
        self._mean = converter.mean
        self._sumArea = converter.sumMean

    def _check_is_any_selected_feat(self) -> None:
        self._create_selected_list_of_feat()
        if self._selectedFeat:
            self.iface.activeLayer().removeSelection()

    def _check_crs_in_comboBox(self) -> str:
        return self.form.crsBox.currentText()

    def _check_and_return_crs(self):
        if self.form.yesButton.isChecked():
            self._crs = QgsProject.instance().crs()
        else:
            crs_box = self._check_crs_in_comboBox()
            self._crs = QgsCoordinateReferenceSystem.fromEpsgId(int(crs_box[7:]))
            QgsProject.instance().setCrs(self._crs)

    def _check_is_any_active_layer(self) -> bool:
        layerList: bool = any([lyr for lyr in QgsProject.instance().mapLayers().values()])
        if not layerList:
            ErrorMessage(self.iface, 2, "Brak warstwy z obiektami", 10, 2)
            return True
        return False

    def _crs_combobox_view(self):
        form = self.form
        radios = {
            form.yesButton: False,
            form.noButton: True,
        }
        crs = self.form.crsBox
        for radio, flag in radios.items():
            if radio.isChecked():
                crs.setEnabled(flag)

    def draw_graph(self):
        self.graphs = FieldGraphs(self.iface,
                                  self.window,
                                  self.form,
                                  self._uniqueClasses,
                                  self._classesArea,
                                  )

    def save_graph(self):
        self.graphs.save()

    def run(self) -> None:
        self.window = QDialog()
        self.form = Ui_Dialog()
        self.form.setupUi(self.window)
        self.form.openButton.clicked.connect(self._open)
        self.form.selectButton.clicked.connect(self._select)
        self.form.refreshButton.clicked.connect(self._convert)
        self.form.cleanButton.clicked.connect(self._clean_object)
        self.form.buttonBox_2.clicked.connect(self.window.close)
        self.form.yesButton.toggled.connect(self._crs_combobox_view)
        self.form.noButton.toggled.connect(self._crs_combobox_view)
        self.form.saveButton.clicked.connect(self.save_graph)
        self.form.drawButton.clicked.connect(self.draw_graph)
        self.window.show()
