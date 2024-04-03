
class baseShape(object):

    def __init__(self, dim, decoration):
        self.dim_pars = dim
        self.cen = [0,0]
        self._offcenter = [0, 0]
        self._decoration = decoration
        self.anchors = []
        self._transformation = {'rot': 0, 'scale': 1}

    @property
    def offcenter(self):
        return self._offcenter
    
    @offcenter.setter
    def set_offcenter(self, offset):
        self._offcenter = offset

    @property
    def decoration(self):
        return self._decoration
    
    @decoration.setter
    def set_decoration(self, decoration):
        self._decoration = decoration

    @property
    def transformation(self):
        return self._transformation
    
    @transformation.setter
    def set_transformation(self, transformation):
        self._transformation = transformation

    def make_anchors(self, *args, **kwargs):
        raise NotImplementedError
    
    def calculate_the_shape(self):
        raise NotImplementedError
    
    def calculate_anchor_orientation(self):
        raise NotImplementedError
    
    def paint_the_shape(self, qp):
        raise NotImplementedError

class rectangle(baseShape):
    pass

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
