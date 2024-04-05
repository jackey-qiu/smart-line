from PyQt5.QtGui import QPaintEvent, QPainter, QPen, QBrush, QColor, QFont, QCursor, QPainterPath,QTransform
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
import numpy as np

class baseShape(object):

    def __init__(self, dim, decoration, rotation_center=None, transformation={'rotate':0, 'translate':(0,0)}):
        #super().__init__(parent = parent)
        self._dim_pars = dim
        self.cen = self.compute_center_from_dim()
        self._rotcenter = rotation_center
        self._decoration = decoration
        self.anchors = []
        self._transformation = transformation

    @property
    def dim_pars(self):
        return self._dim_pars
    
    @dim_pars.setter
    def dim_pars(self, new_dim):
        self._dim_pars = new_dim
        self.update()

    @property
    def rot_center(self):
        return self._rotcenter
    
    @rot_center.setter
    def rot_center(self, rot_center):
        self._rotcenter = rot_center
        self.update()

    @property
    def decoration(self):
        return self._decoration
    
    @decoration.setter
    def decoration(self, decoration):
        self._decoration = decoration

    @property
    def transformation(self):
        return self._transformation
    
    @transformation.setter
    def transformation(self, transformation):
        assert isinstance(transformation, dict), 'wrong format of transformation'
        self._transformation = transformation
        # self.calculate_shape()
        self.update()

    def compute_center_from_dim(self):
        raise NotImplementedError

    def make_anchors(self, *args, **kwargs):
        raise NotImplementedError
    
    def calculate_shape(self):
        raise NotImplementedError
    
    def calculate_anchor_orientation(self):
        raise NotImplementedError
    
    def apply_transform(self,qp):
        #translate_values = self.transformation['translate'] if 'translate' in self.transformation else (0,0)
        rotate_angle = self.transformation['rotate'] if 'rotate' in self.transformation else 0
        cen = self.compute_center_from_dim()
        #cen_after_offset = [x+x_off for x, x_off in zip(cen, translate_values)]
        if self.rot_center==None:
            rot_center = cen
        else:
            rot_center = self.rot_center
        qp.translate(*rot_center)
        qp.rotate(rotate_angle)
        qp.translate(*[-each for each in rot_center])
        return qp
    
    def paint(self, qp) -> None:
        #qp = QPainter()
        #qp.begin(self)
        qp.setPen(self.decoration['pen'])
        qp.setBrush(self.decoration['brush'])
        self.draw_shape(qp)
        #qp.end()

    def draw_shape(self, qp):
        raise NotImplementedError

class rectangle(baseShape):
    def __init__(self, dim = [700,100,40,80], rotation_center = None, decoration={'pen':QPen(QColor(255,0,0), 3, Qt.SolidLine), 'brush':QBrush(QColor(0,0,255))},\
                 transformation={'rotate':45, 'translate':(0,0)}):

        super().__init__(dim = dim, rotation_center=rotation_center, decoration=decoration, transformation=transformation)

    def draw_shape(self, qp):
        #qp.drawArc(*[0, 0, 40, 40, 16*0, 16 * 270])
        qp = self.apply_transform(qp)
        qp.drawRect(*self.dim_pars)

    def compute_center_from_dim(self):
        x, y, w, h = self.dim_pars
        return x+w/2, y+h/2

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

class shapeContainer(QWidget):
    
    def __init__(self, parent = None) -> None:
        super().__init__(parent = parent)
        self.parent = parent
        self.build_shapes()

    def set_parent(self, parent):
        self.parent = parent

    def build_shapes(self):
        self.shapes = [rectangle(dim = [700,100,40,80],rotation_center = [700,100], transformation={'rotate':45, 'translate':(0,0)}),\
                       rectangle(dim = [500,100,40,80],transformation={'rotate':45, 'translate':(0,0)})]

    def paintEvent(self, a0: QPaintEvent | None) -> None:
        qp = QPainter()
        qp.begin(self)
        for each in self.shapes:
            qp.resetTransform()
            each.paint(qp)
        qp.end()

    def mouseMoveEvent(self, event):
        if self.parent !=None:
            self.parent.statusbar.showMessage('Mouse coords: ( %d : %d )' % (event.x(), event.y()))