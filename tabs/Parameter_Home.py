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

        gui_global.Parameters.init_parameter_dict() # create parameter dict from yaml file
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
                            self.yaml_status_box = Parameter_yaml_status_box(self)
                            dpg.add_spacer(height=10)
                            self.main_graph = Parameter_home_graph()
                            dpg.add_checkbox(label="update plots", default_value=True, callback=self.update_plots)
                        with dpg.group():  # 2nd column / middle of tab
                            dpg.add_spacer() # EMPTY, FREE SPACE FOR NEW MODULES

                        with dpg.group():  # 3rd column / right side of tab
                            dpg.add_spacer() # EMPTY, FREE SPACE FOR NEW MODULES   

                self.toggle_clock_box = dpg.add_checkbox(label="run clock", default_value=True, callback=self.change_plot_update)
                self.clock.enable_lst.append(self.toggle_clock_box)
                self.change_plot_update()

    def update_plots(self):
        self.main_graph.update()

    def change_plot_update(self):
        self.clock.mutex.acquire()

        # enables element
        if(dpg.get_value(self.toggle_clock_box)):
            self.clock.lambda_dict.update({self : self.update_plots})
        else:
            try:
                del self.clock.lambda_dict[self]
            except (KeyError,ValueError):
                pass
        self.clock.mutex.release()



    def toggle_clock(self):

        if dpg.get_value(self.toggle_clock_box):
            self.clock.clock_disabled = False

        else:
            self.clock.clock_disabled = True

class Parameter_yaml_status_box():
    
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

class Parameter_home_graph():

    def __init__(self):
        self.update_lst = []
        with dpg.group(horizontal=True):
            with dpg.child_window(border=False, width=200, height=-70) as self.legend:

                dpg.add_text("Parameters:")
                for id in gui_global.Parameters.parameter_dict:
                    parameter = gui_global.Parameters.parameter_dict[id]
                    dpg.add_button(label=parameter.name)
                    with dpg.drag_payload(parent =dpg.last_item(),drag_data=(parameter.time, parameter.data, (parameter.name + ": " + parameter.unit), parameter.id), payload_type="plotting") as data:
                        dpg.add_text(parameter.name)
                        simple_plot_id = dpg.add_simple_plot(label="", default_value=parameter.data)
                        self.update_lst.append(Parameter_icon_update(id,simple_plot_id))
                        dpg.set_item_user_data(simple_plot_id, id)


            def _legend_drop(sender, app_data, user_data):
                parent = dpg.get_item_info(sender)["parent"]
                yaxis2 = dpg.get_item_info(parent)["children"][1][2]
                dpg.add_line_series(app_data[0], app_data[1], label=app_data[2], parent=yaxis2)
                dpg.add_button(label="Delete Series", user_data = dpg.last_item(), parent=dpg.last_item(), callback=lambda s, a, u: dpg.delete_item(u))

            def _plot_drop(sender, app_data, user_data):
                parent = dpg.get_item_info(sender)["parent"]
                yaxis1 = dpg.get_item_info(sender)["children"][1][0]
                id = dpg.add_line_series(app_data[0], app_data[1], label=app_data[2], parent=yaxis1)
                dpg.add_button(label="Delete Series", user_data = dpg.last_item(), parent=dpg.last_item(), callback=lambda s, a, u: dpg.delete_item(u))
                self.update_lst.append(Parameter_update(app_data[3], id))

                

            def _axis_drop(sender, app_data, user_data):
                dpg.add_line_series(app_data[0], app_data[1], label=app_data[2], parent=sender)
                dpg.add_button(label="Delete Series", user_data = dpg.last_item(), parent=dpg.last_item(), callback=lambda s, a, u: dpg.delete_item(u))

            with dpg.plot(label="Drag/Drop Plot", height=400, width=-1, drop_callback=_plot_drop, payload_type="plotting"):
                dpg.add_plot_legend(drop_callback=_legend_drop, payload_type="plotting",show=True)
                dpg.add_plot_axis(dpg.mvXAxis, label="Time (sec, from gui start)")

                # create y axes with drop callbacks
                dpg.add_plot_axis(dpg.mvYAxis, label="Data: (misc units)", drop_callback=_axis_drop, payload_type="plotting")


    def update(self):
        for update in self.update_lst:
            update.update()
                    
class Parameter_update():
    def __init__(self, param_id, plot_id):
        self.param_id = param_id
        self.plot_id = plot_id
    
    def update(self):
        parameter = gui_global.Parameters.parameter_dict[self.param_id]
        dpg.set_value(self.plot_id, [parameter.time, parameter.data])

class Parameter_icon_update():
    def __init__(self, param_id, icon_id):
        self.param_id = param_id
        self.icon_id = icon_id
    
    def update(self):
        parameter = gui_global.Parameters.parameter_dict[self.param_id]
        dpg.set_value(self.icon_id, parameter.data)
        



