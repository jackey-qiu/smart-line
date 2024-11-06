import numpy as np
import weakref
import typing
from PyQt5.QtWidgets import QMainWindow, QApplication
from PyQt5 import QtCore
from threading import Event, Thread
import time
from copy import deepcopy
from pathlib import Path

def get_folder(topic):
    if topic=='ui':
        folder = Path(__file__).parent.parent / "gui" /"ui"

    return folder

def remove_multiple_tabs_from_tabWidget(ix_info:dict,tabWidget):
    if len(ix_info)==0:
        return
    ix = []
    for (_, value) in ix_info.items():
        if not value['show']:
            ix.append(int(value['index']))
    ix_formated = sorted(ix)[::-1]
    for each in ix_formated:
        tabWidget.removeTab(each)

def generate_pyqtgraph_par_tree_from_config(settings_object: dict={}):
    type_map = {int:'int',float:'float',bool:'bool', str:'str', type(None):'str'}
    pars = []
    for (each, item) in settings_object.items():
        pars.append({'name': each})
        type_out1 = type(item)
        if type_out1 == list:
            type_out2 = type(item[0])
            if type_out2 == dict:
                pars[-1]['type'] = 'group'
                pars[-1]['children'] = []
                for i in range(len(item)):
                    pars[-1]['children'].append({'name':f'case{i+1}','type':'group','children':[]})
                    item1_dict = item1[i]
                    for (each2, item2) in item1_dict.items():
                        type_item2 = type(item2)
                        if type_item2 not in [dict, list]:
                            pars[-1]['children'][-1]['children'].append({'name':each2,'type':type_map[type_item2],'value':item2})
                        else:
                            pars[-1]['children'][-1]['children'].append({'name':each2,'type':'str','value':str(item2)})                            
            else:#a list of normal type
                pars[-1]['type'] = 'str'
                pars[-1]['value'] = str(item)                
                # pars_temp = {'name': each,'type': type_map[type_], 'value': item}
        elif type_out1 == dict: #a dict
            pars[-1]['type'] = 'group'
            pars[-1]['children'] = []
            for (each1, item1) in item.items():
                type_item1 = type(item1)
                if type_item1==dict:
                    pars[-1]['children'].append({'name':each1,'type':'group','children':[]})
                    for (each2, item2) in item1.items():
                        type_item2 = type(item2)
                        if type_item2 not in [dict, list, type(None)]:
                            pars[-1]['children'][-1]['children'].append({'name':each2,'type':type_map[type_item2],'value':item2})
                        else:
                            pars[-1]['children'][-1]['children'].append({'name':each2,'type':'str','value':str(item2)})
                elif type_item1==list:
                    if type(item1[0])==dict:#list of dict
                        pars[-1]['children'].append({'name':each1,'type':'group','children':[]})
                        for i in range(len(item1)):
                            pars[-1]['children'][-1]['children'].append({'name':f'case{i+1}','type':'group','children':[]})
                            item1_dict = item1[i]
                            for (each2, item2) in item1_dict.items():
                                type_item2 = type(item2)
                                if type_item2 not in [dict, list, type(None)]:
                                    pars[-1]['children'][-1]['children'][-1]['children'].append({'name':each2,'type':type_map[type_item2],'value':item2})
                                else:
                                    pars[-1]['children'][-1]['children'][-1]['children'].append({'name':each2,'type':'str','value':str(item2)})                            
                    else:#a list of normal type
                        pars[-1]['children'].append({'name':each1,'type':'str','value':str(item1)})
                else:
                    pars[-1]['children'].append({'name':each1,'type':type_map[type_item1],'value':item1})
    return pars

class trigger(QtCore.QObject):
    def __init__(self, cb = lambda:None, timeout = 10, repeat = False):
        super().__init__()
        self.cb = cb
        self.timeout = timeout
        self.repeat = repeat

    def start_new_cb(self, cb, timeout = None):
        self.cb = cb
        if timeout != None:
            self.timeout = timeout

    def run(self):
        start = time.time()
        while True:
            if (time.time() - start) > self.timeout:
                self.cb()
                if self.repeat:
                    start = time.time()
                else:
                    break
class trigger2(QtCore.QObject):
    def __init__(self, cb = lambda:None, timeout = 10):
        super().__init__()
        self.cb = cb
        self.timeout = timeout

    def start_new_cb(self, cb, timeout = None):
        self.cb = cb
        if timeout != None:
            self.timeout = timeout

    def run(self):
        start = time.time()
        while True:
            if (time.time() - start) > self.timeout:
                self.cb()
                break

def findMainWindow() -> typing.Union[QMainWindow, None]:
    # Global function to find the (open) QMainWindow in application
    app = QApplication.instance()
    for widget in app.topLevelWidgets():
        if isinstance(widget, QMainWindow):
            return widget
    return None

def get_stage_coords_from_tif_file_from_p06_desy(file_path):
    #func to extract the motor stage info from the generated tiff file at P06 beamline, DESY
    #Author: Jan Garrevoet
    #Note: The origin is by default located at top left site of the tif image.
    from PIL import Image
    with Image.open(file_path) as img:
        # Loading also the meaning from the tiff tags enum
        # just using the enum id
        meta_dict = {key : img.tag[key] for key in img.tag}

    # The origin and unit you get from
    description = meta_dict[270]
    desc_items = description[0].split("\n")

    for item in desc_items:
        if item.startswith("xorigin"):
            origin_x = float(item.split("=")[1])
        elif item.startswith("yorigin"):
            origin_y = float(item.split("=")[1])
        elif item.startswith("unit"):
            unit = item.split("=")[1]

    # The pixel size
    pixel_size_x = meta_dict[282][0][1] / meta_dict[282][0][0]
    pixel_size_y = meta_dict[283][0][1] / meta_dict[283][0][0]

    # Calculate the origin of the image in motor positions:
    motor_origin_x = -1 * pixel_size_x * origin_x
    motor_origin_y = -1 * pixel_size_y * origin_y
    return {'origin': (motor_origin_x, motor_origin_y), 'pix_size': (pixel_size_x, pixel_size_y), 'unit': unit}

def quick_level(data):
    while data.size > 1e6:
        ax = np.argmax((data.shape[0],data.shape[1],data.shape[2]))
        sl = [slice(None)] * data.ndim
        sl[ax] = slice(None, None, 2)
        data = data[sl]
    return np.percentile(data, 2.5), np.percentile(data, 97.5)

def quick_min_max(data):
    from numpy import nanmin, nanmax
    while data.size > 1e6:
        ax = np.argmax((data.shape[0],data.shape[1],data.shape[2]))
        sl = [slice(None)] * data.ndim
        sl[ax] = slice(None, None, 2)
        data = data[sl]
    return nanmin(data), nanmax(data)

class WeakList(object):

    def __init__(self):
        self._items = []

    def append(self, obj):
        #Add backwards to iterate backwards (to make iterating more efficient on removal).
        self._items.insert(0, weakref.ref(obj))

    def __iter__(self):
        i = len(self._items)-1
        while i >= 0:
            ref = self._items[i]
            d = ref()
            if d is None:
                del self._items[i]
            else:
                yield d
            i -= 1

from PyQt5 import QtCore, QtGui
import numpy as np
import qimage2ndarray
import copy

def fromPlainText(self, plainText):
    plainTextMacros = []
    macroInfos = []
    macroServerObj = self.getModelObj()
    unknownMacros = []
    for plainTextMacro in plainText.split('\n'):
        # stripping the whitespace characters
        plainTextMacro = plainTextMacro.strip()
        # ignoring the empty lines
        if len(plainTextMacro) == 0:
            continue
        # ignoring the commented lines
        if plainTextMacro[0] in self.comment_characters:
            continue
        macroName = plainTextMacro.split()[0]
        macroInfo = macroServerObj.getMacroInfoObj(macroName)
        if macroInfo is None:
            unknownMacros.append(macroName)
        plainTextMacros.append(plainTextMacro)
        macroInfos.append(macroInfo)
    if len(unknownMacros) > 0:
        msg = ("{0} macro(s) are not loaded in the "
                "MacroServer".format(", ".join(unknownMacros)))
        Qt.QMessageBox.warning(self, "Error while parsing the sequence",
                                msg)
        raise ValueError(msg)
    newRoot = self.tree.fromPlainText(plainTextMacros, macroInfos)
    return newRoot

def submit_jobs(sequence_widget, scan_list = ["ascan gap01 0 10 20 1", "ascan mot01 0 5 10 1"]):
    if len(scan_list)==0:
        return
    string = '\n'.join(scan_list)
    self = sequence_widget
    #@todo: reset macroComboBox to index 0
    try:
        root = self.fromPlainText(string)
        self._sequenceModel.setRoot(root)
        self.sequenceProxyModel.invalidateFilter()
        self.tree.expandAll()
        self.tree.expanded()
        self.parametersProxyModel.setMacroIndex(None)
        self.parametersProxyModel.invalidateFilter()

        if not self._sequenceModel.isEmpty():
            self.newSequenceAction.setEnabled(True)
            self.saveSequenceAction.setEnabled(True)
            self.playSequenceAction.setEnabled(True)
    except:
        self.tree.clearTree()
        self.playSequenceAction.setEnabled(False)
        self.newSequenceAction.setEnabled(False)
        self.saveSequenceAction.setEnabled(False)
        raise
    self.currentMacroChanged.emit(None)

def qt_image_to_array(img, share_memory=False):
    """ Creates a numpy array from a QImage.

        If share_memory is True, the numpy array and the QImage is shared.
        Be careful: make sure the numpy array is destroyed before the image,
        otherwise the array will point to unreserved memory!!
    """
    assert (img.format() == QtGui.QImage.Format.Format_RGB32 or \
            img.format() == QtGui.QImage.Format.Format_ARGB32_Premultiplied),\
        "img format must be QImage.Format.Format_RGB32, got: {}".format(
        img.format())

    '''
    img_size = img.size()
    buffer = img.constBits()
    buffer.setsize(img_size.height() * img_size.width() * img.depth() // 8)
    arr = np.frombuffer(buffer, np.uint8).reshape((img_size.width(), img_size.height(), img.depth() // 8))
    '''

    arr_rec = qimage2ndarray.recarray_view(img)
    #convert the grayscale already
    arr = arr_rec.r * 0.299 + arr_rec.g * 0.587 +arr_rec.b * 0.114

    if share_memory:
        return arr
    else:
        return copy.deepcopy(arr)

class PandasModel(QtCore.QAbstractTableModel):
    """
    Class to populate a table view with a pandas dataframe
    """
    def __init__(self, data, tableviewer, main_gui, parent=None, column_names = {}):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self.column_name_map = column_names
        self._data = data
        self.tableviewer = tableviewer
        self.main_gui = main_gui

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1]

    def data(self, index, role):
        cols = self._data.shape[1]
        checked_columns = [i for i in range(cols) if type(self._data.iloc[0, i])==np.bool_]
        if index.isValid():
            if role in [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole]:
                return str(self._data.iloc[index.row(), index.column()])
            if role == QtCore.Qt.BackgroundRole and index.row()%2 == 0:
                # return QtGui.QColor('green')
                return QtGui.QColor('DeepSkyBlue')
                #return QtGui.QColor('Blue')
            if role == QtCore.Qt.BackgroundRole and index.row()%2 == 1:
                return QtGui.QColor('white')
            if role == QtCore.Qt.BackgroundRole:
                if index.column() in checked_columns:
                    return QtGui.QColor('yellow')
                else:
                    return QtGui.QColor('white')
                # return QtGui.QColor('aqua')
                # return QtGui.QColor('lightGreen')
            # if role == QtCore.Qt.ForegroundRole and index.row()%2 == 1:
            if role == QtCore.Qt.ForegroundRole:
                if index.column() in checked_columns:
                    if self._data.iloc[index.row(), index.column()]:
                        return QtGui.QColor('green')
                    else:
                        return QtGui.QColor('red')
                else:
                    return QtGui.QColor('black')
            
            if role == QtCore.Qt.CheckStateRole and index.column() in checked_columns:
                if self._data.iloc[index.row(),index.column()]:
                    return QtCore.Qt.Checked
                else:
                    return QtCore.Qt.Unchecked
        return None

    def setData(self, index, value, role):
        cols = self._data.shape[1]
        checked_columns = [i for i in range(cols) if type(self._data.iloc[0, i])==np.bool_]        
        if not index.isValid():
            return False
        if role == QtCore.Qt.CheckStateRole and index.column() in checked_columns:
            if value == QtCore.Qt.Checked:
                self._data.iloc[index.row(),index.column()] = True
            else:
                self._data.iloc[index.row(),index.column()] = False
        else:
            if str(value)!='':
                self._data.iloc[index.row(),index.column()] = str(value)
        # if self._data.columns.tolist()[index.column()] in ['select','archive_date','user_label','read_level']:
            # self.update_meta_info_paper(paper_id = self._data['paper_id'][index.row()])
        self.dataChanged.emit(index, index)
        self.layoutAboutToBeChanged.emit()
        self.dataChanged.emit(self.createIndex(0, 0), self.createIndex(self.rowCount(0), self.columnCount(0)))
        self.layoutChanged.emit()
        # self.tableviewer.resizeColumnsToContents() 
        # self.tableviewer.horizontalHeader().setStretchLastSection(True)
        return True
    
    def update_view(self):
        self.tableviewer.resizeColumnsToContents() 
        self.layoutAboutToBeChanged.emit()
        self.dataChanged.emit(self.createIndex(0, 0), self.createIndex(self.rowCount(0), self.columnCount(0)))
        self.layoutChanged.emit()

    def headerData(self, rowcol, orientation, role):
        map_words = self.column_name_map
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            tag = self._data.columns[rowcol]         
            if tag in map_words:
                return map_words[tag]
            else:
                return tag
        if orientation == QtCore.Qt.Vertical and role == QtCore.Qt.DisplayRole:
            return self._data.index[rowcol]         
        return None

    def flags(self, index):
        if self._data.shape[0]==0:
            return
        cols = self._data.shape[1]
        checked_columns = [i for i in range(cols) if type(self._data.iloc[0, i])==np.bool_]        
        if not index.isValid():
           return QtCore.Qt.NoItemFlags
        else:
            if index.column() in checked_columns:
                return (QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsUserCheckable)
            else:
                return (QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEditable)
            """
            if index.column()==0:
                return (QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsUserCheckable)
            else:
                return (QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            """
    def sort(self, Ncol, order):
        """Sort table by given column number."""
        #self._data['sort_me'] = self._data[self._data.columns.tolist()[Ncol]]
        self.layoutAboutToBeChanged.emit()
        self._data = self._data.sort_values(self._data.columns.tolist()[Ncol],
                                        ascending=order == QtCore.Qt.AscendingOrder, ignore_index = True)
        # self._data = self._data.sort_values(self._data.columns.tolist()[Ncol],
                                        # ascending=order == QtCore.Qt.AscendingOrder, ignore_index = True, key=_to_pinyin)
        self.dataChanged.emit(self.createIndex(0, 0), self.createIndex(self.rowCount(0), self.columnCount(0)))
        self.layoutChanged.emit()
        # self._data.drop(columns='sort_me', inplace=True)