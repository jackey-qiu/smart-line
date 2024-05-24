#taurus style api
from taurus.core.util.colors import (ColorPalette, DEVICE_STATE_DATA, ATTRIBUTE_QUALITY_DATA,) 
from taurus.qt.qtgui.util.tauruscolor import QtColorPalette 
from taurus.core.taurusbasetypes import AttrQuality 
from taurus.core.tango import DevState
import numpy as np
QT_DEVICE_STATE_PALETTE = QtColorPalette(DEVICE_STATE_DATA, DevState) 
QT_ATTRIBUTE_QUALITY_PALETTE = QtColorPalette(ATTRIBUTE_QUALITY_DATA, AttrQuality) 

MAX_TRANSLATION_RANGE = {'x': [-20, 20], 'y': [-20, 20], 'rot': [0,360]}

__all__ = ['callback_model_change_with_decoration',
           'callback_model_change_with_transformation',
           'callback_model_change_with_decoration',
           'callback_model_change_with_text_label',
           'callback_leftmouse_click_with_decoration',
           'callback_leftmouse_click_with_transformation',
           'callback_model_change_with_decoration_on_off', 
           'callback_model_change_with_text_label_on_off']

def _apply_translation_steps(shape, value_model, mv_dir = 'x', sign = '+', model_limits = None, max_translation_range = None, val_ix = None, translate = 'True'):
    if type(translate)==str:
        translate = eval(translate)
        
    if mv_dir not in ['x', 'y']:
        return
    x, y = shape.ref_geometry
    x_current, y_current = shape.compute_center_from_dim(apply_translate = True)
    if model_limits == None:
        lms_model = [each.m for each in _get_model_value_limits(value_model, lm_type=None)]
    else:
        lms_model = eval(model_limits)
    if lms_model[0]==float('-inf') or lms_model[1]==float('inf'):
        return
    if max_translation_range == None:
        relative_lms_widget = MAX_TRANSLATION_RANGE[mv_dir]
    else:
        relative_lms_widget = eval(max_translation_range)
    lms_widget_x = [x+each for each in relative_lms_widget]
    lms_widget_y = [y+each for each in relative_lms_widget]
    if mv_dir == 'x':
        lms_widget = lms_widget_x
    else:
        lms_widget = lms_widget_y
    pxs_per_step = (lms_widget[1]-lms_widget[0])/(lms_model[1]-lms_model[0])
    model_value = _get_model_value(value_model)
    if type(model_value) in [list, np.array]:
        model_value = model_value[int(val_ix)]
    if not translate:
        new_pxs_widget = int((model_value - lms_model[0])*pxs_per_step)
        shape.dim_pars = (np.array(shape.dim_pars) * [1,1,1,0] + [0,0,0,new_pxs_widget]).astype(int)
        return
    if sign == '+':
        new_pxs_widget = int((model_value - lms_model[0])*pxs_per_step + lms_widget[0])
        #new_pxs_widget = int((model_value - lms_model[0])*pxs_per_step)
    else:
        new_pxs_widget = int(lms_widget[1] - (model_value - lms_model[0])*pxs_per_step)
        #new_pxs_widget = int((model_value - lms_model[0])*pxs_per_step)
    #shape.dim_pars = (np.array(shape.dim_pars) * [1,1,1,0] + [0,0,0,new_pxs_widget]).astype(int)
    #return
    if mv_dir=='x':
        offset = {'translate': (int(new_pxs_widget), shape.transformation['translate'][1])}
    else:
        offset = {'translate': (shape.transformation['translate'][0], int(new_pxs_widget))}
    shape.transformation = offset

def _get_model_value(value_model):
    return value_model.rvalue.m

def _get_model_value_quality_color(value_model):
    return QT_ATTRIBUTE_QUALITY_PALETTE.rgb(value_model.quality)

def _get_model_value_parent_object(value_model):
    #return the associated tango device proxy for the attribute model
    return value_model.getParentObj()

def _get_model_value_limits(value_model, lm_type = None):
    if lm_type == None:
        return value_model.getLimits()
    elif lm_type == 'warning':
        return value_model.getWarnings()
    elif lm_type == 'alarm':
        return value_model.getWarnings()

def callback_model_change_with_decoration_on_off(shape, value_model):
    _value = bool(value_model.rvalue)
    if _value:
        new_decoration = {'brush': {'color': (0, 255, 0)}}
    else:
        new_decoration = {'brush': {'color': (255, 255, 255)}}
    shape.decoration = new_decoration
    shape.decoration_cursor_on = new_decoration
    shape.decoration_cursor_off = new_decoration
    
def callback_model_change_with_decoration(shape, value_model):
    new_decoration = {'brush': {'color': tuple(list(_get_model_value_quality_color(value_model))+[100])}}
    shape.decoration = new_decoration
    shape.decoration_cursor_on = new_decoration
    shape.decoration_cursor_off = new_decoration

def callback_model_change_with_transformation(shape, value_model, mv_dir, sign = '+',model_limits = None, max_translation_range = None, val_ix = None, translate = 'True'):
    _apply_translation_steps(shape, value_model,mv_dir, sign, model_limits, max_translation_range, val_ix, translate)
    callback_model_change_with_decoration(shape, value_model)

def callback_model_change_with_text_label(shape, value_model, anchor='left', orientation='horizontal'):
    shape.labels = {'text':[f'{value_model.label}:{round(_get_model_value(value_model),3)}'],'anchor':[anchor], 'orientation': [orientation]}

def callback_model_change_with_text_label_on_off(shape, value_model, anchor='left', text = ""):
    checked = bool(value_model.rvalue)
    if checked:
        shape.labels = {'text':[f'{text} on'],'anchor':[anchor],'orientation': ['horizontal']}
    else:
        shape.labels = {'text':[f'{text} off'],'anchor':[anchor], 'orientation': ['horizontal']}

def callback_leftmouse_click_with_decoration(shape, value_model):
    pass

def callback_leftmouse_click_with_transformation(shape, value_model):
    pass

