try:
    import psdrive as psd_api
except:
    pass
from smart import rs_path
import yaml
from enum import Enum
from magicgui import magicgui


config_file = str(rs_path / 'psd_pump_config' / 'nodb_configuration.yml')
#from smart.gui.widgets.shapes.customized_callbacks import *

class Valve(Enum):
    """Enum for various media and their refractive indices."""
    left = 1
    up = 2
    right = 3

def create_pump_client(parent, firstclient = True):
    #firstclient has to be the one making direct connection to the pump
    #ensure the serialport is correctly changed
    if not firstclient:
        try:
            with open(config_file, 'r', encoding='utf8') as f:
                config = yaml.safe_load(f.read())
            host = config['server']['host']
            port = config['server']['port']
            tango_name = config['server']['tangoname']
            full_address = f'tango://{host}:{port}/{tango_name}'
            setattr(parent, "pump_client", psd_api.connect(full_address))
        except Exception as er:
            raise LookupError(str(er))
    else:
        try:
            #server should be started from astor panel
            #psd.start_server_fromFile(config_file)
            #this will create a pumpinterface client and connect to the specified port if necessary
            client = psd_api.fromFile(config_file)
            #reconfig the client and server using the content in config_file
            client.readConfigfile(config_file)
            setattr(parent, 'pump_client', client)
            return client
        except Exception as er:
            raise LookupError(str(er))

def setup_create_pump_client(parent):
    with open(config_file, 'r', encoding='utf8') as f:
        config = yaml.safe_load(f.read())

    host = config['server']['host']
    port = config['server']['port']
    tango_name = config['server']['tangoname']

    @magicgui(call_button='apply')
    def setup_func(host=host, port=port, tango_name = tango_name):
        config['server']['host'] = host
        config['server']['port'] = port
        config['server']['tangoname'] = tango_name
        with open(config_file,'w') as f:
            yaml.dump(config, f, default_flow_style=False)
    return setup_func

#reconfigure client and server using the config_file
def configure(parent, config_file):
    with open(config_file, 'r', encoding='utf8') as f:
        config = yaml.safe_load(f.read())
    if hasattr(parent, "pump_client"):
        parent.pump_client.configure(config)
    else:
        raise Exception("No pump_client attributed has been defined.")

def get_syringe_proxy(parent, id):#id in [1,2,3,4]
    if not hasattr(parent, f'syringe_{id}'):
        setattr(parent, f'syringe_{id}',parent.pump_client.getSyringe(id))
    return getattr(parent, f'syringe_{id}')

def get_mvp_valve_proxy(parent, id=5):
    if not hasattr(parent, 'mvp'):
        setattr(parent, 'mvp',parent.pump_client.getValve(id))
    return getattr(parent, 'mvp')

def set_val_pos_alias(dev_proxy, name_map = {1:'left', 2:'up',3:'right'}):
    for val, name in name_map.items():
        dev_proxy.setValvePosName(val, name)

def set_val_pos_alias_for_exchange(client):#it is recommended to set this using config file
    #id 4, 2, 3, 1 reflect the order of syringe, id 5 is mvp
    set_val_pos_alias(client.getSyringe(4), name_map={1:'Reservoir', 2:'Waste',3:'Cell'})
    set_val_pos_alias(client.getSyringe(2), name_map={1:'Reservoir', 2:'Waste',3:'Cell'})
    set_val_pos_alias(client.getSyringe(3), name_map={1:'Cell', 2:'Waste',3:'Open'})
    set_val_pos_alias(client.getSyringe(1), name_map={1:'Cell', 2:'Waste',3:'Open'})

def init_syringe(parent, val_pos="Waste", speed=250):
    #val_pos the id of val in (1,2,3), or the alias
    parent.syringe_1.initSyringe(val_pos, speed)
    parent.syringe_2.initSyringe(val_pos, speed)
    parent.syringe_3.initSyringe(val_pos, speed)
    parent.syringe_4.initSyringe(val_pos, speed)

def init_valve(parent):
    parent.mvp.initValve()
    parent.syringe_1.join()
    parent.syringe_2.join()
    parent.syringe_3.join()
    parent.syringe_4.join()
    parent.syringe_1.initValve()
    parent.syringe_2.initValve()
    parent.syringe_3.initValve()
    parent.syringe_4.initValve()

def update_volumes(parent):
    vol_change_reservoir = 0
    vol_change_cell = 0
    vol_change_waste = 0

    vol_change_syringe_1 = parent.syringe_1.volume - parent.volume_syringe_1 if parent.syringe_1.busy else 0
    vol_change_syringe_2 = parent.syringe_2.volume - parent.volume_syringe_2 if parent.syringe_2.busy else 0
    vol_change_syringe_3 = parent.syringe_3.volume - parent.volume_syringe_3 if parent.syringe_3.busy else 0
    vol_change_syringe_4 = parent.syringe_4.volume - parent.volume_syringe_4 if parent.syringe_4.busy else 0
    vol_change_list = [vol_change_syringe_1, vol_change_syringe_2, vol_change_syringe_3, vol_change_syringe_4]
    for i, syringe in enumerate([parent.syringe_1, parent.syringe_2, parent.syringe_3, parent.syringe_4]):
        if vol_change_list[i]!=0:
            if syringe.valve == 'Reservoir':
                vol_change_reservoir -= vol_change_list[i]
            elif syringe.valve == 'Cell':
                vol_change_cell -= vol_change_list[i]
            elif syringe.valve == 'Waste':
                vol_change_waste -= vol_change_list[i]
            setattr(parent, f"volume_syringe_{i+1}", getattr(parent, f"syringe_{i+1}").volume)
    #parent.volume_syringe_1 = parent.syringe_1.volume
    #parent.volume_syringe_2 = parent.syringe_2.volume
    #parent.volume_syringe_3 = parent.syringe_3.volume
    #parent.volume_syringe_4 = parent.syringe_4.volume

    parent.volume_reservoir = max([round(parent.volume_reservoir + vol_change_reservoir/1000,3), 0])
    parent.volume_cell = max([round(parent.volume_cell+vol_change_cell,1), 0])
    parent.volume_waste = max([round(parent.volume_waste+vol_change_waste/1000,3),0])
    #parent.statusbar.showMessage(f"reseroir:{round(parent.volume_reservoir,2)} ml, cell: {round(parent.volume_cell,1)} ul, waste: {round(parent.volume_waste,2)} ml")

def pickup_solution(parent, dev_proxy, vol = 0, val_pos = -1, speed = -1, fill = True):
    dev_proxy = getattr(parent, dev_proxy)
    dev_proxy.valve = int(val_pos)
    dev_proxy.join()
    if not eval(fill):
        dev_proxy.pickup(float(vol), float(speed), int(val_pos))
    else:
        dev_proxy.fill(int(val_pos), float(speed))

def setup_pickup_solution(parent, dev_proxy):
    if hasattr(parent, dev_proxy):
        dev_proxy = getattr(parent, dev_proxy)        
        val_pos = dev_proxy.valve
        speed = dev_proxy.rate
    else:
        dev_proxy = None
        speed = 1
        val_pos = 1

    @magicgui(call_button='apply', speed={'min': 1, 'max': 500})
    # def setup_func( speed=float(speed), val_pos = list(Valve)[[1,2,3].index(int(val_pos))]):
    def setup_func( speed=float(speed), val_pos = val_pos):
        if dev_proxy==None:
            print(locals())
        else:
            dev_proxy.valve = val_pos
            dev_proxy.join()
            dev_proxy.rate = speed
    return setup_func

def fill_cell(parent, dev_proxy, vol, drain = False):
    dispense_solution(parent, dev_proxy, float(vol), 3, speed = -1, drain = drain)

def setup_fill_cell(parent, dev_proxy, vol):
    if hasattr(parent, dev_proxy):
        dev_proxy = getattr(parent, dev_proxy)        
        #val_pos = int(dev_proxy.valve)
        speed = dev_proxy.rate
    else:
        dev_proxy = None
        speed = 1
        #val_pos = 3

    @magicgui(call_button='apply', speed={'min': 1, 'max': 500}, fill_vol = {'max': 5000})
    def setup_func(speed=float(speed), val_pos = Valve.right, fill_vol = float(vol)):
        if dev_proxy==None:
            print(locals())
        else:
            dev_proxy.valve = val_pos.value
            dev_proxy.join()
            dev_proxy.rate = speed
            dev_proxy.volume = dev_proxy.volume - fill_vol
    return setup_func

def dispense_solution(parent,dev_proxy, vol = 0, val_pos = -1, speed = -1, drain = True):
    dev_proxy = getattr(parent, dev_proxy)
    dev_proxy.valve = int(val_pos)
    dev_proxy.join()
    if not eval(drain):
        dev_proxy.dispense(float(vol), float(speed))
    else:
        dev_proxy.drain(int(val_pos), float(speed))

def setup_dispense_solution(parent, dev_proxy):
    if hasattr(parent, dev_proxy):
        dev_proxy = getattr(parent, dev_proxy)        
        val_pos = dev_proxy.valve
        speed = dev_proxy.rate
    else:
        dev_proxy = None
        speed = 1
        val_pos = 2

    @magicgui(call_button='apply', speed={'min': 1, 'max': 500})
    # def setup_func(speed=float(speed), val_pos = list(Valve)[[1,2,3].index(int(val_pos))]):
    def setup_func(speed=float(speed), val_pos = val_pos):
        if dev_proxy==None:
            print(locals())
        else:
            dev_proxy.valve = val_pos
            dev_proxy.join()
            dev_proxy.rate = speed
    return setup_func

def move_valve(parent, dev_proxy,val_pos):
    getattr(parent,dev_proxy).valve = int(val_pos)
    name_map = {'syringe_1':'syringe4','syringe_2':'syringe2','syringe_3':'syringe3','syringe_4':'syringe'}
    #val_pos: 1,2,3 while shape_ix: 3,4,5
    _update_connection(parent, name_map[dev_proxy],int(val_pos)+2)

def _update_connection(parent,syringe_key, shape_ix):
    for key in parent.syringe_lines_container[syringe_key].keys():
        parent.syringe_lines_container[syringe_key][key][1] = False
    parent.syringe_lines_container[syringe_key][shape_ix][1] = True

def exchange_solution(parent, operation_pair = 1):
    exchange_obj = parent.pump_client.operations[f"Exchanger {operation_pair}"]
    exchange_obj.exchange(exchange_obj.exchangeableVolume - parent.leftover_vol)

def increase_liquid_vol_in_cell(parent):
    exchange_obj = parent.pump_client.operations[f"Exchanger {parent.exchange_pair}"]
    exchange_obj.increaseVolume(volume = float(parent.volume_change_on_the_fly))

def setup_increase_liquid_vol_in_cell(parent):
    @magicgui(call_button='apply')
    def setup_func(increase_vol_from_cell=parent.volume_change_on_the_fly):
        parent.volume_change_on_the_fly = increase_vol_from_cell
    return setup_func

def decrease_liquid_vol_in_cell(parent):
    exchange_obj = parent.pump_client.operations[f"Exchanger {parent.exchange_pair}"]
    exchange_obj.decreaseVolume(volume = float(parent.volume_change_on_the_fly))

def setup_decrease_liquid_vol_in_cell(parent):
    @magicgui(call_button='apply')
    def setup_func(decrease_vol_from_cell=parent.volume_change_on_the_fly):
        parent.volume_change_on_the_fly = decrease_vol_from_cell
    return setup_func

def prepare_exchange(parent):
    parent.pump_client.operations["Exchanger 1"].pullSyr.valve = "Waste"
    parent.pump_client.operations["Exchanger 1"].pushSyr.valve = "Reservoir"
    parent.pump_client.operations["Exchanger 2"].pullSyr.valve = "Waste"
    parent.pump_client.operations["Exchanger 2"].pushSyr.valve = "Reservoir"
    parent.syringe_1.join()
    parent.syringe_2.join()
    parent.syringe_3.join()
    parent.syringe_4.join()
    parent.pump_client.operations["Exchanger 1"].prepare()
    parent.pump_client.operations["Exchanger 2"].prepare()

def setup_exchange(parent):
    if not hasattr(parent, 'pump_client'):
        fillrate = 200
        drainrate = 200
        rate = 10
        bubbleDispense = 500
    else:
        fillrate = parent.pump_client.operations['Exchanger 1'].fillrate
        drainrate = parent.pump_client.operations['Exchanger 1'].drainrate
        rate = parent.pump_client.operations['Exchanger 1'].rate
        bubbleDispense = parent.pump_client.operations['Exchanger 1'].bubbleDispense
    @magicgui(call_button='apply', 
              fillrate={'min': 1, 'max': 500},
              drainrate={'min': 1, 'max': 500},
              rate={'min':1, 'max':500},
              leftover_vol={'min':1, 'max':2000},
              bubbleDispense={'min': 10, 'max': 5000})
    def setup_func(fillrate=float(fillrate), drainrate=float(drainrate), rate=float(rate),leftover_vol=float(parent.leftover_vol), bubbleDispense = float(bubbleDispense)):
        if not hasattr(parent, 'pump_client'):
            print(locals())
        else:
            for (key, value) in locals().items():
                if key!='parent':
                    setattr(parent.pump_client.operations['Exchanger 1'], key, value)
                    setattr(parent.pump_client.operations['Exchanger 2'], key, value)
        parent.leftover_vol = leftover_vol
    return setup_func

def start_automatic_exchange(parent):
    parent.exchange_timer.timeout.connect(lambda: check_automatic_exchange(parent))
    if not hasattr(parent, "exchange_pair"):
        setattr(parent, "exchange_pair", 1)
        exchange_solution(parent,1)
    else:
        exchange_solution(parent,parent.exchange_pair)
    parent.exchange_timer.start(50)

def check_automatic_exchange(parent):
    if not parent.syringe_1.busy and not parent.syringe_2.busy and not parent.syringe_3.busy and not parent.syringe_4.busy:
        #all has stopped
        if parent.exchange_pair == 1:
            parent.exchange_pair = 2
            exchange_solution(parent, 2)
            parent.pump_client.operations["Exchanger 1"].pullSyr.valve = "Waste"
            parent.pump_client.operations["Exchanger 1"].pushSyr.valve = "Reservoir"
            parent.syringe_3.join()
            parent.syringe_4.join()
            parent.pump_client.operations["Exchanger 1"].prepare()
            parent.statusbar.showMessage("Exchange solution with pair of 2")
        elif parent.exchange_pair == 2:
            parent.exchange_pair = 1
            exchange_solution(parent,1)
            parent.pump_client.operations["Exchanger 2"].pullSyr.valve = "Waste"
            parent.pump_client.operations["Exchanger 2"].pushSyr.valve = "Reservoir"
            parent.syringe_1.join()
            parent.syringe_2.join()
            parent.pump_client.operations["Exchanger 2"].prepare()
            parent.statusbar.showMessage("Exchange solution with pair of 1")

def all_setup_in_one(parent, firstclient=False):
    if type(firstclient)!=bool:
        firstclient = eval(firstclient)
    create_pump_client(parent, firstclient = parent.first_client)
    get_syringe_proxy(parent, 1)
    get_syringe_proxy(parent, 2)
    get_syringe_proxy(parent, 3)
    get_syringe_proxy(parent, 4)
    get_mvp_valve_proxy(parent, 5)
    parent.check_vol_timer.timeout.connect(lambda: update_volumes(parent))

def reset_volumes(parent):
    parent.check_vol_timer.stop()
    @magicgui(call_button='apply')
    def setup_func(cell_volume = float(parent.volume_cell), reservoir_volume = float(parent.volume_reservoir), waste_volume = float(parent.volume_waste)):
        try:
            parent.check_vol_timer.stop()
        except:
            pass
        parent.volume_cell = cell_volume
        parent.volume_reservoir = reservoir_volume
        parent.volume_waste = waste_volume
        parent.volume_syringe_1 = parent.syringe_1.volume
        parent.volume_syringe_2 = parent.syringe_2.volume
        parent.volume_syringe_3 = parent.syringe_3.volume
        parent.volume_syringe_4 = parent.syringe_4.volume
        parent.check_vol_timer.start(5)
    return setup_func

def setup_client_par(parent):
    with open(config_file, 'r', encoding='utf8') as f:
        config = yaml.safe_load(f.read())

    host = config['server']['host']
    port = config['server']['port']
    tango_name = config['server']['tangoname']
    serial_port = config['server']['serialport']

    @magicgui(call_button='apply')
    def setup_func(host=host, port=port, tango_name = tango_name, serial_port = serial_port,first_client = bool(parent.first_client)):
        config['server']['host'] = host
        config['server']['port'] = port
        config['server']['tangoname'] = tango_name
        config['server']['serialport'] = serial_port

        with open(config_file,'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        parent.first_client = first_client
    return setup_func

def stop_all(parent):
    parent.pump_client.stop()
    if parent.exchange_timer.isActive():
        parent.exchange_timer.stop()