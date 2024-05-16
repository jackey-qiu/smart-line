from PyQt5.QtGui import QPaintEvent, QPainter, QPen
from PyQt5.QtCore import Qt
from PyQt5.QtCore import pyqtSlot as Slot
from PyQt5.QtWidgets import QWidget
from ...widgets.shapes.shape_container import rectangle, shapeComposite, isocelesTriangle, buildTools
from ...widgets.shapes.callback_container import *
from ....util.util import findMainWindow
from smart import rs_path

class beamlineSynopticViewer(QWidget):

    def __init__(self, parent = None, yaml_config_file = str(rs_path / 'config' / 'shape_demo.yaml')):
        super().__init__(parent = parent)
        self.config_file = yaml_config_file
        self.composite_shape = None
        self.viewer_shape = None
        self.set_parent()
        self.init_viewer()

    def connect_slots_synoptic_viewer(self):
        self.parent.pushButton_slit.clicked.connect(lambda: self.init_shape('slit'))
        self.parent.pushButton_valve.clicked.connect(lambda: self.init_shape('valve'))

    def set_parent(self):
        self.parent = findMainWindow()

    def init_shape(self, which_composite = 'slit'):
        self.composite_shape = buildTools.build_composite_shape_from_yaml(self.config_file)[which_composite]
        self.composite_shape.updateSignal.connect(self.update_canvas)

    def init_viewer(self, which_viewer = 'viewer1'):
        self.viewer_shape = buildTools.build_view_from_yaml(self.config_file)[which_viewer]
        for each_composite in self.viewer_shape.values():
            each_composite.updateSignal.connect(self.update_canvas)

    def paintEvent(self, a0: QPaintEvent | None) -> None:
        qp = QPainter()
        qp.begin(self)
        # for each in self.shapes:                       
        if self.viewer_shape == None:
            return
        #make a line simulating x-ray beam path
        if len(self.viewer_shape)>1:
            qp.setPen(QPen(Qt.yellow, 3, Qt.SolidLine))   
            all_composite_shapes = list(self.viewer_shape.values())
            shape_upstream, shape_downstream = all_composite_shapes[0].ref_shape, all_composite_shapes[-1].ref_shape
            lines = buildTools.make_line_connection_btw_two_anchors(shapes = [shape_upstream, shape_downstream], anchors=['right','left'], direct_connection=True)
            for i in range(len(lines)-1):
                pts = list(lines[i]) + list(lines[i+1])
                qp.drawLine(*pts)
        for composite_shape in self.viewer_shape.values():
            for each_shape in composite_shape.shapes:
                qp.resetTransform()
                each_shape.paint(qp)
        """        
        if self.composite_shape == None:
            return
        for each_shape in self.composite_shape.shapes:
            qp.resetTransform()
            each_shape.paint(qp)
        """
        qp.end()

    @Slot()
    def update_canvas(self):
        self.update()

    def mouseMoveEvent(self, event):
        self.last_x, self.last_y = event.x(), event.y()
        if self.parent !=None:
            self.parent.statusbar.showMessage('Mouse coords: ( %d : %d )' % (event.x(), event.y()))
        if self.viewer_shape == None:
            return
        for composite_shape in self.viewer_shape.values():
            for each_shape in composite_shape.shapes:
                each_shape.cursor_pos_checker(event.x(), event.y())
        """
        if self.composite_shape == None:
            return
        for each_shape in self.composite_shape.shapes:
            each_shape.cursor_pos_checker(event.x(), event.y())
        """
        self.update()

    def mousePressEvent(self, event):
        x, y = event.x(), event.y()
        pass