from PyQt5.QtGui import QPaintEvent, QPainter, QPen, QBrush, QColor, QFont, QPolygonF, QCursor, QPainterPath,QTransform
from PyQt5.QtWidgets import QWidget
from taurus.qt.qtgui.base import TaurusBaseComponent
from PyQt5.QtCore import Qt, QPointF, pyqtSignal, pyqtSlot
from PyQt5.QtCore import QTimer
import numpy as np
import copy
import math
import time
from dataclasses import dataclass
from smart.util.geometry_transformation import rotate_multiple_points, angle_between

DECORATION_UPON_CURSOR_ON = {'pen': {'color': (255, 255, 0), 'width': 3, 'ls': 'DotLine'}, 'brush': {'color': (0, 0, 255)}} 
DECORATION_UPON_CURSOR_OFF = {'pen': {'color': (255, 0, 0), 'width': 3, 'ls': 'SolidLine'}, 'brush': {'color': (0, 0, 255)}}

DECORATION_TEXT_DEFAULT = {'font_size': 8, 'text_color': (255,255,255), 'alignment': 'AlignCenter', 'padding': 0}

def make_decoration_from_text(dec = {'pen': {'color': (255, 255, 0), 'width': 3, 'ls': 'DotLine'}, 'brush': {'color': (0, 0, 255)}}):

    pen_color = QColor(*dec['pen']['color'])
    pen_width = dec['pen']['width']
    pen_style = getattr(Qt,dec['pen']['ls'])
    qpen = QPen(pen_color, pen_width, pen_style)
    brush_color = QColor(*dec['brush']['color'])
    qbrush = QBrush(brush_color)
    return {'pen': qpen, 'brush': qbrush}

class baseShape(object):

    def __init__(self, dim, decoration_cursor_off = DECORATION_UPON_CURSOR_OFF, decoration_cursor_on = DECORATION_UPON_CURSOR_ON , rotation_center=None, transformation={'rotate':0, 'translate':(0,0), 'scale':1}, text_decoration = DECORATION_TEXT_DEFAULT, lables = {'text':[], 'anchor':[],'decoration':None}):
        #super().__init__(parent = parent)
        self._dim_pars = dim
        self._dim_pars_origin = dim
        # self.cen = self.compute_center_from_dim()
        self._rotcenter = rotation_center
        self._decoration = copy.deepcopy(decoration_cursor_off)
        self._decoration_cursor_on = copy.deepcopy(decoration_cursor_on)
        self._decoration_cursor_off = copy.deepcopy(decoration_cursor_off)
        self.anchors = {}
        self._transformation = transformation
        self._text_decoration = copy.deepcopy(text_decoration)
        self._labels = copy.deepcopy(lables)
        self.show = True

    def show_shape(self):
        self.show = True

    def hide_shape(self):
        self.show = False

    @property
    def labels(self):
        return self._labels
    
    @labels.setter
    def labels(self, labels):
        assert type(labels)==dict, 'Need dictionary for labels'
        assert 'text' in labels and 'anchor' in labels, 'need text and anchor key at least'
        assert type(labels['text'])==list and type(labels['anchor'])==list, 'the value of text and anchor must be a list'
        assert len(labels['text'])==len(labels['anchor']), 'The dim of text and anchor must be equal'
        if len(labels['text'])!=0:
            self._labels.update(labels)

    @property
    def text_decoration(self):
        return self._text_decoration
    
    @text_decoration.setter
    def text_decoration(self, decoration):
        self._text_decoration.update(decoration)

    @property
    def dim_pars(self):
        return self._dim_pars
    
    @dim_pars.setter
    def dim_pars(self, new_dim):
        self._dim_pars = new_dim
        self._dim_pars_origin = new_dim

    @property
    def rot_center(self):
        if self._rotcenter == None:
            self._rotcenter = [int(each) for each in self.compute_center_from_dim(False)]
        return self._rotcenter
    
    @rot_center.setter
    def rot_center(self, rot_center):
        if type(rot_center)==tuple or type(rot_center)==list or type(rot_center)==np.ndarray:
            self._rotcenter = [int(each) for each in rot_center]
        elif rot_center==None:
            self._rotcenter = [int(each) for each in self.compute_center_from_dim(False)]

    @property
    def decoration(self):
        return self._decoration
    
    @decoration.setter
    def decoration(self, decoration):
        self._decoration.update(decoration)

    @property
    def decoration_cursor_on(self):
        return self._decoration_cursor_on
    
    @decoration_cursor_on.setter
    def decoration_cursor_on(self, decoration):
        self._decoration_cursor_on.update(decoration)

    @property
    def decoration_cursor_off(self):
        return self._decoration_cursor_off
    
    @decoration_cursor_off.setter
    def decoration_cursor_off(self, decoration):
        self._decoration_cursor_off.update(decoration)

    @property
    def transformation(self):
        return self._transformation
    
    @transformation.setter
    def transformation(self, transformation):
        assert isinstance(transformation, dict), 'wrong format of transformation'
        self._transformation.update(transformation)
        # self.calculate_shape()

    def compute_center_from_dim(self, apply_translate = True):
        raise NotImplementedError

    def make_anchors(self, *args, **kwargs):
        raise NotImplementedError
    
    def calculate_shape(self):
        raise NotImplementedError
    
    def calculate_anchor_orientation(self):
        raise NotImplementedError

    def calculate_shape_boundary(self):
        raise NotImplementedError

    def check_pos(self, x, y):
        raise NotImplementedError

    def text_label(self, qp):
        raise NotImplementedError

    def get_proper_extention_dir_for_one_anchor(self, key):
        possible_dirs = []
        possible_dirs_offset = []
        anchor_pos, cen, _ = self.compute_anchor_pos_after_transformation(key, return_pos_only=False)
        orientations = {'left': np.array([-1, 0]),
                        'right': np.array([1, 0]),
                        'top': np.array([0, -1]),
                        'bottom': np.array([0, 1]),
                        }
        for each, value in orientations.items():
            if not self.check_pos(*(np.array(anchor_pos) + value)):
                possible_dirs.append(each)
                possible_dirs_offset.append(value)
        if len(possible_dirs)==0:
            return None
        else:
            ix_shortest = np.argmin(np.linalg.norm(cen - (np.array(anchor_pos) + np.array(possible_dirs_offset))))
            return possible_dirs[ix_shortest]
    
    def compute_anchor_pos_after_transformation(self, key, return_pos_only = False, ref_anchor = None):
        #calculate anchor pos for key after transformation
        #ref_anchor in [None, 'left', 'right', 'top', 'bottom']
        ref_anchor_offset = {'left': np.array([-1, 0]),
                            'right': np.array([1, 0]),
                            'top': np.array([0, -1]),
                            'bottom': np.array([0, 1]),
                            }
        ref_anchor_dir = None
        if ref_anchor!=None:
            ref_anchor_dir = ref_anchor_offset[ref_anchor]
        
        orientation = key
        or_len = self.calculate_orientation_length(orientation, ref_anchor = ref_anchor)
        cen = self.compute_center_from_dim(apply_translate=True)
        rotate_angle = self.transformation['rotate'] if 'rotate' in self.transformation else 0
        anchor = None
        if orientation == 'top':
            anchor = np.array(cen) + [0, -or_len]
            ref_anchor = cen
        elif orientation == 'bottom':
            anchor = np.array(cen) + [0, or_len]
            ref_anchor = cen
        elif orientation == 'left':
            anchor = np.array(cen) + [-or_len, 0]
            ref_anchor = cen
        elif orientation == 'right':
            anchor = np.array(cen) + [or_len, 0]
            ref_anchor = cen
        elif orientation == 'cen':
            anchor = np.array(cen)
            if ref_anchor!=None:
                # ref_anchor = anchor - ref_anchor_offset[ref_anchor_dir]
                ref_anchor = anchor - ref_anchor_dir
            else:
                ref_anchor = anchor - ref_anchor_offset['left']#by default
        else:
            if orientation in self.anchors:
                anchor = self.anchors[orientation]
                if ref_anchor!=None:
                    # ref_anchor = anchor - ref_anchor_offset[ref_anchor_dir]
                    ref_anchor = anchor - ref_anchor_dir
                else:
                    ref_anchor = cen
            else:
                raise KeyError('Not the right key for orientation')
        rot_center = np.array(self.rot_center) + np.array(self.transformation['translate'])
        cen_, anchor_, ref_anchor_ = rotate_multiple_points([cen, anchor, ref_anchor], rot_center, rotate_angle)
        #return cen and anchor pos and or_len after transformation
        if return_pos_only:
            return anchor_
        else:
            # return anchor_, cen_, or_len
            return anchor_, ref_anchor_, or_len
    
    def cursor_pos_checker(self, x, y):
        cursor_inside_shape = self.check_pos(x, y)
        if cursor_inside_shape:
            self.decoration = copy.deepcopy(self.decoration_cursor_on)
        else:
            self.decoration  = copy.deepcopy(self.decoration_cursor_off)
    
    def apply_transform(self,qp):
        #translate_values = self.transformation['translate'] if 'translate' in self.transformation else (0,0)
        rotate_angle = self.transformation['rotate'] if 'rotate' in self.transformation else 0
        rot_center = self.rot_center
        qp.translate(*rot_center)
        qp.translate(*self.transformation['translate'])
        qp.rotate(rotate_angle)
        qp.translate(*[-each for each in rot_center])
        return qp
    
    def paint(self, qp) -> None:
        if not self.show:
            return
        decoration = make_decoration_from_text(self.decoration)
        qp.setPen(decoration['pen'])
        qp.setBrush(decoration['brush'])
        self.draw_shape(qp)

    def draw_shape(self, qp):
        raise NotImplementedError
    
    def calculate_orientation_vector(self, orientation = 'top', ref_anchor = None):
        anchor_, cen_, or_len = self.compute_anchor_pos_after_transformation(orientation,return_pos_only=False, ref_anchor=ref_anchor)
        return cen_, (anchor_ - cen_)/or_len
        
    def translate(self, v):
        self.transformation['translate'] = v

    def rotate(self, angle):
        self.transformation['rotate'] = angle

    def scale(self, sf):
        raise NotImplementedError

    def reset(self):
        self.transformation.update({'rotate': 0, 'translate': [0, 0]})

class rectangle(baseShape):
    def __init__(self, dim = [700,100,40,80], rotation_center = None, decoration_cursor_off=DECORATION_UPON_CURSOR_OFF, decoration_cursor_on =DECORATION_UPON_CURSOR_ON, \
                 transformation={'rotate':45, 'translate':(0,0), 'scale': 1}, text_decoration = DECORATION_TEXT_DEFAULT, lables = {'text':[], 'anchor':[],'decoration':None}):

        super().__init__(dim = dim, rotation_center=rotation_center, decoration_cursor_off=decoration_cursor_off, decoration_cursor_on= decoration_cursor_on, transformation=transformation, text_decoration=text_decoration, lables=lables)

    def scale(self, sf):
        self.dim_pars = (np.array(self.dim_pars)*[1,1,sf/self.transformation['scale'],sf/self.transformation['scale']]).astype(int)
        self.transformation['scale'] = sf

    def draw_shape(self, qp):
        qp = self.apply_transform(qp)
        qp.drawRect(*np.array(self.dim_pars).astype(int))
        self.text_label(qp)

    def text_label(self, qp):
        labels = self.labels
        decoration = self.text_decoration 
        cen = self.compute_center_from_dim(False)
        _, _, w, h = self.dim_pars
        for i, text in enumerate(labels['text']):
            x, y = cen
            anchor = labels['anchor'][i]
            if labels['decoration'] == None:
                decoration = self.text_decoration
            else:
                if type(labels['decoration'])==list and len(labels['decoration'])==len(labels['text']):
                    decoration = labels['decoration'][i]
                else:
                    decoration = self.text_decoration
            alignment = decoration['alignment']
            padding = decoration['padding']
            text_color = decoration['text_color']
            font_size = decoration['font_size']
            if anchor == 'left':
                x = x - w/2 - padding
            elif anchor == 'right':
                x = x + w/2 + padding
            elif anchor == 'top':
                y = y - h/2 - padding
            elif anchor == 'bottom':
                y = y + h/2 + padding
            elif anchor == 'center':
                x = x + padding
                y = y + padding
            else:
                if anchor in self.anchors:
                    x, y = self.anchors[anchor]
            qp.setPen(QColor(*text_color))
            qp.setFont(QFont('Decorative', font_size))
            x, y, width, height = self.dim_pars
            qp.drawText(int(x), int(y), int(width), int(height), getattr(Qt, alignment), text)

    def calculate_shape_boundary(self):
        x, y, w, h = self.dim_pars
        four_corners = [[x,y], [x+w,y],[x, y+h], [x+w, y+h]]
        four_corners = [np.array(each) + np.array(self.transformation['translate']) for each in four_corners]
        rot_center = np.array(self.rot_center) + np.array(self.transformation['translate'])
        four_corners = rotate_multiple_points(four_corners, rot_center, self.transformation['rotate'])
        #return x_min, x_max, y_min, y_max
        return int(four_corners[:,0].min()), int(four_corners[:,0].max()), int(four_corners[:,1].min()), int(four_corners[:,1].max())

    def compute_center_from_dim(self, apply_translate = True):
        x, y, w, h = self.dim_pars
        if apply_translate:
            return x+w/2 + self.transformation['translate'][0], y+h/2+self.transformation['translate'][1]
        else:
            return x+w/2, y+h/2
    
    def make_anchors(self, num_of_anchors_on_each_side = 4, include_corner = True):
        #num_of_anchors_on_each_side: exclude corners

        w, h = self.dim_pars[2:]
        if not include_corner:
            w_step, h_step = w/(num_of_anchors_on_each_side+1), h/(num_of_anchors_on_each_side+1)
        else:
            assert num_of_anchors_on_each_side>2, 'At least two achors at each edge'
            w_step, h_step = w/(num_of_anchors_on_each_side-1), h/(num_of_anchors_on_each_side-1)

        top_left_coord = np.array(self.dim_pars[0:2])
        bottom_right_coord = top_left_coord + np.array([w, h]) 
        anchors = {}
        for i in range(num_of_anchors_on_each_side):
            if not include_corner:
                anchors[f'anchor_top_{i}'] = top_left_coord + [(i+1)*w_step, 0]
                anchors[f'anchor_left_{i}'] = top_left_coord + [0, (i+1)*h_step]
                anchors[f'anchor_bottom_{i}'] = bottom_right_coord + [-(i+1)*w_step, 0]
                anchors[f'anchor_right_{i}'] = bottom_right_coord + [0, -(i+1)*h_step]
            else:
                anchors[f'anchor_top_{i}'] = top_left_coord + [i*w_step, 0]
                anchors[f'anchor_left_{i}'] = top_left_coord + [0, i*h_step]
                anchors[f'anchor_bottom_{i}'] = bottom_right_coord + [-i*w_step, 0]
                anchors[f'anchor_right_{i}'] = bottom_right_coord + [0, -i*h_step]
        for each in anchors:
            anchors[each] = anchors[each] + np.array(self.transformation['translate'])
        self.anchors = anchors

    def calculate_orientation_length(self, orientation = 'top', ref_anchor = None):
        if orientation == 'cen':
            return 1
        w, h = np.array(self.dim_pars[2:])
        if orientation in ['top', 'bottom']:
            return h/2
        elif orientation in ['left', 'right']:
            return w/2
        else:
            if orientation in self.anchors:
                if ref_anchor == None:
                    return np.linalg.norm(np.array(self.anchors[orientation]) - np.array(self.compute_center_from_dim(apply_translate=False)))
                else:
                    return 1
            else:
                raise KeyError('No such orientation key!')
        
    def check_pos(self, x, y):
        ox, oy, w, h = np.array(self.dim_pars)
        pos_ = rotate_multiple_points([(x, y)], np.array(self.rot_center) + np.array(self.transformation['translate']), -self.transformation['rotate'])
        pos_ = np.array(pos_) - np.array(self.transformation['translate'])
        x_, y_ = pos_
        if (ox <= x_ <= ox + w) and (oy <= y_ <= oy + h):
            return True
        else:
            return False
     

class circle(baseShape):
    def __init__(self, dim = [100,100,40], rotation_center = None, decoration_cursor_off=DECORATION_UPON_CURSOR_OFF, decoration_cursor_on =DECORATION_UPON_CURSOR_ON, \
                 transformation={'rotate':0, 'translate':(0,0), 'scale': 1}, text_decoration = DECORATION_TEXT_DEFAULT, lables = {'text':[], 'anchor':[],'decoration':None}):

        super().__init__(dim = dim, rotation_center=rotation_center, decoration_cursor_off=decoration_cursor_off, decoration_cursor_on= decoration_cursor_on, transformation=transformation, text_decoration=text_decoration, lables=lables)
    
    def scale(self, sf):
        self.dim_pars = list((np.array(self.dim_pars)*np.array([1,1,sf/self.transformation['scale']])).astype(int))
        self.transformation['scale'] = sf

    def draw_shape(self, qp):
        qp = self.apply_transform(qp)
        qp.drawEllipse(*(self.dim_pars + [self.dim_pars[-1]]))
        self.text_label(qp)

    def text_label(self, qp):
        labels = self.labels
        decoration = self.text_decoration 
        cen = self.compute_center_from_dim(False)
        r = self.dim_pars[-1]/2
        for i, text in enumerate(labels['text']):
            x, y = cen
            anchor = labels['anchor'][i]
            if labels['decoration'] == None:
                decoration = self.text_decoration
            else:
                if type(labels['decoration'])==list and len(labels['decoration'])==len(labels['text']):
                    decoration = labels['decoration'][i]
                else:
                    decoration = self.text_decoration
            alignment = decoration['alignment']
            padding = decoration['padding']
            text_color = decoration['text_color']
            font_size = decoration['font_size']
            if anchor == 'left':
                x = x - r
                x = x - padding
            elif anchor == 'right':
                x = x + r
                x = x + padding
            elif anchor == 'top':
                y = y - r
                y = y - padding
            elif anchor == 'bottom':
                y = y + r
                y = y + padding
            elif anchor == 'center':
                x, y = x, y
            else:
                if anchor in self.anchors:
                    x, y = self.anchors[anchor]
            qp.setPen(QColor(*text_color))
            qp.setFont(QFont('Decorative', font_size))
            qp.drawText(int(x), int(y), 100, 20, getattr(Qt, alignment), text)

    def calculate_shape_boundary(self):
        cen = np.array(self.compute_center_from_dim(False))
        r = self.dim_pars[-1]/2
        four_corners = [cen + each for each in [[r, 0], [-r, 0], [0, r], [0, -r]]]
        four_corners = [np.array(each) + np.array(self.transformation['translate']) for each in four_corners]
        rot_center = np.array(self.rot_center) + np.array(self.transformation['translate'])
        four_corners = rotate_multiple_points(four_corners, rot_center, self.transformation['rotate'])
        #return x_min, x_max, y_min, y_max
        return int(four_corners[:,0].min()), int(four_corners[:,0].max()), int(four_corners[:,1].min()), int(four_corners[:,1].max())

    def compute_center_from_dim(self, apply_translate = True):
        x, y, R = self.dim_pars
        x, y = x+R/2, y+R/2
        if apply_translate:
            return x + self.transformation['translate'][0], y + self.transformation['translate'][1]
        else:
            return x, y
        
    def make_anchors(self, num_of_anchors = 4):
        #num_of_anchors_on_each_side: exclude corners
        cen = np.array(self.compute_center_from_dim(False))
        ang_step = math.radians(360/num_of_anchors)
        anchors = {}
        for i in range(num_of_anchors):
            dx, dy = math.cos(ang_step*i), -math.sin(ang_step*i)
            anchors[f'anchor_{i}'] = cen + [dx, dy] + np.array(self.transformation['translate'])
        self.anchors = anchors

    def calculate_orientation_length(self, orientation = 'top', ref_anchor = None):
        if orientation == 'cen':
            return 1
        else:
            return self.dim_pars[-1]/2

    def check_pos(self, x, y):
        cen = np.array(self.compute_center_from_dim(False))
        r = self.dim_pars[-1]/2
        p1, p2, p3, p4 = [cen + each for each in [[r, 0], [-r, 0], [0, r], [0, -r]]]
        pos_ = rotate_multiple_points([(x, y)], np.array(self.rot_center) + np.array(self.transformation['translate']), -self.transformation['rotate'])
        pos_ = np.array(pos_) - np.array(self.transformation['translate'])
        x_, y_ = pos_
        if (p2[0] <= x_ <= p1[0]) and (p4[1] <= y_ <= p3[1]):
            return True
        else:
            return False

class isocelesTriangle(baseShape):
    def __init__(self, dim = [100,100,40,60], rotation_center = None, decoration_cursor_off=DECORATION_UPON_CURSOR_OFF, decoration_cursor_on =DECORATION_UPON_CURSOR_ON, \
                 transformation={'rotate':0, 'translate':(0,0), 'scale': 1}, text_decoration = DECORATION_TEXT_DEFAULT, lables = {'text':[], 'anchor':[],'decoration':None}):

        super().__init__(dim = dim, rotation_center=rotation_center, decoration_cursor_off=decoration_cursor_off, decoration_cursor_on= decoration_cursor_on, transformation=transformation, text_decoration=text_decoration, lables=lables)
    
    def scale(self, sf):
        self.dim_pars = (np.array(self.dim_pars)*[1,1,sf/self.transformation['scale'],1]).astype(int)
        self.transformation['scale'] = sf

    def _cal_corner_point_coordinates(self, return_type_is_qpointF = True):
        ang = math.radians(self.dim_pars[-1])/2
        edge_lenth = self.dim_pars[-2]
        dx = edge_lenth * math.sin(ang)
        dy = edge_lenth * math.cos(ang)
        point1 = (np.array(self.dim_pars[0:2])).astype(int)
        point2 = (np.array(self.dim_pars[0:2]) + np.array([-dx, dy])).astype(int)
        point3 = (np.array(self.dim_pars[0:2]) + np.array([dx, dy])).astype(int)
        if return_type_is_qpointF:
            return QPointF(*point1), QPointF(*point2), QPointF(*point3)
        else:
            return point1, point2, point3

    def draw_shape(self, qp):
        qp = self.apply_transform(qp)
        point1, point2, point3 = self._cal_corner_point_coordinates()
        polygon = QPolygonF()
        polygon.append(point1)
        polygon.append(point2)
        polygon.append(point3)
        qp.drawPolygon(polygon)
        self.text_label(qp)

    def text_label(self, qp):
        labels = self.labels
        decoration = self.text_decoration 
        point1, point2, point3 = self._cal_corner_point_coordinates(False)
        for i, text in enumerate(labels['text']):
            anchor = labels['anchor'][i]
            if labels['decoration'] == None:
                decoration = self.text_decoration
            else:
                if type(labels['decoration'])==list and len(labels['decoration'])==len(labels['text']):
                    decoration = labels['decoration'][i]
                else:
                    decoration = self.text_decoration
            alignment = decoration['alignment']
            padding = decoration['padding']
            text_color = decoration['text_color']
            font_size = decoration['font_size']
            if anchor == 'left':
                x, y = point2
                x = x - padding
            elif anchor == 'right':
                x, y = point3
                x = x + padding
            elif anchor == 'top':
                x, y = point1
                y = y - padding
            elif anchor == 'bottom':
                x, y = (point2 + point3)/2
                y = y + padding
            elif anchor == 'center':
                x, y = (point2 + point3)/2
                y = y - abs(point1[1] - y)/2
            else:
                if anchor in self.anchors:
                    x, y = self.anchors[anchor]
            qp.setPen(QColor(*text_color))
            qp.setFont(QFont('Decorative', font_size))
            qp.drawText(int(x), int(y), 100, 20, getattr(Qt, alignment), text)

    def calculate_shape_boundary(self):
        three_corners = self._cal_corner_point_coordinates(False)
        three_corners = [np.array(each) + np.array(self.transformation['translate']) for each in three_corners]
        rot_center = np.array(self.rot_center) + np.array(self.transformation['translate'])
        three_corners = rotate_multiple_points(three_corners, rot_center, self.transformation['rotate'])
        #return x_min, x_max, y_min, y_max
        return int(three_corners[:,0].min()), int(three_corners[:,0].max()), int(three_corners[:,1].min()), int(three_corners[:,1].max())

    def compute_center_from_dim(self, apply_translate = True):
        x, y, edge, ang = self.dim_pars
        p1, p2, p3 = self._cal_corner_point_coordinates(False)
        r = edge**2/2/abs(p3[1]-p1[1])
        #geometry rot center
        x, y = np.array(p1) + [0, r]
        if apply_translate:
            return x + self.transformation['translate'][0], y + self.transformation['translate'][1]
        else:
            return x, y

    def make_anchors(self, num_of_anchors_on_each_side = 4, include_corner = True):
        #num_of_anchors_on_each_side: exclude corners

        edge, ang = self.dim_pars[2:]
        ang = math.radians(ang/2)
        bottom_edge = edge * math.sin(ang) *2
        height = edge * math.cos(ang)
        if not include_corner:
            w_step, h_step = bottom_edge/(num_of_anchors_on_each_side+1), height/(num_of_anchors_on_each_side+1)
        else:
            assert num_of_anchors_on_each_side>2, 'At least two achors at each edge'
            w_step, h_step = bottom_edge/(num_of_anchors_on_each_side-1), height/(num_of_anchors_on_each_side-1)

        p1, p2, p3 = self._cal_corner_point_coordinates(False)
        anchors = {}
        for i in range(num_of_anchors_on_each_side):
            if not include_corner:
                anchors[f'anchor_left_{i}'] = np.array(p1) + [-(i+1)*h_step*math.tan(ang), (i+1)*h_step]
                anchors[f'anchor_bottom_{i}'] = np.array(p2) + [(i+1)*w_step, 0]
                anchors[f'anchor_right_{i}'] = np.array(p1) + [(i+1)*h_step*math.tan(ang), (i+1)*h_step]
            else:
                anchors[f'anchor_left_{i}'] = np.array(p1) + [-i*h_step*math.tan(ang), i*h_step]
                anchors[f'anchor_bottom_{i}'] = np.array(p2) + [i*w_step, 0]
                anchors[f'anchor_right_{i}'] = np.array(p1) + [i*h_step*math.tan(ang), i*h_step]                
        for each in anchors:
            anchors[each] = anchors[each] + np.array(self.transformation['translate'])
        self.anchors = anchors

    def calculate_orientation_length(self, orientation = 'top', ref_anchor = None):
        if orientation == 'cen':
            return 1
        cen = self.compute_center_from_dim(False)
        p1, p2, p3 = self._cal_corner_point_coordinates(False)
        w, h = np.array(self.dim_pars[2:])
        if orientation=='top':
            return abs(cen[1] - p1[1])
        elif orientation == 'bottom':
            return abs(cen[1] - p2[1])
        elif orientation in ['left', 'right']:
            return abs(cen[0] - p1[0])
        else:
            if orientation in self.anchors:
                if ref_anchor == None:
                    return np.linalg.norm(np.array(self.anchors[orientation]) - np.array(self.compute_center_from_dim(apply_translate=False)))
                else:
                    return 1
            else:
                raise KeyError('No such orientation key!')

    def check_pos(self, x, y):
        p1, p2, p3 = self._cal_corner_point_coordinates(False)
        pos_ = rotate_multiple_points([(x, y)], np.array(self.rot_center) + np.array(self.transformation['translate']), -self.transformation['rotate'])
        pos_ = np.array(pos_) - np.array(self.transformation['translate'])
        x_, y_ = pos_
        if (p2[0] <= x_ <= p3[0]) and (p1[1] <= y_ <= p2[1]):
            return True
        else:
            return False

class line(baseShape):
    pass

class ellipse(baseShape):
    pass

class pie(baseShape):
    pass
    
class buildObject(object):

    def __init__(self, shape_config, qpainter):
        self.shape_config = shape_config
        self.shape_info = {}
        self.qpainer = qpainter
        self.unpack_shape_info()

    def unpack_shape_info(self):
        pass

    def paint_all_shapes(self):
        self.build_shapes()
        self.qpainter.begin(self)
        for each in self.shape_info:
            paint_api, paint_pars, paint_decoration = self.shape_info[each]
            self.qpainer.setPen(paint_decoration['pen'])
            self.qpainer.setBrush(paint_decoration['brush'])
            getattr(self.qpainer, paint_api)(*paint_pars)
        self.qpainter.end(self)

    def build_shapes(self):
        pass

class shapeComposite(TaurusBaseComponent):

    modelKeys = [TaurusBaseComponent.MLIST]

    def __init__(self, shapes, anchor_args=None, alignment_pattern=None, connection_pattern = None, ref_shape_index = None, model_index_list = []):
        #connection_patter = {'shapes':[[0,1],[1,2]], 'anchors':[['left','top'],['right', 'bottom']]}
        #alignment_patter = {'shapes':[[0,1],[1,2]], 'anchors':[['left','top'],['right', 'bottom']]}
        TaurusBaseComponent.__init__(self)
        self._shapes = copy.deepcopy(shapes)
        self._model_shape_index_list = model_index_list
        self._callbacks_upon_model_change = []
        self._callbacks_upon_left_mouseclick = []
        self.ref_shape = self.shapes[ref_shape_index] if ref_shape_index!=None else self.shapes[0]
        self.anchor_args = anchor_args
        self.make_anchors()
        self.alignment = alignment_pattern
        self.connection = connection_pattern
        self.lines = []
        self.build_composite()

    @property
    def shapes(self):
        return self._shapes
    
    @property
    def model_shape_index_list(self):
        return self._model_shape_index_list
    
    @model_shape_index_list.setter
    def model_shape_index_list(self, model_shape_index_list):
        shapes_num = len(self.shapes)
        assert type(model_shape_index_list)==list, 'please give a list of model shape index'
        for each in model_shape_index_list:
            assert type(each)==int and each<shapes_num, 'index must be integer and smaller than the num of total shape in the composite obj'
        self._model_shape_index_list = model_shape_index_list

    def make_anchors(self):
        if self.anchor_args==None:
            return
        for shape, arg in zip(self.shapes, self.anchor_args):
            shape.make_anchors(arg)

    def build_composite(self):
        self.align_shapes()
        self.make_line_connection()

    def align_shapes(self):
        if self.alignment==None:
            return
        shape_index = self.alignment['shapes']
        anchors = self.alignment['anchors']
        gaps = self.alignment['gaps']
        ref_anchors = self.alignment['ref_anchors']
        assert len(shape_index) == len(anchors), "Dimension of shape and anchors does not match!"
        for shapes_, anchors_, gap_, ref_anchors_ in zip(shape_index, anchors, gaps, ref_anchors):
            ref_shape, target_shape, *_ = [self.shapes[each] for each in shapes_]
            buildTools.align_two_shapes(ref_shape, target_shape, anchors_, gap_, ref_anchors_)

    def make_line_connection(self):
        if self.lines == None:
            return
        self.lines = []
        shape_index = self.connection['shapes']
        anchors = self.connection['anchors']
        connect_types = self.connection.get('connect_types', [False]*len(anchors))
        assert len(shape_index) == len(anchors), "Dimension of shape and anchors does not match!"
        for shapes_, anchors_, connect_ in zip(shape_index, anchors, connect_types):
            shapes = [self.shapes[each] for each in shapes_]
            lines = buildTools.make_line_connection_btw_two_anchors(shapes, anchors_, direct_connection=connect_)
            self.lines.append(lines)

    def translate(self, vec):
        self.ref_shape.translate(vec)
        self.build_composite()

    def rotate(self, ang):
        self.ref_shape.rotate(ang)
        self.build_composite()

    def scale(self, sf):
        for shape in self.shapes:
            shape.reset()
            shape.scale(sf)
        #update anchors first

        self.make_anchors()
        self.build_composite()
    
    def change_upon_model_change(self, callback_pars):
        #update _callbacks_upon_model_change
        raise NotImplementedError

    def change_upon_left_mouseclick(self, callback_pars = {}):
        #update _callbacks_upon_left_mouseclick
        #by default doing nothing
        if len(callback_pars) == 0:
            self._callbacks_upon_left_mouseclick = [lambda:None for each in self.model_shape_index_list]
    
    def handleEvent(self, evt_src, evt_type, evt_value):
        """reimplemented from TaurusBaseComponent"""
        try:
            for i in range(len(self.model_shape_index_list)):
                if evt_src is self.getModelObj(key=(TaurusBaseComponent.MLIST, i)):
                    self._callbacks_upon_model_change[i](float(evt_value.rvalue.m))
                    break
        except Exception as e:
            self.info("Skipping event. Reason: %s", e)

class buildTools(object):

    @classmethod
    def calculate_boundary_for_combined_shapes(cls, shapes):
        x_min, x_max, y_min, y_max = None, None, None, None
        for i, shape in enumerate(shapes):
            if i == 0:
                x_min, x_max, y_min, y_max = shape.calculate_shape_boundary()
            else:
                _x_min, _x_max, _y_min, _y_max = shape.calculate_shape_boundary()
                x_min = min([x_min, _x_min])
                x_max = max([x_max, _x_max])
                y_min = min([y_min, _y_min])
                y_max = max([y_max, _y_max])
        return x_min, x_max, y_min, y_max

    @classmethod
    def align_multiple_shapes(cls, shapes, orientations):
        def _align_shapes(_shapes, orientations_):
            #_shapes = [ref1, tag1, ref2, tag2, ...], orientations_ = [ref_or1, tag_or1, ref_or2, tag_or2, ...]
            assert len(_shapes) == len(orientations_), 'The length of shapes and orientation must be equal!'
            for i in range(len(_shapes)-1):
                ref_shape, target_shape = _shapes[i], _shapes[i+1]
                orientations_temp = orientations_[i:i+2]
                buildTools.align_two_shapes(ref_shape, target_shape, orientations_temp)

        if type(shapes[0])==list:
            #shapes is a list of _shapes, orientations is a list of orientations_
            assert type(orientations[0])==list, 'Format mismatch. Should be list of list.'
            for shape_segment, orientaion_seg in zip(shapes, orientations):
                _align_shapes(shape_segment, orientaion_seg)
        else:
            _align_shapes(shapes, orientations)

    @classmethod
    def align_two_shapes(cls, ref_shape, target_shape, orientations = ['bottom', 'top'],  gap = 0.1, ref_anchors = [None, None]):
        cen_, v_unit = ref_shape.calculate_orientation_vector(orientations[0], ref_anchors[0])
        v_mag = ref_shape.calculate_orientation_length(orientations[0], ref_anchors[0]) + target_shape.calculate_orientation_length(orientations[1], ref_anchors[1])
        v = v_unit * v_mag * (1+gap)
        #set rot ang to 0 and translate to 0
        target_shape.reset()
        #this center is the geometry center if ref_anchor is None, and become offseted anchor otherwise
        if orientations[1] in ['left', 'right', 'top', 'bottom']:
            origin_cen_target = target_shape.compute_center_from_dim()
        else:
            if ref_anchors[1]==None:
                origin_cen_target = target_shape.compute_center_from_dim()
            else:
                if orientations[1]=='cen':
                    anchor = target_shape.compute_center_from_dim()
                else:
                    anchor = target_shape.anchors[orientations[1]]
                ref_anchor_offset = {'left': np.array([-1, 0]),
                                    'right': np.array([1, 0]),
                                    'top': np.array([0, -1]),
                                    'bottom': np.array([0, 1]),
                                    }
                assert ref_anchors[1] in ref_anchor_offset, "Wrong key for ref anchor"
                origin_cen_target = anchor - ref_anchor_offset[ref_anchors[1]]
        new_cen_target = v + cen_
        v_diff = new_cen_target - origin_cen_target
        target_shape.rot_center = origin_cen_target
        #let's calculate the angle between the original target shape and the orientated one
        target_cen_, target_v_unit = target_shape.calculate_orientation_vector(orientations[1], ref_anchors[1])
        target_v_new = - v
        angle_offset = -angle_between(target_v_unit, target_v_new)
        target_shape.transformation.update({'rotate': angle_offset, 'translate': v_diff})
        return target_shape

    @classmethod
    def make_line_connection_btw_two_anchors(cls, shapes, anchors, short_head_line_len = 10, direct_connection = False):
        line_nodes = []
        def _apply_offset(pos, dir):
            offset = {'left': np.array([-short_head_line_len, 0]),
                      'right': np.array([short_head_line_len, 0]),
                      'top': np.array([0, -short_head_line_len]),
                      'bottom': np.array([0, short_head_line_len]),
                     }
            return np.array(pos) + offset[dir]

        def _extend_to_beyond_boundary(pos, dir, overshot_pix_ct = 20):
            x_min, x_max, y_min, y_max = buildTools.calculate_boundary_for_combined_shapes(shapes)
            if dir == 'left':
                x = min([x_min, pos[0]]) - overshot_pix_ct
                y = pos[1]
            elif dir == 'right':
                x = max([x_max, pos[0]]) + overshot_pix_ct
                y = pos[1]
            elif dir == 'top':
                x = pos[0]
                y = min([y_min, pos[1]]) - overshot_pix_ct
            elif dir == 'bottom':
                x = pos[0]
                y = max([y_max, pos[1]]) + overshot_pix_ct
            return [int(x), int(y)]

        def _get_sign_from_dir(dir):
            if dir in ['left', 'top']:
                return '>='
            elif dir in ['right','bottom']:
                return '<='

        assert len(shapes)==2 and len(anchors)==2, 'shapes and anchors must be list of two items'
        dirs = []
        anchor_pos = []
        for shape, anchor in zip(shapes, anchors):
            dirs.append(shape.get_proper_extention_dir_for_one_anchor(anchor))
            anchor_pos.append(shape.compute_anchor_pos_after_transformation(anchor, return_pos_only=True))
        
        if direct_connection:
            line_pos = []
            for _pos, _dir in zip(anchor_pos, dirs):
                pos_offset = _apply_offset(_pos, _dir)
                if (_pos==anchor_pos[0]).all():
                    line_pos = line_pos + [_pos, pos_offset]
                else:
                    line_pos = line_pos + [pos_offset, _pos]
            return np.array(line_pos).astype(int)

            #return np.array(anchor_pos).astype(int)

        dir0, dir1 = dirs
        anchor_pos_offset = [_apply_offset(_pos, _dir) for _pos, _dir in zip(anchor_pos, dirs)]

        # if direct_connection:
            # return np.array(anchor_pos_offset).astype(int)
        
        if ('left' not in dirs) and ('right' not in dirs):
            if (dirs == ['top', 'top']) or (dirs == ['bottom', 'bottom']):
                first_anchor_pos_after_extend = _extend_to_beyond_boundary(anchor_pos_offset[0], dir0)
                second_anchor_pos_after_extend = _extend_to_beyond_boundary(anchor_pos_offset[1], dir1)
                if dirs == ['top', 'top']:
                    y_min = min([first_anchor_pos_after_extend[1], second_anchor_pos_after_extend[1]])
                else:
                    y_min = max([first_anchor_pos_after_extend[1], second_anchor_pos_after_extend[1]])
                first_anchor_pos_after_extend = [first_anchor_pos_after_extend[0], y_min]
                second_anchor_pos_after_extend = [second_anchor_pos_after_extend[0], y_min]
                line_nodes = [anchor_pos[0], anchor_pos_offset[0], first_anchor_pos_after_extend, second_anchor_pos_after_extend,anchor_pos_offset[1], anchor_pos[1]]
            else:
                first_anchor_pos_after_extend = _extend_to_beyond_boundary(anchor_pos_offset[0], dir0)
                second_anchor_pos_after_extend = _extend_to_beyond_boundary(anchor_pos_offset[1], dir1)
                x_cen = (anchor_pos_offset[0][0] + anchor_pos_offset[1][0])/2
                first_anchor_pos_after_extend_cen = [x_cen, first_anchor_pos_after_extend[1]]
                second_anchor_pos_after_extend_cen = [x_cen, second_anchor_pos_after_extend[1]]
                line_nodes = [anchor_pos[0], anchor_pos_offset[0], first_anchor_pos_after_extend, first_anchor_pos_after_extend_cen, \
                              second_anchor_pos_after_extend_cen, second_anchor_pos_after_extend,anchor_pos_offset[1], anchor_pos[1]]
        elif ('top' not in dirs) and ('bottom' not in dirs):
            if (dirs == ['left', 'left']) or (dirs == ['right', 'right']):
                first_anchor_pos_after_extend = _extend_to_beyond_boundary(anchor_pos_offset[0], dir0)
                second_anchor_pos_after_extend = _extend_to_beyond_boundary(anchor_pos_offset[1], dir1)
                if dirs == ['left', 'left']:
                    x_min = min([first_anchor_pos_after_extend[0], second_anchor_pos_after_extend[0]])
                else:
                    x_min = max([first_anchor_pos_after_extend[0], second_anchor_pos_after_extend[0]])
                first_anchor_pos_after_extend = [x_min, first_anchor_pos_after_extend[1]]
                second_anchor_pos_after_extend = [x_min, second_anchor_pos_after_extend[1]]                
                line_nodes = [anchor_pos[0], anchor_pos_offset[0], first_anchor_pos_after_extend, second_anchor_pos_after_extend,anchor_pos_offset[1], anchor_pos[1]]
            else:
                first_anchor_pos_after_extend = _extend_to_beyond_boundary(anchor_pos_offset[0], dir0)
                second_anchor_pos_after_extend = _extend_to_beyond_boundary(anchor_pos_offset[1], dir1)
                y_cen = (anchor_pos_offset[0][1] + anchor_pos_offset[1][1])/2
                first_anchor_pos_after_extend_cen = [first_anchor_pos_after_extend[0], y_cen]
                second_anchor_pos_after_extend_cen = [second_anchor_pos_after_extend[0], y_cen]
                line_nodes = [anchor_pos[0], anchor_pos_offset[0], first_anchor_pos_after_extend, first_anchor_pos_after_extend_cen, \
                              second_anchor_pos_after_extend_cen, second_anchor_pos_after_extend,anchor_pos_offset[1], anchor_pos[1]]            
        else: # mixture of top/bottom and left/right
            if dir0 in ['top', 'bottom']:
                ref_x, ref_y = [anchor_pos_offset[0][0], anchor_pos_offset[1][1]] 
                check_x, check_y = [anchor_pos_offset[1][0], anchor_pos_offset[0][1]] 
                check_result_x = eval(f'{check_x}{_get_sign_from_dir(dir1)}{ref_x}')
                check_result_y = eval(f'{check_y}{_get_sign_from_dir(dir0)}{ref_y}')
                if check_result_x and check_result_y:
                    cross_pt = [ref_x, ref_y]
                    line_nodes = [anchor_pos[0], anchor_pos_offset[0], cross_pt, anchor_pos_offset[1], anchor_pos[1]]
                else:
                    first_anchor_pos_after_extend = _extend_to_beyond_boundary(anchor_pos_offset[0], dir0)
                    second_anchor_pos_after_extend = _extend_to_beyond_boundary(anchor_pos_offset[1], dir1)
                    cross_pt = [second_anchor_pos_after_extend[0], first_anchor_pos_after_extend[1]]
                    line_nodes = [anchor_pos[0], anchor_pos_offset[0], first_anchor_pos_after_extend, cross_pt, second_anchor_pos_after_extend, anchor_pos_offset[1], anchor_pos[1]]
            else:
                ref_x, ref_y = [anchor_pos_offset[1][0], anchor_pos_offset[0][1]] 
                check_x, check_y = [anchor_pos_offset[0][0], anchor_pos_offset[1][1]] 
                check_result_x = eval(f'{check_x}{_get_sign_from_dir(dir0)}{ref_x}')
                check_result_y = eval(f'{check_y}{_get_sign_from_dir(dir1)}{ref_y}')
                if check_result_x and check_result_y:
                    cross_pt = [ref_x, ref_y]
                    line_nodes = [anchor_pos[0], anchor_pos_offset[0], cross_pt, anchor_pos_offset[1], anchor_pos[1]]
                else:
                    first_anchor_pos_after_extend = _extend_to_beyond_boundary(anchor_pos_offset[0], dir0)
                    second_anchor_pos_after_extend = _extend_to_beyond_boundary(anchor_pos_offset[1], dir1)
                    cross_pt = [first_anchor_pos_after_extend[0], second_anchor_pos_after_extend[1]]
                    line_nodes = [anchor_pos[0], anchor_pos_offset[0], first_anchor_pos_after_extend, cross_pt, second_anchor_pos_after_extend, anchor_pos_offset[1], anchor_pos[1]]
        return np.array(line_nodes).astype(int)

class queueSynopticView(QWidget):
    FILL_QUEUED = {'brush': {'color': (0, 0, 255)}}
    FILL_RUN = {'brush': {'color': (50, 255, 0)}}
    FILL_DISABLED = {'brush': {'color': (50, 50, 50)}}
    FILL_FAILED = {'brush': {'color': (255, 50, 0)}}
    FILL_PAUSED = {'brush': {'color': (255, 0, 255)}}
    CLICKED_SHAPE = {'pen': {'color': (255, 255, 0), 'width': 3, 'ls': 'SolidLine'}}
    NONCLICKED_SHAPE = {'pen': {'color': (255, 0, 0), 'width': 3, 'ls': 'SolidLine'}}

    def __init__(self, parent = None, padding_vertical = 20, padding_hor = 60, block_width=180, block_height =20) -> None:
        super().__init__(parent = parent)
        self.parent = parent
        self.padding_vertical = padding_vertical
        self.padding_hor = padding_hor
        self.block_width = block_width
        self.block_height = block_height
        self._data = []
        self.composite_shape_container = {}
        self.composite_shapes = []
        self.last_clicked_shape = None
        self.lines_bw_composite = []
        self.triangle_ends = []

    def set_data(self, data):
        self._data = data
        self.build_shapes()

    def _calculate_col_num_blocks(self):
        widget_height = self.size().height()
        widget_width = self.size().width()
        num_blocks_each_column = int((widget_height - widget_height%(self.padding_vertical + self.block_height))/(self.padding_vertical + self.block_height))
        return num_blocks_each_column

    def build_shapes(self):
        self.composite_shape_container = {}
        if len(self._data)==0:
            self.shapes = []
            return
        size_col = self._calculate_col_num_blocks()
        for i in range(len(self._data)):
            which_col = int((i+1)/size_col)
            shape = rectangle(dim = [self.padding_hor + which_col*(self.block_width + self.padding_hor),self.padding_vertical,self.block_width,self.block_height],rotation_center = None, transformation={'rotate':0, 'translate':(0,0), 'scale':1})
            state = self._data.iloc[i,:]['state']
            queue_id = self._data.iloc[i,:]['queue_id']
            cmd = self._data.iloc[i,:]['scan_command']
            if state == 'queued':
                shape.decoration = self.FILL_QUEUED
                shape.decoration_cursor_off = self.FILL_QUEUED
                shape.decoration_cursor_on = self.FILL_QUEUED
            elif state == 'running':
                shape.decoration = self.FILL_RUN
                shape.decoration_cursor_off = self.FILL_RUN
                shape.decoration_cursor_on = self.FILL_RUN
            elif state == 'failed':
                shape.decoration = self.FILL_FAILED
                shape.decoration_cursor_off = self.FILL_FAILED
                shape.decoration_cursor_on = self.FILL_FAILED
            elif state == 'paused':
                shape.decoration = self.FILL_PAUSED
                shape.decoration_cursor_off = self.FILL_PAUSED
                shape.decoration_cursor_on = self.FILL_PAUSED
            elif state == 'disabled':
                shape.decoration = self.FILL_DISABLED
                shape.decoration_cursor_off = self.FILL_DISABLED
                shape.decoration_cursor_on = self.FILL_DISABLED
            shape.labels = {'text':[f'{queue_id}:{cmd}'],'anchor':['left']}
            if which_col not in self.composite_shape_container:
                self.composite_shape_container[which_col] = []
                self.composite_shape_container[which_col].append(shape)
            else:
                self.composite_shape_container[which_col].append(shape)
        self.build_composite_object()
        self.update()

    def build_composite_object(self):
        self.composite_shapes = []
        self.lines_bw_composite = []
        self.triangle_ends = []
        for each, shapes in self.composite_shape_container.items():
            composite = shapeComposite(shapes = shapes, \
                                             anchor_args = [4 for i in range(len(shapes))], \
                                             alignment_pattern= {'shapes':[[i, i+1] for i in range(len(shapes)-1)], \
                                                                 'anchors':[['bottom', 'top'] for i in range(len(shapes)-1)],\
                                                                 'gaps': [self.padding_vertical/self.block_height for i in range(len(shapes)-1)],\
                                                                 'ref_anchors': [['bottom', 'top'] for i in range(len(shapes)-1)],\
                                                                },
                                             connection_pattern= {'shapes':[[i, i+1] for i in range(len(shapes)-1)], \
                                                                 'anchors':[['bottom', 'top'] for i in range(len(shapes)-1)], \
                                                                 'connect_types':[True for i in range(len(shapes)-1)] })
            self.composite_shapes.append(composite)
        #make line connection between two adjacent composit shapes
        for i in range(len(self.composite_shapes)-1):
            shapes = [self.composite_shapes[i].shapes[-1], self.composite_shapes[i+1].shapes[0]]
            anchors = ['right', 'left']
            rot_cen = [shapes[-1].dim_pars[0], shapes[-1].dim_pars[1]+int(shapes[-1].dim_pars[-1]/2)]
            self.triangle_ends.append(isocelesTriangle(dim = rot_cen + [10, 60]))
            self.triangle_ends[-1].transformation = {'rotate':90}
            self.triangle_ends[-1].rot_center = rot_cen
            self.triangle_ends[-1].decoration = {'pen': {'color': (0, 255, 0), 'width': 2, 'ls': 'SolidLine'}, 'brush': {'color': (0, 255, 0)}} 
            self.lines_bw_composite.append(buildTools.make_line_connection_btw_two_anchors(shapes, anchors, short_head_line_len = int(self.padding_hor/2), direct_connection = True))

    def set_parent(self, parent):
        self.parent = parent

    def paintEvent(self, a0: QPaintEvent | None) -> None:
        qp = QPainter()
        qp.begin(self)
        # for each in self.shapes:            
        for each in self.composite_shapes:
            for line in each.lines:
                qp.setPen(QPen(Qt.green, 2, Qt.SolidLine))        
                for i in range(len(line)-1):
                    pts = list(line[i]) + list(line[i+1])
                    qp.drawLine(*pts)  
        for line in self.lines_bw_composite:
            qp.setPen(QPen(Qt.green, 2, Qt.SolidLine))        
            for i in range(len(line)-1):
                pts = list(line[i]) + list(line[i+1])
                qp.drawLine(*pts)              
        for each in self.composite_shapes:
            for each_shape in each.shapes:
                qp.resetTransform()
                each_shape.paint(qp)
        for each_shape in self.triangle_ends:
            qp.resetTransform()
            each_shape.paint(qp)
        qp.end()

    def mouseMoveEvent(self, event):
        self.last_x, self.last_y = event.x(), event.y()
        # if self.parent !=None:
            # self.parent.statusbar.showMessage('Mouse coords: ( %d : %d )' % (event.x(), event.y()))
        for each in self.composite_shapes:
            for each_shape in each.shapes:
                each_shape.cursor_pos_checker(event.x(), event.y())
        self.update()

    def mousePressEvent(self, event):
        x, y = event.x(), event.y()
        shapes_under_cursor = []
        for each in self.composite_shapes:
            for each_shape in each.shapes:
                if each_shape.check_pos(x, y) and event.button() == Qt.LeftButton:
                    queue_id = each_shape.labels['text'][0].rsplit(':')[0]
                    self.parent.update_task_from_server(queue_id)
                    if self.parent !=None:
                        self.parent.statusbar.showMessage(f'Clicked job id is: {queue_id}')
                    if self.last_clicked_shape==None:
                        #self.last_clicked_shape.decoration_cursor_off = self.NONCLICKED_SHAPE
                        self.last_clicked_shape = each_shape
                        self.last_clicked_shape.decoration_cursor_off = self.CLICKED_SHAPE
                    else:
                        self.last_clicked_shape.decoration_cursor_off = self.NONCLICKED_SHAPE
                        self.last_clicked_shape = each_shape
                        self.last_clicked_shape.decoration_cursor_off = self.CLICKED_SHAPE
                    return

class shapeContainer(QWidget):
    
    def __init__(self, parent = None) -> None:
        super().__init__(parent = parent)
        self.parent = parent
        self.build_shapes()
        self.composite_shape = shapeComposite(shapes = self.shapes[0:-2], \
                                             anchor_args = [4, 3, 3, 3, 3], \
                                             alignment_pattern= {'shapes':[[0,1],[0,2],[0,3],[0,4]], \
                                                                 'anchors':[['cen','cen'],\
                                                                            ['anchor_bottom_0','anchor_top_1'],\
                                                                            ['anchor_bottom_1','anchor_top_1'],\
                                                                            ['anchor_bottom_2','anchor_top_1']],\
                                                                 'gaps': [0.3, 0.3, 0.3, 13],\
                                                                 'ref_anchors': [['bottom', 'bottom'], \
                                                                                 ['bottom', 'top'],\
                                                                                 ['bottom', 'top'], \
                                                                                 ['bottom', 'top']],\
                                                                },
                                             connection_pattern= {'shapes':[[1,2],[3,4]], \
                                                                 'anchors':[['left','right'],\
                                                                            ['top','top'],\
                                                                            ]})

        self.composite_shape_2 = shapeComposite(shapes = [self.shapes[i] for i in [-1,-3,-4,-5,-6,-2]], \
                                             anchor_args = [4, 3, 3, 3, 3, 3], \
                                             alignment_pattern= {'shapes':[[0,1],[0,2],[0,3],[0,4], [0,5]], \
                                                                 'anchors':[['left','right'],\
                                                                            ['top','bottom'],\
                                                                            ['right','left'],\
                                                                            ['bottom','top'],\
                                                                            ['cen','cen']],\
                                                                 'gaps': [0.3, 0.3, 0.3, 0.3, 0.3],\
                                                                 'ref_anchors': [['bottom', 'bottom'], \
                                                                                 ['bottom', 'top'],\
                                                                                 ['bottom', 'top'], \
                                                                                 ['bottom', 'top'], \
                                                                                 ['bottom', 'top']],\
                                                                },
                                             connection_pattern= {'shapes':[[1,2],[3,4], [0,0],[0,0],[0,0],[0,0]], \
                                                                 'anchors':[['left','right'],\
                                                                            ['top','top'],\
                                                                            ['top','left'],\
                                                                            ['left','bottom'],\
                                                                            ['bottom','right'],\
                                                                            ['right','top'],\
                                                                            ],\
                                                                 'connect_types': [False, False, True, True, True, True]})                                                                            
        self.test_timer = QTimer()
        self.test_timer.timeout.connect(self.test_rotate_shape)
        self.test_connection_or = ['bottom','top']
        #self.align_multiple_shapes(shapes = [[self.shapes[0], self.shapes[1]], [self.shapes[0], self.shapes[2]], [self.shapes[0], self.shapes[3]], [self.shapes[0], self.shapes[4]]], \
        #                           orientations = [['top', 'bottom'], ['bottom', 'top'], ['left', 'right'], ['right', 'left']])

    def set_parent(self, parent):
        self.parent = parent

    def build_shapes(self):
        self.shapes = [rectangle(dim = [200,180,100*1.,100*1.],rotation_center = None, transformation={'rotate':0, 'translate':(0,0), 'scale':1}), \
                       rectangle(dim = [100,300,20*1.,20*1.],rotation_center = [110,310], transformation={'rotate':0, 'translate':(0,0), 'scale':1}),\
                       rectangle(dim = [100,300,20*1.,20*1.],rotation_center = [110,310], transformation={'rotate':0, 'translate':(0,0), 'scale':1}),\
                       rectangle(dim = [100,300,20*1.,20*1.],rotation_center = [110,310], transformation={'rotate':0, 'translate':(0,0), 'scale':1}),\
                       rectangle(dim = [100,300,20*1.,20*1.],rotation_center = [110,310], transformation={'rotate':0, 'translate':(0,0), 'scale':1}), \
                       isocelesTriangle(dim=[500,500, 69.28, 60]), \
                       circle(dim=[700,400, 80])]#,\
                    #    rectangle(dim = [300,100,50,50],rotation_center = [340,120], transformation={'rotate':0, 'translate':(0,0)}),\
                    #    rectangle(dim = [300,100,50,50],rotation_center = [340,120], transformation={'rotate':0, 'translate':(0,0)}),\
                    #    rectangle(dim = [300,100,50,50],rotation_center = [340,120], transformation={'rotate':0, 'translate':(0,0)})]# \
                    #    rectangle(dim = [300,100,80,40],rotation_center = [300,100], transformation={'rotate':0, 'translate':(50,20)})]
                    #    rectangle(dim = [500,100,40,80],transformation={'rotate':0, 'translate':(0,0)}), \
                    #    rectangle(dim = [500,100,80,80],transformation={'rotate':0, 'translate':(0,0)})]

    def align_multiple_shapes(self, shapes, orientations):
        buildTools.align_multiple_shapes(shapes, orientations)

    def align_two_shapes(self, ref_shape, target_shape, orientations = ['bottom', 'top']):
        buildTools.align_two_shapes(ref_shape, target_shape, orientations)

    def _test_get_rot_center_lines(self, which_shape = 0, offset = 20):
        cen = np.array(self.shapes[which_shape].rot_center) + np.array(self.shapes[which_shape].transformation['translate'])
        line_hor_left = cen - [offset, 0]
        line_hor_right = cen + [offset, 0]
        line_ver_top = cen - [0, offset]
        line_ver_bottom = cen + [0, offset]
        return list(line_hor_left) + list(line_hor_right), list(line_ver_top) + list(line_ver_bottom)

    def _test_connection(self, qp):
        lines = self.make_line_connection_btw_two_anchors(self.shapes, self.test_connection_or)
        self.test_draw_connection_lines(qp, lines)

    def _test_composite_shape(self, qp):
        for line in self.composite_shape.lines + self.composite_shape_2.lines:
            self.test_draw_connection_lines(qp, line)

    def paintEvent(self, a0: QPaintEvent | None) -> None:
        qp = QPainter()
        qp.begin(self)
        #self._test_connection(qp)
        self._test_composite_shape(qp)
        # for each in self.shapes:
        for each in self.composite_shape.shapes:
            qp.resetTransform()
            each.paint(qp)
        for each in self.composite_shape_2.shapes:
            qp.resetTransform()
            each.paint(qp)
        #qp.resetTransform()
        #self.shapes[-1].paint(qp)
        #qp.resetTransform()
        #self.shapes[-2].paint(qp)
        qp.resetTransform()
        qp.setPen(QPen(Qt.green, 4, Qt.SolidLine))
        hor, ver = self._test_get_rot_center_lines()
        qp.drawLine(*[int(each) for each in hor])
        qp.drawLine(*[int(each) for each in ver])
        qp.end()

    def test_draw_connection_lines(self, qp, line_nodes):
        qp.setPen(QPen(Qt.green, 4, Qt.SolidLine))        
        for i in range(len(line_nodes)-1):
            pts = list(line_nodes[i]) + list(line_nodes[i+1])
            qp.drawLine(*pts)

    def start_(self):
        self.test_timer.start(200)

    def stop_(self):
        self.test_timer.stop()

    def test_rotate_shape(self):
        self.composite_shape.shapes[0].transformation = {'rotate':(self.composite_shape.shapes[0].transformation['rotate']+10)%360, 'translate':self.composite_shape.shapes[0].transformation['translate']}
        self.composite_shape_2.shapes[0].transformation = {'rotate':(self.composite_shape_2.shapes[0].transformation['rotate']+10)%360, 'translate':self.composite_shape_2.shapes[0].transformation['translate']}
        #self.align_multiple_shapes(shapes = [[self.shapes[0], self.shapes[1]], [self.shapes[0], self.shapes[2]], [self.shapes[0], self.shapes[3]], [self.shapes[0], self.shapes[4]]], \
        #                           orientations = [['top', 'bottom'], ['bottom', 'top'], ['left', 'right'], ['right', 'left']])
        # self.align_two_shapes(ref_shape=self.shapes[0], target_shape=self.shapes[1], orientations=  ['bottom', 'top'])
        self.composite_shape.build_composite()
        self.composite_shape_2.build_composite()
        for each in self.composite_shape.shapes + self.composite_shape_2.shapes:
            each.cursor_pos_checker(self.last_x, self.last_y)
        self.update()


    def make_line_connection_btw_two_anchors(self, shapes, anchors, short_head_line_len = 10):
        return buildTools.make_line_connection_btw_two_anchors(shapes, anchors, short_head_line_len)
        
    def mouseMoveEvent(self, event):
        self.last_x, self.last_y = event.x(), event.y()
        if self.parent !=None:
            self.parent.statusbar.showMessage('Mouse coords: ( %d : %d )' % (event.x(), event.y()))
        for each in self.composite_shape.shapes + self.shapes[-2:] + self.composite_shape_2.shapes:
            each.cursor_pos_checker(event.x(), event.y())
        self.update()