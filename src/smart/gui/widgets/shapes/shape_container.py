from PyQt5.QtGui import QPaintEvent, QPainter, QPen, QBrush, QColor, QFont, QCursor, QPainterPath,QTransform
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtCore import QTimer
import numpy as np
import copy
import time
from dataclasses import dataclass
from smart.util.geometry_transformation import rotate_multiple_points, angle_between

DECORATION_UPON_CURSOR_ON = {'pen': {'color': (255, 255, 0), 'width': 3, 'ls': 'DotLine'}, 'brush': {'color': (0, 0, 255)}} 
DECORATION_UPON_CURSOR_OFF = {'pen': {'color': (255, 0, 0), 'width': 3, 'ls': 'SolidLine'}, 'brush': {'color': (0, 0, 255)}}


def make_decoration_from_text(dec = {'pen': {'color': (255, 255, 0), 'width': 3, 'ls': 'DotLine'}, 'brush': {'color': (0, 0, 255)}}):

    pen_color = QColor(*dec['pen']['color'])
    pen_width = dec['pen']['width']
    pen_style = getattr(Qt,dec['pen']['ls'])
    qpen = QPen(pen_color, pen_width, pen_style)
    brush_color = QColor(*dec['brush']['color'])
    qbrush = QBrush(brush_color)
    return {'pen': qpen, 'brush': qbrush}

class baseShape(object):

    def __init__(self, dim, decoration_cursor_off = DECORATION_UPON_CURSOR_OFF, decoration_cursor_on = DECORATION_UPON_CURSOR_ON , rotation_center=None, transformation={'rotate':0, 'translate':(0,0), 'scale':1}):
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
        if rot_center == None:
            self._rotcenter = [int(each) for each in self.compute_center_from_dim(False)]
        else:
            self._rotcenter = [int(each) for each in rot_center]

    @property
    def decoration(self):
        return self._decoration
    
    @decoration.setter
    def decoration(self, decoration):
        self._decoration = decoration

    @property
    def decoration_cursor_on(self):
        return self._decoration_cursor_on
    
    @decoration_cursor_on.setter
    def decoration_cursor_on(self, decoration):
        self._decoration_cursor_on = decoration

    @property
    def decoration_cursor_off(self):
        return self._decoration_cursor_off
    
    @decoration_cursor_off.setter
    def decoration_cursor_off(self, decoration):
        self._decoration_cursor_off = decoration

    @property
    def transformation(self):
        return self._transformation
    
    @transformation.setter
    def transformation(self, transformation):
        assert isinstance(transformation, dict), 'wrong format of transformation'
        self._transformation = transformation
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
    
    def compute_anchor_pos_after_transformation(self, key, return_pos_only = False):
        #calculate anchor pos for key after transformation
        orientation = key
        or_len = self.calculate_orientation_length(orientation)
        cen = self.compute_center_from_dim(apply_translate=True)
        rotate_angle = self.transformation['rotate'] if 'rotate' in self.transformation else 0
        anchor = None
        if orientation == 'top':
            anchor = np.array(cen) + [0, -or_len]
        elif orientation == 'bottom':
            anchor = np.array(cen) + [0, or_len]
        elif orientation == 'left':
            anchor = np.array(cen) + [-or_len, 0]
        elif orientation == 'right':
            anchor = np.array(cen) + [or_len, 0]
        else:
            if orientation in self.anchors:
                anchor = self.anchors[orientation]
            else:
                raise KeyError('Not the right key for orientation')
        rot_center = np.array(self.rot_center) + np.array(self.transformation['translate'])
        cen_, anchor_ = rotate_multiple_points([cen, anchor], rot_center, rotate_angle)
        #return cen and anchor pos and or_len after transformation
        if return_pos_only:
            return anchor_
        else:
            return anchor_, cen_, or_len
    
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
        decoration = make_decoration_from_text(self.decoration)
        qp.setPen(decoration['pen'])
        qp.setBrush(decoration['brush'])
        self.draw_shape(qp)

    def draw_shape(self, qp):
        raise NotImplementedError
    
    def calculate_orientation_vector(self, orientation = 'top'):
        anchor_, cen_, or_len = self.compute_anchor_pos_after_transformation(orientation,return_pos_only=False)
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
                 transformation={'rotate':45, 'translate':(0,0), 'scale': 1}):

        super().__init__(dim = dim, rotation_center=rotation_center, decoration_cursor_off=decoration_cursor_off, decoration_cursor_on= decoration_cursor_on, transformation=transformation)

    def scale(self, sf):
        self.dim_pars = (np.array(self.dim_pars)*[1,1,sf/self.transformation['scale'],sf/self.transformation['scale']]).astype(int)
        self.transformation['scale'] = sf

    def draw_shape(self, qp):
        qp = self.apply_transform(qp)
        qp.drawRect(*np.array(self.dim_pars).astype(int))

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

    def calculate_orientation_length(self, orientation = 'top'):

        w, h = np.array(self.dim_pars[2:])
        if orientation in ['top', 'bottom']:
            return h/2
        elif orientation in ['left', 'right']:
            return w/2
        else:
            if orientation in self.anchors:
                return np.linalg.norm(np.array(self.anchors[orientation]) - np.array(self.compute_center_from_dim(apply_translate=False)))
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
    pass

class polygon(baseShape):
    pass

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

class shapeComposite(object):

    def __init__(self, shapes, anchor_args, alignment_pattern, connection_pattern, ref_shape_index = None):
        #connection_patter = {'shapes':[[0,1],[1,2]], 'anchors':[['left','top'],['right', 'bottom']]}
        #alignment_patter = {'shapes':[[0,1],[1,2]], 'anchors':[['left','top'],['right', 'bottom']]}
        self._shapes = copy.deepcopy(shapes)
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

    def make_anchors(self):
        for shape, arg in zip(self.shapes, self.anchor_args):
            shape.make_anchors(arg)

    def build_composite(self):
        self.align_shapes()
        self.make_line_connection()

    def align_shapes(self):
        shape_index = self.alignment['shapes']
        anchors = self.alignment['anchors']
        assert len(shape_index) == len(anchors), "Dimension of shape and anchors does not match!"
        for shapes_, anchors_ in zip(shape_index, anchors):
            ref_shape, target_shape, *_ = [self.shapes[each] for each in shapes_]
            buildTools.align_two_shapes(ref_shape, target_shape, anchors_, 0)

    def make_line_connection(self):
        self.lines = []
        shape_index = self.connection['shapes']
        anchors = self.connection['anchors']
        assert len(shape_index) == len(anchors), "Dimension of shape and anchors does not match!"
        for shapes_, anchors_ in zip(shape_index, anchors):
            shapes = [self.shapes[each] for each in shapes_]
            lines = buildTools.make_line_connection_btw_two_anchors(shapes, anchors_)
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

class buildTools(object):

    @classmethod
    def align_multiple_shapes(cls, shapes, orientations):
        def _align_shapes(_shapes, orientations_):
            assert len(_shapes) == len(orientations_), 'The length of shapes and orientation must be equal!'
            for i in range(len(_shapes)-1):
                ref_shape, target_shape = _shapes[i], _shapes[i+1]
                orientations_temp = orientations_[i:i+2]
                cls.align_two_shapes(ref_shape, target_shape, orientations_temp)

        if type(shapes[0])==list:
            assert type(orientations[0])==list, 'Format mismatch. Should be list of list.'
            for shape_segment, orientaion_seg in zip(shapes, orientations):
                _align_shapes(shape_segment, orientaion_seg)
        else:
            _align_shapes(shapes, orientations)

    @classmethod
    def align_two_shapes(cls, ref_shape, target_shape, orientations = ['bottom', 'top']):
        cen_, v_unit = ref_shape.calculate_orientation_vector(orientations[0])
        v_mag = ref_shape.calculate_orientation_length(orientations[0]) + target_shape.calculate_orientation_length(orientations[1])
        v = v_unit * v_mag
        #set rot ang to 0 and translate to 0
        target_shape.reset()
        origin_cen_target = target_shape.compute_center_from_dim(apply_translate=False)
        new_cen_target = v + cen_
        v_diff = new_cen_target - origin_cen_target
        target_shape.rot_center = origin_cen_target
        #let's calculate the angle between the original target shape and the orientated one
        target_cen_, target_v_unit = target_shape.calculate_orientation_vector(orientations[1])
        target_v_new = - v
        angle_offset = -angle_between(target_v_unit, target_v_new)
        target_shape.transformation.update({'rotate': angle_offset, 'translate': v_diff})
        return target_shape

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
            assert len(_shapes) == len(orientations_), 'The length of shapes and orientation must be equal!'
            for i in range(len(_shapes)-1):
                ref_shape, target_shape = _shapes[i], _shapes[i+1]
                orientations_temp = orientations_[i:i+2]
                buildTools.align_two_shapes(ref_shape, target_shape, orientations_temp)

        if type(shapes[0])==list:
            assert type(orientations[0])==list, 'Format mismatch. Should be list of list.'
            for shape_segment, orientaion_seg in zip(shapes, orientations):
                _align_shapes(shape_segment, orientaion_seg)
        else:
            _align_shapes(shapes, orientations)

    @classmethod
    def align_two_shapes(cls, ref_shape, target_shape, orientations = ['bottom', 'top'], gap = 0.1):
        cen_, v_unit = ref_shape.calculate_orientation_vector(orientations[0])
        v_mag = ref_shape.calculate_orientation_length(orientations[0]) + target_shape.calculate_orientation_length(orientations[1])
        v = v_unit * v_mag * (1+gap)
        #set rot ang to 0 and translate to 0
        target_shape.reset()
        origin_cen_target = target_shape.compute_center_from_dim()
        new_cen_target = v + cen_
        v_diff = new_cen_target - origin_cen_target
        target_shape.rot_center = origin_cen_target
        #let's calculate the angle between the original target shape and the orientated one
        target_cen_, target_v_unit = target_shape.calculate_orientation_vector(orientations[1])
        target_v_new = - v
        angle_offset = -angle_between(target_v_unit, target_v_new)
        target_shape.transformation.update({'rotate': angle_offset, 'translate': v_diff})
        return target_shape

    @classmethod
    def make_line_connection_btw_two_anchors(cls, shapes, anchors, short_head_line_len = 10):
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
        dir0, dir1 = dirs
        anchor_pos_offset = [_apply_offset(_pos, _dir) for _pos, _dir in zip(anchor_pos, dirs)]
        
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

class shapeContainer(QWidget):
    
    def __init__(self, parent = None) -> None:
        super().__init__(parent = parent)
        self.parent = parent
        self.build_shapes()
        self.composite_shape = shapeComposite(shapes = self.shapes, \
                                             anchor_args = [4, 3, 3, 3, 3], \
                                             alignment_pattern= {'shapes':[[0,1],[0,2],[0,3],[0,4]], \
                                                                 'anchors':[['top','bottom'],\
                                                                            ['left','right'],\
                                                                            ['right','left'],\
                                                                            ['anchor_bottom_3','anchor_top_1'],\
                                                                            ]},
                                             connection_pattern= {'shapes':[[1,2],[3,4]], \
                                                                 'anchors':[['left','right'],\
                                                                            ['top','top'],\
                                                                            ]})
        self.test_timer = QTimer()
        self.test_timer.timeout.connect(self.test_rotate_shape)
        self.test_connection_or = ['bottom','top']
        #self.align_multiple_shapes(shapes = [[self.shapes[0], self.shapes[1]], [self.shapes[0], self.shapes[2]], [self.shapes[0], self.shapes[3]], [self.shapes[0], self.shapes[4]]], \
        #                           orientations = [['top', 'bottom'], ['bottom', 'top'], ['left', 'right'], ['right', 'left']])

    def set_parent(self, parent):
        self.parent = parent

    def build_shapes(self):
        self.shapes = [rectangle(dim = [200,180,100*1.,100*1.],rotation_center = [200,180], transformation={'rotate':0, 'translate':(0,0), 'scale':1}), \
                       rectangle(dim = [100,300,20*1.,20*1.],rotation_center = [110,310], transformation={'rotate':0, 'translate':(0,0), 'scale':1}),\
                       rectangle(dim = [100,300,20*1.,20*1.],rotation_center = [110,310], transformation={'rotate':0, 'translate':(0,0), 'scale':1}),\
                       rectangle(dim = [100,300,20*1.,20*1.],rotation_center = [110,310], transformation={'rotate':0, 'translate':(0,0), 'scale':1}),\
                       rectangle(dim = [100,300,20*1.,20*1.],rotation_center = [110,310], transformation={'rotate':0, 'translate':(0,0), 'scale':1})]#,\
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
        for line in self.composite_shape.lines:
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
        #self.align_multiple_shapes(shapes = [[self.shapes[0], self.shapes[1]], [self.shapes[0], self.shapes[2]], [self.shapes[0], self.shapes[3]], [self.shapes[0], self.shapes[4]]], \
        #                           orientations = [['top', 'bottom'], ['bottom', 'top'], ['left', 'right'], ['right', 'left']])
        # self.align_two_shapes(ref_shape=self.shapes[0], target_shape=self.shapes[1], orientations=  ['bottom', 'top'])
        self.composite_shape.build_composite()
        for each in self.composite_shape.shapes:
            each.cursor_pos_checker(self.last_x, self.last_y)
        self.update()


    def make_line_connection_btw_two_anchors(self, shapes, anchors, short_head_line_len = 10):
        return buildTools.make_line_connection_btw_two_anchors(shapes, anchors, short_head_line_len)
        
    def mouseMoveEvent(self, event):
        self.last_x, self.last_y = event.x(), event.y()
        if self.parent !=None:
            self.parent.statusbar.showMessage('Mouse coords: ( %d : %d )' % (event.x(), event.y()))
        for each in self.composite_shape.shapes:
            each.cursor_pos_checker(event.x(), event.y())
        self.update()