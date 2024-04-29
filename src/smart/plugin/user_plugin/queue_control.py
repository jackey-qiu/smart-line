from . import p06io
from taurus import info, error, warning, critical

REQUIRED_KEYS = ['queue', 'scan_command', 'session']

class queueControl(object):

    def __init__(self, parent=None):
        self.ntp_host = self.settings_object.value("QueueControl/ntp_host")
        self.ntp_port = int(self.settings_object.value("QueueControl/ntp_port"))
        self.queue_comm = None
        # self.set_models()

    def connect_queue_server(self, which_instance = 0):
        try:
            ntp_comm = p06io.zeromq.ClientReq(self.ntp_host, self.ntp_port)
            queue_info = ntp_comm.send_receive_message(["info", ["scan_queue"]])

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

    def display_info_for_a_queue(self):
        queue_name = str(self.comboBox_queue_name_list.currentText())
        msg = self.queue_comm.send_receive_message(['get', queue_name])
        self.textEdit_queue_info_output.setPlainText(str(msg))

    def add_task_from_ui(self):
        task_from_widget = {'execution_id':self.lineEdit_exe_id.text(),
                          'queue':self.lineEdit_queue_name.text(),
                          'scan_command': self.lineEdit_cmd.text().rsplit(' '),
                          'session': self.lineEdit_session.text(), 
                          'state': self.lineEdit_state.text(), 
                          'scan_info': self.lineEdit_scan_info.text()}
        self._append_task(task_from_widget)

    def _append_task(self,task):
        assert type(task)==dict, 'Task must be formated in a python dict'
        for each in REQUIRED_KEYS:
            if each not in task or task[each]=='':
                error(f'Required key {each} is not provided!')
                self.statusUpdate(f'Required key {each} is not provided!')
                return
        try:
            self.queue_comm.send_receive_message(['add', task])
            self.statusUpdate('New task added!')
        except Exception as err:
            error(f'Fail to add one task due to {str(err)}')

    def insert_task(self, pre_task_id, task):
        pass

    def swab_two_tasks(self, first_task_id, second_task_id):
        pass

    def update_task(self,):
        pass

    def repeat_task(self, ref_task_id):
        pass

    def pause_task(self, task_id):
        pass

    def disable_task(self, task_id):
        pass

    def enable_task(self, task_id):
        pass

    def remove_tasks(self, ):
        pass

    def remove_queues(self,):
        pass

    def submit_queue_task(self):
        pass

    def connect_slots_queue_control(self):
        self.pushButton_get_all_queues.clicked.connect(self.get_available_queues)
        self.pushButton_connect_queue_server.clicked.connect(self.connect_queue_server)
        self.pushButton_get_queue_info.clicked.connect(self.display_info_for_a_queue)
        self.pushButton_add_task.clicked.connect(self.add_task_from_ui)
