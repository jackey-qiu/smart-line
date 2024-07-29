from PyQt5.QtWidgets import QLabel, QPushButton, QSlider, QAbstractItemView, QMessageBox
from PyQt5.QtCore import Qt, pyqtSlot as Slot
from PyQt5.QtGui import QFont
from PyQt5 import QtCore
from functools import partial
from taurus.qt.qtgui.display import TaurusLabel
from taurus import Attribute
import pandas as pd
from smart.util.util import PandasModel
from smart.plugin.user_plugin.queue_control import REQUIRED_KEYS

class beamlineControl(object):

    def __init__(self, parent=None):
        self.group_names = self.settings_object["widgetMaps"]["beamlineControlGpNames"].rsplit(',')
        self.camara_pixel_size = 1
        self.stage_pos_at_prim_beam = [0, 0]
        self.crosshair_pos_at_prim_beam = [0, 0]
        self.saved_crosshair_pos = [0, 0]
        self.illum_pos_latest = {}
        # self.set_models()

    def connect_slots_beamline_control(self):
        self.init_pandas_model_queue_camara_viewer()
        self.update_pixel_size()
        # self.pushButton_connect_model.clicked.connect(self.set_models)
        self.pushButton_append_job.clicked.connect(self.add_one_task_to_scan_viewer)
        self.tableView_scan_list_camera_viewer.clicked.connect(self.update_roi_upon_click_tableview_camera_widget)
        self.pushButton_remove_one_task.clicked.connect(self.remove_currently_selected_row)
        self.pushButton_submit_all.clicked.connect(lambda: self.submit_jobs_to_queue_server(viewer='camera'))

    def update_pixel_size(self):
        from taurus import Attribute
        try:
            self.camara_pixel_size = Attribute(self.settings_object["Camaras"]["pixel_size"]).read().value
        except:
            pass
        self.camara_widget.img_viewer.axes['left']['item'].setScale(self.camara_pixel_size)
        self.camara_widget.img_viewer.axes['left']['item'].setLabel('ver (mm)')
        self.camara_widget.img_viewer.axes['bottom']['item'].setScale(self.camara_pixel_size)
        self.camara_widget.img_viewer.axes['bottom']['item'].setLabel('hor (mm)')

    def set_models(self):
        allkeys = self.settings_object.keys()
        selected_keys = [key for key in allkeys if key in self.group_names]
        for each in selected_keys:
            widget_model_dict = self.settings_object[each]
            for (key, value) in widget_model_dict.items():
                if not value.endswith('{}'):#model name ends with {} is a dynamically changed model
                    getattr(self, key).model = value
        #get the num of illum devices
        num_illum_devices = len(Attribute(self.settings_object["Mscope"]["comboBox_illum_types"]).read().value)
        self.populate_illum_widgets(num_illum_devices, 3)
        self._start_spock()

    def _start_spock(self):
        if 'spockLogin' not in self.settings_object:
            print('No spock login field, please add the fields to start spock.')
            return
        self.widget_spock._door_name = self.settings_object['spockLogin']['doorName']
        self.widget_spock._door_alias = self.settings_object['spockLogin']['doorAlias']
        self.widget_spock._macro_server_name = self.settings_object['spockLogin']['msName']
        self.widget_spock._macro_server_alias = self.settings_object['spockLogin']['msAlias']
        if self.widget_spock.kernel_manager.has_kernel:
            # RichJupyterWidget.restart_kernel does not support extra arguments
            self.widget_spock.kernel_manager.restart_kernel(
                extra_arguments=self.widget_spock._extra_arguments())
            self.widget_spock._kernel_restarted_message(died=False)
        else:
            self.widget_spock.start_kernel()        
        self.setModel(self.settings_object['spockLogin']['msName'])
        self.onDoorChanged(self.settings_object['spockLogin']['doorName'])

    def mv_stages_to_cursor_pos(self):
        self.statusUpdate(f'moving sample stages to {self.last_cursor_pos_on_camera_viewer}')
        Attribute(self.settings_object['SampleStages']['label_x_stage_value']).write(self.last_cursor_pos_on_camera_viewer[0])
        Attribute(self.settings_object['SampleStages']['label_y_stage_value']).write(self.last_cursor_pos_on_camera_viewer[1])

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
                    model_str = self.settings_object["Mscope"]["label_illum_pos"].format(i)
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

    def init_pandas_model_queue_camara_viewer(self, table_view_widget_name='tableView_scan_list_camera_viewer'):
        data = pd.DataFrame.from_dict({'session':[], 'queue':[],'scan_command':[], 'scan_info':[], 'geo_roi':[]})
        #disable_all_tabs_but_one(self, tab_widget_name, tab_indx)
        self.pandas_model_queue_camara_viewer = PandasModel(data = data, tableviewer = getattr(self, table_view_widget_name), main_gui=self)
        getattr(self, table_view_widget_name).setModel(self.pandas_model_queue_camara_viewer)
        getattr(self, table_view_widget_name).resizeColumnsToContents()
        getattr(self, table_view_widget_name).setSelectionBehavior(QAbstractItemView.SelectRows)
        getattr(self, table_view_widget_name).horizontalHeader().setStretchLastSection(True)

    def add_one_task_to_scan_viewer(self):
        num_of_existing_task = self.pandas_model_queue_camara_viewer._data.shape[0]
        roi = self.camara_widget.roi_scan
        value_list = [self.lineEdit_queue_section_name.text(),\
                      self.lineEdit_scan_queue_name.text(),\
                      self.lineEdit_full_macro_name.text(),\
                      'To be added',
                      f'[{roi.x()},{roi.y()},{roi.size()[0]},{roi.size()[1]}]'
                      ]
        self.pandas_model_queue_camara_viewer._data.loc[num_of_existing_task] = value_list
        self.pandas_model_queue_camara_viewer.update_view()

    def remove_currently_selected_row(self):
        which_row = self.tableView_scan_list_camera_viewer.selectionModel().selectedRows()[0].row()
        self.pandas_model_queue_camara_viewer._data.drop([which_row], inplace=True)
        self.pandas_model_queue_camara_viewer._data.reset_index(drop=True, inplace=True)
        self.pandas_model_queue_camara_viewer.update_view()

    @Slot(QtCore.QModelIndex)
    def update_roi_upon_click_tableview_camera_widget(self, modelindex):
        row = modelindex.row()
        roi = eval(self.pandas_model_queue_camara_viewer._data.iloc[row,:]['geo_roi'])
        x, y, w, h = roi
        scan_cmd_list = self.pandas_model_queue_camara_viewer._data.iloc[row,:]['scan_command'].rsplit(' ')
        x_, y_ = float(scan_cmd_list[2]), float(scan_cmd_list[6])
        self.camara_widget.roi_scan_xy_stage = [x_, y_]
        x, y = self.camara_widget._convert_stage_coord_to_pix_unit(x_, y_)

        self.camara_widget.roi_scan.setX(x)
        self.camara_widget.roi_scan.setY(y)
        self.camara_widget.roi_scan.setSize((w, h))

    def update_roi_at_row(self, row):
        roi = eval(self.pandas_model_queue_camara_viewer._data.iloc[row,:]['geo_roi'])
        x, y, w, h = roi
        scan_cmd_list = self.pandas_model_queue_camara_viewer._data.iloc[row,:]['scan_command'].rsplit(' ')
        x_, y_ = float(scan_cmd_list[2]), float(scan_cmd_list[6])
        self.camara_widget.roi_scan_xy_stage = [x_, y_]
        x, y = self.camara_widget._convert_stage_coord_to_pix_unit(x_, y_)

        self.camara_widget.roi_scan.setX(x)
        self.camara_widget.roi_scan.setY(y)
        self.camara_widget.roi_scan.setSize((w, h))

    def submit_jobs_to_queue_server(self, viewer = 'camrera'):
        if self.queue_comm==None:
            self.statusUpdate('queue server is not created. Create the connection first.')
            return
        def _make_job_list():
            jobs = []
            rows = self.pandas_model_queue_camara_viewer._data.shape[0]
            for i in range(rows):
                jobs.append({
                    'queue': self.lineEdit_scan_queue_name.text(),
                    'session': self.lineEdit_queue_section_name.text(),
                    'scan_command': self.pandas_model_queue_camara_viewer._data['scan_command'].to_list()[i].rsplit(' ')
                })
            return jobs
        def _make_job_list_img_reg():
            jobs = []
            rows = self.pandas_model_scan_list._data.shape[0]
            for i in range(rows):
                jobs.append({
                    'queue': self.lineEdit_queue_name_imgreg.text(),
                    'session': self.lineEdit_session_name.text(),
                    'scan_command': self.pandas_model_scan_list._data['scan macro'].to_list()[i].rsplit(' ')
                })
            return jobs            
        try:
            if viewer == 'camera':
                self.queue_comm.send_receive_message(['add', _make_job_list()])
            elif viewer == 'img_reg':
                self.queue_comm.send_receive_message(['add', _make_job_list_img_reg()])
            self.statusUpdate('Jobs are submitted to queue server.')
        except Exception as e:
            self.statusUpdate('Fail to submit the jobs.'+str(e))
