from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from qgis._core import QgsProject
from typing import List
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
import json
import importlib.resources
from .ErrosMessage import ErrorMessage

# load json
with importlib.resources.path("FieldsClassifier", "units.json") as data_path:
    with open(data_path) as f:
        UNITS_JSON = json.load(f)


# load units to convert from json
CONVERT_UNITS = UNITS_JSON["convert_units"]

class AreaConverter:
    def __init__(self,iface,form,combBoxUnit,oldUnit,mean:float,sumArea:float,unitLabels,valuesLabels):
        self._iface = iface
        self.form = form
        self._unit: str = combBoxUnit.currentText()
        self._oldUnit: str = oldUnit.text()
        self._mean: float = mean
        self._sumArea: float = sumArea
        self._unitLabels = unitLabels
        self._valuesLabels = valuesLabels

    @property
    def mean(self):
        return self._mean

    @property
    def sumMean(self):
        return self._sumArea

    def convert(self)->None:
        """
        Method is responsible for refreshing the text after changing the unit

        :return: None
        """
        form = self.form
        self._refresh_area_values()
        valuesList: list = [self._sumArea, self._mean]
        if self._unit != self._oldUnit:
            for idx in range(len(valuesList)):
                self._valuesLabels[idx].setText(f"{round(valuesList[idx],5)}")
                self._unitLabels[idx].setText(self._unit)


    def _refresh_area_values(self)->None:
        """
        Method is responsible for refreshing the values in the class after changing the unit
        :return: None
        """
        if self._unit != self._oldUnit:
            newUnit = CONVERT_UNITS[self._oldUnit][self._unit]
            self._mean = self._mean * newUnit
            self._sumArea = self._sumArea * newUnit
        else:
            ErrorMessage(self._iface,1,"Jednostka jest aktualna",5,1)
