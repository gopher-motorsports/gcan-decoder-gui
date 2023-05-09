# this file provides global vars and functions that are visible to add gui modules,
# this is to have a narrow waist for usb traffic so all usb messages go though this file between the gui elements and the py serial library

# also hosts misc helper functions that I did not want to tie to a specific gui element / module
import configparser
from core_gui.USB_Driver import USB_DeviceNotFound, USB_Interface
import threading
import dearpygui.dearpygui as dpg
from serial import SerialException
import struct
import time

primary_window = None
global_clock_enabled = True
fdcan_size_ref = [0,1,2,3,4,5,6,7,8,12,16,20,24,32,48,64]  # 64 byte fdcan messages, will probably break the gui (2 usb packets)
USB_footer = None # the entire footer class defined in footer.py as its modules/ element are commonly refereed to by other parts of the GUI
mass_debug_invalid_cmd_text = None
start_time = time.time()

def bin_to_lin11(val):
    # logic was taken form artyPMBus.py
    val = val & 0xFFFF # cutting off any excess bits
    exp = val >> 11
    mantissa = val & 0x7FF
    if (exp & (1 << 4) != 0):
        exp = exp - (1 << 5)
    if (mantissa & (1 << 10) != 0):
        mantissa = mantissa - (1 << 11)
    return(round(mantissa * (2 ** exp), 5))

# assumes that input val is a unsigned 16 bit int
def bin_to_lin16(val):
    if (val & (1 << 15) != 0):
        return(val - (1 << 16))
    return(val)

# used to interpret bools in the ini config file
def str_to_bool(val):

    if val == 'True':
        return True
    else:
        return False
    
def decode_parameter_bytes(data, parameter):
        #TODO: test code
        # assumes bytes is proerly formatted / length as it is check in the usb driver class / functions
        # big endian

        data_bytes = bytes(data)
        output = None
        if parameter["type"] == "UNSIGNED8" or parameter["type"] == "UNSIGNED16" or parameter["type"] == "UNSIGNED32" or parameter["type"] == "UNSIGNED64":
            output = int.from_bytes(data_bytes, byteorder='big', signed=False)
            return output
        
        elif parameter["type"] == "SIGNED8" or parameter["type"] == "SIGNED16" or parameter["type"] == "SIGNED32" or parameter["type"] == "SIGNED64":
            output = int.from_bytes(data_bytes, byteorder='big', signed=True)
            return output
             
        elif parameter["type"] == "FLOATING":
            output = round(struct.unpack(">f", data_bytes)[0], 2)
            return output
        
        else:
            return None

# takes in a int(binary) and formats it to fit lin11, 16, hex, ect
def format_data(format,data,padding=0):

        if format == "HEX" or format == "Bitfeild":
            # turning int into hex string
            output_str = "{0:0{1}X}".format(data, padding)
            # adding spaces between bytes
            output_str = " ".join(output_str[i:i + 2] for i in range(0, len(output_str), 2))
            return output_str

        elif format == "LIN11":
            return str(bin_to_lin11(data))

        elif format == "LIN16":
            return str(bin_to_lin16(data))

        elif format == "ASCII": # since the data is turned into an int we have to do it the hard way vs if we just kept it as a byte array
            data_conv = data
            output = ""
            while data_conv != 0:
                output += chr(data_conv & 0xFF)
                data_conv = data_conv >> 8
            
            return output


        # defaults to decimal if there is an unexpected value in the combo
        else:
            return str(data)
# initializes the config file for the gui

class Config_File:

    config = configparser.ConfigParser()
    try:
        config.read('gui_config.ini')

    except BaseException:
        config = None

class Global_cmds:

    cmd_dict = configparser.ConfigParser()
    try:
        cmd_dict.read('cmd_list.ini')
    except:
        cmd_dict = None

# class is just a wrapper for usb related functions and vars
class USB_Middleware:
    USB_Device_id = None               # USB_Interface class instance that is used by entire gui (set by Footer.py in USB_module class)
    USB_connected = False              # bool for if a USB device is connected. (set by Footer.py in USB_module class)
    Secondary_id = "N\\a"              # current id of the secondary we want to communicate with. (set by Footer.py in USB_module class)
    current_comm_protocol = "GopherCAN"# default comm protocol to use for general modules. (set by Footer.py in USB_module class)
    global_clock_timer = 1000          # how many ms between each global clock cycle
    parameter_clock_timer = 1       # how many ms between each parameter clock cycle
    global_timeout_clock = 0           # total amount of times we have timed out trying to read form the usb device
    usb_error_log_tab = None           # the usb error log class instance defined by main_gui.py
    paramter_data = {}                 # dictionary of all the parameter data that is currently being displayed in the gui
    # occurs

    usb_lock = threading.Lock()

    # should add custom exceptions for this function
    # message type: determines the header of the usb message
    # currently supported message types"
    # "FDCAN RD/WR", "FDCAN WR"
    # "I2C RD/WR", "I2C WR"
    # size_ret_msg: how many data bytes are expected back (only required by "I2C RD/WR" message type can be set to none for other messages)
    # expected_msgs_back: how many usb messages in total you expect back from this command (USB error messages not included)
    # cmd: hex string of the cmd / data bytes you want to send
    # caller_info: optional string with information about the caller, which is passed into the USB error log if there are any usb errors
    # returns a list of each usb command which is a list of bytes ex: [[00,01,ff]]
    @staticmethod
    def send_usb_msg(message_type: str, size_ret_msg: int, expected_msgs_back: int, cmd: str, caller_info=""):

        USB_Middleware.usb_lock.acquire()

        if USB_Middleware.USB_connected:
            expected_header_back = None

            try:

                if message_type == "I2C_RD/WR":

                    # 0x0A is the command code for RD/WR I2C msg
                    # secondary id is the id of the id of the secondary device we want to talk to (b0, b2, etc)
                    # ret_msg indicates how many bytes we expect in the response msg
                    USB_Middleware.USB_Device_id.send_data(bytearray.fromhex("0A" + USB_Middleware.Secondary_id + "{0:0{1}X}".format(size_ret_msg, 2) + "00" + cmd))
                    expected_header_back = 0x0A

                elif message_type == "I2C_WR":

                    # 0x0A is the command code for RD/WR I2C msg
                    # secondary id is the id of the id of the secondary device we want to talk to (b0, b2, etc)
                    # ret_msg indicates how many bytes we expect in the response msg
                    USB_Middleware.USB_Device_id.send_data(bytearray.fromhex("0B" + USB_Middleware.Secondary_id + cmd))

                else:
                    USB_Middleware.usb_lock.release()
                    raise Invalid_USB_T_Cmd
                

            except SerialException:  # USB device disconnected
                dpg.configure_item(USB_footer.USB_module.usb_connect_stat, default_value="USB Disconnected!", color=[255, 0, 0])
                USB_footer.USB_module.usb_disconnected()
                
                USB_Middleware.usb_lock.release()
                return []

            recv_usb_cmds = []
            usb_msgs_received = 0

            try:
                while usb_msgs_received < expected_msgs_back:
                    usb_msg = USB_Middleware.USB_Device_id.get_data()
                    len_msg = len(usb_msg) - 2 # remove header bytes

                    if len_msg == -2:  # timeout, just return what was read.
                        USB_Middleware.global_timeout_clock += 1
                        USB_Middleware.usb_lock.release()
                        return recv_usb_cmds

                    if len_msg > usb_msg[1]: # multiple usb message packets received
                        multiple_packets = True

                    if usb_msg[0] == expected_header_back: 
                        # i2c / other msg
                        if len_msg != size_ret_msg: # invalid length!
                            USB_Middleware.usb_lock.release()
                            USB_Middleware.USB_Device_id.reset_input_buffer()
                            raise Invalid_USB_msg_received

                        recv_usb_cmds.append(usb_msg)
                        usb_msgs_received += 1

                    elif usb_msg[0] == 0xFF:  # usb error msg
                        USB_Middleware.usb_error_log_tab.add_usb_error(usb_msg, caller_info)
                        # keep going, msg might still be received
                        

                    else:  # invalid header received,
                        USB_Middleware.usb_lock.release()
                        USB_Middleware.USB_Device_id.reset_input_buffer()
                        raise Invalid_USB_msg_received

            except OSError:  # usb device disconnected
                USB_Middleware.USB_connected = False
                USB_footer.USB_module.usb_disconnected()
                USB_Middleware.usb_lock.release()
                return[]

            USB_Middleware.usb_lock.release()
            return recv_usb_cmds

        USB_Middleware.usb_lock.release()
        return[]

    # This function gets all parameter messages and returns them in a list
    # due to the nature of the telemetry communication protocol, mutiple messages may be grouped into one list element, as I do not want to put the decoding logic in this class
    @staticmethod
    def get_usb_gophercan_parameter_msg():
        USB_Middleware.usb_lock.acquire()
        try:
            if USB_Middleware.USB_connected:
                usb_msgs = []
                while True: # loop till all parameter messages received 
                    usb_msg = USB_Middleware.USB_Device_id.get_data_paramter()
                    if usb_msg == []:  # timeout, just return empty list (does not increment timeout var)
                        USB_Middleware.usb_lock.release()
                        return usb_msgs
                    try:
                        data = decode_parameter_bytes(usb_msg[1], usb_msg[0])
                        if data != None:
                            Parameters.add_parameter_data(int(usb_msg[0]["id"]), data)
                    except(KeyError, TypeError):
                        print("Error: Invalid parameter data file or parameter id")

                    usb_msgs.append(usb_msg) # we know this is a paramter message due to the get_parameter_data function
        except(SerialException, OSError):  # usb device disconnected
            USB_Middleware.USB_connected = False
            USB_footer.USB_module.usb_disconnected()
            USB_Middleware.usb_lock.release()
            return[]
                    
class Parameters:
    parameter_dict = {}
    data_max = 10000

    @staticmethod
    def init_parameter_dict():
        Parameters.parameter_dict = {}

        try:
            Parameters.data_max = int(Config_File.config["Parameter"]["max_data_pts_per_param"])
        except(KeyError, TypeError, FileNotFoundError):
            Parameters.data_max = 10000

        try:
            for parameter in USB_Middleware.paramter_data["parameters"]:
                id = int(USB_Middleware.paramter_data["parameters"][parameter]["id"])
                name = USB_Middleware.paramter_data["parameters"][parameter]["motec_name"]
                unit = USB_Middleware.paramter_data["parameters"][parameter]["unit"]
                type = USB_Middleware.paramter_data["parameters"][parameter]["type"]
                Parameters.parameter_dict[id] = Parameter(id, name, unit, type)
        except(KeyError, TypeError):
            print("Error: Invalid parameter data file")
            return
    # need to add to list but delete older data if we hit cap
    @staticmethod
    def add_parameter_data(id, data):
        if id in Parameters.parameter_dict:
            Parameters.parameter_dict[id].data.append(data)
            time_diff = time.time() - start_time
            Parameters.parameter_dict[id].time.append(time_diff)
            if len(Parameters.parameter_dict[id].data) > Parameters.data_max:
                Parameters.parameter_dict[id].data.pop(0)
                Parameters.parameter_dict[id].time.pop(0)   
        else:
            print("Error: Invalid parameter id")

        

class Parameter:
    def __init__(self, id, name, unit, type):
        self.id = id
        self.name = name
        self.unit = unit
        self.type = type
        self.data = []
        self.time = []
    
        
            

class Invalid_USB_msg_received(Exception):
    pass

class Invalid_USB_T_Cmd(Exception):
    pass

class USB_Disconnected(Exception):
    pass


if __name__ == "__main__":
    print(bin_to_lin11(0xfffffffffff))
