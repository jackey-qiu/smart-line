from PyQt5.QtWidgets import QLabel, QPushButton, QSlider
from PyQt5.QtCore import Qt, pyqtSlot as Slot
from PyQt5.QtGui import QFont
from functools import partial
from taurus.qt.qtgui.display import TaurusLabel
from taurus import Attribute


class beamlineControl(object):

    def __init__(self, parent=None):
        self.group_names = self.settings_object.value("widgetMaps/beamlineControlGpNames").rsplit(',')
        self.camara_pixel_size = 1
        self.stage_pos_at_prim_beam = [0, 0]
        self.crosshair_pos_at_prim_beam = [0, 0]
        self.saved_crosshair_pos = [0, 0]
        self.illum_pos_latest = {}
        # self.set_models()

    def connect_slots_beamline_control(self):
        self.update_pixel_size()
        self.pushButton_connect_model.clicked.connect(self.set_models)

    def update_pixel_size(self):
        from taurus import Attribute
        self.camara_pixel_size = Attribute(self.settings_object.value("Camaras/pixel_size")).read().value
        self.camara_widget.img_viewer.axes['left']['item'].setScale(self.camara_pixel_size)
        self.camara_widget.img_viewer.axes['left']['item'].setLabel('ver (mm)')
        self.camara_widget.img_viewer.axes['bottom']['item'].setScale(self.camara_pixel_size)
        self.camara_widget.img_viewer.axes['bottom']['item'].setLabel('hor (mm)')

    def set_models(self):
        allkeys = self.settings_object.allKeys()
        selected_keys = [key for key in allkeys if key.rsplit('/')[0] in self.group_names]
        for each in selected_keys:
            model = self.settings_object.value(each)
            if not model.endswith('{}'):#model name ends with {} is a dynamically changed model
                getattr(self, each.rsplit('/')[1]).model = model
        #get the num of illum devices
        num_illum_devices = len(Attribute(self.settings_object.value('Mscope/comboBox_illum_types')).read().value)
        self.populate_illum_widgets(num_illum_devices, 3)

    def populate_illum_widgets(self, rows = 0, first_row = 4):
        cols = ['label_illum','horizontalSlider_illum', 'label_illum_pos', 'pushButton_lighton','pushButton_lightoff']
        widgets = [QLabel, QSlider, TaurusLabel, QPushButton, QPushButton]
        for i in range(rows):
            for j in range(len(cols)):
                widget_name = f'{cols[j]}_{i}'
                args = [(f'illum device {i}',), (Qt.Horizontal,), (),('Lighton',),('Lightoff',)]
                widget_obj = widgets[j](*args[j])
                widget_obj.setFont(QFont('Arial', 10))
                if type(widget_obj)==QSlider:
                    widget_obj.setMinimum(0)
                    widget_obj.setMaximum(100)
                if type(widget_obj)==TaurusLabel:
                    #set the model
                    model_str = self.settings_object.value("Mscope/label_illum_pos").format(i)
                    widget_obj.model = model_str
                    #slider slot connection setup
                    current_value = Attribute(model_str).read().rvalue.m
                    getattr(self, f'horizontalSlider_illum_{i}').setValue(int(current_value))
                    getattr(self, f'horizontalSlider_illum_{i}').valueChanged.connect(partial(self.write_illum_attr_value, Attribute(model_str), i))
                if args[j] == ('Lighton',):#turn on light button
                    widget_obj.clicked.connect(lambda state, ix=i: self.callback_light_on_ix(ix))
                if args[j] == ('Lightoff',):#turn on light button
                    widget_obj.clicked.connect(lambda state, ix=i: self.callback_light_off_ix(ix))
                setattr(self, widget_name, widget_obj)
                self.gridLayout_cam_stage.addWidget(widget_obj, i+first_row, j)

    @Slot(int)
    def write_illum_attr_value(self, attribute_proxy,which,value):
        attribute_proxy.write(float(value))
        self.illum_pos_latest[which] = float(value)

    def callback_light_on_ix(self, ix):
        if len(self.illum_pos_latest)==0:
            return
        else:
            getattr(self, f'horizontalSlider_illum_{ix}').setValue(int(self.illum_pos_latest[ix]))

    def callback_light_off_ix(self, ix):
        current_value = self.illum_pos_latest.pop(ix, None)
        if current_value!=None:
            getattr(self, f'horizontalSlider_illum_{ix}').setValue(int(0))
            self.illum_pos_latest[ix] = current_value
