import dearpygui.dearpygui as dpg
import core_gui.gui_global as gui_global
from core_gui.Shared_modules import Clock, status_box, Command_element
import yaml


class All_Parameters():

    def __init__(self):    
        self.clock = Clock()
        
        with dpg.tab(label="All Parameters",):  # all code for the layout / configuration of the tab should be done in this with statement

            # use child window to allow for horizontal scaling
            with dpg.child_window(border=False, height=-100) as self.main_window:
                dpg.add_spacer(height=10)
                # using nested tables to allow for scalability and uneven cell size thers allot of them due to the way dear py gui shrinks right to left with no general scaling
                for id in gui_global.Parameters.parameter_dict:
                    Parameter_sub_graph(self.clock, id)


                self.toggle_clock_box = dpg.add_checkbox(label="run clock", default_value=True, callback=self.toggle_clock)
                self.clock.enable_lst.append(self.toggle_clock_box)

    def toggle_clock(self):

        if dpg.get_value(self.toggle_clock_box):
            self.clock.clock_disabled = False

        else:
            self.clock.clock_disabled = True

    def update_plots(self):
        self.main_graph.update()



    def toggle_clock(self):

        if dpg.get_value(self.toggle_clock_box):
            self.clock.clock_disabled = False

        else:
            self.clock.clock_disabled = True

class Parameter_sub_graph():

    def __init__(self, clock ,id):
        self.clock = clock
        self.id = id
        parameter = gui_global.Parameters.parameter_dict[id]
        with dpg.group(horizontal=True):
            self.enable = dpg.add_checkbox(label="enable", default_value=True, callback=self.change_element_status)    
            with dpg.collapsing_header(label=parameter.name):                   
                with dpg.plot(label=parameter.name, height=400, width=-1) as self.parameter_plot:
                    dpg.add_plot_legend(show=True)
                    dpg.add_plot_axis(dpg.mvXAxis, label="Time (sec, from gui start)")
                    dpg.add_plot_axis(dpg.mvYAxis, label="Data: " + parameter.unit)
                    self.line_series = dpg.add_line_series([0], [0], label=parameter.name, parent=dpg.last_item())
                
                
        clock.enable_lst.append(self.enable)
        self.change_element_status()

    def update(self):
        parameter = gui_global.Parameters.parameter_dict[self.id]
        dpg.set_value(self.line_series, [parameter.time, parameter.data])
    
    def change_element_status(self):

        self.clock.mutex.acquire()

        # enable element
        if(dpg.get_value(self.enable)):
            self.clock.lambda_dict.update({self : self.update})

        # disable element
        else:
            try:
                del self.clock.lambda_dict[self]
            except (KeyError,ValueError):
                pass
        
        self.clock.mutex.release()
        
        
                    




