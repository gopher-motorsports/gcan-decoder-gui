import dearpygui.dearpygui as dpg
import core_gui.gui_global as gui_global
import time
from datetime import datetime
from core_gui.Shared_modules import Clock, status_box
import threading
import struct

class Decoder_Tab:

    clock = Clock()

    def __init__(self):

        self.data_mutex = threading.Lock()
        self.type_dict = { }
        self.message_data = [] 
        try:
            self.max_table_rows = int(gui_global.Config_File.config["Decoder"]["max_table_rows"])
        except:
            print("Decoder: max_table_rows not found in config file, using default value (100000)")
            self.max_table_rows = 100000
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
            data_converted = gui_global.decode_parameter_bytes(data[1], data[0])
            parameter_data = dpg.add_text(str(data_converted) + " " + data[0]["unit"])
            parameter_id = dpg.add_text(data[0]["id"])
            time_val = dpg.add_text(time.asctime(time.localtime()))

        self.parameter_table_list.append((paramter_row, parameter_name, parameter_data, parameter_data, time_val))

        if len(self.parameter_table_list) > self.max_table_rows:
            dpg.delete_item(self.parameter_table_list[0][0])
            self.parameter_table_list.pop(0)
        

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
