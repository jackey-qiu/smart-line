from taurus.qt.qtgui.base import TaurusBaseComponent
from taurus.external.qt import Qt
from taurus import Device
from pyqtgraph import GraphicsLayoutWidget
import pyqtgraph as pg
from PyQt5 import QtCore

from .shape_container import shapeComposite, rectangle, buildTools

SHAPE_MAP = {'rectangle': rectangle}

class slit(object):

    def __init__(self, config_file, composite_tag):
        #blade_lf = {'shape': 'rectangle', 'shape_args': [0,0,20,40]}
        #shapeComposite(shapes = [cen_ref_obj, blade_lf_obj, blade_rt_obj, blade_top_obj, blade_bottom_obj]
        #               alignment_pattern = {'shapes':[[0,1],[0,2],[0,3],[0,4]], 
        #                                    'anchors':[['left','right'],['right', 'left'], ['top', 'bottom'],['bottom', 'top']]})
        self.config_file = config_file
        self.composite_tag = composite_tag
        self.composite_shape = buildTools.build_composite_shape_from_yaml(self.config_file)[self.composite_tag]

    def set_model(self, model_list, shape_index_list):
        assert(len(model_list)==len(shape_index_list)), "The length of model_list and shape index list must equal."
        self.composite_shape.model_shape_index_list = shape_index_list
        self.set_callbacks()
        self.composite_shape.setModel(model_list)

    def set_callbacks(self):
        self.composite_shape.callbacks_upon_model_change = [lambda shape, value: None for i in range(len(self.composite_shape.model_shape_index_list))]
        self.composite_shape.callbacks_upon_left_mouseclick = [lambda shape, value: None for i in range(len(self.composite_shape.model_shape_index_list))]
        
    def callback_model_change_shape1(self, shape, value):
        pass
