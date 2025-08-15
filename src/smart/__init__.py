from pathlib import Path
import yaml
import zmq
from taurus import Attribute
from threading import Thread

rs_path = Path(__file__).parent / 'resource'
icon_path = Path(__file__).parent / 'gui' / 'ui' /'icons'

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class smartProperties(Thread, metaclass=Singleton):
    """
        This is a singleton property class, which is supposed to be used with taurus 'eval' scheme to render and set some
        properties.eg: eval:@p=smart.smartProperties()/p.scan_progress_req 
        This class is importable, (from smart import smartProperties), and has one or multiple set/get function for different properties
        There are two sockets (SUB and REQ) being connected to server sockets (PUB and REP)
        The workflow is of of two cases as follows depending on the direction of data stream:
        1. upstream --> downstream
        PUB broatcast some data from upstream, SUB socket receive the upstream data and reformat the received data to numerical or list form 
        and update the associated property using set function
        taurus eval schema grab the data from the associated get function (property decorator)
        2. downstream --> upstream (set something from taurus attribute interface)
        taurus attribute will call the set func, the value as argument is passed to the set func, and the function body need to respect the 
        socket data format setting, otherwise it wont take any effect.

        NOTES:
        You can add as many properties as you need.
        For each property, you need 2 set and 2 get funcs (like here, set_scan_progress, set_scan_progress_req)
        The set func that is ended with '_req' is supposed to send data through req socket to do something upstream.
        The set func without a _req ending is supposed to update the property using data extracted from upstream via SUB socket

    """
    def __init__(self, topics = ['scan_progress']):
        super().__init__()
        with open(str(rs_path / 'config' / 'appsettings.yaml'), 'r') as f:
            self.settings_object = yaml.safe_load(f)
        self.ntp_host = self.settings_object["QueueControl"]["ntp_host"]
        self.ntp_port_req = int(self.settings_object["QueueControl"]["ntp_port"])
        self.ntp_port_brcast = [int(each) for each in self.settings_object["QueueControl"]["brcast_port"]]
        self.poller = zmq.Poller()
        self.brcast_comm = []
        self.context = None
        self.listening = False
        self._scan_progress = 0
        self.topics = topics
        self.daemon = True
        self.init_zmq()
        self.start()

    def run(self):
        self.start_listen_server()

    @property
    def scan_progress_req(self):
        return self._scan_progress

    @scan_progress_req.setter
    def scan_progress_req(self, value):
        #this is customisible to send a pyobj to rep server socket
        #The format of the pyobj being sent needed to be agreed on in advance
        #by default it does nothing but print out some ascii str

        #self.queue_comm.send_pyobj(['stop',None])
        #state = str(self.queue_comm.recv_json())
        print('simulate setting obj via req socket!')

    @property
    def scan_progress(self):
        return self._scan_progress

    @scan_progress.setter
    def scan_progress(self, value):
        self._scan_progress = value['progress']

    def init_zmq(self, start_listening = False):
        #zmq init
        [self.poller.unregister(each) for each in self.brcast_comm]
        self.brcast_comm = []
        try:
            #REQ socket connetion
            if self.context==None:
                self.context = zmq.Context()
            self.queue_comm = self.context.socket(zmq.REQ)
            self.queue_comm.connect(f"tcp://{self.ntp_host}:{self.ntp_port_req}") 
            #SUB sockets connection
            for port in self.ntp_port_brcast:
                self.brcast_comm.append(self.context.socket(zmq.SUB))
                # zmq.ssh.tunnel_connection(self.brcast_comm[-1],f"tcp://localhost:{port}",f'p25user@{self.ntp_host}')
                self.brcast_comm[-1].connect(f"tcp://{self.ntp_host}:{port}")
                for topic in self.topics:
                    self.brcast_comm[-1].setsockopt(zmq.SUBSCRIBE, topic.encode('ascii'))
                self.poller.register(self.brcast_comm[-1],zmq.POLLIN)
            if start_listening:
                self.start_listen_server()
        except Exception as er:
            print(f"Fail to connect to queue server with the following error:/n {str(er)}") 
            raise

    def start_listen_server(self):
        self.listening = True
        while self.listening:
            sockets = dict(self.poller.poll())
            for socket in self.brcast_comm:
                if (socket in sockets) and (sockets[socket]==zmq.POLLIN):
                    # self.msg = socket.recv_pyobj()
                    try:
                        topic = socket.recv_string()
                        msg = socket.recv_json()
                        if topic in self.topics:
                            # setattr(self, topic, msg)
                            setattr(self, topic, msg)
                    except Exception as err:
                        print(f'ERROR due to:', err)
                        return