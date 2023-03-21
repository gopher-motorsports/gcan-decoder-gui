import dearpygui.dearpygui as dpg
import core_gui.gui_global as gui_global
from core_gui.USB_Driver import USB_DeviceNotFound, USB_Interface


class Footer:

    def __init__(self):
        with dpg.table(header_row=False, policy=dpg.mvTable_SizingStretchProp, no_host_extendX=True, no_pad_outerX=True, no_pad_innerX=True):
            # using a table for separating the elements of the gui as is allows for easy resizing

            dpg.add_table_column()  # logo column
            dpg.add_table_column()  # USB connect module
            dpg.add_table_column()  # Usb custom command module
            dpg.add_table_column()  # USB global config module

            with dpg.table_row():
                # you can change the order of these modules by changing the order of these methods
                # just make sure the column configs are right
                self.draw_logo()  # very simple, so it doesn't have its own class
                # draw usb connect module and usb global config module
                self.USB_module = USB_module()
                # draw custom usb command module
                USB_custom_command_module(self.USB_module)

    def draw_logo(self):
        try:
            with dpg.group(horizontal=True):  # 1st table column
                width, height, channels, data = dpg.load_image("thumbnail.png")
                with dpg.texture_registry():  # code to load logo into program
                    logo = dpg.add_static_texture(width=width, height=height, default_value=data)

                dpg.add_image(logo)  # adding logo to gui

                dpg.add_spacer(width=5)  # padding
        except:
            dpg.add_text("No Logo found!")


class USB_module:

    def __init__(self):  # draws the module and assigns callbacks

        with dpg.theme() as self.button_green_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, [0,100,0])
                
        with dpg.theme() as self.button_red_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, [100,0,0])

        with dpg.theme() as self.button_toggle_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, [0,50,0])

        gui_global.USB_connected = False
        # usb connect module
        with dpg.group(horizontal=True):  # 2nd table column

            # code for usb device vid / pid text / connect button
            with dpg.group():
                # the wrap setting allows for text to be compressed in window resizing, howver with how the footer is configured, wrapping should not occur
                # the text is mostly static so it doesn't need to be assigned a var for later reference
                dpg.add_text("USB Device Vid:", wrap=0)
                dpg.add_text("USB Device Pid:", wrap=0)
                dpg.add_text("USB Device Nme:", wrap=0)
                self.connect_button = dpg.add_button(label="Connect", callback=self.connect_to_usb_cdc, width=103)

            # code for the input text boxes for connecting toa usb device
            with dpg.group():  # group for connect button and connect status text

                if gui_global.Config_File.config is not None:
                    try:
                        self.vid_input = dpg.add_input_int(step=0, width=150, default_value=int(gui_global.Config_File.config['Footer']['default_vid']))
                    except (KeyError, ValueError):
                        self.vid_input = dpg.add_input_int(step=0, width=150, default_value=1155)
                    try:
                        self.pid_input = dpg.add_input_int(step=0, width=150, default_value=int(gui_global.Config_File.config['Footer']['default_pid']))
                    except (KeyError, ValueError):
                        self.pid_input = dpg.add_input_int(step=0, width=150, default_value=22336)

                else:
                    self.vid_input = dpg.add_input_int(step=0, width=150, default_value=1155)
                    self.pid_input = dpg.add_input_int(step=0, width=150, default_value=22336)

                self.name_value = dpg.add_input_text(readonly=True, width=150, default_value="N/A", tag="USB_device_name_text_box")
                self.usb_connect_stat = dpg.add_text(default_value="No USB Device connected", color=(255, 0, 0), wrap=0)
            
            dpg.bind_item_theme(self.connect_button, self.button_red_theme)

        with dpg.group(horizontal=True):  # 3rd table column (global usb config)

            with dpg.group():
                dpg.add_text("   Main comm bus:", wrap=0)
                dpg.add_text("     Device addr:", wrap=0)
                dpg.add_text("Clock timer (ms):", wrap=0)
                dpg.add_text("    Global clock:", wrap=0)

            with dpg.group():
                try:
                    self.comm_bus = dpg.add_combo(
                        (["GopherCAN"]),
                        default_value=gui_global.Config_File.config['Footer']['default_comm_bus'],
                        width=100,
                        callback=self.update_comm_protocol)
                except(KeyError,ValueError):
                    self.comm_bus =  dpg.add_combo(("GopherCAN"), default_value="GopherCAN", width=100, callback=self.update_comm_protocol)
                
                try:                    
                    self.device_addr = dpg.add_combo(
                        (["N\\A"]),
                        default_value=gui_global.Config_File.config['Footer']['default_device_addr'],
                        width=100,
                        callback=self.update_USB_addr)
                except(KeyError,ValueError):
                    self.device_addr =  dpg.add_combo(("N\\A"), default_value="N\\A", width=100, callback=self.update_USB_addr)

                try:
                    self.global_timer = dpg.add_input_int(width=100, default_value=int(gui_global.Config_File.config['Footer']['default_comm_timer']),callback = self.update_global_clock_tim)

                except (KeyError, ValueError):  # invalid config file setting going to delete whatever was drawn and remake with default values                    
                    self.global_timer = dpg.add_input_int(width=100, default_value=1000,callback=self.update_global_clock_tim)
                
            

                self.clock_btn = dpg.add_button(label="Enabled", width=100, callback=self.enable_disable_global_clock)
                dpg.bind_item_theme(self.clock_btn, self.button_green_theme)

    # callback when the connect button is pressed in the footer (to connect to the usb device)
    # USB settings is a tuple with the settings of the vid, pid, name text ,and status text, (vid,pid,name,status)

    def connect_to_usb_cdc(self):
        
        gui_global.USB_Middleware.usb_lock.acquire() # making sure no other usb traffic is happening
        # if usb device already connected, disconnect
        if(gui_global.USB_Middleware.USB_connected):
            gui_global.USB_Middleware.USB_Device_id.stop()

        try:
            # declaring a usb device with the vid and pid given in the input boxes
            if gui_global.Config_File.config is None:
                gui_global.USB_Middleware.USB_Device_id = USB_Interface(dpg.get_value(self.vid_input), dpg.get_value(self.pid_input))

            else:
                try:
                    gui_global.USB_Middleware.USB_Device_id = USB_Interface(
                        dpg.get_value(self.vid_input), 
                        dpg.get_value(self.pid_input),
                        .01, 
                        int(gui_global.Config_File.config['Footer']['usb_baud_rate']),
                        gui_global.USB_Middleware.paramter_data)

                except KeyError:
                    gui_global.USB_Middleware.USB_Device_id = USB_Interface(dpg.get_value(self.vid_input), dpg.get_value(self.pid_input), .01, 9600, gui_global.USB_Middleware.paramter_data)


            # updating usb status message
            dpg.configure_item(self.usb_connect_stat, color=[0, 255, 0], default_value="USB Device Connected!")
            dpg.bind_item_theme(self.connect_button, self.button_green_theme)

            # getting name of device and putting it in the device nme text box
            dpg.set_value(self.name_value, gui_global.USB_Middleware.USB_Device_id.get_device_name())

            gui_global.USB_Middleware.USB_connected = True

        except USB_DeviceNotFound:
            # updating usb status message
            dpg.configure_item(self.usb_connect_stat, color=[255, 0, 0], default_value="USB Device not found.")
            dpg.bind_item_theme(self.connect_button, self.button_red_theme)
            gui_global.USB_Middleware.USB_connected = False
    
        gui_global.USB_Middleware.usb_lock.release()

    def usb_disconnected(self):
        gui_global.USB_Middleware.USB_connected = False
        dpg.configure_item(self.usb_connect_stat, default_value="USB Device Disconnected", color = (255,0,0))
        dpg.bind_item_theme(self.connect_button, self.button_red_theme)

    def update_USB_addr(self):
        gui_global.USB_Middleware.Secondary_id = dpg.get_value(self.device_addr)

    def update_comm_protocol(self):
        gui_global.USB_Middleware.current_comm_protocol = dpg.get_value(self.comm_bus)

    def update_global_clock_tim(self):
        gui_global.USB_Middleware.global_clock_timer = dpg.get_value(self.global_timer)

    def enable_disable_global_clock(self):
        if gui_global.global_clock_enabled:
            dpg.bind_item_theme(self.clock_btn, self.button_red_theme)
            dpg.configure_item(self.clock_btn, label ="Disabled")
            gui_global.global_clock_enabled = False
        else:
            dpg.bind_item_theme(self.clock_btn, self.button_green_theme)
            dpg.configure_item(self.clock_btn, label="Enabled")
            gui_global.global_clock_enabled = True

class USB_custom_command_module:

    def __init__(self, USB_data):

        self.USB_module = USB_data

        # USB custom command send module
        with dpg.group(horizontal=True):  # 3rd table column

            with dpg.group():
                dpg.add_text(" USB command:", wrap=0)
                dpg.add_text("# msg's back:", wrap=0)
                dpg.add_text("USB Response:")

                self.USB_custom_command_send_button = dpg.add_button(
                    tag="USB_custom_command_send_button", 
                    label="Send message", 
                    callback=self.send_custom_USB_message)

            with dpg.group():

                self.USB_custom_command_input_box = dpg.add_input_text(
                    hexadecimal=True, width=250, 
                    hint="Input raw USB command here.", 
                    callback=self.format_input_string)

                self.USB_custom_expected_messages_back = dpg.add_input_int(width=250, default_value=1)

                self.USB_custom_response = dpg.add_input_text(
                    width=250, 
                    readonly=True, 
                    hint="Last Response message goes here")

                self.USB_custom_command_status_text = dpg.add_text("No USB message sent", color=[255, 0, 0])

    def format_input_string(self):
        # get input string and strip its white space
        output_str = (dpg.get_value(self.USB_custom_command_input_box)).replace(' ','')
        output_str = " ".join(output_str[i:i + 2] for i in range(0, len(output_str), 2))
        dpg.set_value(self.USB_custom_command_input_box, output_str)

    # skips over usb_middleware and just used the usb driver directly

    def send_custom_USB_message(self):

        # check to see if connected to USB device
        if not gui_global.USB_Middleware.USB_connected:
            dpg.configure_item(self.USB_custom_command_status_text, default_value="No USB Device connected!", color=[255, 0, 0])
            return

        # converting value from USB command input text box (id provided though user_data)
        data_string = dpg.get_value(self.USB_custom_command_input_box)

        if(data_string == 0):
            # updating status text (input box was empty)
            dpg.configure_item(self.USB_custom_command_status_text, value="No USB command provided!", color=[255, 0, 0])
            return

        # converting string to byte array to send though COM port
        data = bytearray.fromhex(data_string)

        gui_global.USB_Middleware.usb_lock.acquire() # making sure no other usb traffic is happening
        try:
            gui_global.USB_Middleware.USB_Device_id.send_data(data)
        except:
            gui_global.USB_footer.USB_module.usb_disconnected()
            dpg.configure_item(self.USB_custom_command_status_text, default_value="No USB Device connected!", color=[255, 0, 0])
            gui_global.USB_Middleware.usb_lock.release()
            return
        
        if dpg.get_value(self.USB_custom_expected_messages_back) == 0:
            gui_global.USB_Middleware.usb_lock.release()
            return

        # loop for amount of times specified by "# msg's back"
        for _ in range(dpg.get_value(self.USB_custom_expected_messages_back)):

            # get first two bytes of USB message to see how long the received message is
            response = gui_global.USB_Middleware.USB_Device_id.get_data()

            # Py serial has no timeout flag / check so we just need to see if the bytes we requested were actually read vs just timed out
            if len(response) < 3:
                dpg.configure_item(self.USB_custom_command_status_text, default_value="Timeout reached!", color=[255, 0, 0])
                gui_global.USB_Middleware.USB_Device_id.reset_input_buffer()
                gui_global.USB_Middleware.usb_lock.release()
                return

            if len(response) != response[1] + 2:  # either the main board sent a invalid usb message, or the usb message was not received properly
                dpg.configure_item(self.USB_custom_command_status_text, default_value="Error, invalid USB message length", color=[255, 0, 0])
                gui_global.USB_Middleware.USB_Device_id.reset_input_buffer()
                gui_global.USB_Middleware.usb_lock.release()
                return

        # updating status text
        dpg.configure_item(self.USB_custom_command_status_text, default_value="USB message received", color=[0, 255, 0])
        # pushing received value to gui
        dpg.set_value(self.USB_custom_response, str(response))
        gui_global.USB_Middleware.usb_lock.release()