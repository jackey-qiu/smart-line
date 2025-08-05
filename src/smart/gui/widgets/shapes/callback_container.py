#taurus style api
from taurus.core.util.colors import (ColorPalette, DEVICE_STATE_DATA, ATTRIBUTE_QUALITY_DATA,) 
from taurus.qt.qtgui.util.tauruscolor import QtColorPalette 
from taurus.core.taurusbasetypes import AttrQuality 
from taurus.core.tango import DevState
import numpy as np
from magicgui import magicgui
from enum import Enum
from taurus.qt.qtgui.panel import TaurusDevicePanel
try:
    from blissclient import BlissClient, get_object
    client = BlissClient()
except:
    client = None

QT_DEVICE_STATE_PALETTE = QtColorPalette(DEVICE_STATE_DATA, DevState) 
QT_ATTRIBUTE_QUALITY_PALETTE = QtColorPalette(ATTRIBUTE_QUALITY_DATA, AttrQuality) 

MAX_TRANSLATION_RANGE = {'x': [-20, 20], 'y': [-20, 20], 'rot': [0,360]}

__all__ = ['callback_model_change_with_decoration',
           'callback_model_change_with_transformation',
           'callback_model_change_with_decoration',
           'callback_model_change_with_text_label',
           'callback_leftmouse_click_change_txt_label',
           'callback_leftmouse_click_with_transformation',
           'callback_model_change_with_decoration_on_off', 
           'callback_model_change_with_text_label_on_off',
           'callback_model_change_with_decoration_valve_position',
           "callback_model_change_with_text_label_main_gui",
           'callback_model_change_with_decoration_on_off_idx',
           'callback_leftmouse_click_change_attribute_value',
           'callback_leftmouse_click_change_attribute_bool',
           'callback_rightmouse_click_set_step_size',
           'callback_rightmouse_click_show_device_panel',
           'callback_rightmouse_click_set_item',
           'callback_model_change_with_composite_rotation']

def _apply_translation_steps(shape, value_model, mv_dir = 'x', sign = '+', model_limits = None, max_translation_range = None, val_ix = None, translate = 'True'):
    if type(translate)==str:
        translate = eval(translate)
        
    if mv_dir not in ['x', 'y']:
        return
    x, y = shape.ref_geometry
    x_current, y_current = shape.compute_center_from_dim(apply_translate = True)
    if model_limits == None:
        lms_model = _get_model_value_limits(value_model, lm_type=None)
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
    if type(model_value) in [list, np.array, np.ndarray]:
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
    # print(lms_model,model_value,offset)
    shape.transformation = offset

def _get_model_value(value_model):
    rvalue = value_model.rvalue
    if type(rvalue) == bool:
        return int(rvalue)
    return rvalue.m

def _get_model_value_quality_color(value_model):
    return QT_ATTRIBUTE_QUALITY_PALETTE.rgb(value_model.quality)

def _get_model_value_parent_object(value_model):
    #return the associated tango device proxy for the attribute model
    return value_model.getParentObj()

def _get_model_value_limits(value_model, lm_type = None):
    if type(value_model.rvalue)==bool:
        return [0,1]
    if lm_type == None:
        return [each.m for each in value_model.getLimits()]
    elif lm_type == 'warning':
        return [each.m for each in value_model.getWarnings()]
    elif lm_type == 'alarm':
        return [each.m for each in value_model.getWarnings()]

def callback_model_change_with_decoration_on_off(parent, shape, value_model):
    _value = bool(value_model.rvalue)
    if _value:
        new_decoration = {'brush': {'color': (0, 255, 0)}}
    else:
        new_decoration = {'brush': {'color': (255, 255, 255)}}
    shape.decoration = new_decoration
    shape.decoration_cursor_on = new_decoration
    shape.decoration_cursor_off = new_decoration

def callback_model_change_with_decoration_on_off_idx(parent, shape, value_model, idx):
    _value = bool(value_model.rvalue[int(idx)])
    if _value:
        new_decoration = {'brush': {'color': (0, 255, 0)}}
    else:
        new_decoration = {'brush': {'color': (255, 255, 255)}}
    shape.decoration = new_decoration
    shape.decoration_cursor_on = new_decoration
    shape.decoration_cursor_off = new_decoration

def _update_connection(parent,syringe_key, shape_ix, set_true):
    if shape_ix in parent.syringe_lines_container[syringe_key]:
        parent.syringe_lines_container[syringe_key][shape_ix][1] = set_true
    else:
        pass
        #print(list(parent.syringe_lines_container[syringe_key].keys()))

def callback_model_change_with_decoration_valve_position(parent, shape, value_model, val_ix, connect_value, syringe_shape_name):
    model_value = _get_model_value(value_model)
    if type(model_value) in [list, np.array, np.ndarray]:
        model_value = model_value[int(val_ix)]
    if int(model_value) == int(connect_value):
        new_decoration = {'brush': {'color': (0, 255, 0)}}
        _update_connection(parent, syringe_shape_name, int(connect_value)+2, True)
    else:
        new_decoration = {'brush': {'color': (0, 0, 255)}}
        _update_connection(parent, syringe_shape_name, int(connect_value)+2, False)
    shape.decoration = new_decoration
    shape.decoration_cursor_on = new_decoration
    shape.decoration_cursor_off = new_decoration

def callback_model_change_with_decoration(shape, value_model):
    new_decoration = {'brush': {'color': tuple(list(_get_model_value_quality_color(value_model))+[100])}}
    shape.decoration = new_decoration
    shape.decoration_cursor_on = new_decoration
    shape.decoration_cursor_off = new_decoration

def callback_model_change_with_transformation(parent, shape, value_model, mv_dir, sign = '+',model_limits = None, max_translation_range = None, val_ix = None, translate = 'True'):
    _apply_translation_steps(shape, value_model,mv_dir, sign, model_limits, max_translation_range, val_ix, translate)
    # callback_model_change_with_decoration(shape, value_model)

def callback_model_change_with_text_label(parent, shape, value_model, anchor='left', orientation='horizontal', val_ix = None, sf = 1, label="", end_txt=""):
    if label==None:
        label = ''
    else:
        if len(label)==0:
            label = value_model.label+':'
    if val_ix == None or val_ix=='None':
        shape.labels = {'text':[f'{label}{round(_get_model_value(value_model)*float(sf),2)} {end_txt}'],'anchor':[anchor], 'orientation': [orientation]}
    else:
        shape.labels = {'text':[f'{label}{round(_get_model_value(value_model)[int(val_ix)]*float(sf),2)} {end_txt}'],'anchor':[anchor], 'orientation': [orientation]}
    # callback_model_change_with_decoration(shape, value_model)

def callback_model_change_with_composite_rotation(parent, shape, value_model, which_gap = None):
    if shape.parent==None:
        return
    # callback_model_change_with_decoration(shape, value_model)
    value = _get_model_value(value_model)
    shape.parent.rotate(value)
    if which_gap!=None:
        dy = shape._dynamic_attribute_yoffset
        dx = abs(dy/np.tan(np.radians(value*2)))
        shape.parent.set_dx_for_fix_exit(dx)
        shape.parent.alignment['gaps'][which_gap]=[int(dx), int(dy)]

#state updated from main gui attribute
def callback_model_change_with_text_label_main_gui(parent, shape, value_model, anchor='left', orientation='horizontal', attr= "attr", label="", end_txt=""):
    shape.labels = {'text':[f'{label}:{getattr(parent, attr)} {end_txt}'],'anchor':[anchor], 'orientation': [orientation]}

def callback_model_change_with_text_label_on_off(parent, shape, value_model, anchor='left', text = ""):
    checked = bool(value_model.rvalue)
    if checked:
        shape.labels = {'text':[f'{text} open'],'anchor':[anchor],'orientation': ['horizontal']}
    else:
        shape.labels = {'text':[f'{text} close'],'anchor':[anchor], 'orientation': ['horizontal']}

def callback_leftmouse_click_change_txt_label(parent, shape, value_model, label_options, color_options): 
   
    label_options = eval(label_options)
    color_options = eval(color_options)
    if shape.labels['text'][0] not in label_options:
        shape.labels = {'text':[f'{label_options[0]}']}
        i = 0
    else:
        i = label_options.index(shape.labels['text'][0])+1
        if i==len(label_options):
            i = 0
        shape.labels = {'text':[f'{label_options[i]}']}
    new_decoration = {'brush': {'color': color_options[i]+[255]}}
    shape.decoration = new_decoration
    shape.decoration_cursor_on = new_decoration
    shape.decoration_cursor_off = new_decoration 

def callback_leftmouse_click_with_transformation(parent, value_model): ...

def callback_leftmouse_click_change_attribute_value(parent, shape, value_model, change_value=0):
    if hasattr(shape, '_dynamic_attribute_change_value'):
        change_value = shape._dynamic_attribute_change_value
    else:
        change_value = 0
    value_model.write(value_model.rvalue.m + float(change_value))

def callback_leftmouse_click_change_attribute_bool(parent, shape, value_model):
    value_model.write(not bool(value_model.rvalue))

def callback_rightmouse_click_set_step_size(parent, shape, value_model, attr_name, composite_attr_name = None):
    complete_name = f'_dynamic_attribute_{attr_name}'
    if not hasattr(shape, complete_name):
        print(f'Attribute {complete_name} is not defined in the shape!')
        return
    else:
        attr_value = getattr(shape, complete_name)
    if composite_attr_name==None:
        composite_attr_name = 'composite_attr_name'
        composite_attr_value = float(0)
    else:
        if shape.parent==None:
            composite_attr_value = float(0)
        else:
            if hasattr(shape.parent, composite_attr_name):
                composite_attr_value = getattr(shape.parent, composite_attr_name)
    def run_bliss_scan(mot, start, end, intervals, ct):
        if client==None:
            print('No active bliss client! san is not running!')
        else:
            future=client.session.call('ascan', get_object(mot), start, end, intervals, ct, in_terminal=True)
            return future.state
    scan=Enum('scan',[('scan', True),('move', False)])
    if composite_attr_name!='composite_attr_name':
        @magicgui(call_button='Action',step_size={'min': -100, 'max': 100},start_value={'min': -100, 'max': 100}, composite_attr_value={'min': -100, 'max': 100})
        def setup_func(step_size=float(attr_value), start_value=float(value_model.rvalue.m), end_value=float(value_model.rvalue.m), intervals=int(2), count_time=1.0, scan=scan.move,composite_attr_name = composite_attr_name,composite_attr_value=float(composite_attr_value)):
            setattr(shape, complete_name, step_size)
            if scan.value:
                if value_model.factory().schemes==('bliss',):
                    mot=value_model._dev_name
                    state = run_bliss_scan(mot, start_value, end_value, intervals, count_time)
                    parent.statusbar.showMessage('summit scan request, state:'+str(state))
                else:
                    parent.statusbar.showMessage('scan is only supported with bliss scheme')
            else:
                value_model.write(end_value)
            if shape.parent!=None:
                if hasattr(shape.parent, composite_attr_name):
                    setattr(shape.parent, composite_attr_name, composite_attr_value)
    else:
        @magicgui(call_button='Action',step_size={'min': -100, 'max': 100},start_value={'min': -100, 'max': 100})
        def setup_func(step_size=float(attr_value), start_value=float(value_model.rvalue.m), end_value=float(value_model.rvalue.m),intervals=int(2), count_time=1, scan=scan.move):
            setattr(shape, complete_name, step_size)
            if scan.value:
                if value_model.factory().schemes==('bliss',):
                    mot=value_model._dev_name
                    state = run_bliss_scan(mot, start_value, end_value, intervals, count_time)
                    parent.statusbar.showMessage('summit scan request, state:'+str(state))
                else:
                    parent.statusbar.showMessage('scan is only supported with bliss scheme')
            else:
                value_model.write(end_value)       
    return setup_func        

def callback_rightmouse_click_set_item(parent, shape, value_model, attr_name,composite_attr_name = None, show_label = False):
    current_model_value = value_model.rvalue.m
    which = 0
    complete_name = f'_dynamic_attribute_{attr_name}'
    if not hasattr(shape, complete_name):
        print(f'Attribute {complete_name} is not defined in the shape!')
        return
    else:
        attr_value = getattr(shape, complete_name)
        values = list(attr_value.values())
        if current_model_value in values:
            which = values.index(current_model_value)
        attr_value = Enum('filters', attr_value.items())
    if composite_attr_name==None:
        composite_attr_name = 'composite_attr_name'
        composite_attr_value = float(0)
    else:
        if shape.parent==None:
            composite_attr_value = float(0)
        else:
            if hasattr(shape.parent, composite_attr_name):
                composite_attr_value = getattr(shape.parent, composite_attr_name)

    @magicgui(call_button='apply', composite_attr_value={'min': -100, 'max': 100})
    def setup_func(select_channel=getattr(attr_value, list(attr_value._member_map_.keys())[which]), composite_attr_name = composite_attr_name,composite_attr_value=float(composite_attr_value)):
        #setattr(shape, complete_name, step_size)
        print("selected value is:",select_channel.value)
        value_model.write(select_channel.value)
        if show_label:
            #shape.labels = {'text':[f'{label}{round(_get_model_value(value_model)*float(sf),2)} {end_txt}'],'anchor':[anchor], 'orientation': [orientation]}
            shape.labels['text']=[list(attr_value._member_map_.keys())[values.index(select_channel.value)]]
        if shape.parent!=None:
            if hasattr(shape.parent, composite_attr_name):
                setattr(shape.parent, composite_attr_name, composite_attr_value)
    return setup_func 


def callback_rightmouse_click_show_device_panel(parent, shape, value_model):
    #this func for displaying device panel conflit with magicgui popup frame
    #side effect is the mgicgui popup window close automatically after around 2 seconds
    dev_proxy = _get_model_value_parent_object(value_model)
    name = dev_proxy.name
    host = dev_proxy.get_db_host()
    port = dev_proxy.get_db_port()
    full_name = f'tango://{host}:{port}/{name}'
    setattr(parent, '_taurus_device_widget', TaurusDevicePanel())
    parent._taurus_device_widget.setModel(full_name)
    parent._taurus_device_widget.closeEvent = lambda _: setattr(parent, '_taurus_device_widget', None)
    parent._taurus_device_widget.show()

