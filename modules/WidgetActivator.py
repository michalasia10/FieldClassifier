class WidgetActivator:
    def __init__(self, form, uniqueClasses):
        self._form = form
        self._uniqueClasses = uniqueClasses

    def change_visibility(self, flag: bool = True):
        form = self._form
        widgetsForClass = {
            1: form.firstClassW,
            2: form.secondClassW,
            3: form.thirdClassW,
            4: form.fourthClassW,
            5: form.fifthClassW,

        }
        form.statWidgets.setEnabled(flag)
        form.graphWidget.setEnabled(flag)
        for item in self._uniqueClasses:
            widgetsForClass[item].setEnabled(flag)
