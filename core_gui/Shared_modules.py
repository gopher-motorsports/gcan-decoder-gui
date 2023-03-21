import dearpygui.dearpygui as dpg
import core_gui.gui_global as gui_global
import threading
import math

# this file is primarily used to share usb / modules between tabs to keep copied code to a minimum


# clock used to run functions / callbacks in a separate thread from the gui 
#
# each tab that makes use of a clock had a separate instance of this class to keep the code separate
    # all clocks run in the same thread, the order is determined in main_gui.py
#    
# has a dict of lambda expressions that are executed every x ms (determined by comm timer setting in footer)
# has a list of dpg check box objects that enable / disable the module, when the module is disabled, its lambda expression is removed from the dict and thus is not executed
    # The list is primarily used to keep track of all modules in a tab (for the enable / disable all checkbox)
#
# when a module is enabled, its function is added to the lambda dict
# it also has (an optional) functionality to show a popup window when it detects that the functions are timing out
class Clock:
    
    popup_enabled = True
    popup_shown = False
    popup_window = None

    def __init__(self):
        # called by main clock / render loop in main GUI (RUNS IN A SEPARATE THREAD FROM REST OF PROGRAM)
        self.lambda_dict = {}            # dict of all functions to run
        self.enable_lst = []             # list of all modules that can be enabled / disables (the checkbox of the module specifically)
        self.mutex = threading.Lock()    # mutex to ensure that no other thread tries to edit the enable list or the lambda dict during clock execution
        self.clock_disabled = False      

    def run_clock_cycle(self):
        if self.clock_disabled is False and Clock.popup_shown is False:
            # in global_vars_and_funcs.py there is a counter to the total number of messages timed out, we just want ot see how many time out in this clock cycle
            init = gui_global.USB_Middleware.global_timeout_clock

            self.mutex.acquire()
            for element in self.lambda_dict.values():
                element()  # this is a lambda expression that runs whatever function specified in the dict
            self.mutex.release()

            # check to see if the device is not responding
            if gui_global.USB_Middleware.global_timeout_clock - init >= len(self.lambda_dict) / 2 and len(self.lambda_dict) != 0:  # at least half of the messages timed out
                if Clock.popup_enabled:
                    Clock.popup_shown = True
                    # while showing popup window, clock is stopped/disabled until window is closed
                    dpg.configure_item(Clock.popup_window, show=True, 
                        pos = [(dpg.get_item_width(gui_global.primary_window) / 2) - 300, (dpg.get_item_height(gui_global.primary_window) / 2) -75])

# end of clock class

# class used when device is not responding / multiple messages are timing out
class Clock_popup_window():

    def __init__(self):
        # popup window when clock times out
        with dpg.window(modal=True, show=False, no_title_bar=True, popup=True, width=600, height=150) as self.popup_window:
            dpg.add_text("Device doesn't seem to be responding, do you want to turn off the global clock?", wrap=0)
            dpg.add_text("(This can also be caused by unsupported fdcan commands being sent to the device)", wrap=0)
            dpg.add_spacer(height=10)
            self.popup_check_bx = dpg.add_checkbox(label=": Disable this popup (GUI may freeze up!)", default_value=False, callback=self.disable_popup)
            dpg.add_spacer(height=10)

            with dpg.group(horizontal=True):
                dpg.add_spacer(width=200)
                self.popup_yes_btn = dpg.add_button(label="Yes", width=75, callback=self.popup_close)
                self.popup_no_btn = dpg.add_button(label="No", width=75, callback=self.popup_close)

        Clock.popup_window = self.popup_window
        

    def popup_close(self,sender):
        if sender == self.popup_yes_btn:
            gui_global.global_clock_enabled = True # making sure global clock gets disabled (this should be unnecessary)
            gui_global.USB_footer.USB_module.enable_disable_global_clock()

        dpg.configure_item(self.popup_window, show = False) # hide popup window
        Clock.popup_shown = False

    def disable_popup(self):
        if dpg.get_value(self.popup_check_bx):
            Clock.popup_enabled = False
        else:
            Clock.popup_enabled = True

# status box used in dynamic readings and the gpio_pin class in simple_commands.py
class status_box:

    # title will be the title of the table
    # labels is a list of all the bits of the table
    # command is the command code that the table is linked to (type = string)
    # clock is the Clock class of the tab
    # offset is an optional setting that allows you to offset where the table starts readings bits
        # the class will only read enough bits to fill out the table and ignore the rest even if there are more
    # data_bytes_bk is the length of how many data bytes the command should send back
        # data_bytes_bk is only required when you have extra bytes you are not reading / using to make sure they get consumed
    # enabled determines if the module is initialized enabled or disabled
    def __init__(self, title, labels, command, clock , offset=0,data_bytes_bk = None,enabled=True):
        self.bit_list = []         # list of all the byte objects in the table 
        self.command = command 
        self.clock = clock    
        self.offset = offset
        self.bit_set_colors = []   # what color the bit status "led" light up as when triggered defaults to red and can be changed after initialization

        self.header_enable_color = (255,255,255) # color of the header when the table is initialized, can be changed after execution
        self.cmd_block_rd = False                # if the command is a block read command turn this to true after initialization

        self.data_bytes_bk = data_bytes_bk
        self.usb_data = None # not used in this class, but used in child classes
        
        # make trigger color lst
        for _ in labels:
            self.bit_set_colors.append(([255,255,255],[255,0,0]))

        # removing default padding to allow for the elements to be squeezed together to save space
        with dpg.theme() as status_box_style:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, 0, category=dpg.mvThemeCat_Core)
                dpg.add_theme_style(dpg.mvStyleVar_CellPadding, 0, 0, category=dpg.mvThemeCat_Core)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 0, 0, category=dpg.mvThemeCat_Core)

        # drawing of table / box starts here:
        # uses nested tables to allow for resizing while also enforcing a max width
        with dpg.table(policy=dpg.mvTable_SizingFixedFit, header_row=False, no_host_extendX=True) as parent_table: # used to bind the custom theme and force max width
            dpg.add_table_column(init_width_or_weight=200)
            with dpg.table_row():
                with dpg.table(
                    header_row=False, 
                    policy=dpg.mvTable_SizingStretchProp,
                    borders_outerH=True,
                    borders_outerV=True) as header_table:  # header table (allows for resizing)

                    dpg.add_table_column(width_fixed=True)    # table title
                    dpg.add_table_column(width_stretch=True)  # spacer col to push other elements to the end of the table
                    dpg.add_table_column(width_fixed=True)    # table  cmd result print out
                    dpg.add_table_column(width_fixed=True)    # table enable / disable check box a

                    with dpg.table_row():
                        self.title = dpg.add_text(title, color=self.header_enable_color) # title
                        dpg.add_spacer(width=1999) # spacer

                        self.cmd_text = dpg.add_text("0x{0:0{1}X} ".format(0,2)) # table_cmd
                        self.enable = dpg.add_checkbox(default_value=enabled, callback=self.change_element_status) # enable / disable checkbox
                        self.clock.enable_lst.append(self.enable)  # adding status bits to clock / tab enable/disable list
                    
                    dpg.highlight_table_row(header_table, 0, [48, 48, 51]) # add a grey shade to header row to make it stand out

            with dpg.table_row():
                with dpg.table(
                    policy=dpg.mvTable_SizingFixedFit, 
                    borders_innerH=True, 
                    borders_innerV=False, 
                    borders_outerH=True, 
                    borders_outerV=True, 
                    header_row=False) as self.status: # main / bit table

                    dpg.add_table_column(width_fixed=True)    # status box
                    dpg.add_table_column(width_fixed=True)    # spacer col
                    dpg.add_table_column(width_stretch=True)  # flag title / desc
                    dpg.add_table_column(width_fixed=True)    # check box
                    
                    i = 0
                    for bit in labels:
                        with dpg.table_row():
                            test = status_box_bit(bit,i)
                            dpg.highlight_table_cell(self.status, i,0,(0,0,0)) # "led" starts off as black
                            self.bit_list.append(test) # add to bit list
                        i += 1

        dpg.bind_item_theme(parent_table, status_box_style) # bind the custom theme to the parent table to get rid of the default padding
        self.change_element_status() # add the elements to the clock queue 

    # checks the value of the table checkbox and either enables or disables the object
    def change_element_status(self):

        self.clock.mutex.acquire() # grab clock mutex to ensure clock doesn't run while we are adding and removing things from the lambda dict

        if dpg.get_value(self.enable): # enable box
            dpg.configure_item(self.title, color = self.header_enable_color) # update colors
            dpg.configure_item(self.cmd_text, color = (255,255,255))

            for bit in self.bit_list: # enable every bit in the table
                dpg.set_value(bit.check_box, True)
                bit.change_status()
            
            # adding callback / update byte fun to clock dict 
            self.clock.lambda_dict.update({self: (lambda: self.update_byte())})

        else: # disable
            dpg.configure_item(self.title, color = (75,75,75))   # update colors
            dpg.configure_item(self.cmd_text, color = (75,75,75))

            for bit in self.bit_list: # disable every bit
                dpg.set_value(bit.check_box, False) 
                bit.change_status()

            try:
                del self.clock.lambda_dict[self] # remove callback function from clock queue
            except:
                pass
        self.clock.mutex.release()

    # sends the command through the set global comm bus and updates the table accordingly
    def update_byte(self):

        if self.data_bytes_bk is None: # if no command size is given calculate it by the # of bits provided
            cmd_bytes_bk = math.ceil(len(self.bit_list) / 8) # rounds up instead of down (division)
        else:
            cmd_bytes_bk = self.data_bytes_bk
        # does nothing if no usb device connected
        if gui_global.USB_Middleware.USB_connected:
            header_bytes = 2 # how many header bytes are in the message before the data bytes (not counting the offset)

            if self.cmd_block_rd:
                header_bytes = 3

            if gui_global.USB_Middleware.current_comm_protocol == "FDCAN":
                USB_message_type = "FDCAN_RD/WR"
            
            elif gui_global.USB_Middleware.current_comm_protocol == "I2C":
                USB_message_type = "I2C_RD/WR"
            
            else:    
                return # unsupported comm protocol for this module just return
        
            try:
                # send usb message though middle ware
                usb_data_bk = gui_global.USB_Middleware.send_usb_msg(USB_message_type, cmd_bytes_bk, 1, self.command, "STATUS BOX: " + dpg.get_value(self.title))
            except gui_global.Invalid_USB_msg_received:
                return

            if usb_data_bk == []:  # timeout
                self.usb_data = usb_data_bk
                return
            
            # skipping over address byte
            if (usb_data_bk[0][1] * 8) < cmd_bytes_bk and usb_data_bk[0][1] == len(usb_data_bk) + 2:  # rounding up, checking to see if we received enough bits 
                gui_global.USB_Middleware.USB_Device_id.reset_input_buffer() # probably out of sync resetting usb buffer to try and fix (usb messages may be lost)
                return
           
            self.usb_data = usb_data_bk
            current_byte_pos = header_bytes + (usb_data_bk[0][1] - 1) - self.offset # is the location of the current byte we are looking at in the byte array
            current_bit = 0  # current bit in the byte we are looking at
            byte_num = 0     # how many bytes we have looked at, this exists because of the difference in the byte order (endianness) of the table vs the byte array
            cmd_text = 0     # int of the bits read, used to print out the hex val of the received command to the table
               
            for bit in self.bit_list:
                if bit.enabled: # if bit is no enabled, just ignore and loop over
                    
                    mask = (1 << (7 - current_bit))           # mask out everything except the bit we care about
                    bit_location = current_bit + 8 * byte_num # find what bit we are on (loop count)

                    # left side of bitwise and is the byte that we are looking at
                    # right side of bitwise and is a mask that consists of the bit we want to look at
                    if (usb_data_bk[0][current_byte_pos] & mask) == mask:  # flag / bit is set        
                        dpg.configure_item(bit.text, color=self.bit_set_colors[bit_location][0]) # 1st element in tuple is the text color value 2nd is for the "led"
                        dpg.highlight_table_cell(self.status, (byte_num * 8) + current_bit, 0, self.bit_set_colors[bit_location][1])
                        
                    else: # flag / bit is not set
                        dpg.configure_item(bit.text, color=(75,75,75))
                        dpg.highlight_table_cell(self.status, bit_location, 0, (0,0,0))
                        
                current_bit += 1
                        
                if current_bit == 8:  # end of byte
                    cmd_text = usb_data_bk[0][current_byte_pos] | (cmd_text << (8 * byte_num)) # adding byte to output text var
                    current_bit = 0       # resetting current bit as we are moving to new byte
                    current_byte_pos -= 1 # updating byte pos
                    byte_num += 1         # updating byte num

            # done just need to update hex val at top of table    
            if self.data_bytes_bk is None:
                dpg.set_value(self.cmd_text, "0x" + "{0:0{1}X}".format(cmd_text, int(cmd_bytes_bk * 2))) # updating cmd text
            else:
                dpg.set_value(self.cmd_text, "0x" + "{0:0{1}X}".format(cmd_text,math.ceil(len(self.bit_list) / 8))) # updating cmd text

# class for a row in the status box class above
class status_box_bit:

    def __init__(self,text,row_number,enabled = True):
        self.enabled = enabled
        self.row_number =  row_number

        dpg.add_spacer(width=15)  # color section
        dpg.add_spacer(width=5)  # space between color box and text

        with dpg.group(horizontal= True) as self.text_grp: # spacer allows for the checkbox to be pushed to the end of the table
            self.text = dpg.add_text(text, color = (78,78,78))
            dpg.add_spacer(width=2000)

        self.check_box = dpg.add_checkbox(default_value=self.enabled, callback=self.change_status)

    def change_status(self): # only need to worry about disabling 
        
        if dpg.get_value(self.check_box) == False: # disable bit
            dpg.configure_item(self.text, color = [78, 78, 78])
            dpg.highlight_table_cell(dpg.get_item_parent(dpg.get_item_parent(self.text_grp)), self.row_number, 0,(0,0,0))
            self.enabled = False
        else:
            self.enabled = True
                    

