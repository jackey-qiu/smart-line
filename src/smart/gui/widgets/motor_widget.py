from taurus.qt.qtgui.base import TaurusBaseComponent
from taurus.external.qt import Qt
from taurus import Device
from pyqtgraph import GraphicsLayoutWidget
import pyqtgraph as pg
from PyQt5 import QtCore


class PowerMeter(Qt.QProgressBar, TaurusBaseComponent):
    """A Taurus-ified QProgressBar with separate models for value and color"""
    # setFormat() defined by both TaurusBaseComponent and QProgressBar. Rename.
    setFormat = TaurusBaseComponent.setFormat
    setBarFormat = Qt.QProgressBar.setFormat

    modelKeys = ["power", "color"]  # support 2 models (default key is "power")
    _template = "QProgressBar::chunk {background: %s}"  # stylesheet template

    def __init__(self, parent=None, value_range=(0, 100)):
        super(PowerMeter, self).__init__(parent=parent)
        self.parent = parent
        self.setOrientation(Qt.Qt.Vertical)
        self.setRange(*value_range)
        self.setTextVisible(False)
        self.setModel("eval:Q(60+20*rand())")  # implicit use of  key="power"
        self.setModel("eval:['green','red','blue'][randint(3)]", key='color')

    def handleEvent(self, evt_src, evt_type, evt_value):
        """reimplemented from TaurusBaseComponent"""
        try:
            if evt_src is self.getModelObj(key="power"):
                self.setValue(int(evt_value.rvalue.m))
            elif evt_src is self.getModelObj(key="color"):
                if hasattr(self,'holder'):
                    if self.holder.taurusLCD.value()>50:
                        self.setStyleSheet(self._template % 'red')
                    else:
                        self.setStyleSheet(self._template % 'green')
                else:
                    self.setStyleSheet(self._template % evt_value.rvalue)
        except Exception as e:
            self.info("Skipping event. Reason: %s", e)


class motorMeter(GraphicsLayoutWidget, TaurusBaseComponent):
    modelKeys = [TaurusBaseComponent.MLIST]

    def __init__(self, parent=None):
        GraphicsLayoutWidget.__init__(self)
        TaurusBaseComponent.__init__(self)
        self.parent = parent
        self.motor_name_list = []
        self.plot_objs= []
        self.motor_pos_marker_list = []

    def set_parent(self, parent):
        self.parent = parent

    def update_motor_viewer(self):
        motor_keys = [each for each in self.parent.settings_object.allKeys() if each.startswith('Motors')]
        models = [self.parent.settings_object.value(key)+'/Position' for key in motor_keys]
        self._setModel_list([each.rsplit('/')[1] for each in motor_keys], models)

    def _setModel_list(self, motor_name_list, motor_model_list):
        self.setModel(motor_model_list)
        self.clear()
        self.motor_pos_marker_list = []
        self.motor_name_list = motor_name_list
        for motor in motor_name_list:
            self.plot_objs.append(self.addPlot(title = motor))
            self.plot_objs[-1].hideAxis('left')
            self.plot_objs[-1].setXRange(-10,10,padding=2)
            self.motor_pos_marker_list.append(pg.InfiniteLine(angle=90, movable=True, pen=pg.mkPen('g', width=1, style=QtCore.Qt.SolidLine)))
            self.plot_objs[-1].addItem(self.motor_pos_marker_list[-1])
            self.motor_pos_marker_list[-1].setValue(Device(motor).position)
            self.motor_pos_marker_list[-1].sigPositionChangeFinished.connect(lambda state, motor=motor,line=self.motor_pos_marker_list[-1]:self.move_motor_to_finishing_line(motor, line))
            if motor != motor_name_list[-1]:
                self.nextRow()

    def handleEvent(self, evt_src, evt_type, evt_value):
        """reimplemented from TaurusBaseComponent"""
        try:
            for i in range(len(self.motor_name_list)):
                if evt_src is self.getModelObj(key=(TaurusBaseComponent.MLIST, i)):
                    self.motor_pos_marker_list[i].setValue(float(evt_value.rvalue.m))
                    break
        except Exception as e:
            self.info("Skipping event. Reason: %s", e)

    def move_motor_to_finishing_line(self, motor_name, infinitline_obj):
        if self.parent==None:
            return
        if self.parent._qDoor!=None:
            self.parent._qDoor.runMacro(f'<macro name="mv"><paramrepeat name="motor_pos_list"><repeat nr="1">\
                                    <param name="motor" value="{motor_name}"/><param name="pos" value="{infinitline_obj.value()}"/>\
                                    </repeat></paramrepeat></macro>')

        


    