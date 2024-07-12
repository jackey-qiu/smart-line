import sys, copy
from taurus.qt.qtgui.base import TaurusBaseComponent
from taurus.external.qt import Qt
from pyqtgraph.Qt import QtCore, QtGui
from pyqtgraph.Point import Point
from pyqtgraph import GraphicsLayoutWidget, ImageItem
from PyQt5.QtCore import pyqtSlot as Slot, pyqtSignal as Signal
import pyqtgraph as pg
from taurus import Device, Attribute
from taurus.core import TaurusEventType, TaurusTimeVal
from smart.gui.widgets.context_menu_actions import setRef, resumePrim, mvMotors, VisuaTool, camSwitch, AutoLevelTool, LockCrossTool, SaveCrossHair, ResumeCrossHair
from taurus.qt.qtgui.tpg import ForcedReadTool
from functools import partial
import numpy as np
from smart import icon_path
from ...util.util import findMainWindow

class camera_control_panel(object):

    def __init__(self):
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
        samx = self.settings_object["SampleStages"]["label_x_stage_value"]
        samy = self.settings_object["SampleStages"]["label_y_stage_value"]
        return samx, samy

    def build_cam_widget(self):
        gridLayoutWidgetName, viewerWidgetName, *_ = self._extract_cam_info_from_config()

        if gridLayoutWidgetName!=None:
            if viewerWidgetName!=None:
                if not hasattr(self, viewerWidgetName):
                    setattr(self, viewerWidgetName,TaurusImageItem(parent=self))
                    getattr(self, gridLayoutWidgetName).addWidget(getattr(self, viewerWidgetName))

    def connect_slots_cam(self):
        level1, level2, level3 = self.settings_object["Camaras"]["presetZoom"]
        self.pushButton_zoom_level1.clicked.connect(lambda: self.set_zoom_level(level1))
        self.pushButton_zoom_level2.clicked.connect(lambda: self.set_zoom_level(level2))
        self.pushButton_zoom_level3.clicked.connect(lambda: self.set_zoom_level(level3))
        self.pushButton_save_roi_xy.clicked.connect(self.camara_widget.save_current_roi_xy)

    def control_cam(self):
        gridLayoutWidgetName, viewerWidgetName, camaraStreamModel, *_ = self._extract_cam_info_from_config()
        if not getattr(self, viewerWidgetName).getModel():
            self.start_cam_stream()
        else:
            self.stop_cam_stream()

    def start_cam_stream(self):
        _, viewerWidgetName, camaraStreamModel, device_name, data_format_cbs = self._extract_cam_info_from_config()
        model_samx, model_samy = self._extract_sample_stage_models()
        if getattr(self, viewerWidgetName).getModel()!='':
            return
        getattr(self, viewerWidgetName).setModel(camaraStreamModel)
        getattr(self, viewerWidgetName).setModel(model_samx, key='samx')
        getattr(self, viewerWidgetName).setModel(model_samy, key='samy')
        _device = Device(device_name)
        getattr(self, viewerWidgetName).width = _device.width
        getattr(self, viewerWidgetName).height = _device.height
        getattr(self, viewerWidgetName).data_format_cbs = data_format_cbs
        self.statusbar.showMessage(f'start cam streaming with model of {camaraStreamModel}')

    def set_zoom_level(self, level = 50):
        Attribute(self.settings_object["SampleStages"]["label_zoom_pos"]).write(level)

    def stop_cam_stream(self):
        _, viewerWidgetName, *_ = self._extract_cam_info_from_config()
        getattr(self, viewerWidgetName).setModel(None)
        self.statusbar.showMessage('stop cam streaming')

    def _append_img_processing_cbs(self, cb_str):
        #cb_str must be an lambda func of form like lambda data:data.reshape((2048, 2048, 3))
        if cb_str in self.camara_widget.data_format_cbs:
            pass
        else:
            self.camara_widget.data_format_cbs.append(cb_str)

    def _lock_crosshair_lines(self):
        self.camara_widget.isoLine_h.setMovable(False)
        self.camara_widget.isoLine_v.setMovable(False)

    def _unlock_crosshair_lines(self):
        self.camara_widget.isoLine_h.setMovable(True)
        self.camara_widget.isoLine_v.setMovable(True)

    def _save_crosshair(self):
        x, y = self.camara_widget.isoLine_v.value(),self.camara_widget.isoLine_h.value()
        self.camara_widget.saved_crosshair_pos = [x, y]

    def _resume_crosshair(self):
        x, y = self.camara_widget.saved_crosshair_pos
        self.camara_widget.isoLine_v.setValue(x)
        self.camara_widget.isoLine_h.setValue(y)

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
        flip_left_right = QAction(QIcon(str(icon_path / 'smart' / 'left_and_right.png')),'flip left and right',self)
        flip_left_right.setStatusTip('You can flip the image left and right.')
        flip_left_right.triggered.connect(lambda:self._append_img_processing_cbs('lambda data:np.flipud(data)'))  
        flip_up_down = QAction(QIcon(str(icon_path / 'smart' / 'up_and_down.png')),'flip up and down',self)
        flip_up_down.setStatusTip('You can flip the image up and down.')
        flip_up_down.triggered.connect(lambda:self._append_img_processing_cbs('lambda data:np.fliplr(data)'))               
        lock = QAction(QIcon(str(icon_path / 'smart' / 'lock.png')),'lock crosshair',self)
        lock.setStatusTip('You can freeze the crosshair lines.')
        lock.triggered.connect(self._lock_crosshair_lines)            
        unlock = QAction(QIcon(str(icon_path / 'smart' / 'unlock.png')),'unlock crosshair',self)
        unlock.setStatusTip('You can unfreeze the crosshair lines.')
        unlock.triggered.connect(self._unlock_crosshair_lines)               
        savecrosshair = QAction(QIcon(str(icon_path / 'smart' / 'save_crosshair.png')),'save crosshair pos',self)
        savecrosshair.setStatusTip('Save the crosshair line positions to be resumed in future.')
        savecrosshair.triggered.connect(self._save_crosshair)     
        resumecrosshair = QAction(QIcon(str(icon_path / 'smart' / 'resume_crosshair.png')),'resume crosshair pos',self)
        resumecrosshair.setStatusTip('Resume the crosshair line positions to previous saved pos.')
        resumecrosshair.triggered.connect(self._resume_crosshair)     
        poscalibration = QAction(QIcon(str(icon_path / 'icons_n' / 'lasing_navigate.png')),'stage calibration',self)
        poscalibration.setStatusTip('You can calibrate the crosshair pos to reflect sample stage position at the prim beam.')
        poscalibration.triggered.connect(self._calibrate_pos)               
        autoscale = QAction(QIcon(str(icon_path / 'smart' / 'scale_rgb.png')),'auto scaling the rgb color',self)
        autoscale.setStatusTip('Turn on the autoscaling of RGB channels.')
        autoscale.triggered.connect(lambda: self.camara_widget.update_autolevel(True))               
        autoscaleoff = QAction(QIcon(str(icon_path / 'smart' / 'unscale_rgb.png')),'turn off auto scaling the rgb color',self)
        autoscaleoff.setStatusTip('Turn off the autoscaling of RGB channels.')
        autoscaleoff.triggered.connect(lambda: self.camara_widget.update_autolevel(False))               
        roi_rect = QAction(QIcon(str(icon_path / 'smart' / 'rectangle_roi.png')),'select rectangle roi',self)
        roi_rect.setStatusTip('click an drag to get a rectangle roi.')
        roi_rect.triggered.connect(lambda: self.camara_widget.set_roi_type('rectangle'))               
        roi_polyline = QAction(QIcon(str(icon_path / 'smart' / 'polyline_roi.png')),'select polygone roi',self)
        roi_polyline.setStatusTip('click an drag to get a polygone roi selection.')
        roi_polyline.triggered.connect(lambda: self.camara_widget.set_roi_type('polyline'))               
        self.camToolBar.addAction(action_switch_on_camera)
        self.camToolBar.addAction(action_switch_off_camera)
        self.camToolBar.addAction(autoscale)
        self.camToolBar.addAction(autoscaleoff)
        self.camToolBar.addAction(flip_up_down)
        self.camToolBar.addAction(flip_left_right)
        self.camToolBar.addAction(savecrosshair)
        self.camToolBar.addAction(resumecrosshair)
        self.camToolBar.addAction(poscalibration)
        self.camToolBar.addAction(lock)
        self.camToolBar.addAction(unlock)
        self.camToolBar.addAction(roi_rect)
        self.camToolBar.addAction(roi_polyline)
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
    modelKeys = ['img','samx','samy']
    # modelKeys = [TaurusBaseComponent.MLIST]
    # TODO: clear image if .setModel(None)
    def __init__(self, parent = None, rgb_viewer = True, *args, **kwargs):
        GraphicsLayoutWidget.__init__(self, *args, **kwargs)
        TaurusBaseComponent.__init__(self, "TaurusImageItem")
        self._timer = Qt.QTimer()
        self._timer.timeout.connect(self._forceRead)
        self._parent = parent
        self.rgb_viewer = rgb_viewer
        self._init_ui()
        self.width = None
        self.width = None
        self.data_format_cbs = [lambda x: x]
        self.autolevel = True
        self.roi_scan = None
        self.roi_scan_xy_stage = [None, None]
        self.roi_type = 'rectangle'
        self.pos_calibration_done = False
        self.sigScanRoiAdded.connect(self.set_reference_zone)
        # self.setModel('sys/tg_test/1/long64_image_ro')

    def set_roi_type(self, roi_type):
        if roi_type in ['rectangle','polyline']:
            self.roi_type = roi_type

    def save_current_roi_xy(self):
        main_gui = findMainWindow()
        if self.roi_type=='rectangle':
            cmd = main_gui.lineEdit_full_macro_name.text()
            if cmd != '':
                scan_cmd_list = cmd.rsplit(' ')
                x, y = float(scan_cmd_list[2]), float(scan_cmd_list[6])
            self.roi_scan_xy_stage = [x, y]
        else:
            pass

    def update_autolevel(self, autolevel):
        self.autolevel = autolevel

    def _init_ui(self):
        if self.rgb_viewer:
            self._setup_rgb_viewer()
        else:
            self._setup_one_channel_viewer()
        self._setup_context_action()

    def _setup_context_action(self):
        main_gui = findMainWindow()
        if not self.rgb_viewer:
            self.vt = VisuaTool(self, properties = ['prof_hoz','prof_ver'])
            self.vt.attachToPlotItem(self.img_viewer)
        self.fr = CumForcedReadTool(self, period=100)
        self.fr.attachToPlotItem(self.img_viewer)
        self.resume_prim_action = resumePrim(self)
        self.resume_prim_action.attachToPlotItem(self.img_viewer)
        # self.cam_switch = camSwitch(self._parent)
        # self.cam_switch.attachToPlotItem(self.img_viewer)
        # self.autolevel = AutoLevelTool(self)
        # self.autolevel.attachToPlotItem(self.img_viewer) 
        # self.crosshair = LockCrossTool(self)
        # self.crosshair.attachToPlotItem(self.img_viewer) 
        # self.savecrosshair = SaveCrossHair(self)
        # self.savecrosshair.attachToPlotItem(self.img_viewer) 
        # self.resumecrosshair = ResumeCrossHair(self)
        # self.resumecrosshair.attachToPlotItem(self.img_viewer) 
        # self.setPosRef = setRef(self)
        # self.setPosRef.attachToPlotItem(self.img_viewer) 
        if main_gui.user_right == 'super':
            self.mvMotors = mvMotors(self._parent)
            self.mvMotors.attachToPlotItem(self.img_viewer) 

    def _setup_one_channel_viewer(self):
        #for horizontal profile
        self.prof_hoz = self.addPlot(col = 1, colspan = 5, rowspan = 2)
        #for vertical profile
        self.prof_ver = self.addPlot(col = 6, colspan = 5, rowspan = 2)
        self.nextRow()
        self.hist = pg.HistogramLUTItem()
        self.isoLine = pg.InfiniteLine(angle=0, movable=True, pen='g')
        self.hist.vb.addItem(self.isoLine)
        self.hist.vb.setMouseEnabled(y=True) # makes user interaction a little easier
        self.isoLine.setValue(0.8)
        self.isoLine.setZValue(100000) # bring iso line above contrast controls
        # self.addItem(self.hist, row = 2, col = 0, rowspan = 5, colspan = 1)
        self.addItem(self.hist, row = 2, col = 0, rowspan = 5, colspan = 1)
        #for image
        self.img_viewer = self.addPlot(row = 2, col = 1, rowspan = 5, colspan = 10)
        self.img_viewer.setAspectLocked()
        self.img = pg.ImageItem()
        self.img_viewer.addItem(self.img)
        self.hist.setImageItem(self.img)
        #isocurve for image
        self.iso = pg.IsocurveItem(level = 0.8, pen = 'g')
        self.iso.setParentItem(self.img)
        #cuts on image
        self.region_cut_hor = pg.LinearRegionItem(orientation=pg.LinearRegionItem.Horizontal)
        self.region_cut_ver = pg.LinearRegionItem(orientation=pg.LinearRegionItem.Vertical)
        self.region_cut_hor.setRegion([120,150])
        self.region_cut_ver.setRegion([120,150])
        self.img_viewer.addItem(self.region_cut_hor, ignoreBounds = True)
        self.img_viewer.addItem(self.region_cut_ver, ignoreBounds = True)
        # self.vt = VisuaTool(self, properties = ['prof_hoz','prof_ver'])
        # self.vt.attachToPlotItem(self.img_viewer)

    def _setup_rgb_viewer(self):

        self.isoLine_v = pg.InfiniteLine(angle=90, movable=True, pen=pg.mkPen('green', width=4))
        self.isoLine_h = pg.InfiniteLine(angle=0, movable=True, pen=pg.mkPen('green', width=4))
        self.isoLine_v.setValue(0)
        self.isoLine_v.setZValue(100000) # bring iso line above contrast controls
        self.isoLine_h.setValue(0)
        self.isoLine_h.setZValue(100000) # bring iso line above contrast controls
        # self.isoLine_h.sigPositionChangeFinished.connect(lambda:self.update_stage_pos_at_prim_beam(self.isoLine_h,'y'))
        # self.isoLine_v.sigPositionChangeFinished.connect(lambda:self.update_stage_pos_at_prim_beam(self.isoLine_v,'x'))
        self.img_viewer = self.addPlot(row = 2, col = 1, rowspan = 5, colspan = 10)
        self.img_viewer.setAspectLocked()
        # ax_item_img_hor = scale_pixel(scale = 0.036, shift = 0, orientation = 'bottom')
        # ax_item_img_ver = scale_pixel(scale = 0.036, shift = 0, orientation = 'left')
        # ax_item_img_hor.attachToPlotItem(self.img_viewer)
        # ax_item_img_ver.attachToPlotItem(self.img_viewer)
        self.img = pg.ImageItem()
        self.img_viewer.addItem(self.img)

        self.img_viewer.addItem(self.isoLine_v, ignoreBounds = True)
        self.img_viewer.addItem(self.isoLine_h, ignoreBounds = True)

        self.hist = pg.HistogramLUTItem(levelMode='rgba')
        #self.isoLine = pg.InfiniteLine(angle=0, movable=True, pen='g')
        #self.hist.vb.addItem(self.isoLine)
        self.hist.vb.setMouseEnabled(y=True) # makes user interaction a little easier
        self.addItem(self.hist, row = 2, col = 0, rowspan = 5, colspan = 1)
        self.hist.setImageItem(self.img)

        self.img_viewer.vb.scene().sigMouseMoved.connect(self._connect_mouse_move_event)
        self.img_viewer.vb.mouseDragEvent = partial(self._mouseDragEvent, self.img_viewer.vb)

        #set the img to origin (0,0)
        self._mv_img_to_pos(0, 0)

    #suppose to move the bottomleft corner of image to the pos(x, y)
    def _mv_img_to_pos(self, x, y):
        self.img.setX(0)
        self.img.setY(0)
        tr = QtGui.QTransform()
        tr.translate(x, y)
        self.img.setTransform(tr)

    @Slot(float,float,float,float)
    def set_reference_zone(self, x0, y0, w, h):
        """
        Sets the coordinates of the rectangle selection within the reference zone

        :param x0: left-top corner x coordinate
        :param y0: left-top corner y coordinate
        :param w: roi width in hor direction
        :param h: roi height in ver direction
        :return:
        """
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
            # self.roi_scan.addScaleHandle([0.5, 1], [0.5, 0.5], lockAspect=False)
            # self.roi_scan.addScaleHandle([0.5, 0], [0.5, 0.5], lockAspect=False)
            # self.roi_scan.addScaleHandle([1, 0.5], [0.5, 0.5], lockAspect=False)
        elif self.roi_type == 'polyline':
            pen = pg.mkPen((0, 200, 200), width=1)
            self.roi_scan = pg.PolyLineROI([],closed=True)
            self.roi_scan.handleSize = 10
            self.roi_scan.setPoints([[x0,y0],[x0+w,y0],[x0+w, y0+h],[x0,y0+h]])
            self.roi_scan.setZValue(10000)
            self.roi_scan.handlePen = pg.mkPen("#FFFFFF")
        self.img_viewer.vb.addItem(self.roi_scan)
        self.roi_scan.sigRegionChanged.connect(self._cal_scan_coordinates)
        self._cal_scan_coordinates()

    def _cal_scan_coordinates(self):
        main_gui = findMainWindow()
        if self.roi_type=='rectangle':
            #samx = Attribute(main_gui.settings_object["SampleStages"]["label_x_stage_value"]).read().value
            #samy = Attribute(main_gui.settings_object["SampleStages"]["label_y_stage_value"]).read().value
            #current_stage_pos = np.array([samx, samy])
            #crosshair_pos_offset = (current_stage_pos - main_gui.stage_pos_at_prim_beam)/main_gui.camara_pixel_size
            #crosshair_pos_corrected_by_offset = main_gui.crosshair_pos_at_prim_beam + crosshair_pos_offset
            self.roi_scan_xy_stage = [None, None]
            scan_cmd = main_gui.lineEdit_scan_cmd.text()
            stage_x = main_gui.lineEdit_sample_stage_name_x.text()
            stage_y = main_gui.lineEdit_sample_stage_name_y.text()
            step_size = eval(main_gui.lineEdit_step_size.text())
            steps_x = main_gui.spinBox_steps_hor.value()
            steps_y = main_gui.spinBox_steps_ver.value()
            #topleft = np.array(self.roi_scan.pos())
            # dist_from_prim_beam_pos = (topleft - main_gui.crosshair_pos_at_prim_beam)*main_gui.camara_pixel_size
            #dist_from_prim_beam_pos = (topleft - crosshair_pos_corrected_by_offset)*main_gui.camara_pixel_size
            #sample_x_stage_start_pos, sample_y_stage_start_pos = main_gui.stage_pos_at_prim_beam + dist_from_prim_beam_pos
            sample_x_stage_start_pos, sample_y_stage_start_pos = self._cal_scan_coordinates_from_pos(np.array(self.roi_scan.pos())*main_gui.camara_pixel_size)
            width, height = abs(np.array(self.roi_scan.size()))*main_gui.camara_pixel_size
            if main_gui.checkBox_use_step_size.isChecked():
                steps_x = int(width/step_size[0]*1000)
                steps_y = int(height/step_size[1]*1000)
            exposure_time = float(main_gui.lineEdit_exposure_time.text())
            scan_cmd_str = f'{scan_cmd} {stage_x}' + \
                        f' {round(sample_x_stage_start_pos,4)} {round(sample_x_stage_start_pos+width,4)} {steps_x}' + \
                        f' {stage_y} {round(sample_y_stage_start_pos,4)} {round(sample_y_stage_start_pos-height,4)} {steps_y}'+\
                        f' {exposure_time}'
            main_gui.lineEdit_full_macro_name.setText(scan_cmd_str)
            self.save_current_roi_xy()
            return scan_cmd_str
        else:
            self.roi_scan_xy_stage = [None, None]
            main_gui.lineEdit_full_macro_name.setText(str(self._generate_handle_pos_list_polylineroi()))
    
    def _from_viewport_coords_to_stage_coords(self, x_vp, y_vp):
        main_gui = findMainWindow()
        samx = Attribute(main_gui.settings_object["SampleStages"]["label_x_stage_value"]).read().value
        samy = Attribute(main_gui.settings_object["SampleStages"]["label_y_stage_value"]).read().value
        current_stage_pos = np.array([samx, samy])
        crosshair_pos_offset = (current_stage_pos - main_gui.stage_pos_at_prim_beam)/main_gui.camara_pixel_size
        crosshair_pos_corrected_by_offset = main_gui.crosshair_pos_at_prim_beam + crosshair_pos_offset
        vp_coords = np.array([x_vp, y_vp])
        # dist_from_prim_beam_pos = (topleft - main_gui.crosshair_pos_at_prim_beam)*main_gui.camara_pixel_size
        dist_from_prim_beam_pos = (vp_coords - crosshair_pos_corrected_by_offset)*main_gui.camara_pixel_size
        stage_coords = main_gui.stage_pos_at_prim_beam + dist_from_prim_beam_pos
        return list(stage_coords.round(3))

    def _generate_handle_pos_list_polylineroi(self):
        main_gui = findMainWindow()
        pos_list = []
        #the pos always start with [0,0] upon creating the polyroi no matter where you make this roi object
        #once the roi is moved, the pos attribute values will change wrt [0,0] at the beginning
        #therefore the pos always hold the relative movement compared to its beginning state
        offset = np.array(self.roi_scan.pos())*[1,-1]
        for handle in self.roi_scan.handles:
            handle_ls = [handle['pos'].x(), handle['pos'].y()]
            # pos_list.append(self._from_viewport_coords_to_stage_coords(*handle_ls))
            pos_list.append(list(np.array(self._cal_scan_coordinates_from_pos(np.array(handle_ls+offset)*main_gui.camara_pixel_size)).round(3)))
        return pos_list

    def _cal_scan_coordinates_from_pos_old(self, pos):
        #pos is in mm unit
        main_gui = findMainWindow()
        samx = Attribute(main_gui.settings_object["SampleStages"]["label_x_stage_value"]).read().value
        samy = Attribute(main_gui.settings_object["SampleStages"]["label_y_stage_value"]).read().value
        current_stage_pos = np.array([samx, samy])
        crosshair_pos_offset = (current_stage_pos - main_gui.stage_pos_at_prim_beam)/main_gui.camara_pixel_size
        crosshair_pos_corrected_by_offset = main_gui.crosshair_pos_at_prim_beam + crosshair_pos_offset
        topleft = np.array(pos)/main_gui.camara_pixel_size
        # dist_from_prim_beam_pos = (topleft - main_gui.crosshair_pos_at_prim_beam)*main_gui.camara_pixel_size
        dist_from_prim_beam_pos = (topleft - crosshair_pos_corrected_by_offset)*main_gui.camara_pixel_size
        sample_x_stage_start_pos, sample_y_stage_start_pos = main_gui.stage_pos_at_prim_beam - dist_from_prim_beam_pos
        return sample_x_stage_start_pos, sample_y_stage_start_pos

    def _cal_scan_coordinates_from_pos(self, pos):
        #pos is in mm unit
        main_gui = findMainWindow()
        samx = Attribute(main_gui.settings_object["SampleStages"]["label_x_stage_value"]).read().value
        samy = Attribute(main_gui.settings_object["SampleStages"]["label_y_stage_value"]).read().value
        current_stage_pos = np.array([samx, samy])
        crosshair_pos_offset_mm = np.array(pos) - np.array(main_gui.crosshair_pos_at_prim_beam)*main_gui.camara_pixel_size
        sample_x_stage_start_pos, sample_y_stage_start_pos = current_stage_pos + crosshair_pos_offset_mm*[1,-1]
        return sample_x_stage_start_pos, sample_y_stage_start_pos

    def _convert_stage_coord_to_pix_unit_old(self, original_samx, original_samy):
        main_gui = findMainWindow()
        samx = Attribute(main_gui.settings_object["SampleStages"]["label_x_stage_value"]).read().value
        samy = Attribute(main_gui.settings_object["SampleStages"]["label_y_stage_value"]).read().value
        #if the stage is right at the prim beam position
        pos = (np.array([original_samx, original_samy]) - main_gui.stage_pos_at_prim_beam)/main_gui.camara_pixel_size + main_gui.crosshair_pos_at_prim_beam
        #if the stage already move away from the prim beam position, then another translation is needed
        diff_pos = (np.array([samx, samy]) - main_gui.stage_pos_at_prim_beam)/main_gui.camara_pixel_size
        return pos-diff_pos

    def _convert_stage_coord_to_pix_unit(self, original_samx, original_samy):
        main_gui = findMainWindow()
        samx = Attribute(main_gui.settings_object["SampleStages"]["label_x_stage_value"]).read().value
        samy = Attribute(main_gui.settings_object["SampleStages"]["label_y_stage_value"]).read().value
        pos = (np.array([original_samx, original_samy]) - [samx, samy])/main_gui.camara_pixel_size*[1,-1] + [main_gui.camara_widget.isoLine_v.value(),main_gui.camara_widget.isoLine_h.value()]
        return pos

    def update_stage_pos_at_prim_beam(self, infline_obj = None, dir='x'):
        main_gui = findMainWindow()
        if dir=='x':
            attr = Attribute(main_gui.settings_object["SampleStages"]["label_x_stage_value"]).read()
            main_gui.stage_pos_at_prim_beam[0] = attr.value
            main_gui.crosshair_pos_at_prim_beam[0] = infline_obj.value()
        elif dir == 'y':
            attr = Attribute(main_gui.settings_object["SampleStages"]["label_y_stage_value"]).read()
            main_gui.stage_pos_at_prim_beam[1] = attr.value
            main_gui.crosshair_pos_at_prim_beam[1] = infline_obj.value()
        
    def mv_img_to_ref(self):
        #after this movement, the pos of crosshair pos reflect the current sample stage position
        main_gui = findMainWindow()
        self.update_stage_pos_at_prim_beam(self.isoLine_h, 'y')
        self.update_stage_pos_at_prim_beam(self.isoLine_v, 'x')
        x_pix, y_pix = main_gui.crosshair_pos_at_prim_beam
        x, y = x_pix * main_gui.camara_pixel_size, y_pix * main_gui.camara_pixel_size
        stage_x, stage_y = main_gui.stage_pos_at_prim_beam
        dx, dy = (stage_x - x)/main_gui.camara_pixel_size, (stage_y - y)/main_gui.camara_pixel_size
        self.img.setX(self.img.x()+dx)
        self.img.setY(self.img.y()+dy)
        if self.roi_scan != None:
            self.roi_scan.setX(self.roi_scan.x()+dx)
            self.roi_scan.setY(self.roi_scan.y()+dy)
        self.isoLine_h.setValue(self.isoLine_h.value()+dy)
        self.isoLine_v.setValue(self.isoLine_v.value()+dx)
        main_gui.crosshair_pos_at_prim_beam[0] = self.isoLine_v.value()
        main_gui.crosshair_pos_at_prim_beam[1] = self.isoLine_h.value()

    def update_img_settings(self):
        main_gui = findMainWindow()
        main_gui.settings_object['PrimBeamGeo'] = {
            'img_x': self.img.x(),
            'img_y': self.img.y(),
            'iso_h': self.isoLine_h.value(),
            'iso_v': self.isoLine_v.value(),
            'stage_x': main_gui.stage_pos_at_prim_beam[0],
            'stage_y': main_gui.stage_pos_at_prim_beam[1]
        }

    def resume_prim_beam_to_saved_values(self):
        #after this movement, the pos of crosshair pos reflect the current sample stage position
        main_gui = findMainWindow()
        if 'PrimBeamGeo' not in main_gui.settings_object:
            return
        geo_dict = main_gui.settings_object['PrimBeamGeo']
        img_x, img_y = geo_dict['img_x'], geo_dict['img_y']
        iso_h, iso_v = geo_dict['iso_h'], geo_dict['iso_v']
        stage_x, stage_y = geo_dict['stage_x'],geo_dict['stage_y']
        self.img.setX(img_x)
        self.img.setY(img_y)
        main_gui.stage_pos_at_prim_beam = [stage_x, stage_y]
        main_gui.crosshair_pos_at_prim_beam = [iso_v, iso_h]
        self.isoLine_h.setValue(iso_h)
        self.isoLine_v.setValue(iso_v)

    def reposition_scan_roi(self):
        #after this movement, the pos of crosshair pos reflect the current sample stage position
        if self.roi_scan_xy_stage[0]!=None:
            pos = self._convert_stage_coord_to_pix_unit(*self.roi_scan_xy_stage)
            if self.roi_scan != None:
                self.roi_scan.setPos(pos=pos)
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
                if self.autolevel:
                    self.hist.imageChanged(self.autolevel, self.autolevel)
                else:
                    self.hist.regionChanged()
                if not self.rgb_viewer:
                    hor_region_down,  hor_region_up= self.region_cut_hor.getRegion()
                    ver_region_l, ver_region_r = self.region_cut_ver.getRegion()
                    hor_region_down,  hor_region_up = int(hor_region_down),  int(hor_region_up)
                    ver_region_l, ver_region_r = int(ver_region_l), int(ver_region_r)
                    self.prof_ver.plot(data[ver_region_l:ver_region_r,:].sum(axis=0),pen='g',clear=True)
                    self.prof_hoz.plot(data[:,hor_region_down:hor_region_up].sum(axis=1), pen='r',clear = True)
            elif key in ['samx','samy']:
                self.reposition_scan_roi()
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
        self._timer.stop()
        filters = self.getEventFilters()
        if self.__ONLY_OWN_EVENTS in filters:
            filters.remove(self.__ONLY_OWN_EVENTS)
            self.setEventFilters(filters)

        # if period is positive, set the filter and start
        if period > 0:
            self.insertEventFilter(self.__ONLY_OWN_EVENTS)
            self._timer.start(period)

    def _connect_mouse_move_event(self, evt):
        main_gui = findMainWindow()
        vp_pos = self.img_viewer.vb.mapSceneToView(evt)
        x, y = vp_pos.x(), vp_pos.y()
        #in_side_scene, coords = self._scale_rotate_and_translate([x,y])
        #if not in_side_scene:
        #    self._parent.statusbar.showMessage('viewport coords:'+str(self.mapSceneToView(evt)))
        #else:
        point = self.img_viewer.vb.mapSceneToView(evt).toPoint()
        px_size = main_gui.camara_pixel_size
        main_gui.last_cursor_pos_on_camera_viewer = self._cal_scan_coordinates_from_pos([round(point.x()*px_size,4), round(point.y()*px_size,4)])
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