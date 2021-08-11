from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from qgis.core import *
from qgis.gui import *
from qgis.utils import *

MESSAGE_TYPE = {
    0: Qgis.Info,
    1: Qgis.Warning,
    2: Qgis.Critical,
    3: Qgis.Success,
}
PROBLEM_TYPE = {
    0:"INFO",
    1:"WARNING",
    2:"ERROR",
    3:"SUCCES",
}


class ErrorMessage:

    def __init__(self,iface,problemType,message,time):
        self._iface = iface
        self._problemType = PROBLEM_TYPE[problemType]
        self._message = message
        self._time = time
        self._messageType = MESSAGE_TYPE[problemType]
        self._push_message()

    def _push_message(self):
        self._iface.messageBar().pushMessage(self._problemType,
                                             f"{self._message}",
                                             level=self._messageType,
                                             duration=self._time)