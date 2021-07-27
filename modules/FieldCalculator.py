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
        self._numberOfFeat = 0
        self._uniqueClasses = {}
        self._numberOfUniqueClasses = 0
        self._classesArea = {}

    @property
    def areaFeat(self):
        return self._areaFeat

    @property
    def sumArea(self):
        return self._sumArea

    @property
    def mean(self):
        return self._mean

    @property
    def numberOfFeat(self):
        return self._numberOfFeat

    @property
    def numberOfUniqueClasses(self):
        return self._numberOfUniqueClasses

    @property
    def uniqueClasses(self):
        return self._uniqueClasses

    @property
    def classesArea(self):
        return self._classesArea

    def _count_sum_area(self) -> None:
        """
        The method is responsible for calculating the sum of the areas of selected objects.
        The method updates the variables in the class.

        :return: None
        """
        self._areaFeat = self._expresion_calculator('$area')
        self._sumArea = sum(self._areaFeat)

    def _count_mean(self) -> None:
        """
        Method is responsible for calculating the average area of selected objects and updating the variable in the class.
        :return: None
        """
        self._mean = self._sumArea / len(self._areaFeat)

    def _count_objects(self)->None:
        """
        Method is responsible for calculating the number of marked objects and updating the text associated with that number
        :return:None
        """
        self._numberOfFeat = len(self._areaFeat)

    def _count_classes_in_selected_feat(self)->None:
        """
        The method creates a set with classes and calculates the number of unique classes based on the set
        :return: None
        """
        _uniqueClasses = set(self._expresion_calculator('value'))
        self._uniqueClasses = _uniqueClasses
        self._numberOfUniqueClasses = len(_uniqueClasses)

    def _count_area_for_unique_class(self)->None:
        """
        The method calculates the sum of the areas of each class using the method responsible for creating the list with surfaces after giving expression
        :return: None
        """
        for uniqueClass in self._uniqueClasses:
            areaForClass = self._expresion_calculator(f'CASE WHEN "value" LIKE {uniqueClass} THEN $area END')
            self._classesArea[uniqueClass] = (sum(areaForClass) / self._sumArea) * 100

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

    def _check_len_of_lists(self,firstList: list, secondList: List[tuple])->bool:
        return len(firstList) == len(secondList)

    def set_text_for_fields(self,fieldsToSet: list)->None:
        valuesForFields: list = [self._numberOfFeat,self._sumArea,self._mean,self._numberOfUniqueClasses]
        if self._check_len_of_lists(fieldsToSet, valuesForFields):
            for field, value in zip(fieldsToSet, valuesForFields):
                text,rounding = field
                text.setText(f"{round(value,rounding)}")

    def count_all_values(self):
        self._count_sum_area()
        self._count_mean()
        self._count_classes_in_selected_feat()
        self._count_area_for_unique_class()
        self._count_objects()
