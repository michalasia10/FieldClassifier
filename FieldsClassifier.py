from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from qgis._core import QgsDistanceArea, QgsUnitTypes, QgsProject
from typing import List
from PyQt5.QtGui import QPen
from .form import Ui_Dialog
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
from math import sqrt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np
import matplotlib.pyplot as plt
import json
import importlib.resources


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
    """
    PL: Klasa reprezentuje plugin o nazwie LasiaPlugin.
        Plugin pozwala na obliczenie statystyk obiektów (sume powierzchni, średnią, odchylenie standardowe)
        dla warstwy wektorowej która przyjmuje pliki typu *.shp.
        Plugin pozwala również na obliczenie liczby obiektów oraz na wizualizacje obliczonych danych na wykresach.
        Plugin sprawdza czy w projekcie jest jakakolwiek warstwa jeśli nie to pokaże ERROR.

    ----------------
    Methods
    ----------------

    initGui

            Metoda odpowiada za inicjalizacje pluginu

    unload

            Metoda odpowiada za usunięcie pluginu z Qgis'a

    _add_action(pathIcon: str, pluginTitle: str, menuTitle: str)

            Metoda odpowiada za dodanie pluginu do Qgis'a

    _open

            Metoda odpowiada za otworzenie okna z folderami w celu wyszukania pliku

    _select

            Metoda odpowiada za zaznaczenie obiektów okręgiem, jeśli nie ma żadnej warstwy pokaże ERROR

    _end_select

            Metoda odpowiada za aktualizacje tekstu z wartościami po zakończeniu zaznaczania obiektów

    _count_sum_area(layer)

            Metoda odpowiada za obliczenie sumy powierzchni zaznaczonych obiektów

    _count_mean

            Metoda odpowiada za obliczenie średniej powierzchni zaznaczonych obiektów

    _count_standard_deviation

            Metoda odpowiada za obliczenie odchylenia standardowego dla zaznaczonych obiektów

    _count_objects

            Metoda odpowiada za obliczenie liczby zaznaczonych obiektów i aktualizacji tekstu związanego z ta liczbą

    _refresh_lineEdits

            Metoda odpowiada za odświeżenie tekstu po zmianie jednostki

    _refresh_area_values

            Metoda odpowiada za odświeżenie wartości w klasie po zmianie jednostki

    _check_unit_in_comboBox

            Metoda odpowiada za sprawdzenie jednostki jaka występuje w comboBoxie odpowiadjącego za jednostki

    _check_plot_name_in_comboBox2

            Metoda odpowiada za sprawdzenie metody jaka występuje w comboBoxie odpowiadjącego za metody wykresy

    _check_is_any_active_layer

            Metoda odpowiada za sprawdzenie czy jest jakakolwiek warstwa w projekcie

    _values_for_one_bar(subValue: float)

            Metoda odpowiada za przygotowanie danych dla wykresu który zawiera tylko jedną metode wyświetlania

    _values_for_two_bars(subValueDict: dict)

            Metoda odpowiada za przygotowanie danych dla wykresu który zawiera dwie metody wyświetlania

    _plot_barChart

            Metoda odpowiada za wyświetlenie wykresów


    """
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

    def _select(self)->None:
        """
        The method is responsible for selecting objects with freehand, if there is no layer, it will show ERROR.
        :return: None
        """

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
        layer = self.iface.activeLayer()
        layer.selectionChanged.disconnect(self._end_select)
        self._create_selected_list_of_feat()
        self._count_sum_area()
        self._count_mean()
        self._count_classes_in_selected_feat()
        self.form.lineEdit_2.setText(f"{round(self._sumArea, 5)}")
        self.form.lineEdit_3.setText(f"{round(self._mean, 5)}")
        self.form.lineEdit_4.setText(f"{self._numberOfUniqueClasses}")
        self._count_objects()
        self._active_widgets()
        self._count_area_for_unique_class()

        self.window.show()

    def _count_sum_area(self)->None:
        """
        The method is responsible for calculating the sum of the areas of selected objects.
        The method updates the variables in the class.

        :return: None
        """
        form = self.form
        unitName: str = form.comboBox.currentText()
        labels: list = [form.label_5, form.label_6,]
        self._set_text_for_list(labels,unitName)
        self._areaFeat = self._expresion_calculator('$area')
        self._sumArea = sum(self._areaFeat)

    def _count_mean(self) -> None:
        """
        Method is responsible for calculating the average area of ​​selected objects and updating the variable in the class.
        :return: None
        """
        self._mean = self._sumArea / len(self._areaFeat)

    def _count_objects(self) -> None:
        """
        Method is responsible for calculating the number of marked objects and updating the text associated with that number
        :return:None
        """
        self.form.lineEdit.setText(str(len(self._areaFeat)))

    def _count_classes_in_selected_feat(self)->None:
        """
        The method creates a set with classes and calculates the number of unique classes based on the set
        :return: None
        """
        self._uniqueClasses = set(self._expresion_calculator('value'))
        print('set',self._uniqueClasses)
        self._numberOfUniqueClasses = len(self._uniqueClasses)

    def _count_area_for_unique_class(self)->None:
        """
        The method calculates the sum of the areas of each class using the method responsible for creating the list with surfaces after giving expression
        :return: None
        """
        for uniqueClass in self._uniqueClasses:
            areaForClass = self._expresion_calculator(f'CASE WHEN "value" LIKE {uniqueClass} THEN $area END')
            self._classesArea[uniqueClass] = (sum(areaForClass)/self._sumArea)*100

    def _check_path(self,path:tuple,lineEdit,crs)->None:
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

    def _expresion_calculator(self,expression:str)->List[float]:
        """
        The method responsible for creating a list with surfaces after giving expression
        :param expression: expression
        :return: list with areas
        """
        expression = QgsExpression(expression)
        context = QgsExpressionContext()
        listOfValues = []
        for feat in self._selectedFeat:
            context.setFeature(feat)
            value = expression.evaluate(context)
            if value is not None:
                listOfValues.append(value)
        return listOfValues

    def _create_selected_list_of_feat(self)->None:
        """
        The method responsible for creating a list of selected objects
        :return: None
        """
        self._check_is_any_active_layer()
        layer = self.iface.activeLayer()
        self._selectedFeat = [feat for feat in layer.selectedFeatures()]

    def _clean_object(self)->None:
        """
        The method is responsible for clearing all values
        :return: None
        """
        del self._areaFeat[:]
        del self._selectedFeat[:]
        print(self._classesArea)
        self._classesArea.clear()
        print(self._classesArea)
        self.form.lineEdit.setText('0')
        form = self.form
        valuesInText = [form.lineEdit_2, form.lineEdit_3, form.lineEdit_4]
        self.form.graphicsView_2.scene().clear()
        self._active_widgets(False)
        self._set_text_for_list(valuesInText, "")
        self._sumArea = 0.0
        self._check_is_any_selected_feat()

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

    def _active_widgets(self,flag : bool=True)->None:
        """
        The method enables or disables widgets
        :param flag: bolean flah
        :return: None
        """
        form = self.form

        widgets = [form.label,form.label_2,form.label_3,
                   form.label_4,form.label_5,form.label_6,
                   form.label_11,form.label_10,
                   form.lineEdit_2,form.lineEdit_3,
                   form.lineEdit_4,form.comboBox,form.pushButton_3,
                   form.lineEdit,form.pushButton_5,form.comboBox_2,
                   form.pushButton_6]

        for widget in widgets:
            widget.setEnabled(flag)

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



    def _check_and_return_crs(self):
        radioButtonYes = self.form.radioButton
        if radioButtonYes.isChecked():
            self._crs = QgsProject.instance().crs()
        else:
            crs_box = self._check_crs_in_comboBox()
            self._crs = QgsCoordinateReferenceSystem.fromEpsgId(int(crs_box[7:]))
            QgsProject.instance().setCrs(self._crs)


    def _plot_bar_chart(self)->None:
        """
        The method is responsible for creating the chart
        :return: None
        """
        self._refresh_lineEdits()
        self._check_plot_name_in_comboBox2()
        self._check_unit_in_comboBox()


        fig, ax = plt.subplots()
        widthBar = 0.75

        values: List[float] = list(self._classesArea.values())
        y_pos = np.arange(1,len(self._classesArea.keys())+1)

        rect = ax.bar(y_pos, values,widthBar)

        ax.set_xticks(y_pos)
        ax.set_xticklabels(self._classesArea.keys())
        ax.legend()
        ax.set_title("Procentowy udział klasy w sumie powierzchni pól")

        for re in rect:
            height = re.get_height()
            print("h",height)
            ax.text(re.get_x()+re.get_width()/4., int(height) + 2.5 ,f"{round(height,3)} %")

        ax.set_ylabel(f"% udział klasy")
        ax.set_ylim([0,100])
        scene = QGraphicsScene()
        canvas = FigureCanvas(fig)
        scene.addWidget(canvas)
        self.form.graphicsView_2.setScene(scene)

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
        self.form.pushButton_6.clicked.connect(self._plot_bar_chart)
        self.form.pushButton_5.clicked.connect(self._clean_object)
        self.form.buttonBox_2.clicked.connect(self.window.close)
        self.form.radioButton_2.toggled.connect(self._crs_combobox_view)
        self.form.radioButton.toggled.connect(self._crs_combobox_view)
        self.window.show()
