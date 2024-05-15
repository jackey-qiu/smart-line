from taurus.qt.qtgui.base import TaurusBaseComponent
from taurus.external.qt import Qt
from taurus import Device
from pyqtgraph import GraphicsLayoutWidget
import pyqtgraph as pg
from PyQt5 import QtCore
from ...util.util import findMainWindow

class motorMeter(GraphicsLayoutWidget, TaurusBaseComponent):
    modelKeys = [TaurusBaseComponent.MLIST]

    def __init__(self, parent=None):
        GraphicsLayoutWidget.__init__(self)
        TaurusBaseComponent.__init__(self)
        #self.parent = parent
        self.set_parent()
        self.motor_name_list = []
        self.plot_objs= []
        self.motor_pos_marker_list = []
        self.text_label_list = []

    #def set_parent(self, parent):
    #    self.parent = parent

    def set_parent(self):
        self.parent = findMainWindow()

    def update_motor_viewer(self):
        motor_keys = [each for each in self.parent.settings_object.allKeys() if each.startswith('Motors')]
        models = [self.parent.settings_object.value(key)+'/Position' for key in motor_keys]
        self._setModel_list([each.rsplit('/')[1] for each in motor_keys], models)

    def _setModel_list(self, motor_name_list, motor_model_list):
        self.setModel(motor_model_list)
        self.clear()
        self.motor_pos_marker_list = []
        self.text_label_list = []
        self.motor_name_list = motor_name_list
        colors = ['g','r','y','m','c','b','w']
        if len(colors)<len(self.motor_name_list):
            colors = colors + ['g']*(len(self.motor_name_list)-len(colors))
        
        for i, motor in enumerate(motor_name_list):
            self.plot_objs.append(self.addPlot())
            self.text_label_list.append(pg.TextItem(motor+f'={round(Device(motor).position,3)}', anchor=(0., 7)))
            self.plot_objs[-1].hideAxis('left')
            self.plot_objs[-1].setXRange(-10,10,padding=0.1)
            self.motor_pos_marker_list.append(pg.InfiniteLine(angle=90, movable=True, pen=pg.mkPen(colors[i], width=2, style=QtCore.Qt.SolidLine)))
            self.plot_objs[-1].addItem(self.motor_pos_marker_list[-1])
            self.text_label_list[-1].setParentItem(self.motor_pos_marker_list[-1])
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
                    self.text_label_list[i].setText(f'{self.motor_name_list[i]}={round(float(evt_value.rvalue.m),3)}')
                    break
        except Exception as e:
            self.info("Skipping event. Reason: %s", e)

    def move_motor_to_finishing_line(self, motor_name, infinitline_obj):
        if self.parent==None:
            return
        if self.parent._qDoor!=None:
            #self.plot_objs[self.motor_name_list.index(motor_name)].setTitle(f'{motor_name}={float(infinitline_obj.value())}')
            self.text_label_list[self.motor_name_list.index(motor_name)].setText(f'{motor_name}={round(float(infinitline_obj.value()),3)})')
            self.parent._qDoor.runMacro(f'<macro name="mv"><paramrepeat name="motor_pos_list"><repeat nr="1">\
                                    <param name="motor" value="{motor_name}"/><param name="pos" value="{infinitline_obj.value()}"/>\
                                    </repeat></paramrepeat></macro>')

        


    