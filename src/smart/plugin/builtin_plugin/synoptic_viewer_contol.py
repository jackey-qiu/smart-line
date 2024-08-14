from smart import rs_path
from os import listdir
import numpy as np
import yaml
from PyQt5.QtCore import pyqtSlot as Slot
from smart.gui.widgets.shapes.shape_container import buildTools

class synopticViewerControl(object):

    def __init__(self, parent=None):
        #self.group_names = self.settings_object.value("widgetMaps/beamlineControlGpNames").rsplit(',')
        # self.set_models()
        self.set_cam_sources()
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
        self.comboBox_cam_source1.textActivated.connect(lambda: self.widget_camera_viewer1.setModel(self.comboBox_cam_source1.currentText()))
        self.comboBox_cam_source2.textActivated.connect(lambda: self.widget_camera_viewer2.setModel(self.comboBox_cam_source2.currentText()))
        self.comboBox_cam_source3.textActivated.connect(lambda: self.widget_camera_viewer3.setModel(self.comboBox_cam_source3.currentText()))
        self.pushButton_mv_viewer_left.clicked.connect(self.mv_view_left)
        self.pushButton_mv_viewer_right.clicked.connect(self.mv_view_right)
        self.horizontalSlider_viewer_squeezer.sliderReleased.connect(self.squeeze_view)

    def set_cam_sources(self):
        cam_source_list = self.settings_object['synopticViewer']['camera_sources']
        self.synoptic_viewer_cam_source_list = cam_source_list
        tango_models = [each['model'] for each in cam_source_list]
        self.comboBox_cam_source1.clear()
        self.comboBox_cam_source1.addItems(tango_models)
        self.comboBox_cam_source2.clear()
        self.comboBox_cam_source2.addItems(tango_models)
        self.comboBox_cam_source3.clear()
        self.comboBox_cam_source3.addItems(tango_models)

    def set_scaling_factor(self):
        # self.widget_synoptic.scale_composite_shapes(self.horizontalSlider_sf.value()/2)
        self.widget_synoptic.update()

    def mv_view_left(self):
        x_offset = self.spinBox_step_size.value()
        for each, composite in self.widget_synoptic.viewer_shape.items():
            original_translate = composite.ref_shape.transformation['translate']
            new_translate = original_translate - np.array([x_offset, 0])
            composite.translate(new_translate)
        self.widget_synoptic.update()

    def mv_view_right(self):
        x_offset = self.spinBox_step_size.value()
        for each, composite in self.widget_synoptic.viewer_shape.items():
            original_translate = composite.ref_shape.transformation['translate']
            new_translate = original_translate + np.array([x_offset, 0])
            composite.translate(new_translate)
        self.widget_synoptic.update()

    def squeeze_view(self):
        spacing = self.horizontalSlider_viewer_squeezer.value()
        acc_boundary_offset_x = 0
        for i, (each, composite) in enumerate(self.widget_synoptic.viewer_shape.items()):
            if i==0:
                acc_boundary_offset_x = composite.ref_shape.transformation['translate'][0]
            composite.translate([acc_boundary_offset_x+i*spacing, composite.ref_shape.transformation['translate'][1]])
            x_min, x_max, *_ = buildTools.calculate_boundary_for_combined_shapes(composite.shapes)
            acc_boundary_offset_x = acc_boundary_offset_x + abs(x_max - x_min)
            #original_translate = composite.ref_shape.transformation['translate']
            #new_translate = original_translate + np.array([spacing*i, 0])
            #composite.translate(new_translate)
        self.widget_synoptic.update()
