from .WidgetActivator import WidgetActivator

class WidgetChanger:
    def __init__(self,form):
        self._form = form
        self._scene = self._form.graphScene

    def clean_scene(self):
        if self._scene.scene() is not None:
            self._scene.scene().clear()

    def deactivate_widgets(self,uniqueClasses):
        deactive = WidgetActivator(self._form,uniqueClasses)
        deactive.change_visibility(False)

    def reset_widget(self,widget,value):
        widget.setText(value)

    def deafult_float_values(self,variables:list):
        return tuple([0.0 for _ in variables])

    def set_value_in_widgets(self,widgets:list,value):
        for widget in widgets:
            widget.setText(value)

    def list_drainer(self,dirtyLists):
        return [[] for _ in dirtyLists]


