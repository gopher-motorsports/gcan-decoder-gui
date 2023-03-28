import dearpygui.dearpygui as dpg
import core_gui.gui_global as gui_global
from core_gui.Shared_modules import Clock, status_box, Command_element
import yaml


class Parameter_Home():

    def __init__(self):    
        self.clock = Clock()
        
        
        # try to open an load gopher can config file (specified in gui_condig.ini)
        try:
            self.yaml_file = gui_global.Config_File.config["Parameter"]["default_gcan_file"] 
            with open(self.yaml_file, "r") as file:
                self.gopher_can_config = yaml.safe_load(file)
                gui_global.USB_Middleware.paramter_data = self.gopher_can_config

        except(KeyError, ValueError, FileNotFoundError): # TODO: add fuctionality to look for config file if failed
            self.yaml_file = None
            self.gopher_can_config = {}
            gui_global.USB_Middleware.paramter_data = self.gopher_can_config

        with dpg.tab(label="Parameter Home",):  # all code for the layout / configuration of the FDCAN tab should be done in this with statement

            # use child window to allow for horizontal scaling
            with dpg.child_window(border=False, height=-100) as self.main_window:
                dpg.add_spacer(height=10)
                # using nested tables to allow for scalability and uneven cell size thers allot of them due to the way dear py gui shrinks right to left with no general scaling

                with dpg.table(header_row=False, policy=dpg.mvTable_SizingStretchProp, no_pad_outerX=True, no_pad_innerX=True):
                    # UNUSED
                    dpg.add_table_column()
                    # UNUSED
                    dpg.add_table_column()
                    # UNUSED
                    dpg.add_table_column()

                    with dpg.table_row():
                        with dpg.group():  # first column / left side of tab
                            self.yaml_status_box = Paramter_yaml_status_box(self)
                        with dpg.group():  # 2nd column / middle of tab
                            dpg.add_spacer() # EMPTY, FREE SPACE FOR NEW MODULES

                        with dpg.group():  # 3rd column / right side of tab
                            dpg.add_spacer() # EMPTY, FREE SPACE FOR NEW MODULES   

                self.toggle_clock_box = dpg.add_checkbox(label="run clock", default_value=True, callback=self.toggle_clock)

    def toggle_clock(self):

        if dpg.get_value(self.toggle_clock_box):
            self.clock.clock_disabled = False

        else:
            self.clock.clock_disabled = True

class Paramter_yaml_status_box():
    
        def __init__(self, parent):
            
            self.parent = parent

            with dpg.table(borders_outerH=True, borders_outerV=True, policy=dpg.mvTable_SizingFixedFit, header_row=True, no_host_extendX=True):
                dpg.add_table_column(init_width_or_weight=410, label="Input")

                dpg.add_table_column(init_width_or_weight=418)  # set max width
                with dpg.table_row():
                    with dpg.group(horizontal=True):
                        if self.parent.yaml_file is None:
                            dpg.add_text("Parameter YAML file :")
                            self.file_txt = dpg.add_text("None", color=[255, 0, 0])
                        else:
                            dpg.add_text("Parameter YAML file :")
                            self.file_txt = dpg.add_text(self.parent.yaml_file, color=[0, 255, 0])

        def update(self):
            if self.parent.yaml_file is None:
                dpg.configure_item(self.file_txt, default_value="None", color=[255, 0, 0])
            else:
                dpg.configure_item(self.file_txt, default_value=self.parent.yaml_file, color=[0, 255, 0])
                        





