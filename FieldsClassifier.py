from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from qgis._core import QgsProject
from typing import List
from .form import Ui_Dialog
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
import json
import importlib.resources
from .FieldGraphs import FieldGraphs
from .FieldCalculator import FieldCalculator
from .ListCreator import ListCreator

# load json
with importlib.resources.path("FieldsClassifier", "units.json") as data_path:
    with open(data_path) as f:
        UNITS_JSON = json.load(f)


# load units to convert from json
CONVERT_UNITS = UNITS_JSON["convert_units"]

#load icon
with importlib.resources.path("FieldsClassifier", "iconPlugin.png") as data_path:
    icon_path = str(data_path.absolute())


class FieldsClassifier:

    def __init__(self, iface):
        self.iface = iface
        self._sumArea: float = 0.0
        self._mean: float = 0.0
        self._unit: str = "m2"  # default value 'm2'
        self._areaFeat: List[int] = []  # default value empty list
        self._selectedFeat: list = [] # default  empty list for feats
        self._uniqueClasses : set = {} # deafult empty set for classes
        self._numberOfUniqueClasses: int = 0 # deafult 0 number of classes
        self._classesArea : dict[int : list] = {} # deafult empty dict for area
        self._crs = None
        self._colors:dict = {}
        self._graphLabels:dict = {}
        self._numberOfFeat = 0

    def initGui(self) -> None:
        """
        Method is responsible for the plug-in initialization and for the agent of the _addledz method which adds the plugin
        :return: None
        """

        self.action, self.menu = self._add_action(icon_path,  "Field's Stats","Fields Classifier",)

    def _add_action(self, pathIcon: str, pluginTitle: str, menuTitle: str):
        """
        Method adds a plugin to Qgis with title, icon, menu name

        :param pathIcon: str: plug-in icon path
        :param pluginTitle: str: plugin title
        :param menuTitle: str: menu title
        :return: action , menu
        """

        icon = QIcon(pathIcon)
        action = QAction(icon, pluginTitle, self.iface.mainWindow())
        menu = QMenu(self.iface.mainWindow())
        menu.setTitle(menuTitle)
        menu.addAction(action)
        menuBar = self.iface.mainWindow().menuBar()
        menuBar.addAction(menu.menuAction())
        action.triggered.connect(self.run)
        self.iface.messageBar().pushMessage("ERROR", f"{pathIcon}", level=Qgis.Critical, duration=5)
        return action, menu

    def unload(self) -> None:
        """
        Metoda usuwa plugin z Qgis'a
        :return: None
        """
        self.menu.deleteLater()
        del self.action

    def _open(self)->None:
        """
        Method is responsible for opening the window with folders to search for a file, after adding the layer is in the selected layout

        :return: None
        """
        self._check_and_return_crs()
        path: tuple = QFileDialog.getOpenFileName(self.window, 'Otworz', "C:\\", '*.shp')
        if QFileDialog.accepted:
            self._check_path(path, self.form.lineEdit_5, self._crs)

    def _check_path(self, path: tuple, lineEdit, crs) -> None:
        """
        The method checks if the file is selected if it does not show an error
        :param path: file path
        :param lineEdit: line edit responsible for showing a path
        :param crs: coordinate system
        :return:
        """
        if path[0]:
            lineEdit.setText(path[0])
            self.iface.addVectorLayer(path[0], '', 'ogr').setCrs(crs)
        else:
            lineEdit.setText('Nie wybrano pliku')
            self.iface.messageBar().pushMessage("ERROR", "Nie wybrano pliku", level=Qgis.Critical, duration=5)

    def _select(self)->None:
        """
        The method is responsible for selecting objects with freehand, if there is no layer, it will show ERROR.
        :return: None
        """
        self._clean_object()
        self.iface.actionSelectFreehand().trigger()
        noLayers: bool = self._check_is_any_active_layer()
        if not noLayers:
            self._check_is_any_selected_feat()
            self.window.hide()
            layer = self.iface.activeLayer()
            layer.selectionChanged.connect(self._end_select)


    def _end_select(self)->None:
        """
        The method is responsible for updating text with values after finishing selecting objects
        based on the values of the variables in the class.
        The method runs the computation methods and updates the variables in the class.
        :return: None
        """
        form = self.form
        layer = self.iface.activeLayer()
        layer.selectionChanged.disconnect(self._end_select)
        self._create_selected_list_of_feat()
        unitName: str = form.comboBox.currentText()
        labels: list = [form.label_5, form.label_6, ]
        self._set_text_for_list(labels, unitName)
        calculator = FieldCalculator(self._selectedFeat)
        calculator.count_sum_area()
        self._sumArea = calculator.sumArea
        calculator.count_mean()
        self._mean = calculator.mean
        self._uniqueClasses,self._numberOfUniqueClasses = calculator.count_classes_in_selected_feat()
        self._classesArea = calculator.count_area_for_unique_class()
        self._numberOfFeat = calculator.count_objects()
        self._write_number_of_objects()
        self.form.lineEdit_2.setText(f"{round(self._sumArea, 5)}")
        self.form.lineEdit_3.setText(f"{round(self._mean, 5)}")
        self.form.lineEdit_4.setText(f"{self._numberOfUniqueClasses}")
        self._active_widgets(self._get_default_forms_to_change())
        self._active_edit_form_for_classes()
        self.window.show()

    def _get_default_forms_to_change(self):
        defaultWidgetsToActivate = [self.form.label, self.form.label_2, self.form.label_3,
                                          self.form.label_4, self.form.label_5, self.form.label_6,
                                          self.form.label_11, self.form.label_10, self.form.lineEdit_2,
                                          self.form.lineEdit_3, self.form.lineEdit_4, self.form.comboBox,
                                          self.form.pushButton_3, self.form.lineEdit, self.form.pushButton_5,
                                          self.form.pushButton_6, self.form.label_17,
                                          self.form.label_16, self.form.label_23, self.form.label_24]
        return defaultWidgetsToActivate

    def _create_selected_list_of_feat(self)->None:
        """
        The method responsible for creating a list of selected objects
        :return: None
        """
        self._check_is_any_active_layer()
        layer = self.iface.activeLayer()
        self._selectedFeat = [feat for feat in layer.selectedFeatures()]

    def _write_number_of_objects(self):
        self.form.lineEdit.setText(str(self._numberOfFeat))

    def _clean_object(self)->None:
        """
        The method is responsible for clearing all values
        :return: None
        """
        form = self.form
        widgetsForClass = [form.label_8, form.label_18, form.lineEdit_6, form.mColorButton,
                           form.label_12, form.label_19, form.lineEdit_7, form.mColorButton_2,
                           form.label_13, form.label_20, form.lineEdit_8, form.mColorButton_3,
                           form.label_14, form.label_21, form.lineEdit_9, form.mColorButton_4,
                           form.label_15, form.label_22, form.lineEdit_10, form.mColorButton_5]
        listsToDelete = [self._areaFeat,self._selectedFeat]
        dictsToDelete = [self._classesArea,self._colors,self._graphLabels]
        for list in listsToDelete:
            del list[:]
        for dic in dictsToDelete:
            dic.clear()
        self.form.lineEdit.setText('0')
        form = self.form
        valuesInText = [form.lineEdit_2, form.lineEdit_3, form.lineEdit_4]
        self._active_widgets(widgetsForClass, False)
        self._active_widgets(self._get_default_forms_to_change(),False)
        self._set_text_for_list(valuesInText, "")
        self._sumArea = 0.0
        self._check_is_any_selected_feat()
        scene = self.form.graphicsView_2
        if scene.scene() is not None:
            self.form.graphicsView_2.scene().clear()

    def _refresh_lineEdits(self)->None:
        """
        Method is responsible for refreshing the text after changing the unit

        :return: None
        """
        form = self.form
        self._check_unit_in_comboBox()
        self._refresh_area_values()
        if self._unit != self.form.label_5.text():
            labels: list = [form.label_5, form.label_6]
            self._set_text_for_list(labels, self._unit)
            valuesInText: list = [form.lineEdit_2, form.lineEdit_3]
            values: list = [self._sumArea, self._mean]
            for idx, text in enumerate(valuesInText):
                newValue = values[idx]
                text.setText(f"{round(newValue, 5)}")

    def _set_text_for_list(self,lines:list,text:str):
        """
        method will change the text for the given labels
        :param lines: list of lines
        :param text: text to set
        :return:
        """
        for line in lines:
            line.setText(text)

    def _refresh_area_values(self)->None:
        """
        Method is responsible for refreshing the values in the class after changing the unit
        :return: None
        """
        oldUnit: str = self.form.label_5.text()
        self._check_unit_in_comboBox()
        if self._unit != self.form.label_5.text():
            newUnit = CONVERT_UNITS[oldUnit][self._unit]
            self._mean = self._mean * newUnit
            self._sumArea = self._sumArea * newUnit
            self._areaFeat = [feat * newUnit for feat in self._areaFeat]

    def _check_is_any_selected_feat(self)->None:
        """
        The method is responsible for removing selected objects before starting the plugin
        :return: None
        """
        self._create_selected_list_of_feat()
        if self._selectedFeat:
            self.iface.activeLayer().removeSelection()

    def _check_crs_in_comboBox(self)->str:
        """
        Method checks which coordinate system has been selected
        :return: str cordinanate system
        """
        crs : str = self.form.comboBox_2.currentText()
        return crs

    def _check_unit_in_comboBox(self)->None:
        """
        Method is responsible for checking the existing unit
        in the comboBox responsible for units and variable updates
        :return: None
        """
        self._unit = self.form.comboBox.currentText()

    def _check_plot_name_in_comboBox2(self)->None:
        """
        Method is responsible for checking the method that occurs in
        comboBoxie responsible for the methods of charting and updating the variable
        :return: None
        """
        self._plotName = self.form.comboBox_2.currentText()

    def _check_and_return_crs(self):
        radioButtonYes = self.form.radioButton
        if radioButtonYes.isChecked():
            self._crs = QgsProject.instance().crs()
        else:
            crs_box = self._check_crs_in_comboBox()
            self._crs = QgsCoordinateReferenceSystem.fromEpsgId(int(crs_box[7:]))
            QgsProject.instance().setCrs(self._crs)

    def _check_is_any_active_layer(self)->bool:
        """
        Method is responsible for checking if there is any layer in the project

        :return: bool
        """
        layerList:bool = any([lyr for lyr in QgsProject.instance().mapLayers().values()])
        if not layerList:
            self.iface.messageBar().pushMessage("ERROR", "Brak warstwy z obiektami", level=Qgis.Critical, duration=5)
            return True
        return False

    def _active_widgets(self,widgets : list,flag : bool=True,)->None:
        """
        The method enables or disables widgets
        :param flag: bolean flah
        :return: None
        """
        for widget in widgets:
            widget.setEnabled(flag)

    def _active_edit_form_for_classes(self):
        form = self.form
        widgetsForClass = {
            1:[form.label_8,form.label_18,form.lineEdit_6,form.mColorButton],
            2:[form.label_12,form.label_19,form.lineEdit_7,form.mColorButton_2],
            3:[form.label_13,form.label_20,form.lineEdit_8,form.mColorButton_3],
            4:[form.label_14,form.label_21,form.lineEdit_9,form.mColorButton_4],
            5:[form.label_15,form.label_22,form.lineEdit_10,form.mColorButton_5],

        }
        for item in self._uniqueClasses:
            self._active_widgets(widgetsForClass[item])

    def _crs_combobox_view(self):
        radioButtonYes = self.form.radioButton
        radioButtonNo = self.form.radioButton_2
        radios = {
            radioButtonYes:False,
            radioButtonNo:True,
        }
        crs = self.form.comboBox_2
        for radio,flag in radios.items():
            if radio.isChecked():
                crs.setEnabled(flag)


    def draw_graph(self):
        form = self.form
        labels = {
            1:form.lineEdit_6,
            2:form.lineEdit_7,
            3:form.lineEdit_8,
            4:form.lineEdit_9,
            5:form.lineEdit_10,
        }
        colors = {
            1: form.mColorButton,
            2: form.mColorButton_2,
            3: form.mColorButton_3,
            4: form.mColorButton_4,
            5: form.mColorButton_5,
        }

        color = ListCreator(self._uniqueClasses,colors)
        color.create_color_dict()
        self._colors = color.dictForm
        colorList = color.create_list(tuple)
        label = ListCreator(self._uniqueClasses,labels)
        label.create_label_dict()
        self._graphLabels = label.dictForm
        labelList = label.create_list(str)
        self.graphs = FieldGraphs(self.iface,
                                  self.window,
                                  form)
        self.graphs.plot_bar_chart(colorList, labelList, self._classesArea, self.form.graphicsView_2)

    def save_graph(self):
        self.graphs.save(self.form.graphicsView_2)


    def run(self)->None:
        """
        Run method responsible for assigning buttons to functions and the operation of the entire plugin
        :return: None
        """
        self.window = QDialog()
        self.form = Ui_Dialog()
        self.form.setupUi(self.window)
        self.form.pushButton_4.clicked.connect(self._open)
        self.form.pushButton_2.clicked.connect(self._select)
        self.form.pushButton_3.clicked.connect(self._refresh_lineEdits)
        self.form.pushButton_5.clicked.connect(self._clean_object)
        self.form.buttonBox_2.clicked.connect(self.window.close)
        self.form.radioButton_2.toggled.connect(self._crs_combobox_view)
        self.form.radioButton.toggled.connect(self._crs_combobox_view)
        self.form.pushButton.clicked.connect(self.save_graph)
        self.form.pushButton_6.clicked.connect(self.draw_graph)
        self.window.show()
