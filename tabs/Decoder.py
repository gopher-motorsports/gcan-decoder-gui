import dearpygui.dearpygui as dpg
import core_gui.gui_global as gui_global
import time
from datetime import datetime
from core_gui.Shared_modules import Clock, status_box
import yaml
import threading
import struct

class Decoder_Tab:

    clock = Clock()

    def __init__(self):
        
        # temp code to test functionality should delete and have it be more flexible and be modifiable in the gui
        with open("go4-23c.yaml", "r") as file:
            self.gopher_can_config = yaml.safe_load(file)
            gui_global.USB_Middleware.paramter_data = self.gopher_can_config

        self.data_mutex = threading.Lock()
        self.type_dict = { }
        self.message_data = [] 
        Decoder_Tab.clock.lambda_dict["None"] = self.decode_message_data # don't care about the key as we are not using it and don't add or remove this element from the dict
        with dpg.tab(label="Parameter log"):
            self.parameter_table_list = []
            with dpg.child_window(border=False, height=-100):

                with dpg.table(
                        policy=dpg.mvTable_SizingFixedFit,
                        borders_innerH=True,
                        borders_innerV=True,
                        borders_outerH=True,
                        borders_outerV=True,
                        row_background=True,
                        resizable=True,
                        scrollY=True,
                        scrollX=True,
                        clipper=True,
                        freeze_rows=1,
                        sortable=False,
                        delay_search=True,
                        height=-50) as self.main_table:

                    dpg.add_table_column(label="Name:", init_width_or_weight=170)
                    dpg.add_table_column(label="Data:", init_width_or_weight=90)
                    dpg.add_table_column(label="ID:", init_width_or_weight=90)
                    dpg.add_table_column(label="Time:", init_width_or_weight=500)

                with dpg.group(horizontal=True):
                    dpg.add_button(label="clear table", callback=self.clear_table)
                    dpg.add_button(label="Save current log to disk", callback=self.show_save_file_window)

                with dpg.file_dialog(
                        default_filename=datetime.now().strftime("%Y_%m_%d-%I_%M_%S_%p") + "_Parameter_Log",
                        modal=True,
                        show=False,
                        min_size=(500, 300),
                        callback=self.save_file) as self.file_selector:

                    # can add support for other files in the future
                    dpg.add_file_extension(".csv")

    

    def decode_message_data(self):
        self.data_mutex.acquire()
        for message in self.message_data:
            self.add_parameter(message)
        self.message_data.clear()
        self.data_mutex.release()

    def load_parameter_data(self): # TODO: implement
        self.data_mutex.acquire()
        data = gui_global.USB_Middleware.get_usb_gophercan_parameter_msg()
        if data != [] and data != None:
            for element in data:
                self.message_data.append(element)
        self.data_mutex.release()

    def add_parameter(self, data): 
        with dpg.table_row(parent=self.main_table) as paramter_row:
            parameter_name = dpg.add_text(data[0]["motec_name"])
            # TODO: need to add converion here
            data_converted = self.decode_bytes(data[1], data[0])
            parameter_data = dpg.add_text(str(data_converted) + " " + data[0]["unit"])
            parameter_id = dpg.add_text(data[0]["id"])
            time_val = dpg.add_text(time.asctime(time.localtime()))

        self.parameter_table_list.append((paramter_row, parameter_name, parameter_data, parameter_data, time_val))
        
    def decode_bytes(self, bytes, parameter):
        #TODO: test code
        # assumes bytes is proerly formatted / length as it is check in the usb driver class / functions
        if parameter["type"] == "UNSIGNED8":
            return bytes[0]
        
        elif parameter["type"] == "SIGNED8":
            # convert unsigend8 to signed8
            if bytes[0] > 127:
                return bytes[0] - 128
            else:
                return bytes[0]
            
        elif parameter["type"] == "UNSIGNED16":
            if parameter["encoding"] == "MSB":
                print(bytes)
                print(type(bytes))
                return bytes[1] + (bytes[0] << 8)
            elif parameter["encoding"] == "LSB":
                return bytes[0] + (bytes[1] << 8)
            else:
                return "error no encoding"
            
        elif parameter["type"] == "SIGNED16":
            if parameter["encoding"] == "MSB":
                if bytes[1] > 127:
                    return (bytes[1] - 128) + (bytes[0] << 8) - 32768
                else:
                    return bytes[1] + (bytes[0] << 8)
            elif parameter["encoding"] == "LSB":
                if bytes[0] > 127:
                    return (bytes[0] - 128) + (bytes[1] << 8) - 32768
                else:
                    return bytes[0] + (bytes[1] << 8)
            else:
                return "error no encoding"
        
        elif parameter["type"] == "UNSIGNED32":
            if parameter["encoding"] == "MSB":
                return bytes[3] + (bytes[2] << 8) + (bytes[1] << 16) + (bytes[0] << 24)
            elif parameter["encoding"] == "LSB":
                return bytes[0] + (bytes[1] << 8) + (bytes[2] << 16) + (bytes[3] << 24)
            else:
                return "error no encoding"
        
        elif parameter["type"] == "SIGNED32":
            if parameter["encoding"] == "MSB":
                if bytes[3] > 127:
                    return (bytes[3] - 128) + (bytes[2] << 8) + (bytes[1] << 16) + (bytes[0] << 24) - 2147483648
                else:
                    return bytes[3] + (bytes[2] << 8) + (bytes[1] << 16) + (bytes[0] << 24)
            elif parameter["encoding"] == "LSB":
                if bytes[0] > 127:
                    return (bytes[0] - 128) + (bytes[1] << 8) + (bytes[2] << 16) + (bytes[3] << 24) - 2147483648
                else:
                    return bytes[0] + (bytes[1] << 8) + (bytes[2] << 16) + (bytes[3] << 24)
            else:
                return "error no encoding"
        
        elif parameter["type"] == "FLOATING":
            vstr = ''.join([chr(k) for k in bytes]) #chr converts the integer into the corresponding byte
            return struct.unpack('f', vstr)
        
        elif parameter["type"] == "UNSIGNED64":
            if parameter["encoding"] == "MSB":
                return bytes[7] + (bytes[6] << 8) + (bytes[5] << 16) + (bytes[4] << 24) + (bytes[3] << 32) + (bytes[2] << 40) + (bytes[1] << 48) + (bytes[0] << 56)
            elif parameter["encoding"] == "LSB":
                return bytes[0] + (bytes[1] << 8) + (bytes[2] << 16) + (bytes[3] << 24) + (bytes[4] << 32) + (bytes[5] << 40) + (bytes[6] << 48) + (bytes[7] << 56)
            else:
                return "error no encoding"
        
        elif parameter["type"] == "SIGNED64":
            if parameter["encoding"] == "MSB":
                if bytes[7] > 127:
                    return (bytes[7] - 128) + (bytes[6] << 8) + (bytes[5] << 16) + (bytes[4] << 24) + (bytes[3] << 32) + (bytes[2] << 40) + (bytes[1] << 48) + (bytes[0] << 56) - 9223372036854775808
                else:
                    return bytes[7] + (bytes[6] << 8) + (bytes[5] << 16) + (bytes[4] << 24) + (bytes[3] << 32) + (bytes[2] << 40) + (bytes[1] << 48) + (bytes[0] << 56)
            elif parameter["encoding"] == "LSB":
                if bytes[0] > 127:
                    return (bytes[0] - 128) + (bytes[1] << 8) + (bytes[2] << 16) + (bytes[3] << 24) + (bytes[4] << 32) + (bytes[5] << 40) + (bytes[6] << 48) + (bytes[7] << 56) - 9223372036854775808
                else:
                    return bytes[0] + (bytes[1] << 8) + (bytes[2] << 16) + (bytes[3] << 24) + (bytes[4] << 32) + (bytes[5] << 40) + (bytes[6] << 48) + (bytes[7] << 56)
            else:
                return "error no encoding"
        
        else:
            return "error no type"
        
        
        

    def clear_table(self):

        for element in self.parameter_table_list:

            dpg.delete_item(element[0])

        self.parameter_table_list.clear()

    def show_save_file_window(self):
        dpg.show_item(self.file_selector)

    def save_file(self, sender, app_data):
        if len(self.parameter_table_list) == 0:
            return # can implement error message here if wanted
        else:
            with open(app_data["file_path_name"], 'w') as file:
                file.write("Name,Data,ID, Time\n")
                for element in self.parameter_table_list:
                    line = dpg.get_value(element[1]) + ","
                    line += dpg.get_value(element[2]) + ","
                    line += dpg.get_value(element[3]) + ","
                    line += dpg.get_value(element[4]) + ",\n"
                    file.write(line)

        dpg.hide_item(self.file_selector)
