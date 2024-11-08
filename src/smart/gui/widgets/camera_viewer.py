import copy
from taurus.qt.qtgui.base import TaurusBaseComponent
from taurus.external.qt import Qt
from pyqtgraph import GraphicsLayoutWidget
from PyQt5.QtCore import pyqtSlot as Slot, pyqtSignal as Signal
import pyqtgraph as pg
from taurus.core import TaurusEventType, TaurusTimeVal,TaurusElementType
from smart.gui.widgets.context_menu_actions import  VisuaTool
from taurus.qt.qtgui.tpg import ForcedReadTool,TaurusImgModelChooserTool
from taurus.qt.qtgui.panel import TaurusModelChooser
from functools import partial
import numpy as np
from smart import icon_path
from ...util.util import findMainWindow

class Taurus2DImageItem(GraphicsLayoutWidget, TaurusBaseComponent):
# class Taurus2DImageItem(GraphicsLayoutWidget, TaurusImageItem):
    """
    Displays 2Dimage data
    """
    modelKeys = ['img']
    # modelKeys = [TaurusBaseComponent.MLIST]
    # TODO: clear image if .setModel(None)
    def __init__(self, parent = None, *args, **kwargs):
        GraphicsLayoutWidget.__init__(self, *args, **kwargs)
        TaurusBaseComponent.__init__(self, "Taurus2DImageItem")
        # TaurusImageItem.__init__(self, *args, **kwargs)
        self._timer = Qt.QTimer()
        self._timer.timeout.connect(self._forceRead)
        self._parent = parent
        self._init_ui()
        self.width = None
        self.data_format_cbs = [lambda x: x]
        self.autolevel = True
        # self.setModel('sys/tg_test/1/long64_image_ro')

    def update_autolevel(self, autolevel):
        self.autolevel = autolevel

    def _init_ui(self):
        self._setup_one_channel_viewer()
        self._setup_context_action()

    def _setup_context_action(self):
        main_gui = findMainWindow()
        self.vt = VisuaTool(self, properties = ['prof_hoz','prof_ver'])
        self.vt.attachToPlotItem(self.img_viewer)
        self.fr = CumForcedReadTool(self, period=0)
        self.fr.attachToPlotItem(self.img_viewer)
        self.vt._onTriggered()
        self.mpicker = TaurusImgModelChooserTool(self)
        self.mpicker._onTriggered = self._onTriggered_model_chooser
        self.mpicker.attachToPlotItem(self.img_viewer)
        # self.resume_prim_action = resumePrim(self)
        # self.resume_prim_action.attachToPlotItem(self.img_viewer)
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

    def _onTriggered_model_chooser(self):

        modelName = self.getFullModelName()
        if modelName is None:
            listedModels = []
        else:
            listedModels = [modelName]

        res, ok = TaurusModelChooser.modelChooserDlg(
            selectables=[TaurusElementType.Attribute],
            singleModel=True,
            listedModels=listedModels,
        )
        if ok:
            if res:
                model = res[0]
            else:
                model = None
            self.setModel(model)

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

    def handleEvent(self, evt_src, evt_type, evt_val_list):
        """Reimplemented from :class:`TaurusImageItem`"""
        if type(evt_val_list) is list:
            evt_val, key = evt_val_list
        else:
            evt_val = evt_val_list
            if evt_src is self.getModelObj(key='img'):
                key = 'img'
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