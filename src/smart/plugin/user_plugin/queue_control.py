from . import p06io
from taurus import info, error, warning, critical, Device
from PyQt5.QtCore import pyqtSlot as Slot
from PyQt5.QtWidgets import  QAbstractItemView
from PyQt5 import QtCore
from smart.gui.widgets.event_dialogue import confirmation_dialogue, error_pop_up
from smart.util.util import PandasModel
import logging
import pandas as pd
from smart import icon_path

REQUIRED_KEYS = ['queue', 'scan_command', 'session']

class eventListener(QtCore.QObject):
    queue_entry_event = QtCore.pyqtSignal(list)
    queue_event = QtCore.pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.ntp_host = None
        self.ntp_port = None
        self.msg = None
        self.listening = False

    def update_host_and_port(self, host, port):
        self.ntp_host = host
        self.ntp_port = port

    def connect_queue_server(self, which_instance = 0):
        try:
            ntp_comm = p06io.zeromq.ClientReq(self.ntp_host, self.ntp_port)
            queue_info = ntp_comm.send_receive_message(["info", ["scan_queue"]],timeout=3)

            # In this case you will just have 1 instance running so you take instance zero
            instance_info = queue_info[list(queue_info.keys())[which_instance]]

            # All available connections are under the connections key
            self.brcast_host = instance_info["connections"]["broadcaster"]["host"]
            self.brcast_port = int(instance_info["connections"]["broadcaster"]["port"])
            self.brcast_comm = p06io.zeromq.ClientSub(self.brcast_host, self.brcast_port)
        except Exception as er:
            error(f"Fail to connect to queue server with the following error:/n {str(er)}") 

    def start_listen_server(self):
        self.connect_queue_server()
        self.listening = True
        while self.listening:
            self.msg = self.brcast_comm.receive_message()
            if self.msg[1] == 'entry_event':
                self.queue_entry_event.emit(self.msg[0])
            elif self.msg[1] == 'queue_event':
                self.queue_event.emit(self.msg[0])

    def stop_listen_server(self):
        self.listening = False
        self.msg = None

class queueControl(object):

    def __init__(self, parent=None):
        self.brcast_listener = eventListener()
        self.brcast_listener_thread = QtCore.QThread()
        self.brcast_listener.moveToThread(self.brcast_listener_thread)
        self.brcast_listener_thread.started.connect(self.brcast_listener.start_listen_server)
        self.ntp_host = self.settings_object["QueueControl"]["ntp_host"]
        self.ntp_port = int(self.settings_object["QueueControl"]["ntp_port"])
        self.brcast_listener.update_host_and_port(self.ntp_host, self.ntp_port)
        self.queue_comm = None
        self.queue_info = None
        self._create_toolbar_queue_widget()
        # self.set_models()

    def _create_toolbar_queue_widget(self):
        from PyQt5.QtWidgets import QToolBar, QAction
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QIcon
        self.queueToolBar = QToolBar('camera', self)
        #connect queue action
        action_connect_queue = QAction(QIcon(str(icon_path / 'smart' / 'connect_queue.png')),'connect to queue server',self)
        action_connect_queue.setStatusTip('Connect to queue server.')
        action_connect_queue.triggered.connect(self.connect_queue_server)
        self.queueToolBar.addAction(action_connect_queue)
        #get queue list
        action_get_queue = QAction(QIcon(str(icon_path / 'smart' / 'get_queues.png')),'get queue list from server',self)
        action_get_queue.setStatusTip('Extract queue list from the queue server.')
        action_get_queue.triggered.connect(self.get_available_queues)
        self.queueToolBar.addAction(action_get_queue)
        #create task
        action_create_task = QAction(QIcon(str(icon_path / 'smart' / 'create_task.png')),'create new task',self)
        action_create_task.setStatusTip('Create a new task and push it to the queue server.')
        action_create_task.triggered.connect(self.add_task_from_ui)
        self.queueToolBar.addAction(action_create_task)
        #update task
        action_update_task = QAction(QIcon(str(icon_path / 'smart' / 'update_task.png')),'update current task',self)
        action_update_task.setStatusTip('Update a task and push it to the queue server.')
        action_update_task.triggered.connect(self.update_task)
        self.queueToolBar.addAction(action_update_task)
        #enable task
        action_enable_task = QAction(QIcon(str(icon_path / 'smart' / 'enable_task.png')),'enable current task',self)
        action_enable_task.setStatusTip('Enable a paused task to set it to queued state and push it to the queue server.')
        action_enable_task.triggered.connect(lambda: self.change_state_of_a_task('enabled'))
        self.queueToolBar.addAction(action_enable_task)
        #disable task
        action_disable_task = QAction(QIcon(str(icon_path / 'smart' / 'disable_task.png')),'disable current task',self)
        action_disable_task.setStatusTip('Disable a queued task to set it to disabled state and push it to the queue server.')
        action_disable_task.triggered.connect(lambda: self.change_state_of_a_task('disabled'))
        self.queueToolBar.addAction(action_disable_task)
        #pause a task
        action_pause_task = QAction(QIcon(str(icon_path / 'smart' / 'pause_task.png')),'pause current task',self)
        action_pause_task.setStatusTip('Pause a queued task to set it to paused state and push it to the queue server.')
        action_pause_task.triggered.connect(lambda: self.change_state_of_a_task('paused'))
        self.queueToolBar.addAction(action_pause_task)
        #delete a task
        action_delete_task = QAction(QIcon(str(icon_path / 'smart' / 'delete_task.png')),'delete current task',self)
        action_delete_task.setStatusTip('Delete a task from the queue server.')
        action_delete_task.triggered.connect(self.remove_task)
        self.queueToolBar.addAction(action_delete_task)
        #run a queue
        action_run_queue = QAction(QIcon(str(icon_path / 'smart' / 'run_queue.png')),'run the current queue',self)
        action_run_queue.setStatusTip('Start running the queue of the selected queue name')
        action_run_queue.triggered.connect(self.run_queue)
        self.queueToolBar.addAction(action_run_queue)
        #finally add the toolbar
        self.addToolBar(Qt.LeftToolBarArea, self.queueToolBar)

    def connect_queue_server(self, which_instance = 0):
        try:
            ntp_comm = p06io.zeromq.ClientReq(self.ntp_host, self.ntp_port)
            queue_info = ntp_comm.send_receive_message(["info", ["scan_queue"]],timeout=3)

            # In this case you will just have 1 instance running so you take instance zero
            instance_info = queue_info[list(queue_info.keys())[which_instance]]
            # self.textEdit_queue_info_output.setPlainText(str(queue_info))

            # All available connections are under the connections key
            self.queue_host = instance_info["connections"]["communication"]["host"]
            self.queue_port = int(instance_info["connections"]["communication"]["port"])
            self.queue_comm = p06io.zeromq.ClientReq(self.queue_host, self.queue_port)
            #self.brcast_host = instance_info["connections"]["broadcaster"]["host"]
            #self.brcast_port = int(instance_info["connections"]["broadcaster"]["port"])
            #self.brcast_comm = p06io.zeromq.ClientSub(self.brcast_host, self.brcast_port)
            self.statusUpdate(f'Connect to queue server: {self.queue_host}:{self.queue_port}')
            self.get_available_queues()
            self.brcast_listener_thread.start()
            self.init_pandas_model_queue()
            self.widget_queue_synoptic_viewer.set_data(self.pandas_model_queue._data)
        except Exception as er:
            error(f"Fail to connect to queue server with the following error:/n {str(er)}") 
            self.statusUpdate(f'Failure to connect to queue server! error msg: {str(er)}')

    def get_available_queues(self, set_text_field = True):
        if self.queue_comm==None:
            # self.textEdit_queue_info_output.setPlainText('The queue comm is not yet created! Connect the queue server first.')
            return
        else:
            try:
                msg = self.queue_comm.send_receive_message("get_available_queues", timeout=3)
                current_txt = self.comboBox_queue_name_list.currentText()
                self.comboBox_queue_name_list.clear()
                self.comboBox_queue_name_list.addItems(eval(str(msg)))
                if current_txt in eval(str(msg)):
                    self.comboBox_queue_name_list.setCurrentText(current_txt)
                # if set_text_field:
                    # self.textEdit_queue_info_output.setPlainText(str(msg))
                return eval(str(msg))
            except Exception as err:
                error(f"Fail to run the command: get_available_queues. Error:/n {str(err)}")
                self.statusUpdate(f'Failure to run command get_available_queues!')

    def _clear_all_field(self):
        task_key_widget_setAPI_map = {'execution_id':self.lineEdit_exe_id.setText,
                          'queue':self.lineEdit_queue_name.setText,
                          'scan_command': self.lineEdit_cmd.setText,
                          'session': self.lineEdit_session.setText, 
                          'state': self.lineEdit_state.setText, 
                          'scan_info': self.lineEdit_scan_info.setText,
                          'unique_id': self.lineEdit_job_id.setText}
        for each in task_key_widget_setAPI_map.values():
            each('')

    def _format_queue(self):
        available_queues = self.get_available_queues(set_text_field=False)
        queue_info_dict = {'session':[], 'queue':[],'scan_command':[], 'scan_id':[], 'unique_id':[],'state':[]}
        if available_queues==None:
            return pd.DataFrame(queue_info_dict)
        else:
            for queue in available_queues:
                queue_info = self.queue_comm.send_receive_message(['get', queue],timeout=3)
                for task in queue_info:
                    task.update({'queue':queue})
                    for key in queue_info_dict:
                        if key == 'scan_command':
                            task[key] = ' '.join(task[key])
                        elif key == 'unique_id':
                            task[key] = int(task[key])
                        queue_info_dict[key].append(task[key])
        return pd.DataFrame.from_dict(queue_info_dict)
    
    def init_pandas_model_queue(self, table_view_widget_name='tableView_queue'):
        data = self._format_queue()
        #disable_all_tabs_but_one(self, tab_widget_name, tab_indx)
        self.pandas_model_queue = PandasModel(data = data, tableviewer = getattr(self, table_view_widget_name), main_gui=self)
        getattr(self, table_view_widget_name).setModel(self.pandas_model_queue)
        getattr(self, table_view_widget_name).resizeColumnsToContents()
        getattr(self, table_view_widget_name).setSelectionBehavior(QAbstractItemView.SelectRows)
        getattr(self, table_view_widget_name).horizontalHeader().setStretchLastSection(True)

    def display_info_for_a_queue(self, show_last_item = False):
        queue_name = str(self.comboBox_queue_name_list.currentText())
        msg = self.queue_comm.send_receive_message(['get', queue_name],timeout=3)
        tasks = []
        for each in msg:
            each.update({'queue':queue_name})
            tasks.append(str(each['unique_id']))
        self.queue_info = msg
        self.comboBox_queue_task.clear()
        self.comboBox_queue_task.addItems(tasks)
        # self.textEdit_queue_info_output.setPlainText('\n\n'.join([str(each) for each in msg]))
        if show_last_item:
            last = self.comboBox_queue_task.itemText(self.comboBox_queue_task.count()-1)
            self.comboBox_queue_task.setCurrentText(last)

    def remove_task(self, task_id):
        task_id = self.lineEdit_job_id.text()
        if task_id=='':
            return
        try:
            if not confirmation_dialogue(f'Are you sure to delete the task: {task_id}?'):
                return
            task_id = int(task_id)
            self.queue_comm.send_receive_message(['remove_entry', task_id], timeout=3)
            self.statusUpdate(f'The task with task_id of {task_id} is deleted!')            
            self._clear_all_field()
            self.display_info_for_a_queue()
        except Exception as err:
            error(f"Fail to delete the task. Error:\n {str(err)}")
            self.statusUpdate(f'Failure to delete task!')

    def remove_queue(self):
        queue = self.comboBox_queue_name_list.currentText()
        if queue=='':
            return
        try:
            if not confirmation_dialogue(f'Are you sure to delete the queue: {queue}?'):
                return
            self.queue_comm.send_receive_message(['remove_queue', queue], timeout=3)
            self.statusUpdate(f'The queue with queue name of {queue} is deleted!')            
            self._clear_all_field()
            self.get_available_queues()
            self.display_info_for_a_queue()
            self.init_pandas_model_queue()
            self.widget_queue_synoptic_viewer.set_data(self.pandas_model_queue._data)
        except Exception as err:
            error(f"Fail to delete the queue. Error:\n {str(err)}")
            self.statusUpdate(f'Failure to delete queue!')

    def add_task_from_ui(self):
        task_from_widget = {'execution_id':self.lineEdit_exe_id.text(),
                          'queue':self.lineEdit_queue_name.text(),
                          'scan_command': self.lineEdit_cmd.text().rsplit(' '),
                          'session': self.lineEdit_session.text(), 
                          'state': self.lineEdit_state.text(), 
                          'scan_info': self.lineEdit_scan_info.text()}
        
        task_from_widget = {'execution_id':self.lineEdit_exe_id.text(),
                          'queue':self.lineEdit_queue_name.text(),
                          'scan_command': self.lineEdit_cmd.text().rsplit(' '),
                          'session': self.lineEdit_session.text(), 
                          'scan_info': self.lineEdit_scan_info.text()}

        """
        scan_cmd = task_from_widget['scan_command']
        for i, each in enumerate(scan_cmd):
            try:
                if '.' in each:
                    scan_cmd[i] = float(each)
                else:
                    scan_cmd[i] = int(each)
            except:
                pass
        task_from_widget['scan_command'] = scan_cmd
        """
        # return
        self._append_task(task_from_widget)
        self.display_info_for_a_queue(show_last_item=True)
        # show the added item (last) after adding task
        #last = self.comboBox_queue_task.itemText(self.comboBox_queue_task.count()-1)
        #self.comboBox_queue_task.setCurrentText(last)

    @Slot(str)
    def update_queue_viewer_type(self, viewer_type):
        if viewer_type=='tableViewer':
            self.tableView_queue.show()
            self.widget_queue_synoptic_viewer.hide()
        else:
            self.tableView_queue.hide()
            self.widget_queue_synoptic_viewer.show()
            self.widget_queue_synoptic_viewer.set_data(self.pandas_model_queue._data)


    @Slot(str)
    def update_task_from_server(self, unique_id):

        if not unique_id:
            return
        msg = None
        if self.queue_info == None:
            return
        for each in self.queue_info:
            if each['unique_id']==int(unique_id):
                msg = each
                break
        queue_id_index = self.pandas_model_queue._data[self.pandas_model_queue._data['unique_id']==int(unique_id)].index.to_list()
        if len(queue_id_index)>0:
            queue_id = queue_id_index[0]
            msg.update({'queue_id': queue_id})
        else:
            msg.update({'queue_id': 'ERROR'})
        task_key_widget_setAPI_map = {'execution_id':self.lineEdit_exe_id.setText,
                          'queue':self.lineEdit_queue_name.setText,
                          'scan_command': self.lineEdit_cmd.setText,
                          'session': self.lineEdit_session.setText, 
                          'state': self.lineEdit_state.setText, 
                          'scan_info': self.lineEdit_scan_info.setText,
                          'queue_id': self.lineEdit_queue_id.setText,
                          'unique_id': self.lineEdit_job_id.setText}
        for key, value in msg.items():
            if key=='scan_command':
                value = ' '.join(value)
            if key in task_key_widget_setAPI_map:
                task_key_widget_setAPI_map[key](str(value))

    @Slot(QtCore.QModelIndex)
    def update_task_upon_click_tableview(self, modelindex):
        row = modelindex.row()
        queue = self.pandas_model_queue._data.iloc[row,:]['queue']
        queue_id = self.pandas_model_queue._data.iloc[row,:]['unique_id']
        queued_tasks = self.queue_comm.send_receive_message(["get", queue])
        task_info = None
        for each_task in queued_tasks:
            if each_task['unique_id']==queue_id:
                task_info = each_task
                break
        if task_info!=None:
            task_info.update({'queue': queue, 'queue_id': str(row)})
            task_key_widget_setAPI_map = {'execution_id':self.lineEdit_exe_id.setText,
                            'queue':self.lineEdit_queue_name.setText,
                            'scan_command': self.lineEdit_cmd.setText,
                            'session': self.lineEdit_session.setText, 
                            'state': self.lineEdit_state.setText, 
                            'scan_info': self.lineEdit_scan_info.setText,
                            'queue_id': self.lineEdit_queue_id.setText,
                            'unique_id': self.lineEdit_job_id.setText}
            for key, value in task_info.items():
                if key=='scan_command':
                    value = ' '.join(value)
                if key in task_key_widget_setAPI_map:
                    task_key_widget_setAPI_map[key](str(value))            

    @Slot(list)
    def update_queued_task_from_brcast_event(self, queue_list):
        self._update_queue_status()
        self.statusUpdate('The changed queue names are:'+' '.join(queue_list))
        self.init_pandas_model_queue()
        self.widget_queue_synoptic_viewer.set_data(self.pandas_model_queue._data)
        self.update_scan_roi_upon_state_change()
        # if self.comboBox_queue_name_list.currentText() in queue_list:
            # current_job_id = self.comboBox_queue_task.currentText()
            #self.display_info_for_a_queue()
            # self.comboBox_queue_task.setCurrentText(current_job_id)
            # self.display_info_for_a_queue()

    def update_scan_roi_upon_state_change(self):
        running_row = self.pandas_model_queue._data[self.pandas_model_queue._data['state']=='running']
        if len(running_row)==0:
            return
        queue = running_row['queue'].to_list()[0]
        cmd = running_row['scan_command'].to_list()[0]
        data = self.pandas_model_queue_camara_viewer._data
        #the active row ix
        try:
            which_row = ((data['scan_command'] == cmd) & (data['queue'] == queue)).to_list().index(True)
        except:
            which_row = None
        if which_row != None:
            self.update_roi_at_row(which_row)

    def _update_queue_status(self):
        pass    

    def _append_task(self,task):
        assert type(task)==dict, 'Task must be formated in a python dict'
        for each in REQUIRED_KEYS:
            if each not in task or task[each]=='':
                error(f'Required key {each} is not provided!')
                self.statusUpdate(f'Required key {each} is not provided!')
                return
        try:
            task['execution_id'] = int(task['execution_id'])
        except:
            task.pop('execution_id', None)
        try:
            self.queue_comm.send_receive_message(['add', task], timeout=3)
            self.statusUpdate('New task added!')
        except Exception as err:
            error(f'Fail to add one task due to {str(err)}')

    def update_task(self):
        task_key_widget_map = {
                          'queue':self.lineEdit_queue_name.text(),
                          'scan_command': self.lineEdit_cmd.text(),
                          'session': self.lineEdit_session.text(), 
                          'state': self.lineEdit_state.text(), 
                          'scan_info': self.lineEdit_scan_info.text(),
                          'queue_id': self.lineEdit_queue_id.text(),
                          'unique_id': self.lineEdit_job_id.text()}
        task_key_widget_map_copy = dict(task_key_widget_map.items())
        for each, value in task_key_widget_map.items():
            if value=='':
                task_key_widget_map_copy.pop(each)
            if each=='queue_id':
                try:
                    task_key_widget_map_copy['queue_id'] = int(task_key_widget_map_copy['queue_id'])
                except:
                    task_key_widget_map_copy.pop(each, None)
        unique_id = int(task_key_widget_map_copy.pop('unique_id'))
        task_key_widget_map_copy['scan_command'] = task_key_widget_map_copy['scan_command'].rsplit(' ')
        if confirmation_dialogue('Are you sure to update this task?'):
            try:
                self.queue_comm.send_receive_message(['update_entry', [unique_id, task_key_widget_map_copy]])
                self.statusUpdate('The task is updated!')
            except Exception as err:
                error_pop_up(str(err), 'Error')
                self.statusUpdate('Failure to update the task!')

    def change_state_of_a_task(self, action = 'disabled'):
        assert action in ['enabled','disabled','paused'], 'wrong action, should be in [enabled,disabled,paused]'
        try:
            task_id = int(self.lineEdit_job_id.text())
            self.queue_comm.send_receive_message(['update_entry', [task_id, {'state':action}]])
            self.display_info_for_a_queue()
            self.update_task_from_server(str(task_id))
            self.statusUpdate(f'The task of {task_id} has been {action}!')
        except Exception as err:
            error_pop_up(str(err))

    def update_synoptic_viewer(self):
        self.widget_queue_synoptic_viewer.set_data(self.pandas_model_queue._data)

    def run_queue(self):
        door = Device(self.settings_object['spockLogin']['doorName'])
        queue = self.comboBox_queue_name_list.currentText()
        try:
            #this is a workaround to update the stage xy for scan roi upon starting the queue 
            self.update_roi_at_row(0)
            door.runmacro(['scan_sequence', queue])
            self.statusUpdate(f'start running queue of {queue}')
        except Exception as err:
            self.statusUpdate(f'Fail to run the queue due to {err}')

    def connect_slots_queue_control(self):
        # self.pushButton_run_queue.clicked.connect(self.run_queue)
        # self.pushButton_get_all_queues.clicked.connect(self.get_available_queues)
        # self.pushButton_connect_queue_server.clicked.connect(self.connect_queue_server)
        # self.pushButton_get_queue_info.clicked.connect(self.display_info_for_a_queue)
        # self.pushButton_add_task.clicked.connect(self.add_task_from_ui)
        self.comboBox_queue_task.textActivated.connect(self.update_task_from_server)
        self.comboBox_queue_task.currentTextChanged.connect(self.update_task_from_server)
        self.comboBox_queue_viewer.textActivated.connect(self.update_queue_viewer_type)
        self.comboBox_queue_name_list.textActivated.connect(self.update_synoptic_viewer)
        # self.pushButton_delete_task.clicked.connect(self.remove_task)
        self.pushButton_remove_queue.clicked.connect(self.remove_queue)
        # self.pushButton_update_task.clicked.connect(self.update_task)
        # self.pushButton_enable_task.clicked.connect(lambda: self.change_state_of_a_task('enabled'))
        # self.pushButton_disable_task.clicked.connect(lambda: self.change_state_of_a_task('disabled'))
        # self.pushButton_pause_task.clicked.connect(lambda: self.change_state_of_a_task('paused'))
        self.brcast_listener.queue_entry_event.connect(self.update_queued_task_from_brcast_event)
        self.tableView_queue.clicked.connect(self.update_task_upon_click_tableview)
