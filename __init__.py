from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from .form import Ui_Dialog
from qgis.core import *
from  qgis.gui import *
from qgis.utils import *
from .FieldsClassifier import FieldsClassifier


def classFactory(iface):
    return FieldsClassifier(iface)
