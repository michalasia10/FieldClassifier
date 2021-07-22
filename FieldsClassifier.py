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

# load units from json
UNITS = UNITS_JSON["units"]

# load units to convert from json
CONVERT_UNITS = UNITS_JSON["convert_units"]

#load icon
with importlib.resources.path("FieldsClassifier", "iconPlugin.png") as data_path:
    icon_path = str(data_path.absolute())


#CRS = {
 #   "2180": ,
  #  "2177": QgsCoordinateReferenceSystem(2177),
   # "4326": QgsCoordinateReferenceSystem(4326),
#}



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
        self._selectedFeat: list = [] # empty list for feats
        self._uniqueClasses : set = {}
        self._numberOfUniqueClasses: int = 0
        self._classesArea : dict[int : list] = {}


    def initGui(self) -> None:
        """
        Metoda odpowiada za inicjalizacje pluginu i uruchomienie metody _add_action która dodaje plugin

        :return: None
        """

        self.action, self.menu = self._add_action(icon_path,  "Field's Stats","Fields Classifier",)

    def _add_action(self, pathIcon: str, pluginTitle: str, menuTitle: str):
        """
        Metoda dodaje plugin do Qgisa, jego tytul, ikone, nazwe menu

        :param pathIcon: str: sciezka do ikony dla pluginu
        :param pluginTitle: str: tytul dla pluginy
        :param menuTitle: str: tytul dla menu pluginu
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
        Metoda odpowiada za otworzenie okna z folderami w celu wyszukania pliku, po dodaniu warstwa jest w układzie 2180

        """
        crs_box = self._check_crs_in_comboBox()
        crs = QgsCoordinateReferenceSystem.fromEpsgId(int(crs_box[7:]))
        QgsProject.instance().setCrs(crs)
        path: tuple = QFileDialog.getOpenFileName(self.window, 'Otworz', "C:\\", '*.shp')
        if QFileDialog.accepted:
            self.check_path(path,self.form.lineEdit_5,crs)

    def _select(self)->None:
        """
        Metoda odpowiada za zaznaczenie obiektów okręgiem, jeśli nie ma żadnej warstwy pokaże ERROR.
        :return: None
        """
        self._check_is_any_selected_feat()
        self.iface.actionSelectFreehand().trigger()
        noLayers: bool = self._check_is_any_active_layer()
        if not noLayers:
            self.window.hide()
            layer = self.iface.activeLayer()
            layer.selectionChanged.connect(self._end_select)

    def _end_select(self)->None:
        """
        Metoda odpowiada za aktualizacje tekstu z wartościami po zakończeniu zaznaczania obiektów
        na podstawie wartości zmiennych w klasi.
        Metoda uruchamia metody odpowiedzialne za obliczenia i aktualizaje zmiennych w klasie.

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
        Metoda odpowiada za obliczenie sumy powierzchni zaznaczonych obiektów.
        Metoda aktuzaliuje zmienne w klasie.

        :param layer: warstwa
        :return: None
        """
        form = self.form
        unitName: str = form.comboBox.currentText()
        labels: list = [form.label_5, form.label_6,]
        self._set_text_for_list(labels,unitName)
        self._areaFeat = self._expresion_calculator('$area')
        self._sumArea = sum(self._areaFeat)


    def _count_classes_in_selected_feat(self):
        self._uniqueClasses = set(self._expresion_calculator('value'))
        self._numberOfUniqueClasses = len(self._uniqueClasses)
        print(self._uniqueClasses)


    def _count_area_for_unique_class(self):
        for uniqueClass in self._uniqueClasses:
            areaForClass = self._expresion_calculator(f'CASE WHEN "value" LIKE {uniqueClass} THEN $area END')
            print('area',uniqueClass,areaForClass)
            self._classesArea[uniqueClass] = sum(areaForClass)
        print(self._classesArea)



    def check_path(self,path:tuple,lineEdit,crs):
        if path[0]:
            lineEdit.setText(path[0])
            self.iface.addVectorLayer(path[0], '', 'ogr').setCrs(crs)
        else:
            lineEdit.setText('Nie wybrano pliku')
            self.iface.messageBar().pushMessage("ERROR", "Nie wybrano pliku", level=Qgis.Critical, duration=5)




    def _expresion_calculator(self,expression:str):
        expression = QgsExpression(expression)
        context = QgsExpressionContext()
        listOfValues = []
        for feat in self._selectedFeat:
            context.setFeature(feat)
            value = expression.evaluate(context)
            if value is not None:
                listOfValues.append(value)
        return listOfValues


    def _create_selected_list_of_feat(self):
        self._check_is_any_active_layer()
        layer = self.iface.activeLayer()
        self._selectedFeat = [feat for feat in layer.selectedFeatures()]

    def _count_mean(self)->None:
        """
        Metoda odpowiada za obliczenie średniej powierzchni zaznaczonych obiektów i aktualizacje zmiennej w klasie.
        :return: None
        """
        self._mean = self._sumArea / len(self._areaFeat)


    def _count_objects(self)->None:
        """
        Metoda odpowiada za obliczenie liczby zaznacoznych obiektów i aktualizacji tekstu związanego z ta liczbą
        :return:None
        """
        self.form.lineEdit.setText(str(len(self._areaFeat)))

    def _clean_object(self)->None:
        """
        Metoda odpowiada za obliczenie liczby zaznaczonych obiektów i aktualizacji tekstu związanego z ta liczbą
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
        #self.form.graphicsView.scene().clear()
        self._active_widgets(False)
        self._set_text_for_list(valuesInText, "")
        self._sumArea = 0.0
        self._check_is_any_selected_feat()

    def _refresh_lineEdits(self)->None:
        """
        Metoda odpowiada za odświeżenie tekstu po zmianie jednostki

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
        Metoda zmiena tekst dla podanych labeli
     
        """
        for line in lines:
            line.setText(text)

    def _refresh_area_values(self)->None:
        """
        Metoda odpowiada za odświeżenie wartości w klasie po zmianie jednostki
        :return: None
        """
        oldUnit: str = self.form.label_5.text()
        self._check_unit_in_comboBox()
        if self._unit != self.form.label_5.text():
            newUnit = CONVERT_UNITS[oldUnit][self._unit]
            self._mean = self._mean * newUnit
            self._sumArea = self._sumArea * newUnit
            self._areaFeat = [feat * newUnit for feat in self._areaFeat]


    def _check_is_any_selected_feat(self):
        self._create_selected_list_of_feat()
        if self._selectedFeat:
            self.iface.activeLayer().removeSelection()

    def _check_crs_in_comboBox(self)->str:
        crs : str = self.form.comboBox_2.currentText()
        return crs

    def _check_unit_in_comboBox(self)->None:
        """
        Metoda odpowiada za sprawdzenie jednostki jaka występuje
        w comboBoxie odpowiadjącego za jednostki i aktualizacje zmiennej
        :return: None
        """
        self._unit = self.form.comboBox.currentText()

    def _check_plot_name_in_comboBox2(self)->None:
        """
        Metoda odpowiada za sprawdzenie metody jaka występuje w
        comboBoxie odpowiadjącego za metody wykresy i aktualizacji zmiennej
        :return: None
        """
        self._plotName = self.form.comboBox_2.currentText()

    def _check_is_any_active_layer(self)->bool:
        """
        Metoda odpowiada za sprawdzenie czy jest jakakolwiek warstwa w projekcie

        :return: bool
        """
        layerList:bool = any([lyr for lyr in QgsProject.instance().mapLayers().values()])
        if not layerList:
            self.iface.messageBar().pushMessage("ERROR", "Brak warstwy z obiektami", level=Qgis.Critical, duration=5)
            return True
        return False

    def _active_widgets(self,flag=True):
        form = self.form

        widgets = [form.label,form.label_2,form.label_3,
                   form.label_4,form.label_5,form.label_6,
                   form.label_11,form.label_8,
                   form.lineEdit_2,form.lineEdit_3,
                   form.lineEdit_4,form.comboBox,form.pushButton_3,
                   form.lineEdit,form.pushButton_5,form.comboBox_2,
                   form.pushButton]

        for widget in widgets:
            widget.setEnabled(flag)

    def _values_for_one_bar(self, subValue:float)->list:
        """
        Metoda odpowiada za przygotowanie danych dla wykresu który zawiera tylko jedną metode wyświetlania
        :param subValue: float
        :return: list
        """
        return [feat - subValue for feat in self._areaFeat]

    def _values_for_two_bars(self, subValueDict: dict)->tuple:
        """
        Metoda odpowiada za przygotowanie danych dla wykresu który zawiera dwie metody wyświetlania
        :param subValueDict: dict
        :return: tuple
        """
        mean, sigmoid = subValueDict.values()
        subMean: List[float] = [feat - mean for feat in self._areaFeat]
        subSig: List[float] = [feat - sigmoid for feat in self._areaFeat]
        return subMean, subSig

    def _plot_bar_chart(self)->None:
        """
        Metoda odpowiada za wyświetlenie wykresów
        :return: None
        """
        self._refresh_lineEdits()
        self._check_plot_name_in_comboBox2()
        self._check_unit_in_comboBox()


        fig, ax = plt.subplots()
        widthBar = 0.10

        values: List[float] = list(self._classesArea.values())
        y_pos = np.arange(1,len(self._classesArea.keys())+1)
        plt.bar(y_pos, values, align = 'center',alpha=0.5)
        ax.set_xticks(y_pos)
        ax.set_xticklabels(self._classesArea.keys())
        ax.legend()
        ax.set_title("dupa")

        ax.set_ylabel(f"Różnica [{self._unit}]")
        scene = QGraphicsScene()
        canvas = FigureCanvas(fig)
        scene.addWidget(canvas)
        self.form.graphicsView.setScene(scene)

    def run(self)->None:
        """
        Metoda run odpowiedzialna za przypisanie buttonów do funkcji i działaniu calego pluginu
        :return: None
        """
        self.window = QDialog()
        self.form = Ui_Dialog()
        self.form.setupUi(self.window)
        self.form.pushButton_4.clicked.connect(self._open)
        self.form.pushButton_2.clicked.connect(self._select)
        self.form.pushButton_3.clicked.connect(self._refresh_lineEdits)
        self.form.pushButton.clicked.connect(self._plot_bar_chart)
        self.form.pushButton_5.clicked.connect(self._clean_object)
        self.form.buttonBox_2.clicked.connect(self.window.close)
        self.window.show()
