
import time
import serial
import serial.tools.list_ports
from serial import SerialException


class USB_DeviceNotFound(Exception):
    pass

# the Primary purpose of this class / driver is to handle to low level USB communiucation and pass it onto the usb middleware class or paramter class
# It might be better practice to have the seperation between paramter and non paramter messages in the middleware class, but usb middleware was not desined for non controller responder communication

class USB_Interface:

    # sets up parameters and checks to see if the usb device specified is actually connected
    def __init__(self, vid=0, pid=0, timeout=.001, baudrate=19200, data = None):
        self.vid = vid
        self.pid = pid
        self.data = data
        ports = list(serial.tools.list_ports.comports())
        
        self.port = None
        self.ser = serial.Serial()
        self.ser.baudrate = baudrate
        self.ser.timeout = timeout
        self.ser.port = None
        self.started = False

        self.paramter_list = []
        self.non_paramter_list = []
        # loops though all com ports to see if the device we are looking for is plugged into the computer
        port_list = []
        for p in ports:
            if p.pid == pid and p.vid == vid:
                port_list.append(p)
        
        if port_list == []:
            raise USB_DeviceNotFound

        for device in port_list:
            try:
                self.ser.port = device.name
                self.port = device
                self.ser.open()
                self.started = True
                break
            except SerialException:
                pass

        if self.started is False:
            raise USB_DeviceNotFound

    def start(self):
        if (self.started):
            return
        self.ser.open()
        self.started = True

    def stop(self):
        if(self.started):
            self.ser.close()
            self.started = False

    def send_data(self, bytes):
        self.ser.write(bytes)

    def get_data(self):
        if self.non_paramter_list != []:
            return self.paramter_list.pop(0)

        # this is busy waiting, but we do not want to do any other work while doing this so...
        # may also need to acquire a mutex / sem here as this function can be called in a different thread ran by dearpy gui for callbacks
        start = time.time_ns() / 1000000

        while self.ser.in_waiting == 0:
            if (time.time_ns() / 1000000) - start >= 100:
                return []
        output = self.ser.read(1)
        
        if output[0] == 0x7e: # bypassing usb middleware here 
            return(self.decode_message(False))
        else:   
            # error case going to loop though buffer, if we find a 0x7e we will decode the message if not return empty list (error)
            while self.ser.in_waiting != 0:
                byte = self.ser.read(1)
                if byte[0] ==  0x7e:
                    return(self.decode_message(False))
            
            return []        

    def get_data_paramter(self):
        if self.paramter_list != []:
            return self.paramter_list.pop(0)
            

        elif self.ser.in_waiting != 0:
            output_data = self.ser.read(1)

            if output_data[0] == 0x7e:
                return(self.decode_message(True))
            else:
                return([]) # does not recursivly call as unlike get_data() this function does not want to wait for a message
        else:
            return([])

    def decode_message(self, parameter_flag = True):
        try:
            output = []
            check_sum = 0x7e
            for _ in range(4):
                byte = self.ser.read(1)
                if len(byte) == 0:
                    return []
                
                if byte[0] == 0x7D:
                    byte = self.ser.read(1)
                    if len(byte) == 0:
                        return []
                    byte = byte[0] ^ 0x20
                    check_sum += byte

                else:
                    byte = byte[0]
                    check_sum += byte      
            
            data = self.ser.read(2)
            id  = 0
            if data[0] == 0x7D:
                id = (data[1] << 8) ^ 0x20
                new_data = self.ser.read(1)
                if new_data[0] == 0x7D:
                    id += self.ser.read(1)[0] ^ 0x20
                    check_sum += id 
                else:
                    id += new_data[0]
                    check_sum += new_data[0]
                
            else: 
                id = data[0] << 8
                check_sum += data[0]
                if data[1] == 0x7D:
                    data_byte = int(self.ser.read(1)[0]) ^ 0x20
                    id += data_byte
                    check_sum += data_byte
                else:
                    id += data[1]
                    check_sum += data[1]

            if id == 0xffff: # this is a non paramter message
                message = []

                header = int(self.ser.read(1)[0])
                if header == 0x7D: # get header byte
                    header = self.ser.read(1)[0]
                message.append(header)

                message_len = int(self.ser.read(1)[0])
                if message_len == 0x7D:
                    message_len = self.ser.read(1)[0]
                message.append(message_len)

                for _ in range(message_len):
                    byte = int(self.ser.read(1)[0])
                    if byte == 0x7D:
                        byte = self.ser.read(1)[0]
                    message.append(byte)
                
                if parameter_flag:
                    self.non_paramter_list.append(message)
                else:
                    return message

                return(self.decode_message(parameter_flag))
            
            else:
                for parameter in self.data["parameters"]:
                    if int(self.data["parameters"][parameter]["id"]) == id:
                        output.append(self.data["parameters"][parameter])

                        data_len = 0
                        type = self.data["parameters"][parameter]["type"]
                        if type == "UNSIGNED8" or type == "SIGNED8":
                            data_len = 1
                        elif type == "UNSIGNED16" or type == "SIGNED16":
                            data_len = 2
                        elif type == "UNSIGNED32" or type == "SIGNED32" or type == "FLOATING":
                            data_len = 4
                        elif type == "COMMAND":
                            data_len = 5
                        elif type == "UNSIGNED64" or type == "SIGNED64":
                            data_len = 8
                        else:
                            return []

                        data = self.ser.read(data_len)
                        data_output = []
                        i = 0
                        byte_count = 0
                        
                        while byte_count < data_len:
                            if i >= data_len: # if we have reached the end of the data need to read more
                                new_data = self.ser.read(1)
                                if new_data[0] == 0x7D:
                                    data_byte = int(self.ser.read(1)[0]) ^ 0x20
                                    data_output.append(data_byte)
                                    check_sum += data_byte
                                else:
                                    data_output.append(int(new_data[0]))
                                    check_sum += int(new_data[0])
                                byte_count += 1
                            else:
                                if data[i] == 0x7D:
                                    if i == data_len - 1:
                                        data_byte = int(self.ser.read(1)[0]) ^ 0x20
                                        data_output.append(data_byte)
                                        check_sum += data_byte
                                    else:
                                        data_output.append(int(data[i+1]) ^ 0x20)
                                        check_sum += int(data[i+1] ^ 0x20)
                                    i += 2
                                else:
                                    data_output.append(int(data[i]))
                                    check_sum += int(data[i])
                                    i += 1
                                byte_count += 1
                        chk = self.ser.read(1) # read checksum 
                        if len(chk) == 0:
                            return []
                        chk = int(chk[0])
                        if chk == 0x7D:
                            chk = int(self.ser.read(1)[0]) ^ 0x20
                        #TODO: add checksum checking
                        if (check_sum).to_bytes(2,byteorder="big")[-1] != chk:  
                            print("checksum bad")
                            print(hex(check_sum))
                            print(hex(chk))
                            return self.decode_message(parameter_flag)
                            
                        output.append(data_output)
                        if not parameter_flag:
                            self.paramter_list.append(output)
                        else:
                            return output
                """In normal operation the program, should never reach this state, if it does that menas either an invalid paramter id, or more likely
                the prevous call to this function did not receive the data in time and timed out, and an escape byte must have been read and the escaped byte 
                was missed causing the program to desyncm  this was fixed by increaseing the timeout and also adding thie return statement, as while a message or two may be dropped, the program should
                be able to resync with the next message"""
                #TODO: add more robust error handing to prevent this state from occuring
                return []
              

        except IndexError:
            # no data to read from buffer, just clear cahe and keep going, may skip a message
            # TODO: look into this and see why this is happening, possibly turn up timeout?
            return []

        except KeyError:
            print("key error")
            return []
         
    def get_device_name(self):
        return self.port.description

    def set_timeout(self, new_timeout):
        self.ser.timeout = new_timeout

    def reset_input_buffer(self):
        self.ser.reset_input_buffer()

if __name__ == "__main__":
    test = USB_Interface(1155, 22336)
    test.start()
    test.ser.timeout = 1
    test.send_data(bytearray.fromhex('0a b0 02 00 19'))
    test.send_data(bytearray.fromhex('0a b0 02 00 19'))
    test.send_data(bytearray.fromhex('0a b0 02 00 19'))
    time.sleep(1)
    responce = test.get_data()

    print(responce)
