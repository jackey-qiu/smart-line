from PyQt5.QtGui import QPaintEvent, QPainter, QPen
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget
from ...widgets.shapes.shape_container import rectangle, shapeComposite, isocelesTriangle, buildTools
from ...widgets.shapes.callback_container import *

class beamlineSynopticViewer(QWidget):

    def __init__(self, parent = None, yaml_config_file = 'C:\\Users\\qiucanro\\apps\\smart-line\\src\\smart\\gui\\widgets\\shapes\\shape_demo.yaml'):
        super().__init__(parent = parent)
        self.config_file = yaml_config_file
        self.composite_shape = None
        self.parent = parent
        self.init_shape()

    def set_parent(self, parent):
        self.parent = parent
        setattr(self.composite_shape, 'parent', parent)

    def init_shape(self, which_composite = 'composite1'):
        self.composite_shape = buildTools.build_composite_shape_from_yaml(self.config_file)[which_composite]

    def paintEvent(self, a0: QPaintEvent | None) -> None:
        qp = QPainter()
        qp.begin(self)
        # for each in self.shapes:                       
        for each_shape in self.composite_shape.shapes:
            qp.resetTransform()
            each_shape.paint(qp)
        qp.end()

    def mouseMoveEvent(self, event):
        self.last_x, self.last_y = event.x(), event.y()
        if self.parent !=None:
            self.parent.statusbar.showMessage('Mouse coords: ( %d : %d )' % (event.x(), event.y()))
        for each_shape in self.composite_shape.shapes:
            each_shape.cursor_pos_checker(event.x(), event.y())
        self.update()

    def mousePressEvent(self, event):
        x, y = event.x(), event.y()
        pass