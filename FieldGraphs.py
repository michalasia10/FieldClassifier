from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from qgis._core import QgsDistanceArea, QgsUnitTypes, QgsProject
from typing import List, Callable
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


class FieldGraphs(object):

    def __init__(self, iface, window, form, colorList: Callable, labelList : Callable, classesArea: dict):
        self.iface = iface
        self._colorList = colorList
        self._labelList = labelList
        self._classesArea: dict = classesArea
        self.form = form
        self.window = window

    def plot_bar_chart(self) -> None:
        """
        The method is responsible for creating the chart
        :return: None
        """
        colors = self._colorList()
        labels = self._labelList()

        self.fig, ax = plt.subplots()
        widthBar = 0.75

        values: List[float] = list(self._classesArea.values())
        y_pos = np.arange(1, len(self._classesArea.keys()) + 1)

        rect = ax.bar(y_pos, values, widthBar, color=colors)

        ax.set_xticks(y_pos)
        ax.set_xticklabels(labels)
        ax.set_title("Procentowy udział klasy w sumie powierzchni pól")

        for re in rect:
            height = re.get_height()
            ax.text(re.get_x() + re.get_width() / 4., int(height) + 2.5, f"{round(height, 3)} %")

        ax.set_ylabel(f"% udział klasy")
        ax.set_ylim([0, 100])
        self.scene = QGraphicsScene()
        canvas = FigureCanvas(self.fig)
        self.scene.addWidget(canvas)
        self.form.graphicsView_2.setScene(self.scene)

    def save(self):
        if self.form.graphicsView_2.scene() is None:
            self.iface.messageBar().pushMessage("ERROR", "Wybierz obiekty i wygeneruj wykres",
                                                level=Qgis.Critical, duration=15)
        else:
            path: tuple = QFileDialog.getSaveFileName(self.window, 'Otworz', "C:\\", '*.jpg')
            if path[0] == '':
                self.iface.messageBar().pushMessage("ERROR", "Wybranej ścieżki do zapisu", level=Qgis.Critical,
                                                    duration=15)
            else:
                self.fig.savefig(path[0], format='png')
