import zmq
import _pickle
import numpy as np
from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSlot as Slot
import time
import pyqtgraph as pg
from functools import partial

#host ='max-p3a016.desy.de'
#port = 44391

class zmqListener(QtCore.QObject):
    zmq_event = QtCore.pyqtSignal(object, object)

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.host_name = ''
        self.port = 0
        #self.datasources = []
        self.selected_datasource = ''
        self.origin = (0,0)
        self.unit = 'mm'
        self.pixel_size = (0.01,0.01)
        self.shape = (0,0)
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.connected = False
        self.listening = False
        self.meta_data = {}

    def update_host_and_port(self, host, port):
        self.host_name = host
        self.port = port

    def listening_loop(self):
        # self.connect_zmq_server()
        # self.listening = True
        while self.listening:
            if self.receive_data_stream_one_shot():
                self.zmq_event.emit(np.fliplr(np.rot90(self.data,2)), self.meta_data)
            else:
                continue

    def start_listen_server(self):
        self.listening = True

    def stop_listen_server(self):
        self.listening = False

    def connect_zmq_server(self):
        if not self.connected:
            try:
                self.socket.connect(f"tcp://{self.host_name}:{self.port}")
                self.connected = True
                print('succed to connect to socket')
            except Exception as err:
                self.parent.statusbar.showMessage(f'Fail to connect due to: {err}')
        else:
            return

    def _subscribe_to_topic(self, topic):
        #topic='' to subscribe all sources
        if topic!=self.selected_datasource:
            self.socket.unbind(f"tcp://{self.host_name}:{self.port}")
            self.socket.setsockopt(zmq.UNSUBSCRIBE, bytes(self.selected_datasource,'utf8'))
            self.socket.setsockopt(zmq.UNSUBSCRIBE, bytes('','utf8'))
            self.socket.setsockopt(zmq.SUBSCRIBE, bytes(topic,'utf8'))
            self.socket.connect(f"tcp://{self.host_name}:{self.port}")
            self.selected_datasource = topic
        else:
            self.socket.setsockopt(zmq.SUBSCRIBE, bytes(topic,'utf8'))
    
    def _disconnect_server(self):
        self.socket.unbind(f"tcp://{self.host_name}:{self.port}")
        self.socket.setsockopt(zmq.UNSUBSCRIBE, bytes(self.selected_datasource,'utf8'))
        self.stop_listen_server()

    def receive_data_stream_one_shot(self):
        try:
            message = self.socket.recv_multipart(flags=zmq.NOBLOCK)
        except:
            return False
        md_dict = _pickle.loads(message[2])
        md_dict.pop('datasources')
        #datasources = md_dict['datasources']
        self.origin = md_dict['origin']
        self.pixel_size = md_dict['pixel_size']
        self.unit = md_dict['unit']
        self.dtype = md_dict['dtype']
        self.shape = md_dict['shape']
        #get the data finally
        self.data = np.frombuffer(message[1], dtype=self.dtype).reshape(self.shape)
        self.meta_data = md_dict
        # self.parent.update_meta_info()
        return True

class zmq_control_panel(object):
    def __init__(self, parent=None):
        self.zmq_listener = zmqListener(parent = self)
        self.zmq_listener_thread = QtCore.QThread()
        self.zmq_listener.moveToThread(self.zmq_listener_thread)
        self.zmq_listener_thread.started.connect(self.zmq_listener.listening_loop)
        self.xrf_roi = None
        #set invert Y axis
        self.widget_taurus_2d_plot.img.getViewBox().invertY(True)

    def _disconnect_zmq_server(self):
        self.zmq_listener._disconnect_server()

    def _read_zmq_settings(self):
        self.host_name = self.settings_object.get('zmq',{}).get('host_name','')
        if self.host_name=='':
            self.statusbar.showMessage('host name info is not existing in the config file')
            return False
        self.port = self.settings_object.get('zmq',{}).get('port','')
        if self.port=='':
            self.statusbar.showMessage('zmq port info is not existing in the config file')
            return False
        return True

    def _add_roi(self, p1, p2):
        if self.xrf_roi != None:
            self.widget_taurus_2d_plot.img_viewer.vb.removeItem(self.xrf_roi)
        w = abs(p2.x() - p1.x())
        l = abs(p2.y() - p1.y())
        origin = p1.x() + 0.042, p1.y()
        pen = pg.mkPen((0, 200, 200), width=1)
        self.xrf_roi = pg.ROI(origin,[w,l],pen=pen)
        self.xrf_roi.handleSize = 10
        self.xrf_roi.handlePen = pg.mkPen("#FFFFFF")
        self.xrf_roi.addScaleHandle([0, 0.5], [0.5, 0.5])
        self.xrf_roi.addScaleHandle([0.5, 0], [0.5, 0.5])
        self.widget_taurus_2d_plot.img_viewer.vb.addItem(self.xrf_roi)

    def _formulate_scan_cmd(self):
            main_gui = self
            scan_cmd = main_gui.lineEdit_scan_cmd.text()
            stage_x = main_gui.lineEdit_sample_stage_name_x.text()
            stage_y = main_gui.lineEdit_sample_stage_name_y.text()
            step_size = eval(f"({main_gui.lineEdit_step_size_h.text()},{main_gui.lineEdit_step_size_v.text()})")
            # steps_x = main_gui.spinBox_steps_hor.value()
            # steps_y = main_gui.spinBox_steps_ver.value()
            width, height = self.xrf_roi.size()
            steps_x = int(width/step_size[0]*1000)
            steps_y = int(height/step_size[1]*1000)
            sample_x_stage_start_pos, sample_y_stage_start_pos = self.xrf_roi.pos()
            exposure_time = float(main_gui.lineEdit_exposure_time.text())
            scan_cmd_str = f'{scan_cmd} {stage_x}' + \
                        f' {round(sample_x_stage_start_pos,4)} {round(sample_x_stage_start_pos+steps_x*step_size[0]/1000,4)} {steps_x}' + \
                        f' {stage_y} {round(sample_y_stage_start_pos,4)} {round(sample_y_stage_start_pos+steps_y*step_size[1]/1000,4)} {steps_y}'+\
                        f' {exposure_time}'
            main_gui.lineEdit_full_macro_name.setText(scan_cmd_str)
            main_gui.lineEdit_pre_scan_action_list.setText(f"[['mv',{stage_x}, {round(sample_x_stage_start_pos,4)}],['mv',{stage_y}, {round(sample_y_stage_start_pos,4)}]]")
            main_gui.add_one_task_to_scan_viewer(self.xrf_roi)

    def update_meta_info(self, meta_data):
        #meta_data = {'origin':self.zmq_listener.origin,
        #             'pixel_size': self.zmq_listener.pixel_size,
        #             'unit': self.zmq_listener.unit,
        #             'shape': self.zmq_listener.shape}
        self.lineEdit_origin.setText(str(meta_data.get('origin','')))
        self.lineEdit_pixel_size.setText(str(meta_data.get('pixel_size','')))
        self.lineEdit_unit.setText(str(meta_data.get('unit','')))
        self.lineEdit_shape.setText(str(meta_data.get('shape','')))
        pixel_size_str = self.lineEdit_pixel_size.text()
        origin_str = self.lineEdit_origin.text()
        shape_str = self.lineEdit_shape.text()
        try:
            pixel_size = eval(pixel_size_str)[0]
            origin = eval(origin_str)
            shape = eval(shape_str)
            self.widget_taurus_2d_plot.img.setScale(pixel_size)
            self.widget_taurus_2d_plot.img.setX(origin[0])
            self.widget_taurus_2d_plot.img.setY(origin[1])
            # self.widget_taurus_2d_plot.img.setY(origin[1]-shape[1]*pixel_size)
            # self.test_add_roi(origin, pixel_size*10, pixel_size*10)
        except:
            pass

    def connect_zmq_server(self):
        #if not self.zmq_listener_thread.isRunning():
        #    print('start thread for zmq listening')
        #    if not self.zmq_listener_thread.isRunning():
        if self._read_zmq_settings():
            print('update host and port')
            self.zmq_listener.update_host_and_port(self.host_name, self.port)
            print('connect zmq')
            self.zmq_listener.connect_zmq_server()
            print('get datasources')
            list_sources = self._get_datasource_topics()
            if len(list_sources)!=0:
                self.comboBox_datasources.clear()
                self.comboBox_datasources.addItems(list_sources)
                self.comboBox_datasources.currentIndexChanged.connect(self._upon_datasource_change)
                self._upon_datasource_change()
            # self.zmq_listener_thread.start()

    def _start_thread(self):
        print('start thread upon clicking')
        self.zmq_listener_thread.start()

    def _upon_datasource_change(self):
        topic = self.comboBox_datasources.currentText()
        self.zmq_listener.stop_listen_server()
        self.zmq_listener._subscribe_to_topic(topic)
        self.zmq_listener.start_listen_server()
        # time.sleep(0.5)
        # self.update_meta_info()

    def _get_datasource_topics(self):
        self.zmq_listener._subscribe_to_topic('')
        message = None
        for i in range(10):
            try:
                message = self.zmq_listener.socket.recv_multipart(flags=zmq.NOBLOCK)
                break
            except:
                time.sleep(0.1)
                print(f'Failed to read {i}', 'sleep for 0.1 sec')
        if message!=None:
            md_dict = _pickle.loads(message[2])
            #get the type of datasources topic                              
            self.datasources = md_dict['datasources']
            # self.zmq_listener.socket.setsockopt(zmq.UNSUBSCRIBE, b'')
            return self.datasources
        else:
            return []
    
    def subscribe_to_topic(self, topic):
        #topic='' to subscribe all sources
        self.zmq_listener._subscribe_to_topic(topic)
        self.selected_datasource = topic

    @Slot(object, object)
    def update_image_data_from_zmq_server(self, data, meta_data):
        self.widget_taurus_2d_plot.img.setImage(data)
        self.update_meta_info(meta_data)

    def update_coordinate(self, evt):
        coor = self.widget_taurus_2d_plot.img.getViewBox().mapSceneToView(evt)
        x, y = coor.x(), coor.y()
        self.statusbar.showMessage(f'cursor pos: [{x},{y}]')

    def _mouseDragEvent(self, ev):
        source_object = self.widget_taurus_2d_plot.img.getViewBox()
        # ev = source_object.mapSceneToView(ev)
        ev.accept() 
        if ev.button() == QtCore.Qt.LeftButton:
            if ev.isFinish():

                x0, x1, y0, y1 = ev.buttonDownPos().x(), ev.pos().x(),  ev.buttonDownPos().y(),  ev.pos().y()
                #print(x0,y0,x1,y1)
                if x0 > x1:
                    x0, x1 = x1, x0
                if y0 < y1:
                    y0, y1 = y1, y0
                # if x0 < 0:
                    # x0 = 0

                p1 = source_object.mapSceneToView(QtCore.QPointF(x0,y0))
                p2 = source_object.mapSceneToView(QtCore.QPointF(x1,y1))
                self._add_roi(p1,p2)      
                #self.statusbar.showMessage(f'selected area: {p1},{p2}')
            else:
                x0, y0= ev.pos().x(), ev.pos().y()
                self.statusbar.showMessage(f'{x0},{y0},{source_object.mapSceneToView(QtCore.QPointF(x0,y0))}')

    def zmq_connect_slots(self):
        self.pushButton_connect_zmq.clicked.connect(self.connect_zmq_server)
        self.pushButton_start_zmq_thread.clicked.connect(self._start_thread)
        self.zmq_listener.zmq_event.connect(self.update_image_data_from_zmq_server)
        self.widget_taurus_2d_plot.img.getViewBox().scene().sigMouseMoved.connect(self.update_coordinate)
        self.widget_taurus_2d_plot.img.getViewBox().mouseDragEvent = self._mouseDragEvent
        self.pushButton_apply_roi.clicked.connect(self._formulate_scan_cmd)