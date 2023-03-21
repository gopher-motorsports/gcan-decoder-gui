import dearpygui.dearpygui as dpg
import core_gui.gui_global as gui_global
import time
from datetime import datetime


class USB_Error_Log:

    def __init__(self):

        with dpg.tab(label="USB Error Log"):
            self.error_list = []
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

                    dpg.add_table_column(label="Time:", init_width_or_weight=170)
                    dpg.add_table_column(label="Error Code:", init_width_or_weight=90)
                    dpg.add_table_column(label="Error desc:", init_width_or_weight=500)
                    dpg.add_table_column(label="Caught by:", init_width_or_weight=500)

                with dpg.group(horizontal=True):
                    dpg.add_button(label="clear table", callback=self.clear_table)
                    dpg.add_button(label="Save current log to disk", callback=self.show_save_file_window)

                with dpg.file_dialog(
                        default_filename=datetime.now().strftime("%Y_%m_%d-%I_%M_%S_%p") + "_USB_Error_Log",
                        modal=True,
                        show=False,
                        min_size=(500, 300),
                        callback=self.save_file) as self.file_selector:

                    # can add support for other files in the future
                    dpg.add_file_extension(".csv")

    def add_usb_error(self, error, sender_info):

        with dpg.table_row(parent=self.main_table) as usb_error:
            time_val = dpg.add_text(time.asctime(time.localtime()))
            error_code = dpg.add_text("{0:0{1}X}".format(error[2], 2))
            desc = dpg.add_text(self.get_usb_error_description(error), wrap=0)
            sender = dpg.add_text(sender_info)

        self.error_list.append((usb_error, time_val, error_code, desc, sender))

    def get_usb_error_description(self, error):

        if error[2] == 0x00:
            return "Unknown / unspecified USB error"
        elif error[2] == 0x01:
            return "Invalid USB message (a received USB_T message had an invalid format or used a undefined message id)"
        elif error[2] == 0x02:
            return "USB queue on USB_Main full"
        elif error[2] == 0x03:
            return "FDCAN message dropped by simple can / hal driver (see send_data known issues in USB main documentation [simple can])"
        elif error[2] == 0x04:
            dpg.configure_item(gui_global.mass_debug_invalid_cmd_text,show = True)
            return "FDCAN unexpected response. response given:" + str(error[2:])            
        elif error[2] == 0x05:
            return "FDCAN send queue full. is FDCAN connected and working?"
        elif error[2] == 0x06:
            return "I2C not responding. is I2C connected and working?"

    def clear_table(self):

        for element in self.error_list:

            dpg.delete_item(element[0])

        self.error_list.clear()

    def show_save_file_window(self):
        dpg.show_item(self.file_selector)

    def save_file(self, sender, app_data):
        if len(self.error_list) == 0:
            return # can implement error message here if wanted
        else:
            with open(app_data["file_path_name"], 'w') as file:
                file.write("Time,Error,Error desc, Caught by\n")
                for element in self.error_list:
                    line = dpg.get_value(element[1]) + ","
                    line += dpg.get_value(element[2]) + ","
                    line += dpg.get_value(element[3]) + ","
                    line += dpg.get_value(element[4]) + ",\n"
                    file.write(line)

        dpg.hide_item(self.file_selector)
