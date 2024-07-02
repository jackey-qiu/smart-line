import os
import pyqtgraph as pg
import re
import time

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal as Signal
from taurus.qt.qtcore.configuration import BaseConfigurableClass
import numpy as np

def check_true(v):
    if isinstance(v, bool):
        return v
    elif isinstance(v, int):
        if v <= 0:
            return False
        else:
            return True
    elif isinstance(v, str):
        if v.lower() == "true" or v == "1":
            return True
        else:
            return False
    elif isinstance(v, bytes):
        if v.lower() == b"true" or v == b"1":
            return True
        else:
            return False
    else:
        if v:
            return True
        else:
            return False

class mvMotors(QtWidgets.QAction, BaseConfigurableClass):

    def __init__(
        self,
        parent=None,
        text="Move sample stage here",
    ):
        BaseConfigurableClass.__init__(self)
        QtWidgets.QAction.__init__(self, text, parent)
        tt = "mv the sample stages (x, y) to the cursor position"
        self.setToolTip(tt)
        self._parent = parent

        # register config properties
        # self.registerConfigProperty(self.buffersize, self.setBufferSize, "buffersize")

        # internal conections
        self.triggered.connect(self._onTriggered)

    def _onTriggered(self):
        msgBox = QtWidgets.QMessageBox()
        msgBox.setIcon(QtWidgets.QMessageBox.Question)
        msgBox.setText(f"Are you sure to move sample stage to here: {self._parent.last_cursor_pos_on_camera_viewer}?")
        msgBox.setWindowTitle("Move sample stages to cursor position")
        msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        #msgBox.buttonClicked.connect(self._parent.mv_sample_stage_to_cursor_point)
        returnValue = msgBox.exec()
        if returnValue == QtWidgets.QMessageBox.Ok:
            self._parent.mv_stages_to_cursor_pos()

    def attachToPlotItem(self, plot_item):
        """Use this method to add this tool to a plot
        :param plot_item: (PlotItem)
        """
        menu = plot_item.getViewBox().menu
        menu.addAction(self)
        self.plot_item = plot_item

class setRef(QtWidgets.QAction, BaseConfigurableClass):
    """
    This tool provides a menu option to control the "Forced Read" period of
    Plot data items that implement a `setForcedReadPeriod` method
    (see, e.g. :meth:`TaurusTrendSet.setForcedReadPeriod`).
    The force-read feature consists on forcing periodic attribute reads for
    those attributes being plotted with a :class:`TaurusTrendSet` object.
    This allows to force plotting periodical updates even for attributes
    for which the taurus polling is not enabled.
    Note that this is done at the widget level and therefore does not affect
    the rate of arrival of events for other widgets connected to the same
    attributes
    This tool inserts an action with a spinbox and emits a `valueChanged`
    signal whenever the value is changed.
    The connection between the data items and this tool can be done manually
    (by connecting to the `valueChanged` signal or automatically, if
    :meth:`autoconnect()` is `True` (default). The autoconnection feature works
    by discovering the compliant data items that share associated to the
    plot_item.
    This tool is implemented as an Action, and provides a method to attach it
    to a :class:`pyqtgraph.PlotItem`
    """

    def __init__(
        self,
        parent=None,
        text="match crosshair pos to stage pos",
    ):
        BaseConfigurableClass.__init__(self)
        QtWidgets.QAction.__init__(self, text, parent)
        tt = "click to let the axis label reflect the sample stage coordinates"
        self.setToolTip(tt)
        self._parent = parent

        # register config properties
        # self.registerConfigProperty(self.buffersize, self.setBufferSize, "buffersize")

        # internal conections
        self.triggered.connect(self._onTriggered)

    def _onTriggered(self):
        self._parent.mv_img_to_ref()
        self._parent.pos_calibration_done = True

    def attachToPlotItem(self, plot_item):
        """Use this method to add this tool to a plot
        :param plot_item: (PlotItem)
        """
        menu = plot_item.getViewBox().menu
        menu.addAction(self)
        self.plot_item = plot_item

class camSwitch(QtWidgets.QAction, BaseConfigurableClass):
    """
    This tool provides a menu option to control the "Forced Read" period of
    Plot data items that implement a `setForcedReadPeriod` method
    (see, e.g. :meth:`TaurusTrendSet.setForcedReadPeriod`).
    The force-read feature consists on forcing periodic attribute reads for
    those attributes being plotted with a :class:`TaurusTrendSet` object.
    This allows to force plotting periodical updates even for attributes
    for which the taurus polling is not enabled.
    Note that this is done at the widget level and therefore does not affect
    the rate of arrival of events for other widgets connected to the same
    attributes
    This tool inserts an action with a spinbox and emits a `valueChanged`
    signal whenever the value is changed.
    The connection between the data items and this tool can be done manually
    (by connecting to the `valueChanged` signal or automatically, if
    :meth:`autoconnect()` is `True` (default). The autoconnection feature works
    by discovering the compliant data items that share associated to the
    plot_item.
    This tool is implemented as an Action, and provides a method to attach it
    to a :class:`pyqtgraph.PlotItem`
    """

    def __init__(
        self,
        parent=None,
        text="Start camera streaming",
    ):
        BaseConfigurableClass.__init__(self)
        QtWidgets.QAction.__init__(self, text, parent)
        tt = "Toggle to start or stop camara streaming"
        self.setToolTip(tt)
        self._on = False
        self._parent = parent

        # register config properties
        # self.registerConfigProperty(self.buffersize, self.setBufferSize, "buffersize")

        # internal conections
        self.triggered.connect(self._onTriggered)

    def _onTriggered(self):
        self._on = not self._on
        if self._on:
            self.setText('Stop cam streaming!')
            self._parent.start_cam_stream()
        else:
            self.setText('Start cam streaming!')
            self._parent.stop_cam_stream()

    def attachToPlotItem(self, plot_item):
        """Use this method to add this tool to a plot
        :param plot_item: (PlotItem)
        """
        menu = plot_item.getViewBox().menu
        menu.addAction(self)
        self.plot_item = plot_item

class VisuaTool(QtWidgets.QAction, BaseConfigurableClass):

    valueChanged = QtCore.pyqtSignal(int)

    def __init__(
        self,
        parent=None,
        text="Toggle show or hide profiles",
        properties = [],
    ):
        BaseConfigurableClass.__init__(self)
        QtWidgets.QAction.__init__(self, text, parent)
        tt = "Toggle to show or hide cut profiles"
        self.setToolTip(tt)
        self._show = True
        self._properties = properties

        # register config properties
        # self.registerConfigProperty(self.buffersize, self.setBufferSize, "buffersize")

        # internal conections
        self.triggered.connect(self._onTriggered)

    def _onTriggered(self):
        self._show = not self._show
        if self._show:
            for each in self._properties:
                getattr(self.plot_item.getViewWidget(), each).show()
        else:
            for each in self._properties:
                getattr(self.plot_item.getViewWidget(), each).hide() 

    def buffersize(self):
        return self._bufferSize

    def attachToPlotItem(self, plot_item):
        """Use this method to add this tool to a plot
        :param plot_item: (PlotItem)
        """
        menu = plot_item.getViewBox().menu
        menu.addAction(self)
        self.plot_item = plot_item


class AutoLevelTool(QtWidgets.QAction):


    def __init__(
        self,
        parent=None,
        text="Disable autolevelling the cam image",
    ):
        QtWidgets.QAction.__init__(self, text, parent)
        tt = "Toggle to autolevel the cam image"
        self.setToolTip(tt)
        self._autolevel = True
        self.parent = parent

        # register config properties
        # self.registerConfigProperty(self.buffersize, self.setBufferSize, "buffersize")

        # internal conections
        self.triggered.connect(self._onTriggered)

    def _onTriggered(self):
        self._autolevel = not self._autolevel
        if self._autolevel:
            self.setText('Disable autolevelling the cam image')
            self.parent.update_autolevel(True)
        else:
            self.setText('Enable autolevelling the cam image')
            self.parent.update_autolevel(False)

    def attachToPlotItem(self, plot_item):
        """Use this method to add this tool to a plot
        :param plot_item: (PlotItem)
        """
        menu = plot_item.getViewBox().menu
        menu.addAction(self)
        self.plot_item = plot_item

class SaveCrossHair(QtWidgets.QAction):
    def __init__(
        self,
        parent=None,
        text="Save current crosshair position",
    ):
        QtWidgets.QAction.__init__(self, text, parent)
        tt = "save currentcrosshair position"
        self.setToolTip(tt)
        self.parent = parent

        # register config properties
        # self.registerConfigProperty(self.buffersize, self.setBufferSize, "buffersize")

        # internal conections
        self.triggered.connect(self._onTriggered)

    def _onTriggered(self):
        x, y = self.parent.isoLine_v.value(),self.parent.isoLine_h.value()
        self.parent.saved_crosshair_pos = [x, y]

    def attachToPlotItem(self, plot_item):
        """Use this method to add this tool to a plot
        :param plot_item: (PlotItem)
        """
        menu = plot_item.getViewBox().menu
        menu.addAction(self)
        self.plot_item = plot_item

class ResumeCrossHair(QtWidgets.QAction):
    def __init__(
        self,
        parent=None,
        text="Resume to saved crosshair position",
    ):
        QtWidgets.QAction.__init__(self, text, parent)
        tt = "resume to saved crosshair position"
        self.setToolTip(tt)
        self.parent = parent

        # register config properties
        # self.registerConfigProperty(self.buffersize, self.setBufferSize, "buffersize")

        # internal conections
        self.triggered.connect(self._onTriggered)

    def _onTriggered(self):
        x, y = self.parent.saved_crosshair_pos
        self.parent.isoLine_v.setValue(x)
        self.parent.isoLine_h.setValue(y)

    def attachToPlotItem(self, plot_item):
        """Use this method to add this tool to a plot
        :param plot_item: (PlotItem)
        """
        menu = plot_item.getViewBox().menu
        menu.addAction(self)
        self.plot_item = plot_item

class LockCrossTool(QtWidgets.QAction):
    def __init__(
        self,
        parent=None,
        text="Toggle to lock the crosshair",
    ):
        QtWidgets.QAction.__init__(self, text, parent)
        tt = "Toggle to lock the crosshair"
        self.setToolTip(tt)
        self._lock = False
        self.parent = parent

        # register config properties
        # self.registerConfigProperty(self.buffersize, self.setBufferSize, "buffersize")

        # internal conections
        self.triggered.connect(self._onTriggered)

    def _onTriggered(self):
        self._lock = not self._lock
        if self._lock:
            self.setText('Unlock crosshair')
            self.parent.isoLine_h.setMovable(False)
            self.parent.isoLine_v.setMovable(False)
        else:
            self.setText('Lock crosshair')
            self.parent.isoLine_h.setMovable(True)
            self.parent.isoLine_v.setMovable(True)

    def attachToPlotItem(self, plot_item):
        """Use this method to add this tool to a plot
        :param plot_item: (PlotItem)
        """
        menu = plot_item.getViewBox().menu
        menu.addAction(self)
        self.plot_item = plot_item


class GaussianFitTool(QtWidgets.QMenu, BaseConfigurableClass):
    """
    This tool provides a menu option to control the "Forced Read" period of
    Plot data items that implement a `setForcedReadPeriod` method
    (see, e.g. :meth:`TaurusTrendSet.setForcedReadPeriod`).
    The force-read feature consists on forcing periodic attribute reads for
    those attributes being plotted with a :class:`TaurusTrendSet` object.
    This allows to force plotting periodical updates even for attributes
    for which the taurus polling is not enabled.
    Note that this is done at the widget level and therefore does not affect
    the rate of arrival of events for other widgets connected to the same
    attributes
    This tool inserts an action with a spinbox and emits a `valueChanged`
    signal whenever the value is changed.
    The connection between the data items and this tool can be done manually
    (by connecting to the `valueChanged` signal or automatically, if
    :meth:`autoconnect()` is `True` (default). The autoconnection feature works
    by discovering the compliant data items that share associated to the
    plot_item.
    This tool is implemented as an Action, and provides a method to attach it
    to a :class:`pyqtgraph.PlotItem`
    """

    valueChanged = QtCore.pyqtSignal(int)

    def __init__(
        self,
        parent=None,
        text="Gaussian Fit...",
        properties = [],
    ):
        BaseConfigurableClass.__init__(self)
        QtWidgets.QMenu.__init__(self, text, parent)
        tt = "gaussian fit the plots"
        self.setToolTip(tt)
        # self._show = True
        self._properties = properties

        # register config properties
        # self.registerConfigProperty(self.buffersize, self.setBufferSize, "buffersize")

        # internal conections
        # self.triggered.connect(self._onTriggered)

    def add_actions(self, plot_widget, curve_items):

        def _fit_gaussian(curve):
            from lmfit import Minimizer, create_params, report_fit
            from lmfit.lineshapes import gaussian, lorentzian, linear

            x_data = plot_widget.x_axis['data'].contents()
            cen_g = (max(x_data) - min(x_data))/2 + min(x_data)
            wid_g = (max(x_data) - min(x_data))/5

            def make_gau():
                offset_rand = np.random.normal(scale = 0.1, size = x_data.size)
                mu = (max(x_data) - min(x_data))/2 + min(x_data)
                sig = (max(x_data) - min(x_data))/20
                return 1.0 / (np.sqrt(2.0 * np.pi) * sig) * np.exp(-np.power((x_data - mu) / sig, 2.0) / 2) + curve.curve_data.contents() + offset_rand

            def residual(pars, x, data):
                model = gaussian(x, pars['amp_g'], pars['cen_g'], pars['wid_g']) + linear(x, pars['slope_l'], pars['intercept_l'])
                return model - data
            
            # sim_y_data = make_gau()
            pfit = create_params(amp_g=1, cen_g=cen_g, wid_g=wid_g, slope_l = 0, intercept_l = np.mean(curve.curve_data.contents()))
            mini = Minimizer(residual, pfit, fcn_args=(x_data, curve.curve_data.contents()))
            # mini = Minimizer(residual, pfit, fcn_args=(x_data, sim_y_data))
            out = mini.leastsq()
            last_curve.opts = curve.opts
            last_curve.setData(x_data, curve.curve_data.contents()+out.residual)
            # curve.setData(x_data, sim_y_data)
            # curve.setData(x_data, curve.curve_data.contents())

        # x_data = plot_widget.x_axis['data'].contents()
        last_curve = curve_items[-1]
        curve_items = curve_items[0:-1]
        for curve in curve_items:
            curve_name = curve.name()
            action = QtWidgets.QAction(curve_name, self)
            action.triggered.connect(lambda state, curve=curve:_fit_gaussian(curve))
            self.addAction(action)

    def attachToPlotItem(self, plot_item):
        """Use this method to add this tool to a plot
        :param plot_item: (PlotItem)
        """
        menu = plot_item.getViewBox().menu
        menu.addMenu(self)

class GaussianSimTool(QtWidgets.QMenu, BaseConfigurableClass):
    """
    This tool provides a menu option to control the "Forced Read" period of
    Plot data items that implement a `setForcedReadPeriod` method
    (see, e.g. :meth:`TaurusTrendSet.setForcedReadPeriod`).
    The force-read feature consists on forcing periodic attribute reads for
    those attributes being plotted with a :class:`TaurusTrendSet` object.
    This allows to force plotting periodical updates even for attributes
    for which the taurus polling is not enabled.
    Note that this is done at the widget level and therefore does not affect
    the rate of arrival of events for other widgets connected to the same
    attributes
    This tool inserts an action with a spinbox and emits a `valueChanged`
    signal whenever the value is changed.
    The connection between the data items and this tool can be done manually
    (by connecting to the `valueChanged` signal or automatically, if
    :meth:`autoconnect()` is `True` (default). The autoconnection feature works
    by discovering the compliant data items that share associated to the
    plot_item.
    This tool is implemented as an Action, and provides a method to attach it
    to a :class:`pyqtgraph.PlotItem`
    """

    valueChanged = QtCore.pyqtSignal(int)

    def __init__(
        self,
        parent=None,
        text="Make Gaussian shape...",
        properties = [],
    ):
        BaseConfigurableClass.__init__(self)
        QtWidgets.QMenu.__init__(self, text, parent)
        tt = "gaussian fit the plots"
        self.setToolTip(tt)
        # self._show = True
        self._properties = properties

        # register config properties
        # self.registerConfigProperty(self.buffersize, self.setBufferSize, "buffersize")

        # internal conections
        # self.triggered.connect(self._onTriggered)

    def add_actions(self, plot_widget, curve_items):

        x_data = plot_widget.x_axis['data'].contents()

        def _make_gaussian(curve):
            offset_rand = np.random.normal(scale = 0.1, size = x_data.size)
            mu = (max(x_data) - min(x_data))/2 + min(x_data)
            sig = (max(x_data) - min(x_data))/20
            y_gaussian = 1.0 / (np.sqrt(2.0 * np.pi) * sig) * np.exp(-np.power((x_data - mu) / sig, 2.0) / 2) + curve.curve_data.contents()
            last_curve.opts = curve.opts
            last_curve.setData(x_data, y_gaussian + offset_rand)
        last_curve = curve_items[-1]
        curve_items = curve_items[0:-1]
        for curve in curve_items:
            curve_name = curve.name()
            action = QtWidgets.QAction(curve_name, self)
            action.triggered.connect(lambda state, curve=curve:_make_gaussian(curve))
            self.addAction(action)

    def attachToPlotItem(self, plot_item):
        """Use this method to add this tool to a plot
        :param plot_item: (PlotItem)
        """
        menu = plot_item.getViewBox().menu
        menu.addMenu(self)

class MoveMotorTool(QtWidgets.QAction, BaseConfigurableClass):
    """
    This tool provides a menu option to control the "Forced Read" period of
    Plot data items that implement a `setForcedReadPeriod` method
    (see, e.g. :meth:`TaurusTrendSet.setForcedReadPeriod`).
    The force-read feature consists on forcing periodic attribute reads for
    those attributes being plotted with a :class:`TaurusTrendSet` object.
    This allows to force plotting periodical updates even for attributes
    for which the taurus polling is not enabled.
    Note that this is done at the widget level and therefore does not affect
    the rate of arrival of events for other widgets connected to the same
    attributes
    This tool inserts an action with a spinbox and emits a `valueChanged`
    signal whenever the value is changed.
    The connection between the data items and this tool can be done manually
    (by connecting to the `valueChanged` signal or automatically, if
    :meth:`autoconnect()` is `True` (default). The autoconnection feature works
    by discovering the compliant data items that share associated to the
    plot_item.
    This tool is implemented as an Action, and provides a method to attach it
    to a :class:`pyqtgraph.PlotItem`
    """

    valueChanged = QtCore.pyqtSignal(int)

    def __init__(
        self,
        parent=None,
        text="move motor to clicked position",
        properties = [],
        door_device = None,
        motor_marker_line_obj = None, 
    ):
        BaseConfigurableClass.__init__(self)
        QtWidgets.QAction.__init__(self, text, parent)
        tt = "move motor to a specific right-clicked position"
        self.setToolTip(tt)
        # self._show = True
        self._properties = properties
        self.door = door_device
        self.motor_marker_line_obj = motor_marker_line_obj
        self.motor_name = None
        self.motor_pos = None

        # register config properties
        # self.registerConfigProperty(self.buffersize, self.setBufferSize, "buffersize")

        # internal conections
        self.triggered.connect(self._onTriggered)

    def _onTriggered(self):
        if self.door == None:
            return
        else:
            # mot_name ='mot01'
            # mot_pos = 1
            self.door.runMacro(f'<macro name="mv"><paramrepeat name="motor_pos_list"><repeat nr="1">\
                                 <param name="motor" value="{self.motor_name}"/><param name="pos" value="{self.motor_pos}"/>\
                                 </repeat></paramrepeat></macro>')
            # self.motor_marker_line_obj.setValue(self.motor_pos)

    def buffersize(self):
        return self._bufferSize

    def attachToPlotItem(self, plot_item):
        """Use this method to add this tool to a plot
        :param plot_item: (PlotItem)
        """
        menu = plot_item.getViewBox().menu
        menu.addAction(self)
        self.plot_item = plot_item

class CopyTable(QtWidgets.QTableWidget):
    """
    Class contains the methods that creates a table from which can be copied
    Contains also other utilities associated with interactive tables.
    """

    def __init__(self, parent=None):
        super(CopyTable, self).__init__(parent)
        self._parent = parent
        self.setAlternatingRowColors(True)

    def paste(self):
        s = self._parent.clip.text()
        rows = s.split("\n")
        selected = self.selectedRanges()
        rc = 1
        if selected:
            for r in range(selected[0].topRow(), selected[0].bottomRow() + 1):
                if (len(rows) > rc):
                    v = rows[rc].split("\t")
                    cc = 1
                    for c in range(selected[0].leftColumn(), selected[0].rightColumn() + 1):
                        if (len(v) > cc):
                            self.item(r,c).setText(v[cc])
                        cc+=1
                rc+=1
        else:
            for r in range(0, self.rowCount()):
                if (len(rows) > rc):
                    v = rows[rc].split("\t")
                    cc = 1
                    for c in range(0, self.columnCount()):
                        if (len(v) > cc):
                            self.item(r,c).setText(v[cc])
                        cc+=1
                rc+=1

    def copy(self):
        selected = self.selectedRanges()
        if selected:
            if self.horizontalHeaderItem(0):
                s = '\t' + "\t".join([str(self.horizontalHeaderItem(i).text()) for i in
                                      range(selected[0].leftColumn(), selected[0].rightColumn() + 1)])
            else:
                s = '\t' + "\t".join([str(i) for i in range(selected[0].leftColumn(), selected[0].rightColumn() + 1)])
            s = s + '\n'
            for r in range(selected[0].topRow(), selected[0].bottomRow() + 1):
                if self.verticalHeaderItem(r):
                    s += self.verticalHeaderItem(r).text() + '\t'
                else:
                    s += str(r) + '\t'
                for c in range(selected[0].leftColumn(), selected[0].rightColumn() + 1):
                    try:
                        item_text = str(self.item(r, c).text())
                        if item_text.endswith("\n"):
                            item_text = item_text[:-2]
                        s += item_text + "\t"
                    except AttributeError:
                        s += "\t"
                s = s[:-1] + "\n"  # eliminate last '\t'
            self._parent.clip.setText(s)
        else:
            if self.horizontalHeaderItem(0):
                s = '\t' + "\t".join([str(self.horizontalHeaderItem(i).text()) for i in range(0, self.columnCount())])
            else:
                s = '\t' + "\t".join([str(i) for i in range(0, self.columnCount())])
            s = s + '\n'

            for r in range(0, self.rowCount()):
                if self.verticalHeaderItem(r):
                    s += self.verticalHeaderItem(r).text() + '\t'
                else:
                    s += str(r) + '\t'
                for c in range(0, self.columnCount()):
                    try:
                        item_text = str(self.item(r, c).text())
                        if item_text.endswith("\n"):
                            item_text = item_text[:-2]
                        s += item_text + "\t"
                    except AttributeError:
                        s += "\t"
                s = s[:-1] + "\n"  # eliminate last '\t'
            self._parent.clip.setText(s)


class TableWidgetDragRows(CopyTable):
    rowsSwitched_sig = Signal(int, int)
    dropEventCompleted_sig = Signal()

    def __init__(self, parent, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._parent = parent
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropOverwriteMode(False)
        self.setDropIndicatorShown(True)
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.setDragDropMode(QtGui.QAbstractItemView.InternalMove)
        # // this lock mode can temporary lock all drag movement
        self.locked_status = False
        self.installEventFilter(self)

    def setMultiRowSel(self, selection):
        """
        allow multiple rows to be selected
        :param selection:
        :return:
        """
        self.setSelectionMode(self.MultiSelection)
        for i in selection:
            self.selectRow(i)
        self.setSelectionMode(self.ExtendedSelection)

    def dropEvent(self, event):
        """
        This code runs when a line is dragged and dropped onto the table
        :param event:
        :return:
        """
        if self.locked_status:
            return

        if not event.isAccepted() and event.source() == self:
            drop_row = self.drop_on(event)
            rows = sorted(set(item.row() for item in self.selectedItems()))
            rows_to_move = []
            for row_index in rows:
                row_data = []
                for column_index in range(self.columnCount()):
                    row_data += [QtWidgets.QTableWidgetItem(self.item(row_index, column_index))]
                rows_to_move += [row_data]

            # for i, row in enumerate(rows_to_move):
            #     row[2].loc = self.item(rows[i], 2).loc

            # %increase row count
            # self.setRowCount(self.rowCount()+1)

            # // reorganize field list by inserting the new rows
            for row_index in reversed(rows):
                self.rowsSwitched_sig.emit(drop_row, row_index)
                # self._parent.field_list.insert(drop_row, self._parent.field_list.pop(row_index))

            for row_index, data in enumerate(rows_to_move):
                row_index += drop_row
                self.insertRow(row_index)
                for column_index, column_data in enumerate(data):
                    self.setItem(row_index, column_index, column_data)

                self.setRowHeight(row_index, 20)
                self.setRowHeight(drop_row, 20)

            for row_index in range(len(rows_to_move)):
                self.item(drop_row + row_index, 0).setSelected(True)
                # self.item(drop_row + row_index, 1).setSelected(True)

            for row_index in reversed(rows):
                if row_index < drop_row:
                    self.removeRow(row_index)
                else:
                    self.removeRow(row_index + len(rows_to_move))

            event.accept()
            self.dropEventCompleted_sig.emit()

        super().dropEvent(event)

    def drop_on(self, event):
        index = self.indexAt(event.pos())
        if not index.isValid():
            return self.rowCount()
        return index.row() + 1 if self.is_below(event.pos(), index) else index.row()

    def is_below(self, pos, index):
        rect = self.visualRect(index)
        margin = 2
        if pos.y() - rect.top() < margin:
            return False
        elif rect.bottom() - pos.y() < margin:
            return True
        # noinspection PyTypeChecker
        return rect.contains(pos, True) and not (
                int(self.model().flags(index)) & QtCore.Qt.ItemIsDropEnabled) and pos.y() >= rect.center().y()


class LoadingAnimationDialog(QtWidgets.QDialog):
    """
    Class for displaying loading animations
    """

    def __init__(self, parent):
        super(LoadingAnimationDialog, self).__init__(parent)

    def start_loading_animation(self):
        self.loading_movie = QtGui.QMovie(":/icon/loading.gif")
        self.loading_movie.setScaledSize(QtCore.QSize(60, 60))
        self.loading_label = QtGui.QLabel()
        self.loading_label.setMovie(self.loading_movie)
        self.loading_label.setAlignment(QtCore.Qt.AlignCenter)
        self.loading_movie.start()

    def stop_loading_animation(self):
        self.loading_movie.stop()
        # QtCore.qDebug("stop animation")
        self.loading_movie.setParent(None)
        self.loading_movie.deleteLater()
        self.loading_label.setParent(None)
        self.loading_label.deleteLater()


class DialogWithCheckBox(QtWidgets.QMessageBox):
    """
    Shows a dialog with a checkbox
    """

    def __init__(self, parent=None):
        """

        :param parent:
        """
        super(DialogWithCheckBox, self).__init__()
        self.checkbox = QtGui.QCheckBox()
        # // Access the Layout of the MessageBox to add the Checkbox
        layout = self.layout()
        layout.addWidget(self.checkbox, 2, 2)

    def exec_(self, *args, **kwargs):
        """
        Override the exec_ method so you can return the value of the checkbox
        """
        return QtWidgets.QMessageBox.exec_(self, *args, **kwargs), self.checkbox.isChecked()


