import sys, copy
from taurus.qt.qtgui.base import TaurusBaseComponent
from taurus.external.qt import Qt
from pyqtgraph import GraphicsLayoutWidget, ImageItem
import pyqtgraph as pg
from taurus import Device
from taurus.core import TaurusEventType, TaurusTimeVal
from smart.gui.widgets.context_menu_actions import VisuaTool, camSwitch
from taurus.qt.qtgui.tpg import ForcedReadTool
import numpy as np


class camera_control_panel(object):

    def __init__(self):
        self.build_cam_widget()

    def _extract_cam_info_from_config(self):
        gridLayoutWidgetName = self.settings_object.value("Camaras/gridLayoutWidgetName")
        viewerWidgetName = self.settings_object.value("Camaras/viewerWidgetName")
        camaraStreamModel = self.settings_object.value("Camaras/camaraStreamModel")
        camaraDevice = self.settings_object.value("Camaras/camaraDevice")
        camaraDataCallbacks = self.settings_object.value("Camaras/camaraDataFormatCallbacks")
        return gridLayoutWidgetName, viewerWidgetName, camaraStreamModel, camaraDevice, camaraDataCallbacks

    def build_cam_widget(self):
        gridLayoutWidgetName, viewerWidgetName, *_ = self._extract_cam_info_from_config()

        if gridLayoutWidgetName!=None:
            if viewerWidgetName!=None:
                if not hasattr(self, viewerWidgetName):
                    setattr(self, viewerWidgetName,TaurusImageItem(parent=self))
                    getattr(self, gridLayoutWidgetName).addWidget(getattr(self, viewerWidgetName))

    def connect_slots_cam(self):
        return
        #self.pushButton_camera.clicked.connect(self.control_cam)

    def control_cam(self):
        gridLayoutWidgetName, viewerWidgetName, camaraStreamModel, *_ = self._extract_cam_info_from_config()
        if not getattr(self, viewerWidgetName).getModel():
            self.start_cam_stream()
        else:
            self.stop_cam_stream()

    def start_cam_stream(self):
        _, viewerWidgetName, camaraStreamModel, device_name, data_format_cbs = self._extract_cam_info_from_config()
        getattr(self, viewerWidgetName).setModel(camaraStreamModel)
        _device = Device(device_name)
        getattr(self, viewerWidgetName).width = _device.width
        getattr(self, viewerWidgetName).height = _device.height
        getattr(self, viewerWidgetName).data_format_cbs = data_format_cbs.rsplit('=>')

        self.statusbar.showMessage(f'start cam streaming with model of {camaraStreamModel}')

    def stop_cam_stream(self):
        _, viewerWidgetName, *_ = self._extract_cam_info_from_config()
        getattr(self, viewerWidgetName).setModel(None)
        self.statusbar.showMessage('stop cam streaming')

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
        # self.setModel('sys/tg_test/1/long64_image_ro')

    def _init_ui(self):
        if self.rgb_viewer:
            self._setup_rgb_viewer()
        else:
            self._setup_one_channel_viewer()
        self._setup_context_action()

    def _setup_context_action(self):
        if not self.rgb_viewer:
            self.vt = VisuaTool(self, properties = ['prof_hoz','prof_ver'])
            self.vt.attachToPlotItem(self.img_viewer)
        self.fr = CumForcedReadTool(self, period=3000)
        self.fr.attachToPlotItem(self.img_viewer)
        self.cam_switch = camSwitch(self._parent)
        self.cam_switch.attachToPlotItem(self.img_viewer)

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

        self.isoLine_v = pg.InfiniteLine(angle=90, movable=True, pen='g')
        self.isoLine_h = pg.InfiniteLine(angle=0, movable=True, pen='g')
        self.isoLine_v.setValue(0.8)
        self.isoLine_v.setZValue(100000) # bring iso line above contrast controls
        self.isoLine_h.setValue(0.8)
        self.isoLine_h.setZValue(100000) # bring iso line above contrast controls

        self.img_viewer = self.addPlot(row = 2, col = 1, rowspan = 5, colspan = 10)
        self.img_viewer.setAspectLocked()
        self.img = pg.ImageItem()
        self.img_viewer.addItem(self.img)

        self.img_viewer.addItem(self.isoLine_v, ignoreBounds = True)
        self.img_viewer.addItem(self.isoLine_h, ignoreBounds = True)


    def handleEvent(self, evt_src, evt_type, evt_val):
        """Reimplemented from :class:`TaurusImageItem`"""
        if evt_val is None or getattr(evt_val, "rvalue", None) is None:
            self.debug("Ignoring empty value event from %s" % repr(evt_src))
            return
        try:
            data = evt_val.rvalue
            #cam stream data format from p06 beamline [[v1,...,vn]]
            data = self.preprocess_data(data, self.data_format_cbs)
            #if self.height!=None and self.width!=None:
            #    data = data[0].reshape((self.width, self.height, 3))
                #data = np.clip(data, 0, 255).astype(np.ubyte)

            self.img.setImage(data)
            if not self.rgb_viewer:
                hor_region_down,  hor_region_up= self.region_cut_hor.getRegion()
                ver_region_l, ver_region_r = self.region_cut_ver.getRegion()
                hor_region_down,  hor_region_up = int(hor_region_down),  int(hor_region_up)
                ver_region_l, ver_region_r = int(ver_region_l), int(ver_region_r)
                self.prof_ver.plot(data[ver_region_l:ver_region_r,:].sum(axis=0),pen='g',clear=True)
                self.prof_hoz.plot(data[:,hor_region_down:hor_region_up].sum(axis=1), pen='r',clear = True)
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

    def _forceRead(self, cache=False):
        """Forces a read of the associated attribute.
        :param cache: (bool) If True, the reading will be done with cache=True
                      but the timestamp of the resulting event will be replaced
                      by the current time. If False, no cache will be used at
                      all.
        """
        value = self.getModelValueObj(cache=cache)
        if cache and value is not None:
            value = copy.copy(value)
            value.time = TaurusTimeVal.now()
        self.fireEvent(self, TaurusEventType.Periodic, value)

    def __ONLY_OWN_EVENTS(self, s, t, v):
        """An event filter that rejects all events except those that originate
        from this object
        """
        if s is self:
            return s, t, v
        else:
            return None            