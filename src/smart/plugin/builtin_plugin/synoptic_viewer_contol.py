from smart import rs_path
from os import listdir
import yaml
from PyQt5.QtCore import pyqtSlot as Slot

class synopticViewerControl(object):

    def __init__(self, parent=None):
        #self.group_names = self.settings_object.value("widgetMaps/beamlineControlGpNames").rsplit(',')
        # self.set_models()
        self.populate_synoptic_viewer_config_files()

    def populate_synoptic_viewer_config_files(self):
        files = [each.rsplit('.')[0] for each in listdir(str(rs_path / 'config')) if each.endswith('yaml')]
        self.comboBox_viewer_filename.clear()
        self.comboBox_viewer_filename.addItems(files)

    @Slot(str)
    def populate_synoptic_objs(self, config_file_name):
        with open(str(rs_path / 'config' / (config_file_name+'.yaml')), 'r', encoding='utf8') as f:
           viewers = list(yaml.safe_load(f.read())['viewers'].keys())
        self.comboBox_viewer_obj_name.clear()
        self.comboBox_viewer_obj_name.addItems(viewers)

    def connect_slots_synoptic_viewer_control(self):
        # self.horizontalSlider_sf.valueChanged.connect(self.set_scaling_factor)
        self.pushButton_render.clicked.connect(self.widget_synoptic.init_viewer)
        self.comboBox_viewer_filename.textActivated.connect(self.populate_synoptic_objs)

    def set_models(self):
        allkeys = self.settings_object.keys()
        selected_keys = [key for key in allkeys if key in self.group_names]
        for each in selected_keys:
            model = self.settings_object[each]
            for key, value in model.items():
                getattr(self, key).model = value            

    def set_scaling_factor(self):
        # self.widget_synoptic.scale_composite_shapes(self.horizontalSlider_sf.value()/2)
        self.widget_synoptic.update()
