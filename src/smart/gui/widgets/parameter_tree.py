# -*- coding: utf-8 -*-
from copy import deepcopy
from PyQt5.QtWidgets import QFileDialog
import pyqtgraph as pg
from pyqtgraph.parametertree import Parameter, ParameterTree
import pyqtgraph.parametertree.parameterTypes as pTypes
import configparser
from smart.util.util import generate_pyqtgraph_par_tree_from_config, findMainWindow
import yaml

#p.setReadonly(readonly=True)
class ScalableGroup(pTypes.GroupParameter):
    def __init__(self, head_txt = 'par', **opts):
        opts['type'] = 'group'
        opts['addText'] = "Add"
        opts['addList'] = ['str', 'float', 'int']
        opts['removable'] = True
        opts['renamable'] = True
        children = opts.pop('children')
        opts['children'] = []
        pTypes.GroupParameter.__init__(self, **opts)
        self.addSpecific_rows(children)
        self.head_txt = head_txt
    
    def addNew(self, typ):
        val = {
            'str': '',
            'float': 0.0,
            'int': 0
        }[typ]
        self.addChild(dict(name="%s %d" % (self.head_txt, len(self.childs)+1), type=typ, value=val, removable=True, renamable=True))

    def addSpecific_rows(self, rows):
        for each in rows:
            self.addChild(dict(name=each['name'], type=each['type'], value=each['value'], removable=True, renamable=True))

params_smart = [
    {'name': 'Camaras', 'type': 'group', 'children': [
        ScalableGroup(head_txt='Callback',name='camaraDataFormatCallbacks',children=[{'name': 'Callback 1', 'type': 'str', 'value': "lambda data:np.rot90(data[0].reshape((2048,2048,3)),3)"}]),
        {'name': 'camaraDevice', 'type': 'str', 'value': "tango://hasp029rack.desy.de:10000/p06/tangovimba/test.01"},
        {'name': 'camaraExposure_mode', 'type': 'group', 'children': [
            {'name': 'attr_name', 'type': 'str', 'value': "ExposureAuto"},
            {'name': 'options', 'type': 'str', 'value': "['off','Once','Continuous']"}]},
        {'name': 'camaraExposure_time', 'type': 'group', 'children': [
            {'name': 'attr_name', 'type': 'str', 'value': "ExposureTimeAbs"},
            {'name': 'default_value', 'type': 'str', 'value': "null"}]},
        {'name': 'camaraStreamModel', 'type': 'str', 'value': "tango://hasp029rack.desy.de:10000/p06/tangovimba/test.01/imageRaw"},
        {'name': 'click_move_timeout', 'type': 'int', 'value': 120},
        {'name': 'gridLayoutWidgetName', 'type': 'str', 'value': "gridLayout_cam"},
        {'name': 'pixel_size', 'type': 'str', 'value': "tango://hasp029rack.desy.de:10000/p06/mscope/lab.01/pixelsize"},
        {'name': 'presetZoom', 'type': 'str', 'value': "[60,80,100]"},
        {'name': 'rgb', 'type': 'bool', 'value': True},
        {'name': 'viewerWidgetName', 'type': 'str', 'value': "camara_widget"},
    ]},
    {'name': 'FileManager', 'type': 'group', 'children': [
        {"name":"currentImageDatabaseDir","type":"str","value":'C:\\Users\\_admin\\Downloads\\monitor_test'},
        {"name":"currentimagedbDir","type":"str","value":'C:/Users/qiucanro/Downloads'},
        {"name":"restoreimagedb","type":"str","value":'C:\\Users\\qiucanro\\apps\\imgReg\\imgReg\\ImageBackup.imagedb'},
    ]},
    {'name': 'General', 'type': 'group', 'children': [
        {"name":"ScaleColor","type":"str","value":'null'},
        {"name":"ScaleFontSize","type":"int","value":10},
        {"name":"ScaleHeight","type":"int","value":90},
        {"name":"ScalePosition","type":"str","value":"Bottom Right"},
        {"name":"ScaleSize","type":"int","value":1000},
        {"name":"beamlinePCHostName","type":"str","value":"hasm5570cq"},
        {"name":"connect_model_startup","type":"bool","value":True},
        {"name":"db","type":"str","value":"tango://hasp029rack.desy.de:10000"},
    ]},
    ScalableGroup(head_txt='motorxx',name='Motors',children =[
        {"name":"exp_mot03","type":"str","value":"tango://hasp029rack.desy.de:10000/p06/motor/exp.03"},
        {"name":"exp_mot04","type":"str","value":"tango://hasp029rack.desy.de:10000/p06/motor/exp.04"},
        {"name":"samly","type":"str","value":"tango://hasp029rack.desy.de:10000/p06/motor/exp.02"},
        {"name":"samlz","type":"str","value":'tango://hasp029rack.desy.de:10000/p06/motor/exp.01'},
    ]),
    {'name': 'Mscope', 'type': 'group', 'children': [
        {"name":"comboBox_illum_types","type":"str","value":'tango://hasp029rack.desy.de:10000/p06/beamlinemicroscopeillumination/test.01/AvailableIlluminationTypes'},
        {"name":"label_illum_pos","type":"str","value":'tango://hasp029rack.desy.de:10000/p06/beamlinemicroscopeillumination/test.01/intensity{}'},
    ]},
    {'name': 'PrimBeamGeo', 'type': 'group', 'children': [
        {"name":"img_x","type":"float","value":-1209},
        {"name":"img_y","type":"float","value":-2541},
        {"name":"iso_h","type":"float","value":-1472},
        {"name":"iso_v","type":"float","value":-222},
        {"name":"stage_x","type":"float","value":-5},
        {"name":"stage_y","type":"float","value":-33},
    ]},
    {'name': 'QueueControl', 'type': 'group', 'children': [
        {"name":"ntp_host","type":"str","value":'haspp06deb10'},
        {"name":"ntp_port","type":"str","value":"13345"},
    ]},
    {'name': 'SampleStageMotorNames', 'type': 'group', 'children': [
        {"name":"scanx","type":"str","value":'exp_mot03'},
        {"name":"scany","type":"str","value":"exp_mot04"},
        {"name":"scanz","type":"str","value":'exp_dmy02'},
        {"name":"x","type":"str","value":"samly"},
        {"name":"y","type":"str","value":"samlz"},
        {"name":"z","type":"str","value":"exp_dmy03"},
    ]},
    {'name': 'SampleStages', 'type': 'group', 'children': [
        {"name":"x_pstage_value","type":"str","value":'tango://hasp029rack.desy.de:10000/p06/motor/exp.03/position'},
        {"name":"x_stage_value","type":"str","value":"tango://hasp029rack.desy.de:10000/p06/motor/exp.02/position"},
        {"name":"y_pstage_value","type":"str","value":'tango://hasp029rack.desy.de:10000/p06/motor/exp.04/position'},
        {"name":"y_stage_value","type":"str","value":"tango://hasp029rack.desy.de:10000/p06/motor/exp.01/position"},
        {"name":"z_pstage_value","type":"str","value":"tango://hasp029rack.desy.de:10000/motor/dummy_mot_ctrl/2/position"},
        {"name":"z_stage_value","type":"str","value":"tango://hasp029rack.desy.de:10000/motor/dummy_mot_ctrl/3/position"},
    ]},
    ScalableGroup(head_txt='motorxx',name='motor_alias_address_map',children =[
        {"name":"exp_mot03","type":"str","value":"tango://hasp029rack.desy.de:10000/p06/motor/exp.03"},
        {"name":"exp_mot04","type":"str","value":"tango://hasp029rack.desy.de:10000/p06/motor/exp.04"},
        {"name":"samly","type":"str","value":"tango://hasp029rack.desy.de:10000/p06/motor/exp.02"},
        {"name":"samlz","type":"str","value":'tango://hasp029rack.desy.de:10000/p06/motor/exp.01'},
    ]),    
    {'name': 'spockLogin', 'type': 'group', 'children': [
        {"name":"doorAlias","type":"str","value":'Door-hasp029rack'},
        {"name":"doorName","type":"str","value":'tango://hasp029rack.desy.de:10000/p06/door/hasp029rack.01'},
        {"name":"msAlias","type":"str","value":'MS-hasp029rack'},
        {"name":"msName","type":"str","value":"tango://hasp029rack.desy.de:10000/p06/macroserver/hasp029rack.01"},
        {"name":"useQTSpock","type":"bool","value":True},
    ]},    
    {'name': 'ZoomDevice', 'type': 'group', 'children': [
        {"name":"label_zoom_pos","type":"str","value":'tango://hasp029rack.desy.de:10000/p06/mscope/lab.01/zoom'},
    ]},    
    {'name': 'widgetMaps', 'type': 'group', 'children': [
        {"name":"beamlineControlGpNames","type":"str","value":"['SampleStages','ZoomDevice']"},
    ]},    
]

## Create tree of Parameter objects
p_smart = Parameter.create(name='params', type='group', children=params_smart)

class SmartParameters(ParameterTree):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_type = None
        self.init_pars()

    def init_pars(self, pars = None):
        if pars!=None:
            p_smart = Parameter.create(name='params', type='group', children=generate_pyqtgraph_par_tree_from_config(pars))
        else:
            p_smart = Parameter.create(name='params', type='group', children=params_smart)
        self.setParameters(p_smart, showTop=False)
        self.par = p_smart

    def update_parameter(self,config_file):
        try:
            with open(str(config_file), "r", encoding="utf8") as f:
                par = self.convert_par_tree_to_dict()
                par.update(yaml.safe_load(f.read()))
                self.init_pars(par)
        except Exception as err:
            findMainWindow().statusbar.showMessage(f'Fail to update parameter tree due to {str(err)}')

    def apply_config(self):
        gui = findMainWindow()
        par = self.convert_par_tree_to_dict()
        gui.camara_widget.update_img_settings()#update the file value of PrimBeamGeo
        new_settings = dict([(key,value) for (key, value) in par.items() if key!='PrimBeamGeo'])
        gui.settings_object.update(new_settings)
        gui._upon_settings_change()

    def load_config(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()", "","Conf Files (*.yaml);;text Files (*.*)", options=options)
        if fileName:
            self.update_parameter(fileName)     

    def convert_par_tree_to_dict(self):
        par = self.par
        par_dict = {}
        for (key0,value0) in par.names.items():
            if type(value0)==pg.parametertree.parameterTypes.basetypes.SimpleParameter:
                temp = value0.value()
                if type(temp)==str and (temp.startswith('[') or temp.startswith('{')):
                    par_dict[key0] = eval(temp)
                else:
                    par_dict[key0] = temp
            else:
                par_dict[key0] = {}
                for (key1,value1) in value0.names.items():
                    if type(value1)==pg.parametertree.parameterTypes.basetypes.SimpleParameter:
                        temp = value1.value()
                        if type(temp)==str and (temp.startswith('[') or temp.startswith('{')):
                            par_dict[key0][key1] = eval(temp)
                        else:
                            par_dict[key0][key1] = temp    
                    else:
                        par_dict[key0][key1] = {}
                        if 'case' in list(value1.names.keys())[0]:
                            par_dict[key0][key1] = []
                        for (key2,value2) in value1.names.items():#three layers at maximum
                            if type(value2)==pg.parametertree.parameterTypes.basetypes.SimpleParameter:
                                temp = value2.value()
                                if type(temp)==str and (temp.startswith('[') or temp.startswith('{')):
                                    par_dict[key0][key1][key2] = eval(temp)
                                else:
                                    par_dict[key0][key1][key2] = temp
                            elif type(value2)==pg.parametertree.parameterTypes.basetypes.GroupParameter and ('case' in key2):
                                temp_dict = {}
                                for (key3, value3) in value2.names.items():
                                    try:
                                        temp_dict[key3] = value3.value()
                                    except:
                                        raise Exception('Too deep to unstructure. Maximum allowed depth: 3 levels')
                                par_dict[key0][key1].append(temp_dict)
                            else:
                                print(key0, key1, key2, type(value2))
                                raise Exception('Too deep to unstructure. Maximum allowed depth: 3 levels') 
        return par_dict                                   

    def save_parameter(self, config_file):
        config = configparser.ConfigParser()
        sections = self.par.names.keys()
        for section in sections:
            sub_sections = self.par.names[section].names.keys()
            items = {}
            for each in sub_sections:
                items[each] = str(self.par[(section,each)])
            config[section] = items
        with open(config_file,'w') as config_file:
            config.write(config_file)


