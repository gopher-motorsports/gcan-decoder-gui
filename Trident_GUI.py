import dearpygui.dearpygui as dpg

from tabs.USB_Error_Log import USB_Error_Log
from tabs.Decoder import Decoder_Tab
from tabs.Parameter_Home import Parameter_Home

from core_gui.Footer import Footer
import core_gui.gui_global as gui_global
import core_gui.Shared_modules as Shared_modules

import time
import threading



# This is the main wrapper for the entire program's gui most of the layout / gui code is in their respective py folder, except for the footer
class Main_GUI:
    
    # init function is used for global vars
    def __init__(self):
        self.toggle_bool = True 
        dpg.create_context()

    def start_gui(self):

        
        if gui_global.Config_File.config is None:
            dpg.create_viewport(title='Trident_GUI, Ver:1.0.0b', width=1200, height=1000, min_height=700, min_width=700)

        else:

            try:
                dpg.create_viewport(title='Trident_GUI, Ver:1.0.0b',
                                    width=int(gui_global.Config_File.config['Global']['init_window_width']),
                                    height=int(gui_global.Config_File.config['Global']['init_window_height']),
                                    min_height=int(gui_global.Config_File.config['Global']['window_min_height']),
                                    min_width=int(gui_global.Config_File.config['Global']['window_min_width']))

            except (KeyError, ValueError):  # invalid config file setting
                dpg.create_viewport(title='Trident_GUI, Ver:1.0.0b', width=1200, height=1000, min_height=700, min_width=700)
        try:
            dpg.set_viewport_large_icon("icon.ico")
            dpg.set_viewport_small_icon("icon.ico")
        except:
            pass
        
        dpg.setup_dearpygui()
        dpg.show_viewport()

        # disabled theme, this changes the appearance of disabled elements
        with dpg.theme() as disabled_theme:

            with dpg.theme_component(dpg.mvAll, enabled_state=False):
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, [47, 47, 47])

            with dpg.theme_component(dpg.mvButton, enabled_state=False):
                dpg.add_theme_color(dpg.mvThemeCol_Button, [47, 47, 47])
                dpg.add_theme_color(dpg.mvThemeCol_Text, [77, 77, 77])

            with dpg.theme_component(dpg.mvInputText, enabled_state=False):
                dpg.add_theme_color(dpg.mvThemeCol_Text, [77, 77, 77])
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, [47, 47, 47])

            with dpg.theme_component(dpg.mvCombo, enabled_state=False):
                dpg.add_theme_color(dpg.mvThemeCol_Button, [47, 47, 47])
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, [47, 47, 47])
                dpg.add_theme_color(dpg.mvThemeCol_Text, [77, 77, 77])

            with dpg.theme_component(dpg.mvCheckbox, enabled_state=False):
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, [47, 47, 47])
                dpg.add_theme_color(dpg.mvThemeCol_Text, [77, 77, 77])

            with dpg.theme_component(dpg.mvText, enabled_state=False):
                dpg.add_theme_color(dpg.mvThemeCol_Text, [77, 77, 77])

        dpg.bind_theme(disabled_theme)

        # main window
        with dpg.window(label="GUI", tag="main_win") as main_window:
            gui_global.primary_window = main_window

            with dpg.tab_bar():
                self.parameter_home = Parameter_Home()
                self.decoder_tab = Decoder_Tab()
                gui_global.USB_Middleware.usb_error_log_tab = USB_Error_Log()

            gui_global.USB_footer = Footer()

            # global popup window setup
            self.clock_popup_window = Shared_modules.Clock_popup_window()
            Shared_modules.Clock.popup_window = self.clock_popup_window.popup_window

        

        # normally dear py has a black viewport, and you can add windows inside said viewport, we just want one application window so we just set the main window to be the viewport
        dpg.set_primary_window("main_win", True)

        # main render loop where the global clock is run,
        # this loop renders each frame so we cannot block for the clock, as the gui would freeze
        # since rendering is done every loop there is no "busy waiting for the clock"
        start = time.time_ns() / 1000000
        clock = threading.Thread(target=self.run_clock)
        parameter_clock = threading.Thread(target=self.decoder_tab.load_parameter_data)
        
        while dpg.is_dearpygui_running():

            # global clock timer
            if ((time.time_ns() / 1000000) - start) > gui_global.USB_Middleware.global_clock_timer and gui_global.global_clock_enabled:
                # if(True): debug code
                if clock.is_alive() == False:
                    
                    if gui_global.USB_Middleware.USB_connected:
                        clock = threading.Thread(target=self.run_clock)
                        clock.start()

                start = time.time_ns() / 1000000
            
            # parameter timer
            if ((time.time_ns() / 1000000) - start) > gui_global.USB_Middleware.parameter_clock_timer and gui_global.global_clock_enabled:
                if parameter_clock.is_alive() == False:
                    if gui_global.USB_Middleware.USB_connected:
                        parameter_clock = threading.Thread(target=self.decoder_tab.load_parameter_data)
                        parameter_clock.start()
            dpg.render_dearpygui_frame()

        dpg.destroy_context()
    # end of start gui


    def run_clock(self):
        if self.toggle_bool:
            dpg.bind_item_theme(
                gui_global.USB_footer.USB_module.clock_btn,
                gui_global.USB_footer.USB_module.button_toggle_theme) # changing button color
            self.toggle_bool = False
        else:
            dpg.bind_item_theme(
                gui_global.USB_footer.USB_module.clock_btn,
                gui_global.USB_footer.USB_module.button_green_theme) # changing button color
            self.toggle_bool = True

        self.decoder_tab.clock.run_clock_cycle()
        self.parameter_home.clock.run_clock_cycle() 
       
if (__name__ == "__main__"):
    main_gui = Main_GUI()
    main_gui.start_gui()  # this will not return until the gui is closed
