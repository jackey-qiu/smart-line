from . import p06io
from taurus import info, error, warning, critical
from PyQt5.QtCore import pyqtSlot as Slot
from smart.gui.widgets.event_dialogue import confirmation_dialogue, error_pop_up
import logging

REQUIRED_KEYS = ['queue', 'scan_command', 'session']

class queueControl(object):

    def __init__(self, parent=None):
        self.ntp_host = self.settings_object.value("QueueControl/ntp_host")
        self.ntp_port = int(self.settings_object.value("QueueControl/ntp_port"))
        self.queue_comm = None
        self.queue_info = None
        # self.set_models()

    def connect_queue_server(self, which_instance = 0):
        try:
            ntp_comm = p06io.zeromq.ClientReq(self.ntp_host, self.ntp_port)
            queue_info = ntp_comm.send_receive_message(["info", ["scan_queue"]],timeout=3)

            # In this case you will just have 1 instance running so you take instance zero
            instance_info = queue_info[list(queue_info.keys())[which_instance]]
            self.textEdit_queue_info_output.setPlainText(str(queue_info))

            # All available connections are under the connections key
            self.queue_host = instance_info["connections"]["communication"]["host"]
            self.queue_port = int(instance_info["connections"]["communication"]["port"])
            self.queue_comm = p06io.zeromq.ClientReq(self.queue_host, self.queue_port)
            self.statusUpdate(f'Connect to queue server: {self.queue_host}:{self.queue_port}')
        except Exception as er:
            error(f"Fail to connect to queue server with the following error:/n {str(er)}") 
            self.statusUpdate(f'Failure to connect to queue server!')

    def get_available_queues(self):
        if self.queue_comm==None:
            self.textEdit_queue_info_output.setPlainText('The queue comm is not yet created! Connect the queue server first.')
            return
        else:
            try:
                msg = self.queue_comm.send_receive_message("get_available_queues", timeout=3)
                self.comboBox_queue_name_list.clear()
                self.comboBox_queue_name_list.addItems(eval(str(msg)))
                self.textEdit_queue_info_output.setPlainText(str(msg))
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
                          'queue_id': self.lineEdit_queue_id.setText}
        for each in task_key_widget_setAPI_map.values():
            each('')

    def display_info_for_a_queue(self):
        queue_name = str(self.comboBox_queue_name_list.currentText())
        msg = self.queue_comm.send_receive_message(['get', queue_name],timeout=3)
        tasks = []
        for each in msg:
            each.update({'queue':queue_name})
            tasks.append(str(each['queue_id']))
        self.queue_info = msg
        self.comboBox_queue_task.clear()
        self.comboBox_queue_task.addItems(tasks)
        self.textEdit_queue_info_output.setPlainText('\n\n'.join([str(each) for each in msg]))

    def remove_task(self, task_id):
        task_id = self.lineEdit_queue_id.text()
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
        
        # return
        self._append_task(task_from_widget)

    @Slot(str)
    def update_task_from_server(self, queue_id):
        msg = None
        if self.queue_info == None:
            return
        for each in self.queue_info:
            if each['queue_id']==int(queue_id):
                msg = each
                break
        task_key_widget_setAPI_map = {'execution_id':self.lineEdit_exe_id.setText,
                          'queue':self.lineEdit_queue_name.setText,
                          'scan_command': self.lineEdit_cmd.setText,
                          'session': self.lineEdit_session.setText, 
                          'state': self.lineEdit_state.setText, 
                          'scan_info': self.lineEdit_scan_info.setText,
                          'queue_id': self.lineEdit_queue_id.setText}
        for key, value in msg.items():
            if key=='scan_command':
                value = ' '.join(value)
            if key in task_key_widget_setAPI_map:
                task_key_widget_setAPI_map[key](str(value))

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
        task_key_widget_map = {'execution_id':self.lineEdit_exe_id.text(),
                          'queue':self.lineEdit_queue_name.text(),
                          'scan_command': self.lineEdit_cmd.text(),
                          'session': self.lineEdit_session.text(), 
                          'state': self.lineEdit_state.text(), 
                          'scan_info': self.lineEdit_scan_info.text(),
                          'queue_id': self.lineEdit_queue_id.text()}
        task_key_widget_map_copy = dict(task_key_widget_map.items())
        for each, value in task_key_widget_map.items():
            if value=='':
                task_key_widget_map_copy.pop(each)
            if each=='execution_id':
                try:
                    task_key_widget_map_copy['execution_id'] = int(task_key_widget_map_copy['execution_id'])
                except:
                    task_key_widget_map_copy.pop(each, None)
        queue_id = int(task_key_widget_map_copy.pop('queue_id'))
        task_key_widget_map_copy['scan_command'] = task_key_widget_map_copy['scan_command'].rsplit(' ')
        if confirmation_dialogue('Are you sure to update this task?'):
            try:
                self.queue_comm.send_receive_message(['update_entry', [queue_id, task_key_widget_map_copy]])
                self.statusUpdate('The task is updated!')
            except Exception as err:
                error_pop_up(str(err), 'Error')
                self.statusUpdate('Failure to update the task!')

    def change_state_of_a_task(self, action = 'disabled'):
        assert action in ['enabled','disabled','paused'], 'wrong action, should be in [enabled,disabled,paused]'
        try:
            task_id = int(self.lineEdit_queue_id.text())
            self.queue_comm.send_receive_message(['update_entry', [task_id, {'state':action}]])
            self.display_info_for_a_queue()
            self.update_task_from_server(str(task_id))
            self.statusUpdate(f'The task of {task_id} has been {action}!')
        except Exception as err:
            error_pop_up(str(err))

    def connect_slots_queue_control(self):
        self.pushButton_get_all_queues.clicked.connect(self.get_available_queues)
        self.pushButton_connect_queue_server.clicked.connect(self.connect_queue_server)
        self.pushButton_get_queue_info.clicked.connect(self.display_info_for_a_queue)
        self.pushButton_add_task.clicked.connect(self.add_task_from_ui)
        self.comboBox_queue_task.textActivated.connect(self.update_task_from_server)
        self.pushButton_delete_task.clicked.connect(self.remove_task)
        self.pushButton_remove_queue.clicked.connect(self.remove_queue)
        self.pushButton_update_task.clicked.connect(self.update_task)
        self.pushButton_enable_task.clicked.connect(lambda: self.change_state_of_a_task('enabled'))
        self.pushButton_disable_task.clicked.connect(lambda: self.change_state_of_a_task('disabled'))
        self.pushButton_pause_task.clicked.connect(lambda: self.change_state_of_a_task('paused'))
