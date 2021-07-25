
class ListCreator:
    def __init__(self,uniqueClasses,dictForm,):
        self._uniqueClasses = uniqueClasses
        self._dictForm = dictForm

    @property
    def dictForm(self):
        return self._dictForm

    def create_color_dict(self):
        for item in self._uniqueClasses:
            self._dictForm[item] = tuple(i/255 for i in self._dictForm[item].color().getRgb())

    def create_label_dict(self):
        for item in self._uniqueClasses:
            if self._dictForm[item].text() != '':
                self._dictForm[item] = self._dictForm[item].text()
            else:
                self._dictForm[item] = str(item)

    def create_list(self,type):
        return [label for _,label in self._dictForm.items() if isinstance(label,type)]