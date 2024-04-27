from taurus.qt.qtgui.base import TaurusBaseComponent
from taurus.external.qt import Qt
from taurus import Device
from pyqtgraph import GraphicsLayoutWidget
import pyqtgraph as pg
from PyQt5 import QtCore

from .shape_container import shapeComposite, rectangle

SHAPE_MAP = {'rectangle': rectangle}

class slit(shapeComposite):

    def __init__(self, cen_ref = None, blade_lf = None, blade_rt = None, blade_top = None, blade_bottom = None):
        #blade_lf = {'shape': 'rectangle', 'shape_args': [0,0,20,40]}
        #shapeComposite(shapes = [cen_ref_obj, blade_lf_obj, blade_rt_obj, blade_top_obj, blade_bottom_obj]
        #               alignment_pattern = {'shapes':[[0,1],[0,2],[0,3],[0,4]], 
        #                                    'anchors':[['left','right'],['right', 'left'], ['top', 'bottom'],['bottom', 'top']]})
        shapes = self.build_shape([cen_ref, blade_lf, blade_rt, blade_top, blade_bottom])

    def build_shape(self, shape_pars):
        return [SHAPE_MAP[shape_par.pop('shape')](**shape_par) for shape_par in shape_pars]

