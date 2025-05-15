from PyQt5.QtWidgets import QLabel, QPushButton, QSlider, QAbstractItemView, QMessageBox, QHBoxLayout, QSpacerItem, QSizePolicy
from PyQt5.QtCore import Qt, pyqtSlot as Slot
from PyQt5.QtGui import QFont
from PyQt5 import QtCore
import re
import numpy as np
from functools import partial
from taurus.qt.qtgui.display import TaurusLabel, TaurusLed
from taurus.qt.qtgui.input import TaurusWheelEdit, TaurusValueLineEdit
from taurus import Attribute
import pandas as pd
import pyqtgraph as pg
from smart.util.util import PandasModel
from smart.plugin.user_plugin.queue_control import REQUIRED_KEYS

class beamlineControl(object):

    def __init__(self, parent=None):
        self.group_names = self.settings_object["widgetMaps"]["beamlineControlGpNames"]
        self.camara_pixel_size = 1
        self.stage_pos_at_prim_beam = [0, 0]
        self.pstage_pos_at_prim_beam = [0, 0]
        self.crosshair_pos_at_prim_beam = [0, 0]
        self.saved_crosshair_pos = [0, 0]
        self.illum_pos_latest = {}
        # self.set_models()

    def connect_slots_beamline_control(self):
        self.update_stage_name_from_config()
        self.init_pandas_model_queue_camara_viewer()
        # self.update_pixel_size()
        # self.pushButton_connect_model.clicked.connect(self.set_models)
        self.pushButton_append_job.clicked.connect(lambda:self.add_one_task_to_scan_viewer(self.camara_widget.roi_scan))
        self.pushButton_remove_all.clicked.connect(self.remove_all_tasks_from_table)
        self.pushButton_duplicate_one.clicked.connect(self.duplicate_currently_selected_row)
        self.tableView_scan_list_camera_viewer.clicked.connect(self.update_roi_upon_click_tableview_camera_widget)
        self.pushButton_remove_one_task.clicked.connect(self.remove_currently_selected_row)
        self.pushButton_submit_all.clicked.connect(lambda: self.submit_jobs_to_queue_server(viewer='camera'))
        self.pushButton_show_rois.clicked.connect(self.show_all_rois)
        self.pushButton_rm_rois.clicked.connect(self.delete_rois)
        self.pushButton_fetch_jobs.clicked.connect(self.fetch_data_from_server)
        #parameter tree buttons
        self.pushButton_load_config.clicked.connect(self.widget_pars.load_config)
        self.pushButton_apply_change.clicked.connect(self.widget_pars.apply_config)

    def populate_taurus_motor_widgets(self):
        settings = self.settings_object.get('TaurusMotors', None)
        if settings==None:
            return
        style = settings.get('use_style')
        possible_styles = settings.get('possible_styles')
        if style not in possible_styles:
            raise Exception(f'{style} is Not the right stlye, choose one from {possible_styles}')
        for (key, stages) in settings.items():
            if key in ['use_style','possible_styles']:
                continue
            self.verticalLayout_motor_list.addWidget(QLabel(key))
            for (name, tg_address) in stages.items():
                tmp_Hlayout = QHBoxLayout()
                state = TaurusLed()
                state.setModel('/'.join([tg_address,'state']))
                name_ = QLabel(name)
                read_value = TaurusLabel()
                read_value.setModel('/'.join([tg_address,'position']))
                read_value.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                if style == 'write':
                    write_value = TaurusValueLineEdit()
                    write_value.setModel('/'.join([tg_address,'position']))
                else:
                    write_value = None
                unit = TaurusLabel()
                unit.setModel('/'.join([tg_address,'position#rvalue.units']))
                unit.bgRole = ''
                tmp_Hlayout.addWidget(state)
                tmp_Hlayout.addWidget(name_)
                tmp_Hlayout.addWidget(read_value)
                if write_value!=None:
                    write_value.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                    tmp_Hlayout.addWidget(write_value)
                tmp_Hlayout.addWidget(unit)
                # tmp_Hlayout.addItem(QSpacerItem(1, 1, QSizePolicy.Expanding,QSizePolicy.Fixed))
                self.verticalLayout_motor_list.addLayout(tmp_Hlayout)
        self.verticalLayout_motor_list.addItem(QSpacerItem(1, 1, QSizePolicy.Minimum, QSizePolicy.Expanding))

    def update_stage_name_from_config(self):
        if 'SampleStageMotorNames' in self.settings_object:
            name_map = self.settings_object['SampleStageMotorNames']
            if 'scanx' in name_map:
                getattr(self, 'label_sample_pstage_x').setText(f"scanx:{name_map['scanx']}")
                self.lineEdit_sample_stage_name_x.setText(name_map['scanx'])
            if 'scany' in name_map:
                getattr(self, 'label_sample_pstage_y').setText(f"scany:{name_map['scany']}")
                self.lineEdit_sample_stage_name_y.setText(name_map['scany'])
            if 'scanz' in name_map:
                getattr(self, 'label_sample_pstage_z').setText(f"scanz:{name_map['scanz']}")
            if 'x' in name_map:
                getattr(self, 'label_sample_stage_x').setText(f"samplex:{name_map['x']}")
                # self.lineEdit_sample_stage_name_x.setText(name_map['x'])
            if 'y' in name_map:
                getattr(self, 'label_sample_stage_y').setText(f"sampley:{name_map['y']}")
                # self.lineEdit_sample_stage_name_y.setText(name_map['y'])
            if 'z' in name_map:
                getattr(self, 'label_sample_stage_z').setText(f"samplez:{name_map['z']}")
                # self.lineEdit_sample_stage_name_y.setText(name_map['y'])

    def update_pixel_size(self):
        from taurus import Attribute
        try:
            self.camara_pixel_size = Attribute(self.settings_object["Camaras"]["pixel_size"]).read().value
        except:
            pass
        x_label = self.settings_object["SampleStageMotorNames"]['x']
        y_label = self.settings_object["SampleStageMotorNames"]['y']
        x_unit = Attribute(self.settings_object['SampleStages']['x_stage_value']).display_unit
        y_unit = Attribute(self.settings_object['SampleStages']['y_stage_value']).display_unit
        self.camara_widget.img_viewer.axes['left']['item'].setScale(self.camara_pixel_size)
        self.camara_widget.img_viewer.axes['left']['item'].setLabel(f'{y_label} ({y_unit})')
        self.camara_widget.img_viewer.axes['bottom']['item'].setScale(self.camara_pixel_size)
        self.camara_widget.img_viewer.axes['bottom']['item'].setLabel(f'{x_label} ({x_unit})')

    def set_models(self):
        self.populate_taurus_motor_widgets()
        self.update_pixel_size()
        allkeys = self.settings_object.keys()
        selected_keys = [key for key in allkeys if key in self.group_names]
        for each in selected_keys:
            widget_model_dict = self.settings_object[each]
            for (key, value) in widget_model_dict.items():
                if not value.endswith('{}'):#model name ends with {} is a dynamically changed model
                    if hasattr(self, key):
                        getattr(self, key).model = value
                        if key in ['x_pstage_value','x_stage_value',
                                   'y_pstage_value','y_stage_value',
                                   'z_pstage_value','z_stage_value',]:
                            getattr(self, key.replace('value','state')).model = value.replace('/position','/state')
        #get the num of illum devices
        # num_illum_devices = len(Attribute(self.settings_object["Mscope"]["comboBox_illum_types"]).read().value)
        illum_devices = list(Attribute(self.settings_object["Mscope"]["comboBox_illum_types"]).read().value)
        self.populate_illum_widgets(illum_devices, 3)
        self._set_exposure()
        if self.settings_object['spockLogin']['useQTSpock']:
            self._start_spock()

    def _set_exposure(self):
        tg_dv = self.settings_object['Camaras']['camaraDevice']
        mode_attr = self.settings_object['Camaras']['camaraExposure_mode']['attr_name']
        exp_time_attr = self.settings_object['Camaras']['camaraExposure_time']['attr_name']
        self.comboBox_exposure_mode.setCurrentText(Attribute(f'{tg_dv}/{mode_attr}').read().value)
        self.lineEdit_exposure_time_abs.setModel(f'{tg_dv}/{exp_time_attr}')
        # self.lineEdit_exposure_time_abs.setModel(f'eval:{{{tg_dv}/{exp_time_attr}}}/1000')
        # self.lineEdit_exposure_time_abs.setStylesheet("color: white;  background-color: black")
        self.comboBox_exposure_mode.currentIndexChanged.connect(self._upon_exposure_mode_change)

    def _upon_exposure_mode_change(self):
        tg_dv = self.settings_object['Camaras']['camaraDevice']
        mode_attr = self.settings_object['Camaras']['camaraExposure_mode']['attr_name']
        Attribute(f'{tg_dv}/{mode_attr}').write(self.comboBox_exposure_mode.currentText())

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

    def mv_stages_to_cursor_pos_old(self):
        self.statusUpdate(f'moving sample stages to {self.last_cursor_pos_on_camera_viewer}')
        Attribute(self.settings_object['SampleStages']['x_stage_value']).write(self.last_cursor_pos_on_camera_viewer[0])
        Attribute(self.settings_object['SampleStages']['y_stage_value']).write(self.last_cursor_pos_on_camera_viewer[1])

    def mv_stages_to_cursor_pos(self):
        self.statusUpdate(f'moving sample stages to {self.last_cursor_pos_on_camera_viewer}')
        pstage_offset = self.camara_widget._cal_pstage_offset_wrt_prim_beam()
        Attribute(self.settings_object['SampleStages']['x_stage_value']).write(self.last_cursor_pos_on_camera_viewer[0] - pstage_offset[0])
        Attribute(self.settings_object['SampleStages']['y_stage_value']).write(self.last_cursor_pos_on_camera_viewer[1] - pstage_offset[1])

    def populate_illum_widgets(self, rows = 0, first_row = 4):
        cols = ['label_illum','horizontalSlider_illum', 'label_illum_pos', 'pushButton_lighton','pushButton_lightoff']
        widgets = [QLabel, QSlider, TaurusLabel, QPushButton, QPushButton]
        if type(rows) == list:
            rows_num = len(rows)
        else:
            rows_num = rows 
            rows = [f'illum device {i}' for i in range(rows_num)]
        for i in range(rows_num):
            for j in range(len(cols)):
                widget_name = f'{cols[j]}_{i}'
                args = [(f'{rows[i]}',), (Qt.Horizontal,), (),('Lighton',),('Lightoff',)]
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
        data = pd.DataFrame.from_dict({'new_task_or_not': [],'session':[], 'queue':[],'pre_scan_action':[],'scan_command':[], 'scan_info':[], 'geo_roi':[]})
        #disable_all_tabs_but_one(self, tab_widget_name, tab_indx)
        self.pandas_model_queue_camara_viewer = PandasModel(data = data, tableviewer = getattr(self, table_view_widget_name), main_gui=self)
        getattr(self, table_view_widget_name).setModel(self.pandas_model_queue_camara_viewer)
        getattr(self, table_view_widget_name).resizeColumnsToContents()
        getattr(self, table_view_widget_name).setSelectionBehavior(QAbstractItemView.SelectRows)
        getattr(self, table_view_widget_name).horizontalHeader().setStretchLastSection(True)

    def remove_all_tasks_from_table(self):
        data = pd.DataFrame.from_dict({'new_task_or_not': [],'session':[], 'queue':[],'pre_scan_action':[],'scan_command':[], 'scan_info':[], 'geo_roi':[]})
        self.pandas_model_queue_camara_viewer._data = data
        self.pandas_model_queue_camara_viewer.update_view()

    def add_one_task_to_scan_viewer(self, roi = None):
        num_of_existing_task = self.pandas_model_queue_camara_viewer._data.shape[0]
        #roi = self.camara_widget.roi_scan
        value_list = [
                      True,
                      self.lineEdit_queue_section_name.text(),\
                      self.lineEdit_scan_queue_name.text(),\
                      self.lineEdit_pre_scan_action_list.text(),\
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

    def duplicate_currently_selected_row(self):
        try:
            which_row = self.tableView_scan_list_camera_viewer.selectionModel().selectedRows()[0].row()
            temp = self.pandas_model_queue_camara_viewer._data.loc[which_row].to_list()
            num_of_existing_task = self.pandas_model_queue_camara_viewer._data.shape[0]
            self.pandas_model_queue_camara_viewer._data.loc[num_of_existing_task] = temp
            self.pandas_model_queue_camara_viewer.update_view()
        except:#nothing selected
            pass

    def fetch_data_from_server(self):
        columns = ['queue','pre_scan_action','scan_command','state']
        column_map = {'state':'scan_info'}
        other_info = {'session': self.lineEdit_queue_section_name.text(), 
                      'queue': self.lineEdit_scan_queue_name.text(),
                      'geo_roi': 'NA',
                      'new_task_or_not': False}
        columns_ordered = ['new_task_or_not','session','queue','pre_scan_action','scan_command','scan_info','geo_roi']
        df = self.pandas_model_queue._data[columns].copy().rename(columns=column_map).copy()
        for each, value in other_info.items():
            df[each] = value
        self.pandas_model_queue_camara_viewer._data = df[columns_ordered]
        self.pandas_model_queue_camara_viewer.update_view()

    def show_all_rois(self):
        for each in self.camara_widget.rois:
            self.camara_widget.img_viewer.vb.removeItem(each)
        for i in range(self.pandas_model_queue_camara_viewer._data.shape[0]):
            cmd = self.pandas_model_queue_camara_viewer._data.iloc[i,:]['scan_command']
            scan_roi_ref = self._compute_scan_roi_ref_origin(eval(self.pandas_model_queue_camara_viewer._data.iloc[i,:]['pre_scan_action']))
            scan_roi_ref_pix = self.camara_widget._convert_stage_coord_to_pix_unit(*scan_roi_ref)
            if cmd.startswith('pmesh'):
                anchors_list = re.findall(r"(\[[-+]?(?:\d*\.*\d+) [-+]?(?:\d*\.*\d+)\])", self.pandas_model_queue_camara_viewer._data.iloc[i,:]['scan_command'])
                anchors_list = [self.camara_widget._convert_stage_coord_to_pix_unit(*eval(each.replace(' ', ','))) for each in anchors_list]
                # anchors_list = [np.array(each)/1000+scan_roi_ref_pix for each in anchors_list]
                if self.settings_object['ScanType']['two_set_of_stage']:
                    anchors_list = [np.array(each)+self.camara_widget._convert_stage_coord_to_pix_unit(*scan_roi_ref) for each in anchors_list]
                else:
                    pass
                #anchors_list = [np.array(each)+scan_roi_ref_pix for each in anchors_list]
                pen = pg.mkPen((0, 200, 200), width=1)
                roi = pg.PolyLineROI([],closed=True,movable=False)
                roi.setPoints(anchors_list)
                roi.setZValue(10000)
                roi.handlePen = pg.mkPen("#FFFFFF")
                self.camara_widget.img_viewer.vb.addItem(roi)      
                self.camara_widget.rois.append(roi)
            elif cmd.startswith('mesh'):     
                scan_cmd_list = cmd.rsplit(' ')
                # x_, y_ = float(scan_cmd_list[2])/1000, float(scan_cmd_list[6])/1000
                # x_end_, y_end_ = float(scan_cmd_list[3])/1000, float(scan_cmd_list[7])/1000
                x_, y_ = float(scan_cmd_list[2]), float(scan_cmd_list[6])
                x_end_, y_end_ = float(scan_cmd_list[3]), float(scan_cmd_list[7])
                #self.camara_widget.roi_scan_xy_stage = [x_, y_]
                x, y = self.camara_widget._convert_stage_coord_to_pix_unit(x_, y_)
                x_end, y_end = self.camara_widget._convert_stage_coord_to_pix_unit(x_end_, y_end_)
                w, h = abs(x - x_end), abs(y - y_end)                     
                pen = pg.mkPen((0, 200, 200), width=1)
                roi = pg.ROI(scan_roi_ref_pix, [w, h], pen=pen)
                roi.setZValue(10000)
                self.camara_widget.img_viewer.vb.addItem(roi)      
                self.camara_widget.rois.append(roi)

    def delete_rois(self):
        for each in self.camara_widget.rois:
            self.camara_widget.img_viewer.vb.removeItem(each)

    @Slot(QtCore.QModelIndex)
    def update_roi_upon_click_tableview_camera_widget(self, modelindex):
        row = modelindex.row()
        self.update_roi_at_row(row)

    def _compute_scan_roi_ref_origin(self, pre_scan_action_list):
        assert type(pre_scan_action_list)==list, 'pre scan action not in a list format'
        assert len(pre_scan_action_list)==2, 'two items should be in pre scan action list'
        return pre_scan_action_list[0][2], pre_scan_action_list[1][2]

    def update_roi_at_row(self, row):
        # roi = eval(self.pandas_model_queue_camara_viewer._data.iloc[row,:]['geo_roi'])
        #x, y, w, h = roi
        self.camara_widget.setPaused(True)
        scan_cmd_list = self.pandas_model_queue_camara_viewer._data.iloc[row,:]['scan_command'].rsplit(' ')
        scan_roi_ref = self._compute_scan_roi_ref_origin(eval(self.pandas_model_queue_camara_viewer._data.iloc[row,:]['pre_scan_action']))
        if scan_cmd_list[0]=='pmesh':
            anchors_list = re.findall(r"(\[[-+]?(?:\d*\.*\d+) [-+]?(?:\d*\.*\d+)\])", self.pandas_model_queue_camara_viewer._data.iloc[row,:]['scan_command'])
            anchors_list = [self.camara_widget._convert_stage_coord_to_pix_unit(*eval(each.replace(' ', ','))) for each in anchors_list]
            #scan_roi_ref_ = scan_roi_ref if self.settings_object['ScanType']['two_set_of_stage'] else [0,0]
            if self.settings_object['ScanType']['two_set_of_stage']:
                anchors_list = [np.array(each)+self.camara_widget._convert_stage_coord_to_pix_unit(*scan_roi_ref) for each in anchors_list]
            else:
                pass
            # anchors_list = [np.array(each)/1000+self.camara_widget._convert_stage_coord_to_pix_unit(*scan_roi_ref) for each in anchors_list]
            # if type(self.camara_widget.roi_scan)==pg.PolyLineROI:
                # self.camara_widget.roi_scan.setPos(0,0,update=False,finish=False)
                # self.camara_widget.roi_scan.setPoints(anchors_list)
            # else:
            #this is an ugly hack to remove the footprint of pos of old roi_scan
            self.camara_widget.roi_scan.setPos(0,0)
            self.camara_widget.roi_type = 'polyline'
            self.camara_widget.img_viewer.vb.removeItem(self.camara_widget.roi_scan)
            pen = pg.mkPen((0, 200, 200), width=1)
            self.camara_widget.roi_scan = pg.PolyLineROI([],closed=True,movable=False)
            # self.camara_widget.roi_scan.sigRegionChanged.connect(self.camara_widget._cal_scan_coordinates)
            self.camara_widget.roi_scan.handleSize = 10
            self.camara_widget.roi_scan.setPoints(anchors_list)
            self.camara_widget.roi_scan.setZValue(10000)
            self.camara_widget.roi_scan.handlePen = pg.mkPen("#FFFFFF")
            self.camara_widget.img_viewer.vb.addItem(self.camara_widget.roi_scan)
            #for some reason, the following sig/slot connections are not needed
            # if added, the main thread is dragging, but why? Garbage collection not fast enough?
            # self.camara_widget.roi_scan.sigRegionChangeStarted.connect(lambda: self.camara_widget.setPaused(True))
            # self.camara_widget.roi_scan.sigRegionChanged.connect(self.camara_widget._cal_scan_coordinates)
            # self.camara_widget.roi_scan.sigRegionChangeStarted.connect(lambda: self.camara_widget.setPaused(True))
            self.camara_widget._cal_scan_coordinates()
        elif scan_cmd_list[0]=='mesh':              
            x_, y_ = float(scan_cmd_list[2]), float(scan_cmd_list[6])
            x_end_, y_end_ = float(scan_cmd_list[3]), float(scan_cmd_list[7])
            self.camara_widget.roi_scan_xy_stage = scan_roi_ref
            # x, y = self.camara_widget._convert_stage_coord_to_pix_unit(x_/1000, y_/1000)
            x, y = self.camara_widget._convert_stage_coord_to_pix_unit(x_, y_)
            x_ref, y_ref = self.camara_widget._convert_stage_coord_to_pix_unit(*scan_roi_ref)
            # x_end, y_end = self.camara_widget._convert_stage_coord_to_pix_unit(x_end_/1000, y_end_/1000)
            x_end, y_end = self.camara_widget._convert_stage_coord_to_pix_unit(x_end_, y_end_)
            w, h = abs(x - x_end), abs(y - y_end)
            if type(self.camara_widget.roi_scan)==pg.PolyLineROI:
                self.camara_widget.roi_type = 'rectangle'
                self.camara_widget.set_reference_zone(x_ref,y_ref,w,h)
            else:
                # self.camara_widget.set_reference_zone(x,y,w,h)
                self.camara_widget.roi_scan.setPos(x_ref,y_ref,update=False,finish=False)
                #self.camara_widget.roi_scan.setX(x)
                #self.camara_widget.roi_scan.setY(y)
                self.camara_widget.roi_scan.setSize((w, h))
        else:
            pass
        self.camara_widget.setPaused(False)

    #not used anymore
    def _update_roi_at_row(self, row):
        roi = eval(self.pandas_model_queue_camara_viewer._data.iloc[row,:]['geo_roi'])
        x, y, w, h = roi
        scan_cmd_list = self.pandas_model_queue_camara_viewer._data.iloc[row,:]['scan_command'].rsplit(' ')
        if scan_cmd_list[0]=='pmesh':
            #pmesh scan could not set the polylineRoi this way, just ignore this
            return
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
                if self.pandas_model_queue_camara_viewer._data['new_task_or_not'].to_list()[i]:
                    jobs.append({
                        'queue': self.lineEdit_scan_queue_name.text(),
                        'session': self.lineEdit_queue_section_name.text(),
                        'pre_scan_action': eval(self.pandas_model_queue_camara_viewer._data['pre_scan_action'].to_list()[i]),
                        'scan_command': self.pandas_model_queue_camara_viewer._data['scan_command'].to_list()[i].rsplit(' '),
                        'scan_info': self.pandas_model_queue_camara_viewer._data['scan_info'].to_list()[i]
                    })
            return jobs
        def _make_job_list_img_reg():
            jobs = []
            rows = self.pandas_model_scan_list._data.shape[0]
            for i in range(rows):
                jobs.append({
                    'queue': self.lineEdit_queue_name_imgreg.text(),
                    'session': self.lineEdit_session_name.text(),
                    'scan_command': self.pandas_model_scan_list._data['scan macro'].to_list()[i].rsplit(' '),
                    'pre_scan_action': self.pandas_model_scan_list._data['prescan action'].to_list()[i]
                })
            return jobs            
        try:
            if viewer == 'camera':
                self.queue_comm.send_receive_message(['add', _make_job_list()])
                self.pandas_model_queue_camara_viewer._data.loc[self.pandas_model_queue_camara_viewer._data['new_task_or_not'] == True,'new_task_or_not'] = False
            elif viewer == 'img_reg':
                self.queue_comm.send_receive_message(['add', _make_job_list_img_reg()])
            else:
                return
            self.statusUpdate('Jobs are submitted to queue server.')
        except Exception as e:
            self.statusUpdate('Fail to submit the jobs.'+str(e))
