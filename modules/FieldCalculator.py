from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from typing import List
from qgis.core import *
from qgis.gui import *
from qgis.utils import *


class FieldCalculator:

    def __init__(self, selectedFeat: list):
        self._selectedFeat = selectedFeat
        self._areaFeat: list = []
        self._sumArea: float = 0.0
        self._mean: float = 0.0

    @property
    def areaFeat(self):
        return self._areaFeat

    @property
    def sumArea(self):
        return self._sumArea

    @property
    def mean(self):
        return self._mean

    def count_sum_area(self) -> None:
        """
        The method is responsible for calculating the sum of the areas of selected objects.
        The method updates the variables in the class.

        :return: None
        """
        self._areaFeat = self._expresion_calculator('$area')
        self._sumArea = sum(self._areaFeat)

    def count_mean(self) -> None:
        """
        Method is responsible for calculating the average area of selected objects and updating the variable in the class.
        :return: None
        """
        self._mean = self._sumArea / len(self._areaFeat)

    def count_objects(self) -> int:
        """
        Method is responsible for calculating the number of marked objects and updating the text associated with that number
        :return:None
        """
        # self.form.lineEdit.setText(str(len(self._areaFeat)))
        return len(self._areaFeat)

    def count_classes_in_selected_feat(self) -> (set, int):
        """
        The method creates a set with classes and calculates the number of unique classes based on the set
        :return: None
        """
        _uniqueClasses = set(self._expresion_calculator('value'))
        return _uniqueClasses, len(_uniqueClasses)

    def count_area_for_unique_class(self) -> dict:
        """
        The method calculates the sum of the areas of each class using the method responsible for creating the list with surfaces after giving expression
        :return: None
        """
        _classesArea = {}
        _uniqueClasses, _ = self.count_classes_in_selected_feat()
        self.count_sum_area()
        for uniqueClass in _uniqueClasses:
            areaForClass = self._expresion_calculator(f'CASE WHEN "value" LIKE {uniqueClass} THEN $area END')
            _classesArea[uniqueClass] = (sum(areaForClass) / self._sumArea) * 100
        return _classesArea

    def _expresion_calculator(self, expression: str) -> List[float]:
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
