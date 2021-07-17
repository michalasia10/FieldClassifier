from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from .form import Ui_Dialog
from qgis.core import *
from  qgis.gui import *
from qgis.utils import *
from .LasiaPlugin import LasiaPlugin


def classFactory(iface):
    return LasiaPlugin(iface)
