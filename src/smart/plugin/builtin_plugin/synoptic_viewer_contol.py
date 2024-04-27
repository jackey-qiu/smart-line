
class synopticViewerControl(object):

    def __init__(self, parent=None):
        #self.group_names = self.settings_object.value("widgetMaps/beamlineControlGpNames").rsplit(',')
        # self.set_models()
        pass

    def connect_slots_synoptic_viewer_control(self):
        self.horizontalSlider_sf.valueChanged.connect(self.set_scaling_factor)

    def set_models(self):
        allkeys = self.settings_object.allKeys()
        selected_keys = [key for key in allkeys if key.rsplit('/')[0] in self.group_names]
        for each in selected_keys:
            model = self.settings_object.value(each)
            getattr(self, each.rsplit('/')[1]).model = model

    def set_scaling_factor(self):
        self.widget_synoptic.composite_shape.scale(self.horizontalSlider_sf.value())
        self.widget_synoptic.update()
