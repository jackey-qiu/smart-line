import numpy as np
import copy
from PyQt5.QtGui import QPaintEvent, QPainter, QPen, QColor
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtCore import pyqtSlot as Slot
from PyQt5.QtWidgets import QWidget
from taurus.qt.qtgui.base import TaurusBaseComponent
from ...widgets.shapes.shape_container import rectangle, shapeComposite, isocelesTriangle, buildTools, make_decoration_from_text
from ...widgets.shapes.callback_container import *
from ...widgets.shapes.customized_callbacks import *
from ....util.util import findMainWindow
from smart import rs_path
from magicgui import magicgui

line_pen = QPen(QColor(100,100,100), 2, Qt.DotLine)
line_pen_actived = QPen(QColor(255,0,0), 2, Qt.DotLine)

class beamlineSynopticViewer(QWidget):

    def __init__(self, parent = None):
        super().__init__(parent = parent)
        self.composite_shape = None
        self.viewer_shape = None
        self.viewer_connection = {}
        self.composite_obj_container = None
        self.config_file = None
        self.set_parent()

    def connect_slots_synoptic_viewer(self):
        pass

    def set_parent(self):
        self.parent = findMainWindow()

    def init_shape(self, which_composite = 'slit'):
        self.composite_shape = buildTools.build_composite_shape_from_yaml(self.config_file)[which_composite]
        self.composite_shape.updateSignal.connect(self.update_canvas)
        self.update()

    def init_viewer(self):
        #reset the class attribute first
        shapeComposite.model_str_list = []
        shapeComposite.modelKeys = [TaurusBaseComponent.MLIST]
        config_file = str(rs_path / 'config' / (self.parent.comboBox_viewer_filename.currentText() + '.yaml'))
        if self.config_file != config_file:
            self.config_file = config_file
            self.composite_obj_container = None
        which_viewer = self.parent.comboBox_viewer_obj_name.currentText()
        if self.composite_obj_container==None:
            view_shape, view_connection, self.composite_obj_container = buildTools.build_view_from_yaml(config_file, self.size().width(), which_viewer=which_viewer, composite_obj_container=self.composite_obj_container)
        else:
            view_shape, view_connection, _ = buildTools.build_view_from_yaml(config_file, self.size().width(), which_viewer=which_viewer, composite_obj_container=self.composite_obj_container)
        self.viewer_shape, self.viewer_connection = view_shape[which_viewer], view_connection[which_viewer]
        for each_composite in self.viewer_shape.values():
            each_composite.updateSignal.connect(self.update_canvas)
        self.parent.lines_draw_before, self.parent.lines_draw_after, \
        self.parent.pen_lines_draw_before, self.parent.pen_lines_draw_after, \
        self.parent.syringe_lines_container = self._generate_connection()

    def method_temp_outside(self, sigma_outside):
        @magicgui(auto_call=True,sigma={'max':10})
        def method_temp(sigma: float = sigma_outside):
            """Example class method."""
            #sigma = sigma_outside
            print(f"instance: sigma: {sigma}")
            #self.counter = self.counter + sigma
            self.sigma_temp = sigma
            return sigma
        return method_temp

    def update_connection(self):
        self.parent.lines_draw_before, self.parent.lines_draw_after, \
        self.parent.pen_lines_draw_before, self.parent.pen_lines_draw_after, \
        self.parent.syringe_lines_container = self._generate_connection()

    def _generate_connection(self):
        lines_draw_before = []
        lines_draw_after = []
        pen_lines_draw_before = []
        pen_lines_draw_after = []
        syringe_lines_container = {}
        if len(self.viewer_connection) == 0:
            return [],[],[],[],{}
        
        def _unpack_str(str_):
            
            composite_key, shape_ix, direction = str_.rsplit('.')
            return self.viewer_shape[composite_key].shapes[int(shape_ix)], direction, composite_key, int(shape_ix)
        
        def _make_qpen_from_txt(pen):
            pen_color = QColor(*pen['color'])
            pen_width = pen['width']
            pen_style = getattr(Qt,pen['ls'])
            return QPen(pen_color, pen_width, pen_style)
        for key, con_info in self.viewer_connection.items():
            nodes = key.rsplit('<=>')
            # print(nodes)
            #this way there could be any number of conections
            nodes_formated = [[nodes[i], nodes[i+1]] for i in range(len(nodes)-1)]
            for i, (str_lf, str_rg) in enumerate(nodes_formated):
                pen_dict = con_info['pen'][i] if type(con_info['pen'])==list else con_info['pen']
                pen = _make_qpen_from_txt(pen_dict)
                # print(anchor_lf, shape_lf.anchors)
                draw_after = con_info['draw_after'][i] if type(con_info['draw_after'])==list else con_info['draw_after']
                if str_rg == 'end':#a line from the anchor to the very end of screen
                    shape_lf, anchor_lf, composite_key_lf, shape_ix_lf = _unpack_str(str_lf)
                    if anchor_lf not in shape_lf.anchors:
                        if anchor_lf == 'dynamic_anchor':
                            dynamic_anchor_info = copy.deepcopy(con_info['dynamic_anchor_pars'][i]) if type(con_info['dynamic_anchor_pars'])==list else copy.deepcopy(con_info['dynamic_anchor_pars'])
                            side = dynamic_anchor_info['side'][0]
                            if side in shape_lf.dynamic_anchor:
                                pt_left = shape_lf.dynamic_anchor[side]
                                pt_right = [10000,pt_left[1]]#x is arbitrarily large number
                                lines = [pt_left, pt_right]
                            else:
                                continue
                        else:
                            continue
                    else:
                        pt_left = shape_lf.compute_anchor_pos_after_transformation(
                            anchor_lf, return_pos_only=True
                        )
                        pt_right = [10000,int(pt_left[1])]#x is arbitrarily large number
                        lines = [pt_left, pt_right]
                elif str_lf == 'end':#a line from the anchor to the very end of screen
                    shape_rg, anchor_rg, composite_key_rg, shape_ix_rg = _unpack_str(str_rg)
                    if anchor_rg not in shape_rg.anchors:
                        if anchor_rg == 'dynamic_anchor':
                            dynamic_anchor_info = copy.deepcopy(con_info['dynamic_anchor_pars'][i]) if type(con_info['dynamic_anchor_pars'])==list else copy.deepcopy(con_info['dynamic_anchor_pars'])
                            side = dynamic_anchor_info['side'][0]
                            if side in shape_rg.dynamic_anchor:
                                pt_right = shape_rg.dynamic_anchor[side]
                                pt_left = [0,pt_right[1]]#x is arbitrarily large number
                                lines = [pt_left, pt_right]
                            else:
                                continue
                        else:
                            continue
                    else:
                        pt_right = shape_rg.compute_anchor_pos_after_transformation(
                            anchor_rg, return_pos_only=True
                        )
                        pt_left = [0,int(pt_right[1])]#x is arbitrarily large number
                        lines = [pt_left, pt_right]
                else:
                    shape_lf, anchor_lf, composite_key_lf, shape_ix_lf = _unpack_str(str_lf)
                    shape_rg, anchor_rg, composite_key_rg, shape_ix_rg = _unpack_str(str_rg)
                    direct_connect = con_info['direct_connect'][i] if type(con_info['direct_connect'])==list else con_info['direct_connect']
                    if anchor_rg=='dynamic_anchor':
                        dynamic_anchor_info = copy.deepcopy(con_info['dynamic_anchor_pars'][i]) if type(con_info['dynamic_anchor_pars'])==list else copy.deepcopy(con_info['dynamic_anchor_pars'])
                        if type(dynamic_anchor_info['angle'])==str:
                            ang_str = dynamic_anchor_info['angle'].replace('shape', 'shape_lf')
                            dynamic_anchor_info['angle'] = eval(ang_str)
                        lines = buildTools.make_line_connection_btw_two_anchors(shapes = [shape_lf, shape_rg], anchors=[anchor_lf, anchor_rg], direct_connection=direct_connect, **dynamic_anchor_info)
                    else:
                        lines = buildTools.make_line_connection_btw_two_anchors(shapes = [shape_lf, shape_rg], anchors=[anchor_lf, anchor_rg], direct_connection=direct_connect)
                    if len(lines)==0:
                        continue   
                if draw_after:
                    lines_draw_after.append(lines)
                    pen_lines_draw_after.append(pen)
                else:
                    lines_draw_before.append(lines)
                    pen_lines_draw_before.append(pen)
        return lines_draw_before, lines_draw_after, pen_lines_draw_before, pen_lines_draw_after, syringe_lines_container

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
        qp.setRenderHint(QPainter.Antialiasing, True)
        qp.setRenderHint(QPainter.HighQualityAntialiasing, True)
        # for each in self.shapes:                       
        if self.viewer_shape == None:
            return
        #first update extra_offset par
        extra_offset = [0,0]
        for composite_shape in self.viewer_shape.values():
            pass
            #for each_shape in composite_shape.shapes:
            #    each_shape.transformation['translate_offset'] = extra_offset
            # composite_shape.ref_shape.transformation['translate_offset'] = extra_offset
            # composite_shape.build_composite()
                #each_shape.paint(qp, extra_offset)
            #extra_offset = np.array(extra_offset) + [0,composite_shape.beam_height_offset]            
        self.update_connection()
        #make line connections
        for line_set in self.parent.syringe_lines_container:
            for shape_ix in self.parent.syringe_lines_container[line_set]:
                lines, draw = self.parent.syringe_lines_container[line_set][shape_ix]
                if draw:
                    for i in range(len(lines)-1):
                        pts = list(lines[i]) + list(lines[i+1])
                        if hasattr(self.parent, "exchange_pair"):
                            if (self.parent.exchange_pair==1 and line_set in ["syringe","syringe3"]) or \
                               (self.parent.exchange_pair==2 and line_set in ["syringe2","syringe4"]):
                                qp.setPen(line_pen_actived)
                                qp.drawLine(*pts)
                            else:
                                qp.setPen(line_pen)
                                qp.drawLine(*pts)
                        else:
                            qp.setPen(line_pen)
                            qp.drawLine(*pts)
        #lines to be draw before
        for k, lines in enumerate(self.parent.lines_draw_before):
            qp.setPen(self.parent.pen_lines_draw_before[k])
            for i in range(len(lines)-1):
                pts = list(lines[i]) + list(lines[i+1])
                pts = [int(each) for each in pts]
                qp.drawLine(*pts)
        #draw shapes
        for composite_shape in self.viewer_shape.values():
            for each_shape in composite_shape.shapes:
                qp.resetTransform()
                each_shape.paint(qp)
        #lines to be draw after
        for k, lines in enumerate(self.parent.lines_draw_after):
            qp.resetTransform()
            qp.setPen(self.parent.pen_lines_draw_after[k])
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
        self.update()

    def mousePressEvent(self, event):
        x, y = event.x(), event.y()
        '''
        if event.button() == Qt.RightButton:
            #set the title
            mggui_func = self.method_temp_outside(0.2)
            mggui_func.native.setWindowTitle('method_temp')
            pos = self.parentWidget().mapToGlobal(self.pos())
            mggui_func.native.move(pos.x()+x, pos.y()+y)
            mggui_func.show(run=True)
            return
        '''
        if self.viewer_shape == None:
            return
        for composite_shape in self.viewer_shape.values():
            for i, each_shape in enumerate(composite_shape.shapes):
                if each_shape.cursor_pos_checker(x, y) and each_shape.clickable and each_shape.show:
                    if event.button() == Qt.LeftButton:
                        composite_shape.uponLeftMouseClicked(i)
                        return
                    elif event.button() == Qt.RightButton:
                        mggui_func = composite_shape.uponRightMouseClicked(i)
                        if mggui_func==None:
                            return
                        # if hasattr(mggui_func, 'scan') and mggui_func.scan.value.value:
                            # mggui_func.call_button.text = 'run scan'
                        # else:
                            # mggui_func.call_button.text = 'move'
                        mggui_func.native.setWindowTitle('setup pars')
                        pos = self.parentWidget().mapToGlobal(self.pos())
                        mggui_func.native.move(pos.x()+x, pos.y()+y)
                        mggui_func.show(run=True)                        
                        return