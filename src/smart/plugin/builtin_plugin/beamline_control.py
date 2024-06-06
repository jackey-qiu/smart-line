
class beamlineControl(object):

    def __init__(self, parent=None):
        self.group_names = self.settings_object.value("widgetMaps/beamlineControlGpNames").rsplit(',')
        # self.set_models()

    def connect_slots_beamline_control(self):
        self.pushButton_connect_model.clicked.connect(self.set_models)

    def set_models(self):
        allkeys = self.settings_object.allKeys()
        selected_keys = [key for key in allkeys if key.rsplit('/')[0] in self.group_names]
        for each in selected_keys:
            model = self.settings_object.value(each)
            if not model.endswith('{}'):#model name ends with {} is a dynamically changed model
                getattr(self, each.rsplit('/')[1]).model = model