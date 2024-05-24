from PyQt5.QtGui import QPaintEvent, QPainter, QPen, QColor
from PyQt5.QtCore import Qt
from PyQt5.QtCore import pyqtSlot as Slot
from PyQt5.QtWidgets import QWidget
from ...widgets.shapes.shape_container import rectangle, shapeComposite, isocelesTriangle, buildTools, make_decoration_from_text
from ...widgets.shapes.callback_container import *
from ....util.util import findMainWindow
from smart import rs_path

class beamlineSynopticViewer(QWidget):

    def __init__(self, parent = None):
        super().__init__(parent = parent)
        #self.config_file = yaml_config_file
        self.composite_shape = None
        self.viewer_shape = None
        self.viewer_connection = {}
        self.set_parent()
        #self.init_viewer()

    def connect_slots_synoptic_viewer(self):
        pass
        #self.parent.pushButton_slit.clicked.connect(lambda: self.init_shape('slit'))
        #self.parent.pushButton_valve.clicked.connect(lambda: self.init_shape('valve'))

    def set_parent(self):
        self.parent = findMainWindow()

    def init_shape(self, which_composite = 'slit'):
        self.composite_shape = buildTools.build_composite_shape_from_yaml(self.config_file)[which_composite]
        self.composite_shape.updateSignal.connect(self.update_canvas)
        self.update()

    def detach_models(self):
        #not working this way, need a right solution in the future
        return
        if self.viewer_shape!=None:
            print('Detach models!')
            for each, shape in self.viewer_shape.items():
                if len(shape._models)!=0:
                    for key in shape.modelKeys:
                        shape._removeModelKey(key)

    def init_viewer(self):
        self.detach_models()
        config_file = str(rs_path / 'config' / (self.parent.comboBox_viewer_filename.currentText() + '.yaml'))
        which_viewer = self.parent.comboBox_viewer_obj_name.currentText()
        view_shape, view_connection = buildTools.build_view_from_yaml(config_file, self.size().width())
        self.viewer_shape, self.viewer_connection = view_shape[which_viewer], view_connection[which_viewer]
        for each_composite in self.viewer_shape.values():
            each_composite.updateSignal.connect(self.update_canvas)

    def _generate_connection(self):
        lines_draw_before = []
        lines_draw_after = []
        pen_lines_draw_before = []
        pen_lines_draw_after = []
        if len(self.viewer_connection) == 0:
            return lines_draw_before, lines_draw_after
        
        def _unpack_str(str_):
            composite_key, shape_ix, direction = str_.rsplit('.')
            return self.viewer_shape[composite_key].shapes[int(shape_ix)], direction
        
        def _make_qpen_from_txt(pen):
            pen_color = QColor(*pen['color'])
            pen_width = pen['width']
            pen_style = getattr(Qt,pen['ls'])
            return QPen(pen_color, pen_width, pen_style)
        
        for key, con_info in self.viewer_connection.items():
            shape_lf, anchor_lf = _unpack_str(key.rsplit('<=>')[0])
            shape_rg, anchor_rg = _unpack_str(key.rsplit('<=>')[1])
            pen = _make_qpen_from_txt(con_info['pen'])
            direct_connect = con_info['direct_connect']
            draw_after = con_info['draw_after']
            lines = buildTools.make_line_connection_btw_two_anchors(shapes = [shape_lf, shape_rg], anchors=[anchor_lf, anchor_rg], direct_connection=direct_connect)
            if draw_after:
                lines_draw_after.append(lines)
                pen_lines_draw_after.append(pen)
            else:
                lines_draw_before.append(lines)
                pen_lines_draw_before.append(pen)
        return lines_draw_before, lines_draw_after, pen_lines_draw_before, pen_lines_draw_after

    def scale_composite_shapes(self, sf = None):
        if sf==None:
            width = self.size().width()
            height = self.size().height()
            x_min, x_max, y_min, y_max = buildTools.calculate_boundary_for_combined_shapes(list(self.viewer_shape.values())[0].shapes)
            for composite_shape in self.viewer_shape.values():
                _x_min, _x_max, _y_min, _y_max = buildTools.calculate_boundary_for_combined_shapes(composite_shape.shapes)
                x_min = min([_x_min, x_min])
                x_max = max([_x_max, x_max])
                y_min = min([_y_min, y_min])
                y_max = max([_y_max, y_max])
            sf_width = width / (x_max - x_min)
            sf_height = height / (y_max - y_min)
            sf = min([sf_width, sf_height])
        for composite_shape in self.viewer_shape.values():
            composite_shape.scale(sf)
        self.update()

    def paintEvent(self, a0) -> None:
        qp = QPainter()
        qp.begin(self)
        # for each in self.shapes:                       
        if self.viewer_shape == None:
            return
        #make line connections
        if len(self.viewer_connection)!=0:
            lines_draw_before, lines_draw_after, pen_lines_draw_before, pen_lines_draw_after = self._generate_connection()
        else:
            lines_draw_before = []
            lines_draw_after = []
        #lines to be draw before
        for k, lines in enumerate(lines_draw_before):
            qp.setPen(pen_lines_draw_before[k])
            for i in range(len(lines)-1):
                pts = list(lines[i]) + list(lines[i+1])
                qp.drawLine(*pts)
        #draw shapes
        for composite_shape in self.viewer_shape.values():
            for each_shape in composite_shape.shapes:
                qp.resetTransform()
                each_shape.paint(qp)

        #lines to be draw after
        for k, lines in enumerate(lines_draw_after):
            qp.resetTransform()
            qp.setPen(pen_lines_draw_after[k])
            for i in range(len(lines)-1):
                pts = list(lines[i]) + list(lines[i+1])
                qp.drawLine(*pts)                
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