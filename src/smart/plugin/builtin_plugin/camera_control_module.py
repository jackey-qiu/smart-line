import os, copy, re
import matplotlib.image
from taurus.qt.qtgui.base import TaurusBaseComponent
from taurus.external.qt import Qt
from pyqtgraph.Qt import QtCore, QtGui
from pyqtgraph.Point import Point
from pyqtgraph import GraphicsLayoutWidget, ImageItem
from PyQt5.QtCore import pyqtSlot as Slot, pyqtSignal as Signal
from PyQt5 import QtWidgets
import pyqtgraph as pg
import pyqtgraph.exporters
import tango
from tango._tango import DevState as dev_state
from taurus import Device, Attribute
from taurus.core import TaurusEventType, TaurusTimeVal
from smart.gui.widgets.context_menu_actions import setRef, resumePrim, mvMotors, VisuaTool, camSwitch, AutoLevelTool, LockCrossTool, SaveCrossHair, ResumeCrossHair
from taurus.qt.qtgui.tpg import ForcedReadTool
from functools import partial
import numpy as np
from smart import icon_path
from ...util.util import findMainWindow, trigger, trigger2

# timer_trigger = trigger(timeout=0.1)

class camera_control_panel(object):

    def __init__(self):
        self.camera_is_on = False
        self.last_cursor_pos_on_camera_viewer = [0,0]
        self.build_cam_widget()
        self._create_toolbar_camera_widget()

    def _extract_cam_info_from_config(self):
        gridLayoutWidgetName = self.settings_object["Camaras"]["gridLayoutWidgetName"]
        viewerWidgetName = self.settings_object["Camaras"]["viewerWidgetName"]
        camaraStreamModel = self.settings_object["Camaras"]["camaraStreamModel"]
        camaraDevice = self.settings_object["Camaras"]["camaraDevice"]
        camaraDataCallbacks = self.settings_object["Camaras"]["camaraDataFormatCallbacks"]
        return gridLayoutWidgetName, viewerWidgetName, camaraStreamModel, camaraDevice, camaraDataCallbacks

    def _extract_sample_stage_models(self):
        samx = self.settings_object["SampleStages"]["x_stage_value"]
        samy = self.settings_object["SampleStages"]["y_stage_value"]
        scanx = self.settings_object["SampleStages"]["x_pstage_value"]
        scany = self.settings_object["SampleStages"]["y_pstage_value"]
        return samx, samy, scanx, scany

    def build_cam_widget(self):
        gridLayoutWidgetName, viewerWidgetName, *_ = self._extract_cam_info_from_config()

        if gridLayoutWidgetName!=None:
            if viewerWidgetName!=None:
                if not hasattr(self, viewerWidgetName):
                    setattr(self, viewerWidgetName,TaurusImageItem(parent=self, rgb_viewer=self.settings_object['Camaras']['rgb']))
                    getattr(self, gridLayoutWidgetName).addWidget(getattr(self, viewerWidgetName))

    def connect_slots_cam(self):
        level1, level2, level3 = self.settings_object["Camaras"]["presetZoom"]
        self.pushButton_zoom_level1.clicked.connect(lambda: self.set_zoom_level(level1))
        self.pushButton_zoom_level2.clicked.connect(lambda: self.set_zoom_level(level2))
        self.pushButton_zoom_level3.clicked.connect(lambda: self.set_zoom_level(level3))
        # self.pushButton_save_roi_xy.clicked.connect(self.camara_widget.save_current_roi_xy)

    def control_cam(self):
        gridLayoutWidgetName, viewerWidgetName, camaraStreamModel, *_ = self._extract_cam_info_from_config()
        if not getattr(self, viewerWidgetName).getModel():
            self.start_cam_stream()
        else:
            self.stop_cam_stream()

    def start_cam_stream(self):
        _, viewerWidgetName, camaraStreamModel, device_name, data_format_cbs = self._extract_cam_info_from_config()
        model_samx, model_samy, model_scanx, model_scany = self._extract_sample_stage_models()
        if getattr(self, viewerWidgetName).getModel()!='':
            return
        
        _device = Device(device_name)
        if _device.state.name == 'Ready':
            self.camera_is_on = True
            getattr(self, viewerWidgetName).setModel(camaraStreamModel)
            getattr(self, viewerWidgetName).width = _device.width
            getattr(self, viewerWidgetName).height = _device.height
            self.statusbar.showMessage(f'start cam streaming with model of {camaraStreamModel}')
        else:
            self.camera_is_on = False
            self.camara_widget.img.setImage(self.camara_widget.fake_img)
            self.camara_widget.hist.imageChanged(self.camara_widget.autolevel, self.camara_widget.autolevel)
            getattr(self, viewerWidgetName).setModel(None)
            self.statusbar.showMessage(f'Fail to start cam streaming with state of {_device.state.name}')

        getattr(self, viewerWidgetName).setModel(model_samx, key='samx')
        getattr(self, viewerWidgetName).setModel(model_samy, key='samy')
        getattr(self, viewerWidgetName).setModel(model_scanx, key='scanx')
        getattr(self, viewerWidgetName).setModel(model_scany, key='scany')
        getattr(self, viewerWidgetName).data_format_cbs = data_format_cbs
        # self.camara_widget.setForcedReadPeriod(0.2)

    def set_zoom_level(self, level = 50):
        Attribute(self.settings_object["ZoomDevice"]["label_zoom_pos"]).write(level)
        # self.update_pixel_size()
        self.camara_widget.reset_geo_after_zoom_level_change()

    def stop_cam_stream(self):
        _, viewerWidgetName, *_ = self._extract_cam_info_from_config()
        #model_samx, model_samy, model_scanx, model_scany = self._extract_sample_stage_models()
        getattr(self, viewerWidgetName).setModel(None)
        getattr(self, viewerWidgetName).setModel(None, key='samx')
        getattr(self, viewerWidgetName).setModel(None, key='samy')
        getattr(self, viewerWidgetName).setModel(None, key='scanx')
        getattr(self, viewerWidgetName).setModel(None, key='scany')
        self.camera_is_on = False
        #set aribitray long timeout to simulate cam swtich off
        # self.camara_widget.setForcedReadPeriod(3600)
        self.statusbar.showMessage('stop cam streaming')

    def _append_img_processing_cbs(self, cb_str):
        #cb_str must be an lambda func of form like lambda data:data.reshape((2048, 2048, 3))
        # - lambda data:np.rot90(data[0].reshape((2048,2048,3)),3)
        if cb_str in self.camara_widget.data_format_cbs:
            pass
        else:
            self.camara_widget.data_format_cbs.append(cb_str)

    def _lock_crosshair_lines(self, action_object_pair):
        assert len(action_object_pair)==2, 'two action objects are needed here'
        self.camara_widget.isoLine_h.setMovable(False)
        self.camara_widget.isoLine_v.setMovable(False)
        action_object_pair[0].setVisible(False)
        action_object_pair[1].setVisible(True)

    def _unlock_crosshair_lines(self, action_object_pair):
        assert len(action_object_pair)==2, 'two action objects are needed here'
        self.camara_widget.isoLine_h.setMovable(True)
        self.camara_widget.isoLine_v.setMovable(True)
        action_object_pair[0].setVisible(False)
        action_object_pair[1].setVisible(True)

    def _save_crosshair(self):
        x, y = self.camara_widget.isoLine_v.value(),self.camara_widget.isoLine_h.value()
        self.camara_widget.saved_crosshair_pos = [x, y]

    def _resume_crosshair(self):
        x, y = self.camara_widget.saved_crosshair_pos
        self.camara_widget.isoLine_v.setValue(x)
        self.camara_widget.isoLine_h.setValue(y)

    def _resume_prim_beam_pos(self, direct = False):
        if not direct:
            msgBox = QtWidgets.QMessageBox()
            msgBox.setIcon(QtWidgets.QMessageBox.Question)
            msgBox.setText(f"Are you sure to resume the crosshair position?")
            msgBox.setWindowTitle("Resume crosshair pos")
            msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
            #msgBox.buttonClicked.connect(self._parent.mv_sample_stage_to_cursor_point)
            returnValue = msgBox.exec()
            if returnValue == QtWidgets.QMessageBox.Ok:
                self.camara_widget.resume_prim_beam_to_saved_values()
        else:
            self.camara_widget.resume_prim_beam_to_saved_values()

    def _calibrate_pos(self):
        self.camara_widget.mv_img_to_ref()
        self.camara_widget.pos_calibration_done = True

    def _create_toolbar_camera_widget(self):
        from PyQt5.QtWidgets import QToolBar, QAction
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QIcon
        self.camToolBar = QToolBar('camera', self)
        action_switch_on_camera = QAction(QIcon(str(icon_path / 'smart' / 'cam_on.png')),'switch on camera',self)
        action_switch_on_camera.setStatusTip('You can switch on the camera here.')
        action_switch_on_camera.triggered.connect(self.start_cam_stream)
        action_switch_off_camera = QAction(QIcon(str(icon_path / 'smart' / 'cam_off.png')),'switch off camera',self)
        action_switch_off_camera.setStatusTip('You can switch off the camera here.')
        action_switch_off_camera.triggered.connect(self.stop_cam_stream)
        action_switch_off_camera.setVisible(False)
        lock = QAction(QIcon(str(icon_path / 'smart' / 'unlock.png')),'lock crosshair',self)
        lock.setStatusTip('You can freeze the crosshair lines.')
        unlock = QAction(QIcon(str(icon_path / 'smart' / 'lock.png')),'unlock crosshair',self)
        unlock.setStatusTip('You can unfreeze the crosshair lines.')
        lock.triggered.connect(lambda: self._lock_crosshair_lines([lock, unlock]))            
        unlock.triggered.connect(lambda: self._unlock_crosshair_lines([unlock, lock]))               
        unlock.setVisible(False)
        resumecrosshair = QAction(QIcon(str(icon_path / 'smart' / 'resume_crosshair.png')),'resume crosshair pos',self)
        resumecrosshair.setStatusTip('Resume the crosshair line positions to previous saved pars for prim beam.')
        resumecrosshair.triggered.connect(self._resume_prim_beam_pos)
        poscalibration = QAction(QIcon(str(icon_path / 'icons_n' / 'lasing_navigate.png')),'stage calibration',self)
        poscalibration.setStatusTip('You can calibrate the crosshair pos to reflect sample stage position at the prim beam.')
        poscalibration.triggered.connect(self._calibrate_pos)               
        center = QAction(QIcon(str(icon_path / 'smart' / 'center.png')),'center the stage to prim beam',self)
        center.setStatusTip('You will move the stage back to the primary beam position saved in the config file.')
        center.triggered.connect(self.camara_widget.mv_stage_to_prim_beam)        
        autoscale = QAction(QIcon(str(icon_path / 'smart' / 'unscale_rgb.png')),'auto scaling the rgb color',self)
        autoscale.setStatusTip('Turn on the autoscaling of RGB channels.')
        autoscaleoff = QAction(QIcon(str(icon_path / 'smart' / 'scale_rgb.png')),'turn off auto scaling the rgb color',self)
        autoscaleoff.setStatusTip('Turn off the autoscaling of RGB channels.')
        autoscale.setVisible(False)
        autoscale.triggered.connect(lambda: self.camara_widget.update_autolevel(True, [autoscale, autoscaleoff]))               
        autoscaleoff.triggered.connect(lambda: self.camara_widget.update_autolevel(False, [autoscaleoff, autoscale]))               
        roi_rect = QAction(QIcon(str(icon_path / 'smart' / 'polyline_roi.png')),'select rectangle roi',self)
        roi_rect.setStatusTip('click an drag to get a rectangle roi.')
        roi_polyline = QAction(QIcon(str(icon_path / 'smart' / 'rectangle_roi.png')),'select polygone roi',self)
        roi_polyline.setStatusTip('click an drag to get a polygone roi selection.')
        roi_rect.setVisible(False)
        roi_rect.triggered.connect(lambda: self.camara_widget.set_roi_type('rectangle', [roi_rect, roi_polyline]))               
        roi_polyline.triggered.connect(lambda: self.camara_widget.set_roi_type('polyline', [roi_polyline, roi_rect]))               
        click_move = QAction(QIcon(str(icon_path / 'smart' / 'stop.png')),'enable click to move stage mode',self)
        click_move.setStatusTip('click to activate stage moving with mouse click.')
        # click_move.triggered.connect(lambda: self.camara_widget.enable_mouse_click_move_stage()) 
        # self.click_move = click_move          
        stop_click_move = QAction(QIcon(str(icon_path / 'smart' / 'click.png')),'disable click to move stage mode',self)
        stop_click_move.setStatusTip('click to deactivate stage moving with mouse click.')
        click_move.triggered.connect(lambda: self.camara_widget.enable_mouse_click_move_stage([click_move, stop_click_move])) 
        stop_click_move.triggered.connect(lambda: self.camara_widget.disable_click_move_stage([stop_click_move, click_move])) 
        stop_click_move.setVisible(False)
        show_bound_roi = QAction(QIcon(str(icon_path / 'smart' / 'boundary.png')),'show the boundary according to current stage softlimits',self)
        show_bound_roi.setStatusTip('click to show or hide the boundary roi based on current stage softlimits.')
        show_bound_roi.triggered.connect(lambda: self.camara_widget.get_stage_bounds())
        save_img = QAction(QIcon(str(icon_path / 'others' / 'save_img.png')),'export camera image',self)
        save_img.setStatusTip('click to export camera image.')
        save_img.triggered.connect(lambda: self.camara_widget.export_image())
        self.camToolBar.addAction(action_switch_on_camera)
        self.camToolBar.addAction(action_switch_off_camera)
        self.camToolBar.addAction(save_img)
        self.camToolBar.addAction(autoscale)
        self.camToolBar.addAction(autoscaleoff)
        self.camToolBar.addAction(resumecrosshair)
        self.camToolBar.addAction(poscalibration)
        self.camToolBar.addAction(center)
        self.camToolBar.addAction(lock)
        self.camToolBar.addAction(unlock)
        self.camToolBar.addAction(roi_rect)
        self.camToolBar.addAction(roi_polyline)
        self.camToolBar.addAction(click_move)
        self.camToolBar.addAction(stop_click_move)
        self.camToolBar.addAction(show_bound_roi)
        self.addToolBar(Qt.LeftToolBarArea, self.camToolBar)

class CumForcedReadTool(ForcedReadTool):
    def __init__(self,*args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def setPeriod(self, period):
        """Change the period value. Use 0 for disabling
        :param period: (int) period in ms
        """
        self._period = period
        # update existing items
        if self.autoconnect() and self.plot_item is not None:
            item = self.plot_item.getViewWidget()
            if hasattr(item, "setForcedReadPeriod"):
                item.setForcedReadPeriod(period)
        # emit valueChanged
        self.valueChanged.emit(period)


class TaurusImageItem(GraphicsLayoutWidget, TaurusBaseComponent):
    """
    Displays 2D and 3D image data
    """
    sigScanRoiAdded = Signal(float, float, float, float)
    modelKeys = ['img','samx','samy','scanx','scany']
    # modelKeys = [TaurusBaseComponent.MLIST]
    # TODO: clear image if .setModel(None)
    def __init__(self, parent = None, rgb_viewer = False, *args, **kwargs):
        GraphicsLayoutWidget.__init__(self, *args, **kwargs)
        TaurusBaseComponent.__init__(self, "TaurusImageItem")
        self.period_timer_forceRead = trigger(cb=self._forceRead, repeat=True)
        self.thread_period_timer_forceRead = QtCore.QThread()
        self.period_timer_forceRead.moveToThread(self.thread_period_timer_forceRead)
        self.thread_period_timer_forceRead.started.connect(self.period_timer_forceRead.run)
        # self.timer_mouse_click_reaction = trigger2()
        # self.thread_mouse_click_reation = QtCore.QThread()
        # self.timer_mouse_click_reaction.moveToThread(self.thread_mouse_click_reation)
        # self.thread_mouse_click_reation.started.connect(self.timer_mouse_click_reaction.run)        
        self._parent = parent
        self.rgb_viewer = rgb_viewer
        self._init_ui()
        self.width = None
        self.data_format_cbs = [lambda x: x]
        self.autolevel = True
        self.roi_scan = None
        self.roi_limit = None
        self.rois = []
        self.roi_scan_xy_stage = [None, None]
        self.roi_scan_xy_stage_piezo = [None, None]
        self.piezo_stage_roi_ref_set = False
        self.roi_type = 'rectangle'
        self.mouse_click_move_stage_enabled = False
        self.pos_calibration_done = False
        self.sigScanRoiAdded.connect(self.set_reference_zone)
        self.fake_img = np.random.rand(2048,2048,3) * 255
        # self.setModel('sys/tg_test/1/long64_image_ro')

    def reset_geo_after_zoom_level_change(self):
        main_gui = findMainWindow()
        #calculate the scaling factor, zoom in if sf<1, zoom out if sf>1
        sf = Attribute(main_gui.settings_object["Camaras"]["pixel_size"]).read().value/main_gui.camara_pixel_size
        #calculate the dist between the image center and crosshair pos in both x and y direct
        cen = [self.img.x() + self.img.width()/2, self.img.y() + self.img.height()/2]
        l_cp_to_cen = (self.isoLine_v.value() - cen[0])/sf
        h_cp_to_cen = (self.isoLine_h.value() - cen[1])/sf
        #first disconnect the slot
        self.isoLine_v.sigPositionChanged.disconnect()
        self.isoLine_h.sigPositionChanged.disconnect()
        #cal the new position in the current scale
        main_gui.crosshair_pos_at_prim_beam = list(np.array(main_gui.stage_pos_at_prim_beam)/Attribute(main_gui.settings_object["Camaras"]["pixel_size"]).read().value)
        #now let's cal the new position of the image center
        cen_new = np.array(main_gui.crosshair_pos_at_prim_beam) - [l_cp_to_cen, h_cp_to_cen]
        img_new_pos = cen_new - [self.img.width()/2,self.img.height()/2]
        #now move crosshair and img
        self.isoLine_h.setValue(main_gui.crosshair_pos_at_prim_beam[1])
        self.isoLine_v.setValue(main_gui.crosshair_pos_at_prim_beam[0])
        #move img to new pos
        self.img.setX(img_new_pos[0])
        self.img.setY(img_new_pos[1])
        #update the pix size
        main_gui.camara_pixel_size = Attribute(main_gui.settings_object["Camaras"]["pixel_size"]).read().value
        #reconnect the slot
        self.isoLine_h.sigPositionChanged.connect(main_gui._calibrate_pos)
        self.isoLine_v.sigPositionChanged.connect(main_gui._calibrate_pos)
        #update img settings
        self.update_img_settings()
        #change the axis scale finally
        main_gui.update_pixel_size()

    def get_stage_bounds(self):
        #this is fragile, and should be changed whenever you change the model key
        hor_stage_limits = [each.m for each in self.getModelObj(key='samx').getLimits()]
        ver_stage_limits = [each.m for each in self.getModelObj(key='samy').getLimits()]
        x_, x_end_ = hor_stage_limits
        y_, y_end_ = ver_stage_limits
        #self.camara_widget.roi_scan_xy_stage = [x_, y_]
        x, y = self._convert_stage_coord_to_pix_unit(x_, y_)
        x_end, y_end = self._convert_stage_coord_to_pix_unit(x_end_, y_end_)
        w, h = abs(x - x_end), abs(y - y_end)
        or_x = x if x<x_end else x_end
        or_y = y if y>y_end else y_end
        #note (x,y) is bottom left corner, while top left corner is needed
        if self.roi_limit == None:
            pen = pg.mkPen((200, 0, 0), width=2)
            self.roi_limit = pg.ROI([or_x, or_y-h], [w, h], pen=pen, movable=False, removable=False)
            self.roi_limit.setZValue(100)
            self.img_viewer.vb.addItem(self.roi_limit)
        else:
            self.img_viewer.vb.removeItem(self.roi_limit)
            self.roi_limit = None

    def update_viewer_type(self, rgb: bool):
        self.rgb_viewer = rgb
        self._setup_rgb_viewer()

    def enable_mouse_click_move_stage(self, action_object_pair):
        self.mouse_click_move_stage_enabled = True
        assert len(action_object_pair)==2, 'two action objects are needed here'
        action_object_pair[0].setVisible(False)
        action_object_pair[1].setVisible(True)

    def set_mouse_click_move_stage(self, enabled):
        self.mouse_click_move_stage_enabled = enabled
        gui = findMainWindow()
        if enabled:
            gui.click_move.setEnabled(False)
            try:
                self.thread_mouse_click_reation.terminate()
            except:
                pass
            self.timer_mouse_click_reaction.start_new_cb(self.disable_click_move_stage, gui.settings_object['Camaras']['click_move_timeout'])
            self.thread_mouse_click_reation.start()
        else:
            self.disable_click_move_stage()

    def disable_click_move_stage(self, action_object_pair):
        self.mouse_click_move_stage_enabled = False
        assert len(action_object_pair)==2, 'two action objects are needed here'
        action_object_pair[0].setVisible(False)
        action_object_pair[1].setVisible(True)
        # findMainWindow().click_move.setEnabled(True)

    def set_roi_type(self, roi_type, action_object_pair):
        if roi_type in ['rectangle','polyline']:
            if roi_type != self.roi_type:
                if self.roi_scan!=None:
                    self.img_viewer.vb.removeItem(self.roi_scan)
                    self.roi_scan = None
                    self.roi_type = roi_type
        assert len(action_object_pair)==2, 'two action objects are needed here'
        action_object_pair[0].setVisible(False)
        action_object_pair[1].setVisible(True)

    def _save_current_roi_xy_piezo(self, roi_xy_stage = None):
        main_gui = findMainWindow()
        if type(roi_xy_stage)!=type(None):
            self.roi_scan_xy_stage_piezo = list(roi_xy_stage)
        else:
            self.roi_scan_xy_stage_piezo = [
                Attribute(main_gui.settings_object['SampleStages']['x_pstage_value']).rvalue.m,
                Attribute(main_gui.settings_object['SampleStages']['y_pstage_value']).rvalue.m
            ]

    def save_current_roi_xy(self, roi_xy_stage = None):
        main_gui = findMainWindow()
        if type(roi_xy_stage)!=type(None):
            self.roi_scan_xy_stage = list(roi_xy_stage)
            if not self.piezo_stage_roi_ref_set:
                self._save_current_roi_xy_piezo()
                self.piezo_stage_roi_ref_set = True
            x_stage = main_gui.settings_object['SampleStageMotorNames']['x']
            y_stage = main_gui.settings_object['SampleStageMotorNames']['y']
            main_gui.lineEdit_pre_scan_action_list.setText(f"[['mv','{x_stage}', {self.roi_scan_xy_stage[0]}],['mv','{y_stage}',{self.roi_scan_xy_stage[1]}]]")
            return
        cmd = main_gui.lineEdit_full_macro_name.text()
        if self.roi_type=='rectangle':
            if cmd != '':
                scan_cmd_list = cmd.rsplit(' ')
                x, y = float(scan_cmd_list[2]), float(scan_cmd_list[6])
            self.roi_scan_xy_stage = [x, y]
        else:
            try:
                pos_list = re.findall(r"(\[[-+]?(?:\d*\.*\d+) [-+]?(?:\d*\.*\d+)\])", cmd)
                self.roi_scan_xy_stage = eval(pos_list[0].replace(' ',','))
            except:
                pass
        x_stage = main_gui.settings_object['SampleStageMotorNames']['x']
        y_stage = main_gui.settings_object['SampleStageMotorNames']['y']
        main_gui.lineEdit_pre_scan_action_list.setText(f"[['mv','{x_stage}', {self.roi_scan_xy_stage[0]}],['mv','{y_stage}',{self.roi_scan_xy_stage[1]}]]")

    def update_autolevel(self, autolevel, action_object_pair):
        self.autolevel = autolevel
        assert len(action_object_pair)==2, 'two action objects are needed here'
        action_object_pair[0].setVisible(False)
        action_object_pair[1].setVisible(True)

    def _init_ui(self):
        self.rgb_viewer = findMainWindow().settings_object['Camaras']['rgb']
        self._setup_rgb_viewer()
        self._setup_context_action()

    def _setup_context_action(self):
        main_gui = findMainWindow()
        if not self.rgb_viewer:
            self.vt = VisuaTool(self, properties = ['prof_hoz','prof_ver'])
            self.vt.attachToPlotItem(self.img_viewer)
        self.fr = CumForcedReadTool(self, period=0)
        self.fr.attachToPlotItem(self.img_viewer)
        if main_gui.user_right == 'super':
            self.mvMotors = mvMotors(self._parent)
            self.mvMotors.attachToPlotItem(self.img_viewer) 

    def _setup_rgb_viewer(self):
        self.isoLine_v = pg.InfiniteLine(angle=90, movable=True, pen=pg.mkPen('green', width=4))
        self.isoLine_h = pg.InfiniteLine(angle=0, movable=True, pen=pg.mkPen('green', width=4))
        # self.isoLine_h.sigPositionChanged.connect(main_gui._calibrate_pos)
        # self.isoLine_v.sigPositionChanged.connect(main_gui._calibrate_pos)
        self.isoLine_v.setValue(0)
        self.isoLine_v.setZValue(100000) # bring iso line above contrast controls
        self.isoLine_h.setValue(0)
        self.isoLine_h.setZValue(100000) # bring iso line above contrast controls
        self.img_viewer = self.addPlot(row = 2, col = 1, rowspan = 5, colspan = 10)
        self.img_viewer.setAspectLocked()
        self.img = pg.ImageItem()
        self.img_viewer.addItem(self.img)

        self.img_viewer.addItem(self.isoLine_v, ignoreBounds = True)
        self.img_viewer.addItem(self.isoLine_h, ignoreBounds = True)
        if self.rgb_viewer:
            self.hist = pg.HistogramLUTItem(levelMode='rgba')
        else:
            self.hist = pg.HistogramLUTItem(levelMode='mono')
        self.hist.vb.setMouseEnabled(y=True) # makes user interaction a little easier
        self.addItem(self.hist, row = 2, col = 0, rowspan = 5, colspan = 1)
        self.hist.setImageItem(self.img)

        self.img_viewer.vb.scene().sigMouseMoved.connect(self._connect_mouse_move_event)
        self.img_viewer.vb.scene().sigMouseClicked.connect(self._execute_stage_move_upon_mouseclick)
        self.img_viewer.vb.mouseDragEvent = partial(self._mouseDragEvent, self.img_viewer.vb)

        #set the img to origin (0,0)
        self._mv_img_to_pos(0, 0)

    def _setup_mono_viewer(self):
        self.img_mono = pg.ImageItem()
        self.img_viewer.addItem(self.img_mono)

        self.hist_mono = pg.HistogramLUTItem(levelMode='mono')
        self.hist_mono.vb.setMouseEnabled(y=True) # makes user interaction a little easier
        self.addItem(self.hist_mono, row = 2, col = 0, rowspan = 5, colspan = 1)
        self.hist_mono.setImageItem(self.img_mono)

        #set the img to origin (0,0)
        # self._mv_img_to_pos(0, 0)    

    def _execute_stage_move_upon_mouseclick(self):
        door = tango.DeviceProxy(findMainWindow().settings_object['spockLogin']['doorName'])
        run = (door.state() == dev_state.RUNNING)
        if self.mouse_click_move_stage_enabled and (not run):
            findMainWindow().mv_stages_to_cursor_pos()

    #suppose to move the bottomleft corner of image to the pos(x, y)
    def _mv_img_to_pos(self, x, y):
        self.img.setX(0)
        self.img.setY(0)
        tr = QtGui.QTransform()
        tr.translate(x, y)
        self.img.setTransform(tr)

    @Slot(float,float,float,float)
    def set_reference_zone(self, x0, y0, w, h):
        self.set_reference_zone_pure(x0,y0,w,h)
        self._cal_scan_coordinates()
        
    def export_image(self):
        gui = findMainWindow()
        try:
            folder = gui.settings_object.get('Camaras').get('exported_image_folder')
            img_name, ok = QtWidgets.QInputDialog.getText(self, f'save image in {folder}', 'Input image file name:', text= 'exported_img') 
            if not ok:
                return
            exporter = pyqtgraph.exporters.ImageExporter(self.img_viewer)
            exporter.export(os.path.join(folder,f'{img_name}_with_crosshair.png'))
            self.isoLine_v.hide()
            self.isoLine_h.hide()
            exporter = pyqtgraph.exporters.ImageExporter(self.img_viewer)
            exporter.export(os.path.join(folder,f'{img_name}_without_crosshair.png'))
            self.isoLine_v.show()
            self.isoLine_h.show()
            gui.statusbar.showMessage(f'Success to export viewport image to folder: {folder}')
        except Exception as err:
            gui.statusbar.showMessage(f'Fail to export image due to {str(err)}')

    def export_and_load_image(self):
        gui = findMainWindow()
        try:
            folder = gui.settings_object.get('Camaras').get('exported_image_folder')
            img_full_path, ok = QtWidgets.QInputDialog.getText(self, f'Send image to ImgReg', 'Input full path of image file name:', text= os.path.join(folder, 'exported_img.png')) 
            if not ok:
                return
            self.isoLine_v.hide()
            self.isoLine_h.hide()
            #exporter = pyqtgraph.exporters.ImageExporter(self.img)
            #exporter.export(img_full_path)
            matplotlib.image.imsave(img_full_path, gui.camara_widget.img.image.astype(np.uint8))
            self.isoLine_v.show()
            self.isoLine_h.show()
            gui.import_image_from_disk([img_full_path], use_cam_geo = True)
            gui.statusbar.showMessage(f'Success to export viewport image to folder: {folder}')
        except Exception as err:
            gui.statusbar.showMessage(f'Fail to export image due to {str(err)}')

    def set_reference_zone_pure(self, x0, y0, w, h):
        """
        Sets the coordinates of the rectangle selection within the reference zone

        :param x0: left-top corner x coordinate
        :param y0: left-top corner y coordinate
        :param w: roi width in hor direction
        :param h: roi height in ver direction
        :return:
        """
        self.piezo_stage_roi_ref_set = False
        if self.roi_scan != None:
            self.img_viewer.vb.removeItem(self.roi_scan)
        if self.roi_type == 'rectangle':
            pen = pg.mkPen((0, 200, 200), width=1)
            self.roi_scan = pg.ROI([x0, y0], [w, h], pen=pen)
            self.roi_scan.setZValue(10000)
            self.roi_scan.handleSize = 10
            self.roi_scan.handlePen = pg.mkPen("#FFFFFF")
            self.roi_scan.addScaleHandle([0, 0.5], [1, 0.5], lockAspect=False)
            self.roi_scan.addScaleHandle([1, 0.5], [0, 0.5], lockAspect=False)
            self.roi_scan.addScaleHandle([0.5, 0], [0.5, 1], lockAspect=False)
            self.roi_scan.addScaleHandle([0.5, 1], [0.5, 0], lockAspect=False)
        elif self.roi_type == 'polyline':
            pen = pg.mkPen((0, 200, 200), width=1)
            self.roi_scan = pg.PolyLineROI([],closed=True, movable=False)
            self.roi_scan.handleSize = 10
            self.roi_scan.setPoints([[x0,y0],[x0+w,y0],[x0+w, y0+h],[x0,y0+h]])
            self.roi_scan.setZValue(10000)
            self.roi_scan.handlePen = pg.mkPen("#FFFFFF")
        self.img_viewer.vb.addItem(self.roi_scan)
        self.roi_scan.sigRegionChangeStarted.connect(lambda: self.setPaused(True))
        self.roi_scan.sigRegionChanged.connect(self._cal_scan_coordinates)
        self.roi_scan.sigRegionChangeFinished.connect(lambda: self.setPaused(False))

    def _cal_scan_coordinates(self):
        gui = findMainWindow()
        #one set at the bottom for positioning and one set on top for scanning
        if gui.settings_object['ScanType']['two_set_of_stage']:
            self._cal_scan_coordinates_two_sets_of_stage()
        else:
            self._cal_scan_coordinates_one_set_of_stage()

    def _cal_scan_coordinates_two_sets_of_stage(self):
        main_gui = findMainWindow()
        if self.roi_type=='rectangle':
            self.roi_scan_xy_stage = [None, None]
            scan_cmd = main_gui.lineEdit_scan_cmd.text()
            stage_x = main_gui.lineEdit_sample_stage_name_x.text()
            stage_y = main_gui.lineEdit_sample_stage_name_y.text()
            step_size = eval(f"({main_gui.lineEdit_step_size_h.text()},{main_gui.lineEdit_step_size_v.text()})")
            # steps_x = main_gui.spinBox_steps_hor.value()
            # steps_y = main_gui.spinBox_steps_ver.value()
            sample_x_stage_start_pos, sample_y_stage_start_pos = self._cal_scan_coordinates_from_pos(np.array(self.roi_scan.pos())*main_gui.camara_pixel_size)
            sample_x_pstage_start_pos, sample_y_pstage_start_pos = main_gui.pstage_pos_at_prim_beam
            width, height = abs(np.array(self.roi_scan.size()))*main_gui.camara_pixel_size*1000 # in mícro
            # if main_gui.checkBox_use_step_size.isChecked():
            steps_x = int(width/step_size[0])
            steps_y = int(height/step_size[1])
            exposure_time = float(main_gui.lineEdit_exposure_time.text())
            scan_cmd_str = f'{scan_cmd} {stage_x}' + \
                        f' {round(sample_x_pstage_start_pos,4)} {round(sample_x_pstage_start_pos+width,4)} {steps_x}' + \
                        f' {stage_y} {round(sample_y_pstage_start_pos,4)} {round(sample_y_pstage_start_pos-height,4)} {steps_y}'+\
                        f' {exposure_time}'
            main_gui.lineEdit_full_macro_name.setText(scan_cmd_str)
            self.save_current_roi_xy([round(sample_x_stage_start_pos,4),round(sample_y_stage_start_pos,4)])
            # return scan_cmd_str
        else:
            self.roi_scan_xy_stage = [None, None]
            scan_cmd = 'pmesh'
            stage_x = main_gui.lineEdit_sample_stage_name_x.text()
            stage_y = main_gui.lineEdit_sample_stage_name_y.text()
            exposure_time = float(main_gui.lineEdit_exposure_time.text())
            step_size_x, step_size_y = np.array(eval(f"({main_gui.lineEdit_step_size_h.text()},{main_gui.lineEdit_step_size_v.text()})"))
            handles = self._generate_handle_pos_list_polylineroi()
            pstage_handles = [list((np.array(each) - handles[0])*1000) for each in handles]
            coords = str(pstage_handles).replace(',','')
            main_gui.lineEdit_full_macro_name.setText(f'{scan_cmd} {stage_x} {step_size_x} {stage_y} {step_size_y} {exposure_time} {coords}')
            self.save_current_roi_xy(handles[0])

    def _cal_scan_coordinates_one_set_of_stage(self):
        main_gui = findMainWindow()
        if self.roi_type=='rectangle':
            self.roi_scan_xy_stage = [None, None]
            self.roi_scan_xy_stage_piezo = [None, None]
            scan_cmd = main_gui.lineEdit_scan_cmd.text()
            stage_x = main_gui.lineEdit_sample_stage_name_x.text()
            stage_y = main_gui.lineEdit_sample_stage_name_y.text()
            step_size = eval(f"({main_gui.lineEdit_step_size_h.text()},{main_gui.lineEdit_step_size_v.text()})")
            # steps_x = main_gui.spinBox_steps_hor.value()
            # steps_y = main_gui.spinBox_steps_ver.value()
            sample_x_stage_start_pos, sample_y_stage_start_pos = self._cal_scan_coordinates_from_pos(np.array(self.roi_scan.pos())*main_gui.camara_pixel_size)
            width, height = abs(np.array(self.roi_scan.size()))*main_gui.camara_pixel_size
            # if main_gui.checkBox_use_step_size.isChecked():
            steps_x = int(width/step_size[0]*1000)
            steps_y = int(height/step_size[1]*1000)
            exposure_time = float(main_gui.lineEdit_exposure_time.text())
            scan_cmd_str = f'{scan_cmd} {stage_x}' + \
                        f' {round(sample_x_stage_start_pos,4)} {round(sample_x_stage_start_pos+width,4)} {steps_x}' + \
                        f' {stage_y} {round(sample_y_stage_start_pos,4)} {round(sample_y_stage_start_pos-height,4)} {steps_y}'+\
                        f' {exposure_time}'
            main_gui.lineEdit_full_macro_name.setText(scan_cmd_str)
            self.save_current_roi_xy()
            # return scan_cmd_str
        else:
            self.roi_scan_xy_stage = [None, None]
            self.roi_scan_xy_stage_piezo = [None, None]
            scan_cmd = 'pmesh'
            stage_x = main_gui.lineEdit_sample_stage_name_x.text()
            stage_y = main_gui.lineEdit_sample_stage_name_y.text()
            exposure_time = float(main_gui.lineEdit_exposure_time.text())
            step_size_x, step_size_y = np.array(eval(f"({main_gui.lineEdit_step_size_h.text()},{main_gui.lineEdit_step_size_v.text()})"))/1000
            coords = str(self._generate_handle_pos_list_polylineroi()).replace(',','')
            main_gui.lineEdit_full_macro_name.setText(f'{scan_cmd} {stage_x} {step_size_x} {stage_y} {step_size_y} {exposure_time} {coords}')
            self.save_current_roi_xy()
    
    def _from_viewport_coords_to_stage_coords(self, x_vp, y_vp):
        main_gui = findMainWindow()
        samx = Attribute(main_gui.settings_object["SampleStages"]["x_stage_value"]).read().value
        samy = Attribute(main_gui.settings_object["SampleStages"]["y_stage_value"]).read().value
        current_stage_pos = np.array([samx, samy])
        crosshair_pos_offset = (current_stage_pos - main_gui.stage_pos_at_prim_beam)/main_gui.camara_pixel_size
        crosshair_pos_corrected_by_offset = main_gui.crosshair_pos_at_prim_beam + crosshair_pos_offset
        vp_coords = np.array([x_vp, y_vp])
        # dist_from_prim_beam_pos = (topleft - main_gui.crosshair_pos_at_prim_beam)*main_gui.camara_pixel_size
        dist_from_prim_beam_pos = (vp_coords - crosshair_pos_corrected_by_offset)*main_gui.camara_pixel_size
        stage_coords = main_gui.stage_pos_at_prim_beam + dist_from_prim_beam_pos
        return list(stage_coords.round(3))

    def _generate_handle_pos_list_polylineroi(self, use_pixel_unit = False):
        main_gui = findMainWindow()
        pos_list = []
        #the pos always start with [0,0] upon creating the polyroi no matter where you make this roi object
        #once the roi is moved, the pos attribute values will change wrt [0,0] at the beginning
        #therefore the pos always hold the relative movement compared to its beginning state
        offset = np.array(self.roi_scan.pos())*[1,-1]
        for handle in self.roi_scan.handles:
            handle_ls = [handle['pos'].x(), handle['pos'].y()]
            # pos_list.append(self._from_viewport_coords_to_stage_coords(*handle_ls))
            if use_pixel_unit:
                pos_list.append(handle_ls + offset)
            else:
                pos_list.append(list(np.array(self._cal_scan_coordinates_from_pos(np.array(handle_ls+offset)*main_gui.camara_pixel_size)).round(3)))
        return pos_list

    def _cal_scan_coordinates_from_pos_old(self, pos):
        #pos is in mm unit
        main_gui = findMainWindow()
        samx = Attribute(main_gui.settings_object["SampleStages"]["x_stage_value"]).read().value
        samy = Attribute(main_gui.settings_object["SampleStages"]["y_stage_value"]).read().value
        current_stage_pos = np.array([samx, samy])
        crosshair_pos_offset = (current_stage_pos - main_gui.stage_pos_at_prim_beam)/main_gui.camara_pixel_size
        crosshair_pos_corrected_by_offset = main_gui.crosshair_pos_at_prim_beam + crosshair_pos_offset
        topleft = np.array(pos)/main_gui.camara_pixel_size
        # dist_from_prim_beam_pos = (topleft - main_gui.crosshair_pos_at_prim_beam)*main_gui.camara_pixel_size
        dist_from_prim_beam_pos = (topleft - crosshair_pos_corrected_by_offset)*main_gui.camara_pixel_size
        sample_x_stage_start_pos, sample_y_stage_start_pos = main_gui.stage_pos_at_prim_beam - dist_from_prim_beam_pos
        return sample_x_stage_start_pos, sample_y_stage_start_pos

    def _cal_pstage_offset_wrt_prim_beam(self):
        main_gui = findMainWindow()
        try:
            if 'x_pstage_value' in main_gui.settings_object["SampleStages"]:
                scanx = Attribute(main_gui.settings_object["SampleStages"]["x_pstage_value"]).read().value/1000.
                scanx_offset_from_prim = scanx - self.roi_scan_xy_stage_piezo[0]/1000. #convert to mm unit
            else:
                scanx_offset_from_prim = 0
            if 'y_pstage_value' in main_gui.settings_object["SampleStages"]:
                scany = Attribute(main_gui.settings_object["SampleStages"]["y_pstage_value"]).read().value/1000.
                scany_offset_from_prim = scany - self.roi_scan_xy_stage_piezo[1]/1000. #convert to mm
            else:
                scany_offset_from_prim = 0
        except:
            scanx_offset_from_prim, scany_offset_from_prim = 0, 0
        return scanx_offset_from_prim, scany_offset_from_prim
    
    def _cal_scan_coordinates_from_pos(self, pos):
        #pos is in mm unit
        main_gui = findMainWindow()
        try:
            samx = Attribute(main_gui.settings_object["SampleStages"]["x_stage_value"]).read().value
            samy = Attribute(main_gui.settings_object["SampleStages"]["y_stage_value"]).read().value
        except:
            return 0, 0

        current_stage_pos = np.array([samx, samy])
        crosshair_pos_offset_mm = np.array(pos) - np.array(main_gui.crosshair_pos_at_prim_beam)*main_gui.camara_pixel_size
        sample_x_stage_start_pos, sample_y_stage_start_pos = current_stage_pos + crosshair_pos_offset_mm*[1,-1]
        return sample_x_stage_start_pos, sample_y_stage_start_pos

    def _cal_scan_topleft_coordinates(self):
        main_gui = findMainWindow()
        geo_info = main_gui.settings_object['PrimBeamGeo']
        img_dim = self.img.image.shape
        top_left_coords_in_mm = np.array([geo_info['img_x'], geo_info['img_y']+img_dim[1]])*main_gui.camara_pixel_size
        result = self._cal_scan_coordinates_from_pos(top_left_coords_in_mm)
        result = [round(each, 3) for each in result]
        if len(result)==2:
            return str(list(result) + [0])
        elif len(result)==3:
            return str(result)

    def _get_img_dim_in_mm(self):
        main_gui = findMainWindow()
        img_dim = list(np.array(self.img.image.shape)*main_gui.camara_pixel_size)
        return img_dim[0:-1]

    def _convert_stage_coord_to_pix_unit_old(self, original_samx, original_samy):
        main_gui = findMainWindow()
        samx = Attribute(main_gui.settings_object["SampleStages"]["x_stage_value"]).read().value
        samy = Attribute(main_gui.settings_object["SampleStages"]["y_stage_value"]).read().value
        pos = (np.array([original_samx, original_samy]) - [samx, samy])/main_gui.camara_pixel_size*[1,-1] + [main_gui.camara_widget.isoLine_v.value(),main_gui.camara_widget.isoLine_h.value()]
        return pos
    
    def _convert_stage_coord_to_pix_unit(self, original_samx, original_samy):
        main_gui = findMainWindow()
        samx = Attribute(main_gui.settings_object["SampleStages"]["x_stage_value"]).read().value
        samy = Attribute(main_gui.settings_object["SampleStages"]["y_stage_value"]).read().value
        pstage_offset = np.array(list(self._cal_pstage_offset_wrt_prim_beam()))
        pos = (np.array([original_samx, original_samy]) - [samx, samy] - pstage_offset)/main_gui.camara_pixel_size*[1,-1] + [main_gui.camara_widget.isoLine_v.value(),main_gui.camara_widget.isoLine_h.value()]
        return pos
    
    def update_stage_pos_at_prim_beam(self, infline_obj = None, dir='x'):
        main_gui = findMainWindow()
        if dir=='x':
            attr = Attribute(main_gui.settings_object["SampleStages"]["x_stage_value"]).read()
            main_gui.stage_pos_at_prim_beam[0] = attr.value
            if 'x_pstage_value' in main_gui.settings_object["SampleStages"]:
                attr = Attribute(main_gui.settings_object["SampleStages"]["x_pstage_value"]).read()
                main_gui.pstage_pos_at_prim_beam[0] = attr.value
            main_gui.crosshair_pos_at_prim_beam[0] = infline_obj.value()
        elif dir == 'y':
            attr = Attribute(main_gui.settings_object["SampleStages"]["y_stage_value"]).read()
            main_gui.stage_pos_at_prim_beam[1] = attr.value
            if 'y_pstage_value' in main_gui.settings_object["SampleStages"]:
                attr = Attribute(main_gui.settings_object["SampleStages"]["y_pstage_value"]).read()
                main_gui.pstage_pos_at_prim_beam[1] = attr.value
            main_gui.crosshair_pos_at_prim_beam[1] = infline_obj.value()
        
    def mv_img_to_ref(self):
        #after this movement, the pos of crosshair pos reflect the current sample stage position
        main_gui = findMainWindow()
        self.update_stage_pos_at_prim_beam(self.isoLine_h, 'y')
        self.update_stage_pos_at_prim_beam(self.isoLine_v, 'x')
        x_pix, y_pix = main_gui.crosshair_pos_at_prim_beam
        x, y = x_pix * main_gui.camara_pixel_size, y_pix * main_gui.camara_pixel_size
        stage_x, stage_y = main_gui.stage_pos_at_prim_beam
        # The following lines are needed to avoid crashing GUI by setting isoline to a extremly small value (BUT NOT 0)
        # This happen when the values of x_pix or y_pix and stage_pos_at_prim_beam are still at their intial values (0)
        # If that is the case, the result of (stage_x - x)/main_gui.camara_pixel_size is not zero but a small value like 1e-13
        #the isoLine setValue is not happy taking such a small value, and that will crash the whole program
        if abs(stage_x - x) < 1e-5:
            dx = 0
        else:
            dx = (stage_x - x)/main_gui.camara_pixel_size
        if abs(stage_y - y) < 1e-5:
            dy = 0
        else:
            dy = (stage_y - y)/main_gui.camara_pixel_size

        self.img.setX(self.img.x()+dx)
        self.img.setY(self.img.y()+dy)
        if self.roi_scan != None:
            self.roi_scan.setX(self.roi_scan.x()+dx)
            self.roi_scan.setY(self.roi_scan.y()+dy)
        self.isoLine_h.setValue(self.isoLine_h.value()+dy)
        self.isoLine_v.setValue(self.isoLine_v.value()+dx)
        main_gui.crosshair_pos_at_prim_beam[0] = self.isoLine_v.value()
        main_gui.crosshair_pos_at_prim_beam[1] = self.isoLine_h.value()
        self.update_img_settings()
        # self.img_viewer.vb.autoRange()

    def update_img_settings(self):
        main_gui = findMainWindow()
        main_gui.settings_object['PrimBeamGeo'] = {
            'img_x': float(self.img.x()),
            'img_y': float(self.img.y()),
            'iso_h': float(self.isoLine_h.value()),
            'iso_v': float(self.isoLine_v.value()),
            'stage_x': float(main_gui.stage_pos_at_prim_beam[0]),
            'stage_y': float(main_gui.stage_pos_at_prim_beam[1])
        }

    def mv_stage_to_prim_beam(self):
        main_gui = findMainWindow()
        if 'PrimBeamGeo' not in main_gui.settings_object:
            return
        geo_dict = main_gui.settings_object['PrimBeamGeo']
        stage_x, stage_y = geo_dict['stage_x'],geo_dict['stage_y']
        motor_names_dict = main_gui.settings_object['SampleStageMotorNames']
        door = Device(main_gui.settings_object['spockLogin']['doorName'])
        door.runmacro(['mv',motor_names_dict['x'], str(stage_x),motor_names_dict['y'], str(stage_y)])

    def resume_prim_beam_to_saved_values(self):
        #after this movement, the pos of crosshair pos reflect the current sample stage position
        main_gui = findMainWindow()
        if 'PrimBeamGeo' not in main_gui.settings_object:
            return
        geo_dict = main_gui.settings_object['PrimBeamGeo']
        img_x, img_y = geo_dict['img_x'], geo_dict['img_y']
        iso_h, iso_v = geo_dict['iso_h'], geo_dict['iso_v']
        stage_x, stage_y = geo_dict['stage_x'],geo_dict['stage_y']
        main_gui.stage_pos_at_prim_beam = [stage_x, stage_y]
        main_gui.crosshair_pos_at_prim_beam = [iso_v, iso_h]
        #here the order matters
        #set isoline first and then set the img x and y
        self.isoLine_h.setValue(iso_h)
        self.isoLine_v.setValue(iso_v)
        self.img.setX(img_x)
        self.img.setY(img_y)

    def reposition_scan_roi(self):
        if self.roi_scan_xy_stage[0]!=None:
            pos = self._convert_stage_coord_to_pix_unit(*self.roi_scan_xy_stage)
            if self.roi_scan != None:
                if self.roi_type=='rectangle':
                    old_pos = np.array(list(self.roi_scan.pos()))
                    if abs(sum(old_pos-pos))>0.1:
                        self.roi_scan.setPos(pos=pos)
                elif self.roi_type=='polyline':
                    anchor_pos = self._generate_handle_pos_list_polylineroi(use_pixel_unit=True)
                    offset = np.array(anchor_pos[0]) - pos
                    if abs(sum(offset)) > 0.1:
                        self.roi_scan.setPos(pos=(0,0))
                        self.roi_scan.setPoints([np.array(each)-offset for each in anchor_pos])
        else:
            pass

    def _mouseDragEvent(self, vb, ev):
        ev.accept() 
        # pos = ev.pos()
        if ev.button() == QtCore.Qt.LeftButton:
            if ev.isFinish():
                # x0, x1, y0, y1 = ev.buttonDownPos().x(), ev.pos().x(),  ev.buttonDownPos().y(),  ev.pos().y()
                x0, x1, y0, y1 = ev.buttonDownScenePos().x(), ev.lastScenePos().x(),  ev.buttonDownScenePos().y(),  ev.lastScenePos().y()
                if x0 > x1:
                    x0, x1 = x1, x0
                if y0 < y1:
                    y0, y1 = y1, y0
                p1 = vb.mapSceneToView(QtCore.QPointF(x0,y0))
                p2 = vb.mapSceneToView(QtCore.QPointF(x1,y1))
                # // emit the signal to other widgets
                self.sigScanRoiAdded.emit(p1.x(), p1.y(), abs(p2.x()-p1.x()), abs(p2.y()-p1.y()))
                findMainWindow().statusbar.showMessage("Extend of the rectangle: X(lef-right): [{:.4}:{:.4}],  Y(top-bottom): [{:.4}:{:.4}]".format(p1.x(), p2.x(), p1.y(), p2.y()))
                #self.getdataInRect()

                # self.changePointsColors()

    def handleEvent(self, evt_src, evt_type, evt_val_list):
        """Reimplemented from :class:`TaurusImageItem`"""
        if type(evt_val_list) is list:
            evt_val, key = evt_val_list
        else:
            evt_val = evt_val_list
            if evt_src is self.getModelObj(key='img'):
                key = 'img'
            elif evt_src is self.getModelObj(key='samx'):
                key= 'samx'
            elif evt_src is self.getModelObj(key='samy'):
                key= 'samy'
            elif evt_src is self.getModelObj(key='scanx'):
                key= 'scanx'
            elif evt_src is self.getModelObj(key='scany'):
                key= 'scany'
            else:
                key = None
        if evt_val is None or getattr(evt_val, "rvalue", None) is None:
            self.debug("Ignoring empty value event from %s" % repr(evt_src))
            return
        try:
            if key=='img':
                data = evt_val.rvalue
                #cam stream data format from p06 beamline [[v1,...,vn]]
                data = self.preprocess_data(data, self.data_format_cbs)
                #if self.height!=None and self.width!=None:
                #    data = data[0].reshape((self.width, self.height, 3))
                    #data = np.clip(data, 0, 255).astype(np.ubyte)

                self.img.setImage(data)
                self.hist.imageChanged(self.autolevel, self.autolevel)
            elif key in ['samx','samy','scanx','scany']:
                self.reposition_scan_roi()
                if key in ['scanx','scany']:
                    self._save_current_roi_xy_piezo()
                #self.mv_roi_upon_stage_move()
        except Exception as e:
            self.warning("Exception in handleEvent: %s", e)

    def preprocess_data(self, data, cbs):
        
        for cb in cbs:
            if type(cb)==str:
                data = eval(cb)(data)
            else:
                data = cb(data)
        return data


    @property
    def forcedReadPeriod(self):
        """Returns the forced reading period (in ms). A value <= 0 indicates
        that the forced reading is disabled
        """
        return self._timer.interval()

    def setForcedReadPeriod_old(self, period):
        """
        Forces periodic reading of the subscribed attribute in order to show
        new points even if no events are received.
        It will create fake events as needed with the read value.
        It will also block the plotting of regular events when period > 0.
        :param period: (int) period in milliseconds. Use period<=0 to stop the
                       forced periodic reading
        QTimer eats the resource of main thread. You feel lagacy on widget opts.
        """

        # stop the timer and remove the __ONLY_OWN_EVENTS filter
        self._timer.stop()
        filters = self.getEventFilters()
        if self.__ONLY_OWN_EVENTS in filters:
            filters.remove(self.__ONLY_OWN_EVENTS)
            self.setEventFilters(filters)

        # if period is positive, set the filter and start
        if period > 0:
            self.insertEventFilter(self.__ONLY_OWN_EVENTS)
            self._timer.start(period)

    def setForcedReadPeriod(self, period):
        """
        Forces periodic reading of the subscribed attribute in order to show
        new points even if no events are received.
        It will create fake events as needed with the read value.
        It will also block the plotting of regular events when period > 0.
        :param period: (int) period in milliseconds. Use period<=0 to stop the
                       forced periodic reading
        """

        # stop the timer and remove the __ONLY_OWN_EVENTS filter
        # self._timer.stop()
        try:
            self.thread_period_timer_forceRead.terminate()
        except:
            pass
        filters = self.getEventFilters()
        if self.__ONLY_OWN_EVENTS in filters:
            filters.remove(self.__ONLY_OWN_EVENTS)
            self.setEventFilters(filters)

        # if period is positive, set the filter and start
        if period > 0:
            self.insertEventFilter(self.__ONLY_OWN_EVENTS)
            self.period_timer_forceRead.timeout = period/1000.
            self.thread_period_timer_forceRead.start()
            #self._timer.start(period)

    def _connect_mouse_move_event(self, evt):
        main_gui = findMainWindow()
        # vp_pos = self.img_viewer.vb.mapSceneToView(evt)
        # x, y = vp_pos.x(), vp_pos.y()
        point = self.img_viewer.vb.mapSceneToView(evt).toPoint()
        px_size = main_gui.camara_pixel_size
        main_gui.last_cursor_pos_on_camera_viewer = self._cal_scan_coordinates_from_pos([round(point.x()*px_size,4), round(point.y()*px_size,4)])
        #if main_gui.camera_is_on:
        #    main_gui.last_cursor_pos_on_camera_viewer = self._cal_scan_coordinates_from_pos([round(point.x()*px_size,4), round(point.y()*px_size,4)])
        #else:
        #    main_gui.last_cursor_pos_on_camera_viewer = 'NaN'
        main_gui.statusbar.showMessage(f'viewport coords (stage in mm): {main_gui.last_cursor_pos_on_camera_viewer};viewport coords (native in pix):{point.x(),point.y()}')
        #findMainWindow().statusbar.showMessage(f'viewport coords: {round(point.x()*px_size,4), round(point.y()*px_size,4)}')

    def _forceRead(self, cache=False):
        """Forces a read of the associated attribute.
        :param cache: (bool) If True, the reading will be done with cache=True
                      but the timestamp of the resulting event will be replaced
                      by the current time. If False, no cache will be used at
                      all.
        """
        for key in self.modelKeys:
            value = self.getModelValueObj(cache=cache, key= key)
            if cache and value is not None:
                value = copy.copy(value)
                value.time = TaurusTimeVal.now()
            self.fireEvent(self, TaurusEventType.Periodic, [value, key])

    def __ONLY_OWN_EVENTS(self, s, t, v):
        """An event filter that rejects all events except those that originate
        from this object
        """
        if s is self:
            return s, t, v
        else:
            return None            