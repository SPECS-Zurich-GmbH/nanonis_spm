"""
Created on Wed Feb 24 19:32:05 2021

@author: Samuel O'Neill

@license: Copyright (C) 2023 SPECS ZURICH - support@specs-zurich.com>
 * This file is part of Nanonis Mimea software package.
 * The nanonis_spm_specs python package can not be copied and/or distributed without the
 * permission of Specs Zurich
"""

import socket
import struct
import numpy as np


class Nanonis:
    displayInfo = 0

    def __init__(self, connection):
        self.connection = connection
    def close(self):
        self.connection.close()

    def returnDebugInfo(self, displayInfo):
        self.displayInfo = displayInfo

    def printDebugInfo(self, responseTypes, bodyParts):
        i = 0
        for responseType in responseTypes:
            if (responseType[0] != '2'):
                print(responseType + ": " + str(bodyParts[i]))
            i = i + 1

    # Handles parsing of strings from Client to Server
    def handleString(self, BodyElement, BodyType, BodyPart):
        BodyElement = bytes(BodyElement, 'utf-8')
        BodyType = str(len(BodyElement)) + 's'
        BodyPart = BodyPart + struct.pack('>i', len(BodyElement))
        BodyPart = BodyPart + struct.pack('>' + BodyType, BodyElement)
        return BodyPart

    # Handles parsing of arrays from Client to Server (w. length prepended)
    def handleArrayPrepend(self, Array, BodyType, BodyPart):
        arrayLength = len(Array)

        BodyPart = BodyPart + struct.pack('>i', arrayLength)
        for i in range(0, arrayLength):
            if BodyType[2] == "c":
                Entry = bytes(str(Array[i]), "utf-8")
            else:
                Entry = Array[i]

            BodyPart = BodyPart + (struct.pack('>' + BodyType[2], Entry))  # NEED ALSO BODYTYPE FOR SINGULAR
            # ELEMENTS

        return BodyPart

    #Handles parsing of strings arrays from Client to Server (w. length prepended)
    def handleArrayString(self, Array, BodyType, BodyPart):
        arrayLength = len(Array)
        nrbytes=4*arrayLength
        BodyPart = BodyPart + struct.pack('>i', nrbytes)
        BodyPart = BodyPart + struct.pack('>i', arrayLength)
        for i in range(0, arrayLength):
            Entry = self.handleString(Array[i],BodyType,bytearray())
            BodyType = str(len(Entry)) + 's'
            BodyPart = BodyPart + (struct.pack('>' + BodyType, Entry))  
        return BodyPart

    #Handles parsing of 2D arrays of floats
    def handle2DArray(self, Array, BodyType, BodyPart):
        arrayRows = len(Array) #number of rows
        BodyPart = BodyPart + struct.pack('>i', arrayRows)
        arrayColumns=len(Array[0]) #number of columns
        BodyPart = BodyPart + struct.pack('>i', arrayColumns)
        for i in range(0, arrayRows):
            for j in range(0, arrayColumns):
                Entry = float(Array[i][j])
                BodyPart = BodyPart + (struct.pack('>' + BodyType[1], Entry))
        return BodyPart

    # Handles parsing of arrays form Client to Server
    def handleArray(self, Array, BodyType, BodyPart):
        arrayLength = len(Array)
        for i in range(0, arrayLength):
            Entry = Array[i]
            BodyPart = BodyPart + (struct.pack('>' + BodyType[1], Entry))  
        return BodyPart

    def correctType(self, BodyType, Body):
        if BodyType == 'H' and isinstance(Body, np.uint16) is False:
            Body = np.uint16(Body)
        elif BodyType == 'h' and isinstance(Body, np.int16) is False:
            Body = np.int16(Body)
        elif BodyType == 'I' and isinstance(Body, np.uint32) is False:
            Body = np.uint32(Body)
        elif BodyType == 'i' and isinstance(Body, np.int32) is False:
            Body = np.int32(Body)
        elif BodyType == 'f' and isinstance(Body, np.float32) is False:
            Body = np.float32(Body)
        elif BodyType == 'd' and isinstance(Body, np.float64) is False:
            Body = np.float64(Body)

        return Body

    def send(self, Command, Body, BodyType):
        BodyPart = bytearray()

        for i in range(0, len(Body)):
            if "*" in BodyType[i]:
                instance = Body[i]
                type = BodyType[i]
                if "c" in BodyType[i]:
                    if isinstance(Body[i], str)==True:
                        #Array of chars (i.e. string)
                        BodyPart = self.handleString(Body[i], BodyType[i], BodyPart)
                    else:
                        #array of strings
                        BodyPart = self.handleArrayString(Body[i], BodyType[i], BodyPart)
                elif "-" in BodyType[i]:
                    for j in range(0, len(Body[i])):
                        instance[j] = self.correctType(type[2], instance[j])
                        Body[i] = instance
                    BodyPart = self.handleArray(Body[i], BodyType[i], BodyPart)
                elif "+" in BodyType[i]:
                    for j in range(0, len(Body[i])):
                        instance[j] = self.correctType(type[2], instance[j])
                        Body[i] = instance
                    BodyPart = self.handleArrayPrepend(Body[i], BodyType[i], BodyPart)
                else:
                    BodyPart = self.handleArray(Body[i], BodyType[i], BodyPart) 
            else:
                if "2" in BodyType[i]:
                    BodyPart = self.handle2DArray(Body[i], BodyType[i], BodyPart)
                else:
                    Body[i] = self.correctType(BodyType[i], Body[i])
                    BodyPart = BodyPart + struct.pack('>' + BodyType[i], Body[i])

        SendResponseBack = True

        BodySize = len(BodyPart)
        ZeroBuffer = bytearray(2)

        Message = bytearray(str(Command).ljust(32, '\0').encode()) + \
                  BodySize.to_bytes(4, byteorder='big') + \
                  SendResponseBack.to_bytes(2, byteorder='big') + \
                  ZeroBuffer + \
                  BodyPart
        if (self.displayInfo == 1):
            print('Send message: ')
            print(Message)

        self.connection.send(Message)

        Recv_Header = self.connection.recv(40)  # read header - always 40 bytes
        Recv_BodySize = struct.unpack('>I', Recv_Header[32:36])[0]  # get body size
        Recv_Body = b'\x3e\x35\x79\x8e\xe2\x30\x8c\x3a\xbe\x35\x79\x8e\xe2\x30\x8c\x3a\x00\x00\x00\x00\x00\x00\x00\x00'
        Recv_Body = self.connection.recv(Recv_BodySize)  # read whole body
        Recv_Command = Recv_Header[0:32].decode().strip('0').replace('\x00', '')
        if (self.displayInfo == 1):
            print("BodySize:", Recv_BodySize)
            print("Received Body:", len(Recv_Body))
        counter = 0
        while (Recv_BodySize != len(Recv_Body) or counter < 1000):  # Making sure all the data is received
            Recv_Body = Recv_Body + self.connection.recv(Recv_BodySize - len(Recv_Body))
            counter += 1
        if (self.displayInfo == 1):
            print("BodySize2:", Recv_BodySize)
            print("Received Body2:", len(Recv_Body))
        (self.connection.settimeout(1000))

        if (self.displayInfo == 1):
            print('Received data:')
            print(Recv_Header)
            print(Recv_Body)
        if Recv_Command == Command:
            print('Correct Command.')
            return Recv_Body
        else:
            print('Wrong Command')
            return []

    # Parses Array coming back from Server
    def decodeArray(self, response, index, numOfElements, responseType):
        decoded_nums = []
        decoded_num = 0
        if isinstance(numOfElements, list):
            return []
        for i in range(0, numOfElements):
            decoded_num = response[index:(index + 4)]
            decoded_num = struct.unpack('>' + responseType, decoded_num)
            decoded_nums.append(decoded_num)
            index += 4
        return decoded_nums

    # Parses String Array coming back from Server (with length prepended)
    def decodeStringPrepended(self, response, index, numOfStrings):
        decoded_strings = []
        decoded_string = ""
        for j in range(0, numOfStrings):
            decoded_num = ""
            for i in range(0, 4):
                decoded_num = decoded_num + str(response[index + i])
            decoded_num = int(decoded_num)
            for i in range(index + 4, (index + 4) + decoded_num):
                decoded_string = decoded_string + chr(response[i])
            decoded_strings.append(decoded_string)
            index = index + decoded_num + 4

            decoded_string = ""

        return decoded_strings

    # Parses singular String coming back from Server
    def decodeSingularString(self, response, index, stringLength):
        decoded_string = ""
        for i in range(0, stringLength):
            decoded_string = decoded_string + chr(response[index + i])
        return decoded_string

    # Parses Array coming back form Server (with length of each element prepended)
    def decodeArrayPrepended(self, response, index, numOfElements, responseType):
        decoded_nums = []
        if(responseType == 'd'):
            increment = 8
        else:
            increment = 4
        if isinstance(numOfElements, list):
            return []
        for i in range(0, numOfElements):
            decoded_num = response[index:(index + increment)]
            decoded_num = struct.unpack('>' + responseType, decoded_num)
            decoded_nums.append(decoded_num)
            index = index + increment
        return decoded_nums

    def parseError(self, response, index):
        if(index == 8):
            margin = 4
        else:
            margin = 8
        errorIndex = index + margin
        jumpDistance = len(response) - errorIndex
        errorString = response[errorIndex:(errorIndex + jumpDistance)].decode()
        return errorString

    def parseGeneralResponse(self, Response, ResponseTypes):
        counter = 0
        Variables = []
        universalLength = 0
        for ResponseType in ResponseTypes:
            if ResponseType[0] != '*':
                if ResponseType[0] == '2':
                    NoOfRows = Variables[-2]  # no of rows must be directly before cols
                    NoOfCols = Variables[-1]  # no of cols must be directly before array
                    SentArray = []
                    Datasize = struct.calcsize('>' + ResponseType[1])
                    for i in range(NoOfRows * NoOfCols):
                        Value = struct.unpack('>' + ResponseType[1], Response[counter:(counter + Datasize)])
                        counter = counter + Datasize
                        SentArray.append(Value)
                    Variables.append(np.reshape(SentArray, (NoOfRows, NoOfCols)))  # !!!!!
                    if (self.displayInfo == 1):
                        print(ResponseType, '  : ', np.reshape(SentArray, (NoOfRows, NoOfCols)))

                else:
                    Datasize = struct.calcsize('>' + ResponseType)
                    Value = struct.unpack('>' + ResponseType, Response[counter:(counter + Datasize)])
                    # print(ResponseType, '   : ', Value[0])
                    Variables.append(Value[0])
                    counter = counter + Datasize
            else:
                if ResponseType[1] == '+':
                    NoOfChars = Variables[-1]
                    String = self.decodeStringPrepended(Response, counter, NoOfChars)  # Nano
                    # print(ResponseType, '  : ', String)
                    counter = counter + Variables[-2]
                    Variables.append(String)
                elif ResponseType[1] == '-':
                    NoOfChars = Variables[-1]
                    String = self.decodeSingularString(Response, counter, NoOfChars)  # Nano
                    # print(ResponseType, " : ", String)
                    counter = counter + NoOfChars
                    Variables.append(String)
                elif ResponseType[1] == '*':
                    #if universalLength == 0:
                    #    universalLength = Variables[-1]
                    universalLength = Variables[0]
                    if ResponseType[2] == 'c':
                        Result = self.decodeStringPrepended(Response, counter, universalLength)
                        counter = counter + universalLength
                    else:
                        Result = self.decodeArray(Response, counter, universalLength, ResponseType[2])  # Nano
                        # print(ResponseType, ' : ', Result)
                        counter = counter + (universalLength * 4)
                    Variables.append(Result)
                else:  # ResponseType[1] == 'w':
                    Result = self.decodeArrayPrepended(Response, counter, Variables[-1], ResponseType[1])# Nano
                    if (ResponseType[1]=='d'):
                        increment = 8
                    else:
                        increment = 4
                    if (Variables[-1] != 0): #here lies the problem
                        counter = counter + (Variables[-1] * increment)
                    else:
                        counter = counter + increment
                    Variables.append(Result)
                    # print(ResponseType, '  : ', Result)
        ErrorString = self.parseError(Response, counter)#Response[12:(12 + ErrorLength)].decode()
        if(ErrorString != ''):
            print('The following error appeared:', "\n", ErrorString)
            return [ErrorString, Response, Variables]
        else:
            print('No error messages. Error status was: 0')
            return [ErrorString, Response, Variables]

    def quickSend(self, Command, Body, BodyType, ResponseTypes):

        '''

        quickSend(self, Command, Body, BodyType,ResponseTypes)
        
        Parameters for quicksend:
            Command : as written in documentation
            Body: Body to send as array [] - use [] when no argument should be sent!
            BodyType: Array of [Type of data] - see also ResponseTypes
            ResponseTypes: Array of Types to decode response

            IDENTIFIERS:

            --> "+" --> Array with length of array prepended
            --> "-" --> Array without length of array prepended

            H  : unsigned int16
            h  : int16
            I  : unsigned int32
            i  : int32
            f  : float32
            d  : float64 (double)

            Arrays (1D):
            Start with *
            length taken from directly before the array

            (+  or -) *I : array of unsigned int32
            (+ or -) *i : array of int32
            (+ or -) *f : array of float32
            (+ or -) *d : array of float64
            (+ or -) *c : String! (Array of chars - interpreted as string!)
            NEED TO UPDATE WITHOUT "*"!!!!

            Arrays (2D):
            start with 2
            width and height taken from the two variables before the array

            (+ or -) 2f : 2d array of float32

            UNIQUE FOR RETURN TYPES:

            "**" Identifier for arrays whose size is defined by the first returned argument

        '''

        response = self.send(Command, Body, BodyType)
        if response != []:
            ResponseData = self.parseGeneralResponse(response, ResponseTypes)
            if self.displayInfo == 1:
                self.printDebugInfo(ResponseTypes, ResponseData[2])
            return tuple(ResponseData)
        else:
            print('No data returned.')
            return tuple([])

    def Bias_Set(self, Bias_value_V: np.float32):
        """
        Bias.Set
        Sets the Bias voltage to the specified value.
        Arguments: 
        -- Bias value (V) (float32)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Bias.Set", [Bias_value_V], ["f"], [])

    def Bias_Get(self):
        """
        Bias.Get
        Returns the Bias voltage value.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Bias value (V) (float32)
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Bias.Get", [], [], ["f"])

    def Bias_RangeSet(self, Bias_range_index: np.uint16):
        """
        Bias.RangeSet
        Sets the range of the Bias voltage, if different ranges are available.
        Arguments: 
        -- Bias range index (unsigned int16) is the index out of the list of ranges which can be retrieved by the function <i>Bias.RangeGet</i>. 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Bias.RangeSet", [Bias_range_index], ["H"], [])

    def Bias_RangeGet(self):
        """
        Bias.RangeGet
        Returns the selectable ranges of bias voltage and the index of the selected one.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Bias ranges size (int) is the size in bytes of the bias ranges array
        -- Number of ranges (int) is the number of elements of the bias ranges array
        -- Bias ranges (1D array string) returns an array of selectable bias ranges. Each element of the array is preceded by its size in bytes
        -- Bias range index (unsigned int16) is the index out of the list of bias ranges. 
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Bias.RangeGet", [], [], ["i", "i", "*+c", "H"])

    def Bias_CalibrSet(self, Calibration: np.float32, Offset: np.float32):
        """
        Bias.CalibrSet
        Sets the calibration and offset of bias voltage.
        If several ranges are available, this function sets the values for the selected one.
        Arguments: 
        -- Calibration (float32)
        -- Offset (float32)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Bias.CalibrSet", [Calibration, Offset], ["f", "f"], [])

    def Bias_CalibrGet(self):
        """
        Bias.CalibrGet
        Gets the calibration and offset of bias voltage.
        If several ranges are available, this function returns the values of the selected one.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Calibration (float32)
        -- Offset (float32)
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("Bias.CalibrGet", [], [], ["f", "f"])

    def Bias_Pulse(self, Wait_until_done: np.uint32, Bias_pulse_width_s: np.float32, Bias_value_V: np.float32,
                   Z_Controller_on_hold: np.uint32,
                   Pulse_absolute_relative: np.uint16):
        """
        Bias.Pulse
        Generates one bias pulse.
        Arguments: 
        -- Wait until done (unsigned int32), if True, this function will wait until the pulse has finished. 1_True and 0_False
        -- Bias pulse width (s) (float32) is the pulse duration in seconds
        -- Bias value (V) (float32) is the bias value applied during the pulse
        -- Z-Controller on hold (unsigned int16) sets whether the controller is set to hold (deactivated) during the pulse. Possible values are: 0_no change, 1_hold, 2_don’t hold
        -- Pulse absolute/relative (unsigned int16) sets whether the bias value argument is an absolute value or relative to the current bias voltage. Possible values are: 0_no change, 1_relative, 2_absolute
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        Bias Sweep
        """

        return self.quickSend("Bias.Pulse", [Wait_until_done, Bias_pulse_width_s, Bias_value_V, Z_Controller_on_hold,
                                             Pulse_absolute_relative], ["I", "f", "f", "H", "H"], [])

    def BiasSwp_Open(self):
        """
        BiasSwp.Open
        Opens the Bias Sweep module.
        Arguments: 
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("BiasSwp.Open", [], [], [])

    def BiasSwp_Start(self, Get_data: np.uint32, Sweep_direction: np.uint32, Z_Controller_status: np.uint32,
                      Save_base_name: str,
                      Reset_bias: np.uint32):
        """
        BiasSwp.Start
        Starts a bias sweep in the Bias Sweep module.
        Before using this function, select the channels to record in the Bias Sweep module.
        Arguments: 
        -- Get data (unsigned int32) defines if the function returns the sweep data (1_True) or not (0_False) 
        -- Sweep direction (unsigned int32) defines if the sweep starts from the lower limit (_1) or from the upper limit (_0)
        -- Z-Controller status (unsigned int32) where 0_no change, 1_turn off, 2_don’t turn off
        -- Save base name string size (int) defines the number of characters of the Save base name string
        -- Save base name (string) is the basename used by the saved files. If empty string, there is no change
        -- Reset bias (unsigned int32) where 0_Off, 1_On
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Channels names size (int) is the size in bytes of the Channels names string array
        -- Number of channels (int) is the number of elements of the Channels names string array
        -- Channels names (1D array string) returns the list of channels names. The size of each string item comes right before it as integer 32
        -- Data rows (int) defines the numer of rows of the Data array
        -- Data columns (int) defines the numer of columns of the Data array
        -- Data (2D array float32) returns the sweep data
        -- Error described in the Response message&gt;Body section
        
        """

        return self.quickSend("BiasSwp.Start",
                              [Get_data, Sweep_direction, Z_Controller_status,
                               Save_base_name, Reset_bias], ["I", "I", "I", "+*c", "I"],
                              ["i", "i", "*+c", "i", "i", "2f"])

    def BiasSwp_PropsSet(self, Number_of_steps: np.uint16, Period_ms: np.uint16, Autosave: np.uint16,
                         Save_dialog_box: np.uint16):
        """
        BiasSwp.PropsSet
        Sets the configuration of the parameters in the Bias Sweep module.
        Arguments: 
        -- Number of steps (unsigned int16) defines the number of steps of the sweep. 0 points means no change
        -- Period (ms) (unsigned int16) where 0 means no change
        -- Autosave (unsigned int16) defines if the sweep is automatically saved, where 0_no change, 1_On, 2_Off
        -- Save dialog box (unsigned int16) defines if the save dialog box shows up or not, where 0_no change, 1_On, 2_Off
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("BiasSwp.PropsSet", [Number_of_steps, Period_ms, Autosave, Save_dialog_box],
                              ["H", "H", "H", "H"], [])

    def BiasSwp_LimitsSet(self, Lower_limit: np.float32, Upper_limit: np.float32):
        """
        BiasSwp.LimitsSet
        Sets the limits of Bias in the Bias Sweep module.
        Arguments: 
        -- Lower limit (float32) defines the lower limit of the sweep range
        -- Upper limit (float32) defines the upper limit of the sweep range
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        
        Bias Spectroscopy
        """
        return self.quickSend("BiasSwp.LimitsSet", [Lower_limit, Upper_limit], ["f", "f"], [])

    def BiasSpectr_Open(self):
        """
        BiasSpectr.Open
        Opens the Bias Spectroscopy module.
        Arguments: 
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("BiasSpectr.Open", [], [], [])

    def BiasSpectr_Start(self, Get_data: np.uint32, Save_base_name: str):
        """
        BiasSpectr.Start
        Starts a bias spectroscopy in the Bias Spectroscopy module.
        Before using this function, select the channels to record in the Bias Spectroscopy module.
        Arguments: 
        -- Get data (unsigned int32) defines if the function returns the spectroscopy data (1_True) or not (0_False) 
        -- Save base name string size (int) defines the number of characters of the Save base name string
        -- Save base name (string) is the basename used by the saved files. If empty string, there is no change
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Channels names size (int) is the size in bytes of the Channels names string array
        -- Number of channels (int) is the number of elements of the Channels names string array
        -- Channels names (1D array string) returns the list of channels names. The size of each string item comes right before it as integer 32
        -- Data rows (int) defines the number of rows of the Data array
        -- Data columns (int) defines the number of columns of the Data array
        -- Data (2D array float32) returns the spectroscopy data
        -- Number of parameters (int) is the number of elements of the Parameters array
        -- Parameters (1D array float32) returns the list of fixed parameters and parameters (in that order). To see the names of the returned parameters, use the <i>BiasSpectr.PropsGet</i> function.
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("BiasSpectr.Start", [Get_data, Save_base_name],
                              ["I", "+*c"], ["i", "i", "*+c", "i", "i", "2f", "i", "*f"])

    def BiasSpectr_Stop(self):
        """
        BiasSpectr.Stop
        Stops the current Bias Spectroscopy measurement.
        Arguments: 
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("BiasSpectr.Stop", [], [], [])

    def BiasSpectr_StatusGet(self):
        """
        BiasSpectr.StatusGet
        Returns the status of the Bias Spectroscopy measurement.
        Arguments: 
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Status (unsigned int32) where 0_not running and 1_running
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("BiasSpectr.StatusGet", [], [], [])

    def BiasSpectr_ChsSet(self, Channel_indexes: list):
        """
        BiasSpectr.ChsSet
        Sets the list of recorded channels in Bias Spectroscopy.
        Arguments: 
        -- Number of channels (int) is the number of recorded channels. It defines the size of the Channel indexes array
        -- Channel indexes (1D array int) are the indexes of recorded channels. The indexes are comprised between 0 and 23 for the 24 signals assigned in the Signals Manager.
        To get the signal name and its corresponding index in the list of the 128 available signals in the Nanonis Controller, use the <i>Signals.InSlotsGet</i> function
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("BiasSpectr.ChsSet", [Channel_indexes], ["+*i"], [])

    def BiasSpectr_ChsGet(self):
        """
        BiasSpectr.ChsGet
        Returns the list of recorded channels in Bias Spectroscopy.
        Arguments: 
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Number of channels (int) is the number of recorded channels. It defines the size of the Channel indexes array
        -- Channel indexes (1D array int) are the indexes of recorded channels. The indexes are comprised between 0 and 23 for the 24 signals assigned in the Signals Manager.
        To get the signal name and its corresponding index in the list of the 128 available signals in the Nanonis Controller, use the <i>Signals.InSlotsGet</i> function
        - Channels size (int) is the size in bytes of the Channels string array
        - Channels (1D array string) returns the names of the acquired channels in the sweep. The size of each string item comes right before it as integer 32
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("BiasSpectr.ChsGet", [], [], ["i", "*i", "i", "**c"])

    def BiasSpectr_PropsSet(self, Save_all: np.uint16, Number_of_sweeps: int, Backward_sweep: np.uint16,
                            Number_of_points: int, Z_offset_m: np.float32, Autosave: np.uint16,
                            Show_save_dialog: np.uint16):
        """
        BiasSpectr.PropsSet
        Configures the Bias Spectroscopy parameters.
        Arguments: 
        -- Save all (unsigned int16) where 0 means no change, 1 means that the data from the individual sweeps is saved along with the average data of all of them, and 2 means that the individual sweeps are not saved in the file. This parameter only makes sense when multiple sweeps are configured
        -- Number of sweeps (int) is the number of sweeps to measure and average. 0 means no change with respect to the current selection
        -- Backward sweep (unsigned int16) selects whether to also acquire a backward sweep (forward is always measured) when it is 1. When it is 2 means that no backward sweep is performed, and 0 means no change.
        -- Number of points (int) defines the number of points to acquire over the sweep range, where 0 means no change
        -- Z offset (m) (float32) defines which distance to move the tip before starting the spectroscopy measurement. Positive value means retracting, negative value approaching
        -- Autosave (unsigned int16) selects whether to automatically save the data to ASCII file once the sweep is done (_1). This flag is off when _2, and 0 means no change
        -- Show save dialog (unsigned int16) selects whether to show the save dialog box once the sweep is done (_1). This flag is off when _2, and 0 means no change
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("BiasSpectr.PropsSet",
                              [Save_all, Number_of_sweeps, Backward_sweep, Number_of_points, Z_offset_m, Autosave,
                               Show_save_dialog], ["H", "i", "H", "i", "f", "H", "H"], [])

    def BiasSpectr_PropsGet(self):
        """
        BiasSpectr.PropsGet
        Returns the Bias Spectroscopy parameters.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Save all (unsigned int16) where 1 means that the data from the individual sweeps is saved along with the average data of all of them, and 0 means that the individual sweeps are not saved in the file. This parameter only makes sense when multiple sweeps are configured
        -- Number of sweeps (int) is the number of sweeps to measure and average
        -- Backward sweep (unsigned int16), where 1 means that the backward sweep is performed (forward is always measured) and 0 means that there is no backward sweep
        -- Number of points (int) is the number of points to acquire over the sweep range
        -- Channels size (int) is the size in bytes of the Channels string array
        -- Number of channels (int) is the number of elements of the Channels string array
        -- Channels (1D array string) returns the names of the acquired channels in the sweep. The size of each string item comes right before it as integer 32
        -- Parameters size (int) is the size in bytes of the Parameters string array
        -- Number of parameters (int) is the number of elements of the Parameters string array
        -- Parameters (1D array string) returns the parameters of the sweep. The size of each string item comes right before it as integer 32
        -- Fixed parameters size (int) is the size in bytes of the Fixed parameters string array
        -- Number of fixed parameters (int) is the number of elements of the Fixed parameters string array
        -- Fixed parameters (1D array string) returns the fixed parameters of the sweep. The size of each string item comes right before it as integer 32
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("BiasSpectr.PropsGet", [], [],
                              ["H", "i", "H", "i", "i", "i", "*+c", "i", "i", "*+c", "i", "i", "*+c"])

    def BiasSpectr_AdvPropsSet(self, Reset_Bias: np.uint16, Z_Controller_Hold: np.uint16,
                               Record_final_Z: np.uint16, Lockin_Run: np.uint16):
        """
        BiasSpectr.AdvPropsSet
        Sets parameters from the Advanced configuration section of the bias spectroscopy module.
        Arguments: 
        -- Reset Bias (unsigned int16) sets whether Bias voltage returns to the initial value at the end of the spectroscopy measurement. 0 means no change, 1 means On, and 2 means Off
        -- Z-Controller Hold (unsigned int16) sets the Z-Controller on hold during the sweep. 0 means no change, 1 means On, and 2 means Off
        -- Record final Z (unsigned int16) records the Z position during Z averaging time at the end of the sweep and stores the average value in the header of the file when saving. 0 means no change, 1 means On, and 2 means Off
        -- Lockin Run (unsigned int16) sets the Lock-In to run during the measurement. 
        When using this feature, make sure the Lock-In is configured correctly and settling times are set to twice the Lock-In period at least. This option is ignored when Lock-In is already running.
        This option is disabled if the Sweep Mode is MLS and the flag to configure the Lock-In per segment in the Multiline segment editor is set. 0 means no change, 1 means On, and 2 means Off
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        """
        return self.quickSend("BiasSpectr.AdvPropsSet", [Reset_Bias, Z_Controller_Hold, Record_final_Z, Lockin_Run],
                              ["H", "H", "H", "H"], [])

    def BiasSpectr_AdvPropsGet(self):
        """
        BiasSpectr.AdvPropsGet
        Returns the parameters from the Advanced configuration section of the bias spectroscopy module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Reset Bias (unsigned int16) indicates whether Bias voltage returns to the initial value at the end of the spectroscopy measurement. 0 means Off, 1 means On
        -- Z-Controller Hold (unsigned int16) indicates if the Z-Controller is on hold during the sweep. 0 means Off, 1 means On
        -- Record final Z (unsigned int16) indicates whether to record the Z position during Z averaging time at the end of the sweep and store the average value in the header of the file when saving. 0 means Off, 1 means On
        -- Lockin Run (unsigned int16) indicates if the Lock-In to runs during the measurement. 
        This option is ignored when Lock-In is already running.
        This option is disabled if the Sweep Mode is MLS and the flag to configure the Lock-In per segment in the Multiline segment editor is set. 0 means Off, 1 means On
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("BiasSpectr.AdvPropsGet", [], [], ["H", "H", "H", "H"])

    def BiasSpectr_LimitsSet(self, Start_value_V: np.float32, End_value_V: np.float32):
        """
        BiasSpectr.LimitsSet
        Sets the Bias spectroscopy limits.
        Arguments: 
        -- Start value (V) (float32) is the starting value of the sweep
        -- End value (V) (float32) is the ending value of the sweep
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("BiasSpectr.LimitsSet", [Start_value_V, End_value_V], ["f", "f"], [])

    def BiasSpectr_LimitsGet(self):
        """
        BiasSpectr.LimitsGet
        Returns the Bias spectroscopy limits.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Start value (V) (float32) is the starting value of the sweep
        -- End value (V) (float32) is the ending value of the sweep
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("BiasSpectr.LimitsGet", [], [], ["f", "f"])

    def BiasSpectr_TimingSet(self, Z_averaging_time_s: np.float32, Z_offset_m: np.float32,
                             Initial_settling_time_s: np.float32, Maximum_slew_rate_Vdivs: np.float32,
                             Settling_time_s: np.float32, Integration_time_s: np.float32,
                             End_settling_time_s: np.float32, Z_control_time_s: np.float32):
        """
        BiasSpectr.TimingSet
        Configures the Bias spectroscopy timing parameters.
        Arguments: 
        -- Z averaging time (s) (float32) 
        -- Z offset (m) (float32) 
        -- Initial settling time (s) (float32) 
        -- Maximum slew rate (V/s) (float32) 
        -- Settling time (s) (float32) 
        -- Integration time (s) (float32) 
        -- End settling time (s) (float32) 
        -- Z control time (s) (float32) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("BiasSpectr.TimingSet",
                              [Z_averaging_time_s, Z_offset_m, Initial_settling_time_s, Maximum_slew_rate_Vdivs,
                               Settling_time_s, Integration_time_s, End_settling_time_s, Z_control_time_s],
                              ["f", "f", "f", "f", "f", "f", "f", "f"], [])

    def BiasSpectr_TimingGet(self):
        """
        BiasSpectr.TimingGet
        Returns the Bias spectroscopy timing parameters.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Z averaging time (s) (float32) 
        -- Z offset (m) (float32) 
        -- Initial settling time (s) (float32) 
        -- Maximum slew rate (V/s) (float32) 
        -- Settling time (s) (float32) 
        -- Integration time (s) (float32) 
        -- End settling time (s) (float32) 
        -- Z control time (s) (float32) 
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("BiasSpectr.TimingGet", [], [], ["f", "f", "f", "f", "f", "f", "f", "f"])

    def BiasSpectr_DigSyncSet(self, Digital_Sync: np.uint16):
        """
        BiasSpectr.DigSyncSet
        Returns the configured TTL/pulse sequence synchronization option in the Advanced section of the Bias Spectroscopy module.
        TTL synchronization allows for controlling one high-speed digital output according to the individual stages of the bias spectroscopy measurement.
        Pulse sequence allows running a high speed digital pulse sequence (if the Pulse Generation module is licensed)synchronized with the individual stages of the bias spectroscopy measurement.
        Arguments: 
        - Digital Sync. (unsigned int16) where 0 means no change, 1 is Off, 2 is TTL Sync, and 3 is Pulse Sequence
        Return arguments (if Send response back flag is set to True when sending request message):
        - Error described in the Response message>Body section
        """
        return self.quickSend("BiasSpectr.DigSyncSet", [Digital_Sync],
                              ["H"], [])

    def BiasSpectr_DigSyncGet(self):
        """
        BiasSpectr.DigSyncGet
        Returns the configured TTL/pulse sequence synchronization option in the Advanced section of the Bias Spectroscopy module.
        TTL synchronization allows for controlling one high-speed digital output according to the individual stages of the bias spectroscopy measurement.
        Pulse sequence allows running a high speed digital pulse sequence (if the Pulse Generation module is licensed)synchronized with the individual stages of the bias spectroscopy measurement.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Digital Sync. (unsigned int16) where 0 is Off, 1 is TTL Sync, and 2 is Pulse Sequence
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("BiasSpectr.DigSyncGet", [], [], ["H"])

    def BiasSpectr_TTLSyncSet(self, TTL_line: np.uint16, TTL_polarity: np.uint16,
                              Time_to_on_s: np.float32, On_duration_s: np.float32):
        """
        BiasSpectr.TTLSyncSet
        Sets the configuration of the TTL Synchronization feature in the Advanced section of the Bias Spectroscopy module.
        TTL synchronization allows for controlling one high-speed digital output according to the individual stages of the bias spectroscopy measurement.
        Arguments: 
        -- TTL line (unsigned int16) sets which digital line should be controlled. 0 means no change, 1 means HS Line 1, 2 means HS Line 2, 3 means HS Line 3, 4 means HS Line 4
        -- TTL polarity (unsigned int16) sets the polarity of the switching action. 0 means no change, 1 means Low Active, and 2 means High Active
        -- Time to on (s) (float32) defines the time to wait before activating the TTL line
        -- On duration (s) (float32) defines how long the TTL line should be activated before resetting
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("BiasSpectr.TTLSyncSet", [TTL_line, TTL_polarity, Time_to_on_s, On_duration_s],
                              ["H", "H", "f", "f"], [])

    def BiasSpectr_TTLSyncGet(self):
        """
        BiasSpectr.TTLSyncGet
        Returns the configuration of the TTL Synchronization feature in the Advanced section of the Bias Spectroscopy module.
        TTL synchronization allows for controlling  one high-speed digital output according to the individual stages of the bias spectroscopy measurement.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- TTL line (unsigned int16) indicates which digital line should be controlled. 0 means HS Line 1, 1 means HS Line 2, 2 means HS Line 3, 3 means HS Line 4
        -- TTL polarity (unsigned int16) indicates the polarity of the switching action. 0 means Low Active, 1 means High Active
        -- Time to on (s) (float32) indicates the time to wait before activating the TTL line
        -- On duration (s) (float32) indicates how long the TTL line should be activated before resetting
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("BiasSpectr.TTLSyncGet", [], [], ["H", "H", "f", "f"])

    def BiasSpectr_PulseSeqSyncSet(self, Pulse_Sequence_Nr: np.uint16, Nr_Periods: np.uint32):
        """
        BiasSpectr.PulseSeqSyncSet
        Sets the configuration of the pulse sequence synchronization feature in the Advanced section of the Bias Spectroscopy module.
        Pulse sequence allows running a high speed digital pulse sequence (if the Pulse Generation module is licensed) synchronized with the individual stages of the bias spectroscopy measurement.
        Arguments: 
        - Pulse Sequence Nr. (unsigned int16) is the pulse sequence number as configured in the Pulse Generation module. 0 means no change
        - Nr. Periods (unsigned int32) is the number of times the same pulse sequence is executed
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("BiasSpectr.PulseSeqSyncSet", [Pulse_Sequence_Nr, Nr_Periods],
                              ["H", "I"], [])

    def BiasSpectr_PulseSeqSyncGet(self):
        """
        BiasSpectr.PulseSeqSyncGet
        Returns the configuration of the pulse sequence synchronization feature in the Advanced section of the Bias Spectroscopy module.
        Pulse sequence allows running a high speed digital pulse sequence (if the Pulse Generation module is licensed) synchronized with the individual stages of the bias spectroscopy measurement.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        - Pulse Sequence Nr. (unsigned int16) is the pulse sequence number as configured in the Pulse Generation module. 0 means no change
        - Nr. Periods (unsigned int32) is the number of times the same pulse sequence is executed
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("BiasSpectr.PulseSeqSyncGet", [], [], ["H", "I"])

    def BiasSpectr_AltZCtrlSet(self, Alternate_Z_controller_setpoint: np.uint16, Setpoint: np.float32,
                               Settling_time_s: np.float32):
        """
        BiasSpectr.AltZCtrlSet
        Sets the configuration of the alternate Z-controller setpoint in the Advanced section of the Bias Spectroscopy module.
        When switched on, the Z-controller setpoint is set to the setpoint right after starting the measurement. After changing the setpoint the settling time (s) will be waited for the Z-controller to adjust to the modified setpoint. 
        Then the Z averaging will start. The original Z-controller setpoint is restored at the end of the measurement, before restoring the Z-controller state.
        Arguments: 
        -- Alternate Z-controller setpoint (unsigned int16) where 0 means no change, 1 means On, and 2 means Off
        -- Setpoint (float32) 
        -- Settling time (s) (float32) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("BiasSpectr.AltZCtrlSet", [Alternate_Z_controller_setpoint, Setpoint, Settling_time_s],
                              ["H", "f", "f"], [])

    def BiasSpectr_AltZCtrlGet(self):
        """
        BiasSpectr.AltZCtrlGet
        Returns the configuration of the alternate Z-controller setpoint in the Advanced section of the Bias Spectroscopy module.
        When switched on, the Z-controller setpoint is set to the setpoint right after starting the measurement. After changing the setpoint the settling time (s) will be waited for the Z-controller to adjust to the modified setpoint. 
        Then the Z averaging will start. The original Z-controller setpoint is restored at the end of the measurement, before restoring the Z-controller state.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Alternate Z-controller setpoint (unsigned int16) where 0 means Off, 1 means On
        -- Setpoint (float32) 
        -- Settling time (s) (float32) 
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("BiasSpectr.AltZCtrlGet", [], [], ["H", "f", "f"])

    def BiasSpectr_ZOffRevertSet(self, Z_Offset_Revert: np.uint16):
        """
        BiasSpectr.ZOffRevertSet
        Sets the “Z Offset Revert” flag in the Advanced section of the Bias Spectroscopy module.
        When switched on, the Z Offset (which is applied at the beginning) is reverted (i.e. the position jumps back).
        When switched off, the Z-controller is enabled (if it was enabled before) and will take care of bringing the tip back.
        Arguments:
        - Z Offset Revert (unsigned int16) where 0 means no change, 1 means On, and 2 means Off
        Return arguments (if Send response back flag is set to True when sending request message): 
        - Error described in the Response message>Body section
        """

        return self.quickSend("BiasSpectr.ZOffRevertSet", [Z_Offset_Revert], ["h"], [])

    def BiasSpectr_ZOffRevertGet(self):
        """
        BiasSpectr.ZOffRevertGet
        Returns the “Z Offset Revert” flag in the Advanced section of the Bias Spectroscopy module.
        When switched on, the Z Offset (which is applied at the beginning) is reverted (i.e. the position jumps back).
        When switched off, the Z-controller is enabled (if it was enabled before) and will take care of bringing the tip back.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        -  Z Offset Revert (unsigned int16) where 0 means Off, 1 means On
        -- Error described in the Response message>Body section
        """
        return self.quickSend("BiasSpectr.ZOffRevertGet", [], [], ["H"])

    def BiasSpectr_MLSLockinPerSegSet(self, Lock_In_per_segment: np.uint32):
        """
        BiasSpectr.MLSLockinPerSegSet
        Sets the Lock-In per Segment flag in the Multi line segment editor.
        When selected, the Lock-In can be defined per segment in the Multi line segment editor. Otherwise, the Lock-In is set globally according to the flag in the Advanced section of Bias spectroscopy.
        Arguments: 
        -- Lock-In per segment (unsigned int32) where 0 means Off, 1 means On
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("BiasSpectr.MLSLockinPerSegSet", [Lock_In_per_segment], ["I"], [])

    def BiasSpectr_MLSLockinPerSegGet(self):
        """
        BiasSpectr.MLSLockinPerSegGet
        Returns the Lock-In per Segment flag in the Multi line segment editor.
        When selected, the Lock-In can be defined per segment in the Multi line segment editor. Otherwise, the Lock-In is set globally according to the flag in the Advanced section of Bias spectroscopy.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Lock-In per segment (unsigned int32) where 0 means Off, 1 means On
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("BiasSpectr.MLSLockinPerSegGet", [], [], ["I"])

    def BiasSpectr_MLSModeSet(self, Sweep_mode: str):
        """
        BiasSpectr.MLSModeSet
        Sets the Bias Spectroscopy sweep mode.
        Arguments: 
        -- Sweep mode (int) is the number of characters of the sweep mode string. 
        If the sweep mode is <i>Linear</i>, this value is 6. If the sweep mode is <i>MLS</i>, this value is 3
        -- Sweep mode (string) is <i>Linear</i>  in Linear mode or <i>MLS</i> in MultiSegment mode
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("BiasSpectr.MLSModeSet", [Sweep_mode], ["+*c"], [])

    def BiasSpectr_MLSModeGet(self):
        """
        BiasSpectr.MLSModeGet
        Returns the Bias Spectroscopy sweep mode.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Sweep mode (int) is the number of characters of the sweep mode string. 
        If the sweep mode is <i>Linear</i>, this value is 6. If the sweep mode is <i>MLS</i>, this value is 3
        -- Sweep mode (string) is <i>Linear</i>  in Linear mode or <i>MLS</i> in MultiSegment mode
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("BiasSpectr.MLSModeGet", [], [], ["i", "*-c"])

    def BiasSpectr_MLSValsSet(self, No_Of_Segments: int, Bias_start_V, Bias_end_V, Initial_settling_time_s,
                              Settling_time_s, Integration_time_s, Steps, Lock_In_run):
        """
        BiasSpectr.MLSValsSet
        Sets the bias spectroscopy multiple line segment configuration for Multi Line Segment mode.
        Up to 16 distinct line segments may be defined.  Any segments beyond the maximum allowed amount will be ignored.
        Arguments: 
        -- Number of segments (int) indicates the number of segments configured in MLS mode
        -- Bias start (V) (1D array float32) is the Start Bias value (V) for each line segment.
        -- Bias end (V) (1D array float32 is the End Bias value (V) for each line segment.
        -- Initial settling time (s) (1D array float32) indicates the number of seconds to wait at the beginning of each segment after the Lock-In setting is applied. 
        -- Settling time (s) (1D array float32) indicates the number of seconds to wait before measuring each data point each the line segment.
        -- Integration time (s) (1D array float32) indicates the time during which the data are acquired and averaged in each segment.
        -- Steps (1D array int) indicates the number of steps to measure in each segment.
        -- Lock-In run (1D array unsigned int32) indicates if the Lock-In will run during the segment. This is true only if the global Lock-In per Segment flag is enabled.
        Otherwise, the Lock-In is set globally according to the flag in the Advanced section of Bias spectroscopy
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("BiasSpectr.MLSValsSet",
                              [No_Of_Segments, Bias_start_V, Bias_end_V, Initial_settling_time_s, Settling_time_s,
                               Integration_time_s, Steps, Lock_In_run],
                              ["i", "*f", "*f", "*f", "*f", "*f", "*i", "*i"],
                              [])

    def BiasSpectr_MLSValsGet(self):
        """
        BiasSpectr.MLSValsGet
        Returns the bias spectroscopy multiple line segment configuration for Multi Line Segment mode.
        Up to 16 distinct line segments may be defined.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Number of segments (int) indicates the number of segments configured in MLS mode. This value is also the size of the 1D arrays set afterwards
        -- Bias start (V) (1D array float32) is the Start Bias value (V) for each line segment
        -- Bias end (V) (1D array float32 is the End Bias value (V) for each line segment
        -- Initial settling time (s) (1D array float32) indicates the number of seconds to wait at the beginning of each segment after the Lock-In setting is applied
        -- Settling time (s) (1D array float32) indicates the number of seconds to wait before measuring each data point each the line segment
        -- Integration time (s) (1D array float32) indicates the time during which the data are acquired and averaged in each segment
        -- Steps (1D array int) indicates the number of steps to measure in each segment
        -- Lock-In run (1D array unsigned int32) indicates if the Lock-In will run during the segment. This is true only if the global Lock-In per Segment flag is enabled. 
        Otherwise, the Lock-In is set globally according to the flag in the Advanced section of Bias spectroscopy
        -- Error described in the Response message&gt;Body section
        
        Kelvin Controller
        """
        return self.quickSend("BiasSpectr.MLSValsGet", [], [], ["i", "**f", "**f", "**f", "**f", "**f", "**i", "**I"])

    def KelvinCtrl_CtrlOnOffSet(self, Control_On_Off: np.uint32):
        """
        KelvinCtrl.CtrlOnOffSet
        Switches the KelvinCtrl. Controller on or off.
        Arguments: 
        -- Control On/Off  (unsigned int32) where 0_Off and 1_On
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("KelvinCtrl.CtrlOnOffSet", [Control_On_Off], ["I"], [])

    def KelvinCtrl_CtrlOnOffGet(self):
        """
        KelvinCtrl.CtrlOnOffGet
        Returns the status of the KelvinCtrl. Controller.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Status  (unsigned int32) where 0_Off and 1_On
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("KelvinCtrl.CtrlOnOffGet", [], [], ["I"])

    def KelvinCtrl_SetpntSet(self, Setpoint: np.float32):
        """
        KelvinCtrl.SetpntSet
        Sets the KelvinCtrl. Controller setpoint.
        Arguments: 
        -- Setpoint  (float32) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("KelvinCtrl.SetpntSet", [Setpoint], ["f"], [])

    def KelvinCtrl_SetpntGet(self):
        """
        KelvinCtrl.SetpntGet
        Returns the KelvinCtrl. Controller setpoint.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Setpoint  (float32) 
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("KelvinCtrl.SetpntGet", [], [], ["f"])

    def KelvinCtrl_GainSet(self, P_gain: np.float32, Time_constant_s: np.float32, Slope: np.uint16):
        """
        KelvinCtrl.GainSet
        Sets the regulation loop parameters of the KelvinCtrl. Controller.
        Arguments: 
        -- P-gain  (float32) 
        -- Time constant (s)  (float32) 
        -- Slope  (unsigned int16) where 0_no change, 1_Positive, 2_Negative
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("KelvinCtrl.GainSet", [P_gain, Time_constant_s, Slope], ["f", "f", "H"], [])

    def KelvinCtrl_GainGet(self):
        """
        KelvinCtrl.GainGet
        Returns the regulation loop parameters of the KelvinCtrl. Controller.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- P-gain  (float32) 
        -- Time constant (s)  (float32) 
        -- Slope  (unsigned int16) where 0_Negative and 1_Positive
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("KelvinCtrl.GainGet", [], [], ["f", "f", "H"])

    def KelvinCtrl_ModParamsSet(self, Frequency_Hz: np.float32, Amplitude: np.float32, Phase_deg: np.float32):
        """
        KelvinCtrl.ModParamsSet
        Returns the modulation parameters of the KelvinCtrl. Controller.
        Arguments: 
        -- Frequency (Hz)  (float32) 
        -- Amplitude  (float32) 
        -- Phase (deg)  (float32) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("KelvinCtrl.ModParamsSet", [Frequency_Hz, Amplitude, Phase_deg], ["f", "f", "f"], [])

    def KelvinCtrl_ModParamsGet(self):
        """
        KelvinCtrl.ModParamsGet
        Returns the modulation parameters of the KelvinCtrl. Controller.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Frequency (Hz)  (float32) 
        -- Amplitude  (float32) 
        -- Phase (deg)  (float32) 
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("KelvinCtrl.ModParamsGet", [], [], ["f", "f", "f"])

    def KelvinCtrl_ModOnOffSet(self, AC_mode_On_Off: np.uint16, Modulation_On_Off: np.uint16):
        """
        KelvinCtrl.ModOnOffSet
        Switches the KelvinCtrl. Controller AC mode and modulation.
        Arguments: 
        -- AC mode On/Off  (unsigned int16) where 0_no change, 1_On and 2_Off
        -- Modulation On/Off  (unsigned int16) where 0_Off and 1_On
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("KelvinCtrl.ModOnOffSet", [AC_mode_On_Off, Modulation_On_Off], ["H", "H"], [])

    def KelvinCtrl_ModOnOffGet(self):
        """
        KelvinCtrl.ModOnOffGet
        Returns the status of the KelvinCtrl. Controller AC mode and modulation.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- AC mode status  (unsigned int16) where 0_Off and 1_On
        -- Modulation status  (unsigned int16) where 0_Off and 1_On
        -- Error described in the Response message&gt;Body section
        
        
        
        
        """
        return self.quickSend("KelvinCtrl.ModOnOffGet", [], [], ["H", "H"])

    def KelvinCtrl_CtrlSignalSet(self, Demodulated_Control_signal_index: int):
        """
        KelvinCtrl.CtrlSignalSet
        Sets the demodulated/control signal index of the KelvinCtrl. Controller.
        Arguments: 
        -- Demodulated/Control signal index  (int) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("KelvinCtrl.CtrlSignalSet", [Demodulated_Control_signal_index], ["i"], [])

    def KelvinCtrl_CtrlSignalGet(self):
        """
        KelvinCtrl.CtrlSignalGet
        Returns the demodulated/control signal index of the KelvinCtrl. Controller.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Demodulated/Control signal index  (int) 
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("KelvinCtrl.CtrlSignalGet", [], [], ["i"])

    def KelvinCtrl_AmpGet(self):
        """
        KelvinCtrl.AmpGet
        Returns the amplitude of the demodulated/control signal of the KelvinCtrl. Controller.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Amplitude  (float32) 
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("KelvinCtrl.AmpGet", [], [], ["f"])

    def KelvinCtrl_BiasLimitsSet(self, Bias_high_limit_V: np.float32, Bias_low_limit_V: np.float32):
        """
        KelvinCtrl.BiasLimitsSet
        Sets the bias limits of the KelvinCtrl. Controller.
        The bias voltage will be limited to these values as long as the KelvinCtrl. controller is on.
        Arguments: 
        -- Bias high limit (V)  (float32) 
        -- Bias low limit (V)  (float32) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        """
        return self.quickSend("KelvinCtrl.BiasLimitsSet", [Bias_high_limit_V, Bias_low_limit_V], ["f", "f"], [])

    def KelvinCtrl_BiasLimitsGet(self):
        """
        KelvinCtrl.BiasLimitsGet
        Returns the bias limits of the KelvinCtrl. Controller.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Bias high limit (V)  (float32) 
        -- Bias low limit (V)  (float32) 
        -- Error described in the Response message&gt;Body section
        
        
        
        CPD Compensation
        """
        return self.quickSend("KelvinCtrl.BiasLimitsGet", [], [], ["f", "f"])

    def CPDComp_Open(self):
        """
        CPDComp.Open
        Opens the CPD compensation module.
        This module starts automatically bias wobbling and CPD estimating when it opens.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("CPDComp.Open", [], [], [])

    def CPDComp_Close(self):
        """
        CPDComp.Close
        Closes the CPD compensation module.
        This module stops automatically bias wobbling and CPD estimating when it closes.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("CPDComp.Close", [], [], [])

    def CPDComp_ParamsSet(self, Speed_Hz: np.float32, Range_V: np.float32, Averaging: int):
        """
        CPDComp.ParamsSet
        Sets the speed (Hz), the range (V), and the averaging from the CPD compensation module.
        Arguments:
        -- Speed (Hz)  (float32) sets the frequency of the sawtooth signal used to modulate bias
        -- Range (V)  (float32) sets the amplitude of the sawtooth signal used to modulate bias
        -- Averaging  (int) is used to average the last specified number of results to calculate the CPD. 0 means no change
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("CPDComp.ParamsSet", [Speed_Hz, Range_V, Averaging], ["f", "f", "i"], [])

    def CPDComp_ParamsGet(self):
        """
        CPDComp.ParamsGet
        Sets the speed (Hz), the range (V), and the averaging from the CPD compensation module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Speed (Hz)  (float32) indicates the frequency of the sawtooth signal used to modulate bias
        -- Range (V)  (float32) indicates the amplitude of the sawtooth signal used to modulate bias
        -- Averaging  (int) is used to average the last specified number of results to calculate the CPD. 0 means no change
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("CPDComp.ParamsGet", [], [], ["f", "f", "i"])

    def CPDComp_DataGet(self):
        """
        CPDComp.DataGet
        Returns the graph data, the CPD estimate (V), and the fit coefficients from the CPD compensation module.
        The fit coefficients correspond with the polynomial coefficients in the following fit model: 
        <i>df _ a(U-Uo)^2 + b(U-Uo) + c    </i>where Uo is bias voltage.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Size 1 (int) is the number of elements of Bias forward, Frequency shift forward and Frequency Shift fit 1D data arrays. They contain the same number of elements. Bias forward corresponds to the X axis in the graph of the CPD module
        -- Bias forward data (1D array float32) 
        -- Frequency Shift forward data (1D array float32) 
        -- Frequency Shift forward fit data (1D array float32) 
        -- Size 2 (int) is the number of elements of Bias backward, Frequency shift backward and Frequency Shift fit 1D data arrays. They contain the same number of elements. Bias backward corresponds to the X axis in the graph of the CPD module
        -- Bias backward data (1D array float32) 
        -- Frequency Shift backward data (1D array float32) 
        -- Frequency Shift backward fit data (1D array float32) 
        -- CPD estimate  (float32)
        -- a coefficient  (float64) 
        -- b coefficient  (float64) 
        -- Error described in the Response message&gt;Body section
        
        Current Module
        """
        return self.quickSend("CPDComp.DataGet", [], [],
                              ["i", "**f", "**f", "**f", "i", "**f", "**f", "**f", "f", "d", "d"])

    def Current_Get(self):
        """
        Current.Get
        Returns the tunneling current value.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Current value (A) (float32)
        -- Error described in the Response message&gt;Body section
        
        Current.100Get
        Returns the tunneling current value of the “Current 100” module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Current 100 value (A) (float32)
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Current.Get", [], [], ["f"])

    def Current_100Get(self):
        return self.quickSend("Current.100Get", [], [], ["f"])

    def Current_BEEMGet(self):
        """
        Current.BEEMGet
        Returns the BEEM current value of the corresponding module in a BEEM system.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Current BEEM value (A) (float32)
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Current.BEEMGet", [], [], ["f"])

    def Current_GainSet(self, Gain_index, Filter_Index):
        """
        Current.GainSet
        Sets the gain of the current amplifier.
        Arguments: 
        -- Gain index (unsigned int16) is the index out of the list of gains which can be retrieved by the function <i>Current.GainsGet</i>. 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        """
        return self.quickSend("Current.GainSet", [Gain_index, Filter_Index], ["i", "i"], [])

    def Current_GainsGet(self):
        """
        Current.GainsGet
        Returns the selectable gains of the current amplifier and the index of the selected one.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Gains size (int) is the size in bytes of the Gains array
        -- Number of gains (int) is the number of elements of the Gains array
        -- Gains (1D array string) returns an array of selectable gains. Each element of the array is preceded by its size in bytes
        -- Gain index (unsigned int16) is the index out of the list of gains. 
        -- Filters size (int) is the size in bytes of the Filters array
        -- Number of filters (int) is the number of elements of the Filters array
        -- Filters (1D array string) returns an array of selectable filters. Each element of the array is preceded by itssize in bytes
        -- Filter index (int) is the index out of the list of filters. 
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Current.GainsGet", [], [], ["i", "i", "*+c", "i", "i", "i", "*+c", "i"])

    def Current_CalibrSet(self, Gain_index:np.int32, Calibration: np.float64, Offset: np.float64):
        """
        Current.CalibrSet
        Sets the calibration and offset of the selected gain in the Current module.
        Arguments: 
        -- Gain index (int) is the gain whose calibration and offset are set by this function. If set to -1, the default gain is the currently selected one in the Current module
        -- Calibration (float64)
        -- Offset (float64)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Current.CalibrSet", [Gain_index, Calibration, Offset], ["i", "d", "d"], [])

    def Current_CalibrGet(self, Gain_index:np.int32):
        """
        Current.CalibrGet
        Gets the calibration and offset of the selected gain in the Current module.
        Arguments:
        -- Gain index (int) is the gain whose calibration and offset are set by this function. If set to -1, the default gain is the currently selected one in the Current module
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Calibration (float64)
        -- Offset (float64)
        -- Error described in the Response message&gt;Body section
        
        
        Z-Controller
        """
        return self.quickSend("Current.CalibrGet", [Gain_index], ["i"], ["d", "d"])

    def ZCtrl_ZPosSet(self, Z_position_m: np.float32):
        """
        ZCtrl.ZPosSet
        Sets the Z position of the tip.
        Note: to change the Z-position of the tip, the Z-controller must be switched OFF.
        Arguments: 
        -- Z position (m) (float32)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("ZCtrl.ZPosSet", [Z_position_m], ["f"], [])

    def ZCtrl_ZPosGet(self):
        """
        ZCtrl.ZPosGet
        Returns the current Z position of the tip.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Z position (m) (float32)
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("ZCtrl.ZPosGet", [], [], ["f"])

    def ZCtrl_OnOffSet(self, Z_Controller_status: np.uint32):
        """
        ZCtrl.OnOffSet
        Switches the Z-Controller On or Off.
        Arguments: 
        -- Z-Controller status (unsigned int32) switches the controller Off (_0) or On (_1)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("ZCtrl.OnOffSet", [Z_Controller_status], ["I"], [])

    def ZCtrl_OnOffGet(self):
        """
        ZCtrl.OnOffGet
        Returns the status of the Z-Controller.
        This function returns the status from the real-time controller (i.e. not from the Z-Controller module). 
        This function is useful to make sure that the Z-controller is really off before starting an experiment. Due to the communication delay, switch-off delay... sending the off command with the <i>ZCtrl.OnOffGet</i> function might take some time before the controller is off.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Z-Controller status (unsigned int32) indicates if the controller is Off (_0) or On (_1)
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("ZCtrl.OnOffGet", [], [], ["I"])

    def ZCtrl_SetpntSet(self, Z_Controller_setpoint):
        """
        ZCtrl.SetpntSet
        Sets the setpoint of the Z-Controller.
        Arguments:
        -- Z-Controller setpoint (float32)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("ZCtrl.SetpntSet", [Z_Controller_setpoint], ["f"], [])

    def ZCtrl_SetpntGet(self):
        """
        ZCtrl.SetpntGet
        Returns the setpoint of the Z-Controller.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Z-Controller setpoint (float32)
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("ZCtrl.SetpntGet", [], [], ["f"])

    def ZCtrl_GainSet(self, P_gain, Time_constant_s, I_gain):
        """
        ZCtrl.GainSet
        Sets the Z-Controller gains (P, I) and time settings.
        The integral gain is calculated based on the P-gain and the Time constant as follows: I_P/T.
        Arguments:
        -- P-gain (float32) is the proportional gain of the regulation loop
        -- Time constant (s) (float32) is the time constant T
        -- I-gain (float32) is the integral gain of the regulation loop (I_P/T)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("ZCtrl.GainSet", [P_gain, Time_constant_s, I_gain], ["f", "f", "f"], [])

    def ZCtrl_GainGet(self):
        """
        ZCtrl.GainGet
        Returns the Z-Controller gains (P, I) and time settings.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- P-gain (float32) is the proportional gain of the regulation loop
        -- Time constant (s) (float32) is the time constant T
        -- I-gain (float32) is the integral gain of the regulation loop (I_P/T)
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("ZCtrl.GainGet", [], [], ["f", "f", "f"])

    def ZCtrl_SwitchOffDelaySet(self, Z_Controller_switch_off_delay_s):
        """
        ZCtrl.SwitchOffDelaySet
        Sets the switch off delay in seconds of the Z-Controller.
        Before turning off the controller, the Z position is averaged over this time delay. The tip is then positioned at the averaged value. This leads to reproducible Z positions when switching off the Z-controller.
        Arguments:
        -- Z-Controller switch off delay (s) (float32)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        
        
        """
        return self.quickSend("ZCtrl.SwitchOffDelaySet", [Z_Controller_switch_off_delay_s], ["f"], [])

    def ZCtrl_SwitchOffDelayGet(self):
        """
        ZCtrl.SwitchOffDelayGet
        Returns the switch off delay in seconds of the Z-Controller.
        Before turning off the controller, the Z position is averaged over this time delay. The tip is then positioned at the averaged value. This leads to reproducible Z positions when switching off the Z-controller.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Z-Controller switch off delay (s) (float32)
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("ZCtrl.SwitchOffDelayGet", [], [], ["f"])

    def ZCtrl_TipLiftSet(self, TipLift_m):
        """
        ZCtrl.TipLiftSet
        Sets the TipLift of the Z-Controller.
        Retracts the tip by the specified amount when turning off the Z-controller.
        Arguments:
        -- TipLift (m) (float32)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("ZCtrl.TipLiftSet", [TipLift_m], ["f"], [])

    def ZCtrl_TipLiftGet(self):
        """
        ZCtrl.TipLiftGet
        Returns the TipLift of the Z-Controller.
        Retracts the tip by the specified amount when turning off the Z-controller.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- TipLift (m) (float32)
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("ZCtrl.TipLiftGet", [], [], ["f"])

    def ZCtrl_Home(self):
        """
        ZCtrl.Home
        Moves the tip to its home position.
        This function moves the tip to the home position defined by the Home Absolute (m)/ Home Relative (m) value. (Absolute and relative can be switched in the controller configuration panel in the software).
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("ZCtrl.Home", [], [], [])

    def ZCtrl_HomePropsSet(self, Relative_or_Absolute, Home_position_m):
        """
        ZCtrl.HomePropsSet
        Sets the current status of the Z-Controller Home switch and its corresponding position.
        The Home position can be absolute (fixed position) or relative to the current tip position.
        Arguments:
        -- Relative or Absolute (unsigned int16), where 0 means no change with respect to the current selection, 1 means  that the home position is absolute to the current position, and 2 means that it is relative to the current position
        -- Home position (m) (float32) is the home position value in meters
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("ZCtrl.HomePropsSet", [Relative_or_Absolute, Home_position_m], ["H", "f"], [])

    def ZCtrl_HomePropsGet(self):
        """
        ZCtrl.HomePropsGet
        Returns the current status of the Z-Controller Home switch and its corresponding position.
        The Home position can be absolute (fixed position) or relative to the current tip position.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Relative or Absolute (unsigned int16), where 0 means that the home position is absolute to the current position, and 1 means that it is relative to the current position
        -- Home position (m) (float32) is the home position value in meters
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("ZCtrl.HomePropsGet", [], [], ["H", "f"])

    def ZCtrl_ActiveCtrlSet(self, Z_Controller_index):
        """
        ZCtrl.ActiveCtrlSet
        Sets the active Z-Controller.
        Arguments: 
        -- Z-Controller index (int) is the index out of the list of controllers which can be retrieved by the function <i>ZCtrl.ControllersListGet</i>. 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("ZCtrl.ActiveCtrlSet", [Z_Controller_index], ["i"], [])

    def ZCtrl_CtrlListGet(self):
        """
        ZCtrl.CtrlListGet
        Returns the list of Z-Controllers and the index of the active controller.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- List of controllers size (int) is the size in bytes of the List of controllers array
        -- Number of controllers (int) is the number of elements of the List of controllers array
        -- List of controllers (1D array string) returns an array of the available Z-Controllers. Each element of the array is preceded by its size in bytes
        -- Active Z-Controller index (int) is the index out of the list of gains. 
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("ZCtrl.CtrlListGet", [], [], ["i", "i", "*+c", "i"])

    def ZCtrl_Withdraw(self, Wait_until_finished, Timeout_ms):
        """
        ZCtrl.Withdraw
        Withdraws the tip.
        This function switches off the Z-Controller and then fully withdraws the tip (to the upper limit of the Z-piezo range).
        Arguments: 
        -- Wait until finished (unsigned int32) indicates if the function waits until the tip is fully withdrawn (_1) or it does not wait (_0) 
        -- Timeout (ms) (int) is time in ms this function waits. Set it to -1 to wait indefinitely.
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("ZCtrl.Withdraw", [Wait_until_finished, Timeout_ms], ["I", "i"], [])

    def ZCtrl_WithdrawRateSet(self, Withdraw_slew_rate_mdivs):
        """
        ZCtrl.WithdrawRateSet
        Sets the Z-Controller withdraw slew rate in meters per second.
        Arguments:
        -- Withdraw slew rate (m/s) (float32)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("ZCtrl.WithdrawRateSet", [Withdraw_slew_rate_mdivs], ["f"], [])

    def ZCtrl_WithdrawRateGet(self):
        """
        ZCtrl.WithdrawRateGet
        Returns the Z-Controller withdraw slew rate in meters per second.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Withdraw slew rate (m/s) (float32)
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("ZCtrl.WithdrawRateGet", [], [], ["f"])

    def ZCtrl_LimitsEnabledSet(self, Limit_Z_status):
        """
        ZCtrl.LimitsEnabledSet
        Enables or disables the Z position limits.
        Arguments:
        -- Limit Z status (unsigned int32) enables the  Z limits (_1) or disables them (_0)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("ZCtrl.LimitsEnabledSet", [Limit_Z_status], ["I"], [])

    def ZCtrl_LimitsEnabledGet(self):
        """
        ZCtrl.LimitsEnabledGet
        Returns if the Z limits are enabled or disabled.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Limit Z status (unsigned int32) indicates if the Z limits are disabled (_0) or enabled (_1)
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("ZCtrl.LimitsEnabledGet", [], [], ["I"])

    def ZCtrl_LimitsSet(self, Z_high_limit_m, Z_low_limit_m):
        """
        ZCtrl.LimitsSet
        Sets the Z position high and low limits in meters.
        When the Z position limits are not enabled, this function has no effect.
        Arguments:
        -- Z high limit (m) (float32)
        -- Z low limit (m) (float32) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("ZCtrl.LimitsSet", [Z_high_limit_m, Z_low_limit_m], ["f", "f"], [])

    def ZCtrl_LimitsGet(self):
        """
        ZCtrl.LimitsGet
        Returns the Z position high and low limits in meters.
        When the Z position limits are not enabled, they correspond to the piezo range limits.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Z high limit (m) (float32)
        -- Z low limit (m) (float32) 
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("ZCtrl.LimitsGet", [], [], ["f", "f"])

    def ZCtrl_StatusGet(self):
        """
        ZCtrl.StatusGet
        Returns the current status of the Z-Controller module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Z -Controller Status (unsigned int16) returns if the controller is Off (1), On (2), on Hold (3), switching Off (4), if a Safe Tip event occurred (5), or if the tip is currently withdrawing (6)
        -- Error described in the Response message&gt;Body section
        
        Safe Tip
        """
        return self.quickSend("ZCtrl.StatusGet", [], [], ["H"])

    def SafeTip_OnOffSet(self, Safe_Tip_status):
        """
        SafeTip.OnOffSet
        Switches the Safe Tip feature on or off.
        Arguments: 
        -- Safe Tip status (unsigned int16) sets if the Safe Tip is On (_1) or Off (_2), or if it does not change (_0)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("SafeTip.OnOffSet", [Safe_Tip_status], ["H"], [])

    def SafeTip_OnOffGet(self):
        """
        SafeTip.OnOffGet
        Returns the on-off status of the Safe Tip.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Safe Tip status (unsigned int16) indicates if the Safe Tip is Off (_0) or On (_1)
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("SafeTip.OnOffGet", [], [], ["H"])

    def SafeTip_SignalGet(self):
        """
        SafeTip.SignalGet
        Returns the current Safe Tip signal value.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Signal value (float32)
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("SafeTip.SignalGet", [], [], ["f"])

    def SafeTip_PropsSet(self, Auto_recovery, Auto_pause_scan, Threshold):
        """
        SafeTip.PropsSet
        Sets the Safe Tip configuration.
        Arguments: 
        -- Auto recovery (unsigned int16) indicates if Z-controller automatically recovers from a SafeTip situation after a specified amount of time if Z-Controller was originally on. 0 means Off, 1 means On
        -- Auto pause scan (unsigned int16) indicates if the Z-controller automatically pauses/holds the scan on a SafeTip event. 0 means Off, 1 means On
        -- Threshold (float32) defines the condition to trigger the Safe Tip
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("SafeTip.PropsSet", [Auto_recovery, Auto_pause_scan, Threshold], ["H", "H", "f"], [])

    def SafeTip_PropsGet(self):
        """
        SafeTip.PropsGet
        Returns the Safe Tip configuration.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Auto recovery (unsigned int16) indicates if Z-controller automatically recovers from a SafeTip situation after a specified amount of time if Z-Controller was originally on. 0 means Off, 1 means On
        -- Auto pause scan (unsigned int16) indicates if the Z-controller automatically pauses/holds the scan on a SafeTip event. 0 means Off, 1 means On
        -- Threshold (float32) defines the condition to trigger the Safe Tip
        -- Error described in the Response message&gt;Body section
        
        
        
        Auto Approach
        """
        return self.quickSend("SafeTip.PropsGet", [], [], ["H", "H", "f"])

    def AutoApproach_Open(self):
        """
        AutoApproach.Open
        Opens the Auto-Approach module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("AutoApproach.Open", [], [], [])

    def AutoApproach_OnOffSet(self, On_Off):
        """
        AutoApproach.OnOffSet
        Starts or stops the Z auto- approach procedure.
        Arguments: 
        -- On/Off (unsigned int16) starts the auto-approach procedure (_1) or stops it (_0)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("AutoApproach.OnOffSet", [On_Off], ["H"], [])

    def AutoApproach_OnOffGet(self):
        """
        AutoApproach.OnOffGet
        Returns the on-off status of the Z auto- approach procedure.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Status (unsigned int16) indicates if the auto-approach procedure is Off (_0) or running (_1)
        -- Error described in the Response message&gt;Body section
        
        
        
        Z Spectroscopy
        """
        return self.quickSend("AutoApproach.OnOffGet", [], [], ["H"])

    def ZSpectr_Open(self):
        """
        ZSpectr.Open
        Opens the Z Spectroscopy module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("ZSpectr.Open", [], [], [])

    def ZSpectr_Start(self, Get_data, Save_base_name):
        """
        ZSpectr.Start
        Starts a Z spectroscopy in the Z Spectroscopy module.
        Before using this function, select the channels to record in the Z Spectroscopy module.
        Arguments: 
        -- Get data (unsigned int32) defines if the function returns the spectroscopy data (1_True) or not (0_False) 
        -- Save base name string size (int) defines the number of characters of the Save base name string
        -- Save base name (string) is the basename used by the saved files. If empty string, there is no change
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Channels names size (int) is the size in bytes of the Channels names string array
        -- Number of channels (int) is the number of elements of the Channels names string array
        -- Channels names (1D array string) returns the list of channels names. The size of each string item comes right before it as integer 32
        -- Data rows (int) defines the number of rows of the Data array
        -- Data columns (int) defines the number of columns of the Data array
        -- Data (2D array float32) returns the spectroscopy data
        -- Number of parameters (int) is the number of elements of the Parameters array
        -- Parameters (1D array float32) returns the list of fixed parameters and parameters (in that order). To see the names of the returned parameters, use the Z<i>Spectr.PropsGet</i> function.
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("ZSpectr.Start", [Get_data, Save_base_name], ["I", "+*c"],
                              ["i", "i", "*+c", "i", "i", "2f", "i", "*f"])

    def ZSpectr_Stop(self):
        """
        ZSpectr.Stop
        Stops the current Z Spectroscopy measurement.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("ZSpectr.Stop", [], [], [])

    def ZSpectr_StatusGet(self):
        """
        ZSpectr.StatusGet
        Returns the status of the Z Spectroscopy measurement.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Status (unsigned int32) where 0_not running and 1_running
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("ZSpectr.StatusGet", [], [], ["I"])

    def ZSpectr_ChsSet(self, Channel_indexes):
        """
        ZSpectr.ChsSet
        Sets the list of recorded channels in Z Spectroscopy.
        Arguments: 
        -- Number of channels (int) is the number of recorded channels. It defines the size of the Channel indexes array
        -- Channel indexes (1D array int) are the indexes of recorded channels. The indexes are comprised between 0 and 23 for the 24 signals assigned in the Signals Manager.
        To get the signal name and its corresponding index in the list of the 128 available signals in the Nanonis Controller, use the <i>Signals.InSlotsGet</i> function
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("ZSpectr.ChsSet", [Channel_indexes], ["+*i"], [])

    def ZSpectr_ChsGet(self):
        """
        ZSpectr.ChsGet
        Returns the list of recorded channels in Z Spectroscopy.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Number of channels (int) is the number of recorded channels. It defines the size of the Channel indexes array
        -- Channel indexes (1D array int) are the indexes of recorded channels. The indexes are comprised between 0 and 23 for the 24 signals assigned in the Signals Manager.
        To get the signal name and its corresponding index in the list of the 128 available signals in the Nanonis Controller, use the <i>Signals.InSlotsGet</i> function
        - Channels size (int) is the size in bytes of the Channels string array
        - Channels (1D array string) returns the naames of the acquired channels in the sweep. The size of each string item comes right before it as integer 32
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("ZSpectr.ChsGet", [], [], ["i", "*i", "i", "**c"])

    def ZSpectr_PropsSet(self, Backward_sweep, Number_of_points, Number_of_sweeps, Autosave, Show_save_dialog,
                         Save_all):
        """
        ZSpectr.PropsSet
        Configures the Z Spectroscopy parameters.
        Arguments: 
        -- Backward sweep (unsigned int16) selects whether to also acquire a backward sweep (forward is always measured) when it is 1. When it is 2 means that no backward sweep is performed, and 0 means no change.
        -- Number of points (int) defines the number of points to acquire over the sweep range, where 0 means no change
        -- Number of sweeps (unsigned int16) is the number of sweeps to measure and average. 0 means no change with respect to the current selection
        -- Autosave (unsigned int16) selects whether to automatically save the data to ASCII file once the sweep is done (_1). This flag is off when _2, and 0 means no change
        -- Show save dialog (unsigned int16) selects whether to show the save dialog box once the sweep is done (_1). This flag is off when _2, and 0 means no change
        -- Save all (unsigned int16) where 0 means no change, 1 means that the data from the individual sweeps is saved along with the average data of all of them, and 2 means that the individual sweeps are not saved in the file. This parameter only makes sense when multiple sweeps are configured
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("ZSpectr.PropsSet",
                              [Backward_sweep, Number_of_points, Number_of_sweeps, Autosave, Show_save_dialog,
                               Save_all], ["H", "i", "H", "H", "H", "H"], [])

    def ZSpectr_PropsGet(self):
        """
        ZSpectr.PropsGet
        Returns the Z Spectroscopy parameters.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Backward sweep (unsigned int16), where 1 means that the backward sweep is performed (forward is always measured) and 0 means that there is no backward sweep
        -- Number of points (int) is the number of points to acquire over the sweep range
        -- Parameters size (int) is the size in bytes of the Parameters string array
        -- Number of parameters (int) is the number of elements of the Parameters string array
        -- Parameters (1D array string) returns the parameters of the sweep. The size of each string item comes right before it as integer 32
        -- Fixed parameters size (int) is the size in bytes of the Fixed parameters string array
        -- Number of fixed parameters (int) is the number of elements of the Fixed parameters string array
        -- Fixed parameters (1D array string) returns the fixed parameters of the sweep. The size of each string item comes right before it as integer 32
        -- Number of sweeps (unsigned int16) is the number of sweeps to measure and average
        -- Save all (unsigned int16) where 1 means that the data from the individual sweeps is saved along with the average data of all of them, and 0 means that the individual sweeps are not saved in the file. This parameter only makes sense when multiple sweeps are configured
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("ZSpectr.PropsGet", [], [],
                              ["H", "i", "i", "i", "*+c", "i", "i", "*+c", "H", "H"])

    def ZSpectr_AdvPropsSet(self, Time_between_forward_and_backward_sweep_s, Record_final_Z, Lockin_Run, Reset_Z):
        """
        ZSpectr.AdvPropsSet
        Sets parameters from the Advanced configuration section of the Z spectroscopy module.
        Arguments: 
        -- Time between forward and backward sweep (s) (float32)
        -- Record final Z (unsigned int16) if on, the final Z position is averaged during Z averaging time after Z control time at the end of the sweep. 0 means no change, 1 means On, and 2 means Off
        -- Lockin Run (unsigned int16) sets the Lock-In to run during the measurement. 
        When using this feature, make sure the Lock-In is configured correctly and settling times are set to twice the Lock-In period at least. This option is ignored when Lock-In is already running.
        This option is disabled if the Sweep Mode is MLS and the flag to configure the Lock-In per segment in the Multiline segment editor is set. 0 means no change, 1 means On, and 2 means Off
        -- Reset Z (unsigned int16) if on, the Z position is set back to the initial value at the end of the sweep. If off, the Z position stays at the last value at the end of the sweep.
        Be aware that if the Z-Controller is on and Z is not reset, the Z position will anyway be automatically controlled by the Z-Controller. 0 means no change, 1 means On, and 2 means Off
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        """
        return self.quickSend("ZSpectr.AdvPropsSet",
                              [Time_between_forward_and_backward_sweep_s, Record_final_Z, Lockin_Run, Reset_Z],
                              ["f", "H", "H", "H"], [])

    def ZSpectr_AdvPropsGet(self):
        """
        ZSpectr.AdvPropsGet
        Sets parameters from the Advanced configuration section of the Z spectroscopy module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Time between forward and backward sweep (s) (float32)
        -- Record final Z (unsigned int16) if on, the final Z position is averaged during Z averaging time after Z control time at the end of the sweep. 0 means Off, 1 means On
        -- Lockin Run (unsigned int16) indicates if the Lock-In runs during the measurement. 
        When using this feature, make sure the Lock-In is configured correctly and settling times are set to twice the Lock-In period at least. This option is ignored when Lock-In is already running.
        This option is disabled if the Sweep Mode is MLS and the flag to configure the Lock-In per segment in the Multiline segment editor is set. 0 means Off, 1 means On
        -- Reset Z (unsigned int16) if on, the Z position is set back to the initial value at the end of the sweep. If off, the Z position stays at the last value at the end of the sweep.
        Be aware that if the Z-Controller is on and Z is not reset, the Z position will anyway be automatically controlled by the Z-Controller. 0 means Off, 1 means On
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("ZSpectr.AdvPropsGet", [], [], ["f", "H", "H", "H"])

    def ZSpectr_RangeSet(self, Z_offset_m, Z_sweep_distance_m):
        """
        ZSpectr.RangeSet
        Sets the Z-spectroscopy range settings.
        Arguments: 
        -- Z offset (m) (float32) defines the offset to apply before starting the sweep
        -- Z sweep distance (m) (float32) defines the sweep span
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("ZSpectr.RangeSet", [Z_offset_m, Z_sweep_distance_m], ["f", "f"], [])

    def ZSpectr_RangeGet(self):
        """
        ZSpectr.RangeGet
        Returns the Z-spectroscopy range settings.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Z offset (m) (float32) defines the offset to apply before starting the sweep
        -- Z sweep distance (m) (float32) defines the sweep span
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("ZSpectr.RangeGet", [], [], ["f", "f"])

    def ZSpectr_TimingSet(self, Z_averaging_time_s, Initial_settling_time_s, Maximum_slew_rate_Vdivs, Settling_time_s,
                          Integration_time_s, End_settling_time_s, Z_control_time_s):
        """
        ZSpectr.TimingSet
        Configures the Z spectroscopy timing parameters.
        Arguments: 
        -- Z averaging time (s) (float32) 
        -- Initial settling time (s) (float32) 
        -- Maximum slew rate (V/s) (float32) 
        -- Settling time (s) (float32) 
        -- Integration time (s) (float32) 
        -- End settling time (s) (float32) 
        -- Z control time (s) (float32) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("ZSpectr.TimingSet",
                              [Z_averaging_time_s, Initial_settling_time_s, Maximum_slew_rate_Vdivs, Settling_time_s,
                               Integration_time_s, End_settling_time_s, Z_control_time_s],
                              ["f", "f", "f", "f", "f", "f", "f"], [])

    def ZSpectr_TimingGet(self):
        """
        ZSpectr.TimingGet
        Returns the Z spectroscopy timing parameters.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Z averaging time (s) (float32) 
        -- Initial settling time (s) (float32) 
        -- Maximum slew rate (V/s) (float32) 
        -- Settling time (s) (float32) 
        -- Integration time (s) (float32) 
        -- End settling time (s) (float32) 
        -- Z control time (s) (float32) 
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("ZSpectr.TimingGet", [], [], ["f", "f", "f", "f", "f", "f", "f"])

    def ZSpectr_RetractDelaySet(self, Retract_delay_s):
        """
        ZSpectr.RetractDelaySet
        Sets the Z-spectroscopy retract delay.
        Arguments: 
        -- Retract delay (s) (float32) defines the delay in seconds between forward sweep and backward sweep
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("ZSpectr.RetractDelaySet", [Retract_delay_s], ["f"], [])

    def ZSpectr_RetractDelayGet(self):
        """
        ZSpectr.RetractDelayGet
        Returns the Z-spectroscopy retract delay.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Retract delay (s) (float32) defines the delay in seconds between forward sweep and backward sweep
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("ZSpectr.RetractDelayGet", [], [], ["f"])

    def ZSpectr_RetractSet(self, Enable, Threshold, Signal_index, Comparison):
        """
        ZSpectr.RetractSet
        Sets the configuration for the main condition of the Auto Retract in the Z-Spectroscopy module.
        Arguments: 
        -- Enable (unsigned int16) switches the Auto Retract on or off. 0 means no change, 1 means On, and 2 means Off
        -- Threshold (float32) combined with the comparison, sets which situation triggers the main condition to auto-retract the tip
        -- Signal index (int) sets the index between 0-127 of the signal used to check the main retract condition. Use -1 to leave the value unchanged in the Nanonis software
        -- Comparison (unsigned int16) sets which situation triggers the main condition to auto-retract the tip. 0 means &gt;, 1 means &lt;, and 2 means no change
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("ZSpectr.RetractSet", [Enable, Threshold, Signal_index, Comparison], ["H", "f", "i", "H"],
                              [])

    def ZSpectr_RetractGet(self):
        """
        ZSpectr.RetractGet
        Sets the configuration for the main condition of the Auto Retract in the Z-Spectroscopy module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Enable (unsigned int16) indicates if the Auto Retract is on or off. 0 means Off, 1 means On
        -- Threshold (float32) combined with the comparison, defines which situation triggers the main condition to auto-retract the tip
        -- Signal index (int) is the index between 0-127 of the signal used to check the main retract condition. Use -1 to leave the value unchanged in the Nanonis software
        -- Comparison (unsigned int16) defines which situation triggers the main condition to auto-retract the tip. 0 means &gt;, 1 means &lt;
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("ZSpectr.RetractGet", [], [], ["H", "f", "i", "H"])

    def ZSpectr_RetractSecondSet(self, Second_condition, Threshold, Signal_index, Comparison):
        """
        ZSpectr.RetractSecondSet
        Sets the configuration for the Second condition of the Auto Retract in the Z-Spectroscopy module.
        Arguments: 
        -- Second condition (int) configures the use of a second signal comparison in combination with the main Auto Retract signal comparison. Possible values are 0_no change, 1_-No-, 2_OR, 3_AND, 4_THEN, where:
        
         -No-: disables the use of a second signal comparison
        OR: Auto-Retract will execute if the 1st or the Second condition is met
        AND: Auto-Retract will execute if the 1st and the Second condition are met at the same time
        THEN: the Second condition is only checked once the 1st condition has been met
        
        -- Threshold (float32) combined with the comparison, sets which situation triggers the Second condition to auto-retract the tip
        -- Signal index (int) sets the index between 0-127 of the signal used to check the Second retract condition. Use -1 to leave the value unchanged in the Nanonis software
        -- Comparison (unsigned int16) sets which situation triggers the Second condition to auto-retract the tip. 0 means &gt;, 1 means &lt;, and 2 means no change
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("ZSpectr.RetractSecondSet", [Second_condition, Threshold, Signal_index, Comparison],
                              ["i", "f", "i", "H"], [])

    def ZSpectr_RetractSecondGet(self):
        """
        ZSpectr.RetractSecondGet
        Returns the configuration for the Second condition of the Auto Retract in the Z-Spectroscopy module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Second condition (int) indicates the use of a second signal comparison in combination with the main Auto Retract signal comparison. Possible values are 0_-No-, 1_OR, 2_AND, 3_THEN, where:
        
         -No-: disables the use of a second signal comparison
        OR: Auto-Retract will execute if the 1st or the Second condition is met
        AND: Auto-Retract will execute if the 1st and the Second condition are met at the same time
        THEN: the Second condition is only checked once the 1st condition has been met
        
        -- Threshold (float32) combined with the comparison, indicates which situation triggers the Second condition to auto-retract the tip
        -- Signal index (int) indicates the index between 0-127 of the signal used to check the Second retract condition
        -- Comparison (unsigned int16) indicates which situation triggers the Second condition to auto-retract the tip. 0 means &gt;, 1 means &lt;
        -- Error described in the Response message&gt;Body section
        
        Piezos
        """
        return self.quickSend("ZSpectr.RetractSecondGet", [], [], ["i", "f", "i", "H"])

    def ZSpectr_DigSyncSet(self, Digital_Sync: np.uint16):
        """
        ZSpectr_.DigSyncSet
        Returns the configured TTL/pulse sequence synchronization option in the Advanced section of the Z Spectroscopy module.
        TTL synchronization allows for controlling one high-speed digital output according to the individual stages of the Z Spectroscopy measurement.
        Pulse sequence allows running a high speed digital pulse sequence (if the Pulse Generation module is licensed)synchronized with the individual stages of the Z Spectroscopy measurement.
        Arguments: 
        - Digital Sync. (unsigned int16) where 0 means no change, 1 is Off, 2 is TTL Sync, and 3 is Pulse Sequence
        Return arguments (if Send response back flag is set to True when sending request message):
        - Error described in the Response message>Body section
        """
        return self.quickSend("ZSpectr.DigSyncSet", [Digital_Sync],
                              ["H"], [])

    def ZSpectr_DigSyncGet(self):
        """
        ZSpectr.DigSyncGet
        Returns the configured TTL/pulse sequence synchronization option in the Advanced section of the Z Spectroscopy module.
        TTL synchronization allows for controlling one high-speed digital output according to the individual stages of the Z Spectroscopy measurement.
        Pulse sequence allows running a high speed digital pulse sequence (if the Pulse Generation module is licensed)synchronized with the individual stages of the Z Spectroscopy measurement.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Digital Sync. (unsigned int16) where 0 is Off, 1 is TTL Sync, and 2 is Pulse Sequence
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("ZSpectr.DigSyncGet", [], [], ["H"])

    def ZSpectr_TTLSyncSet(self, TTL_line: np.uint16, TTL_polarity: np.uint16,
                              Time_to_on_s: np.float32, On_duration_s: np.float32):
        """
        ZSpectr.TTLSyncSet
        Sets the configuration of the TTL Synchronization feature in the Advanced section of the Z Spectroscopy module.
        TTL synchronization allows for controlling one high-speed digital output according to the individual stages of the Z Spectroscopy measurement.
        Arguments: 
        -- TTL line (unsigned int16) sets which digital line should be controlled. 0 means no change, 1 means HS Line 1, 2 means HS Line 2, 3 means HS Line 3, 4 means HS Line 4
        -- TTL polarity (unsigned int16) sets the polarity of the switching action. 0 means no change, 1 means Low Active, and 2 means High Active
        -- Time to on (s) (float32) defines the time to wait before activating the TTL line
        -- On duration (s) (float32) defines how long the TTL line should be activated before resetting
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("ZSpectr.TTLSyncSet", [TTL_line, TTL_polarity, Time_to_on_s, On_duration_s],
                              ["H", "H", "f", "f"], [])

    def ZSpectr_TTLSyncGet(self):
        """
        ZSpectr.TTLSyncGet
        Returns the configuration of the TTL Synchronization feature in the Advanced section of the Z Spectroscopy module.
        TTL synchronization allows for controlling  one high-speed digital output according to the individual stages of the Z Spectroscopy measurement.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- TTL line (unsigned int16) indicates which digital line should be controlled. 0 means HS Line 1, 1 means HS Line 2, 2 means HS Line 3, 3 means HS Line 4
        -- TTL polarity (unsigned int16) indicates the polarity of the switching action. 0 means Low Active, 1 means High Active
        -- Time to on (s) (float32) indicates the time to wait before activating the TTL line
        -- On duration (s) (float32) indicates how long the TTL line should be activated before resetting
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("ZSpectr.TTLSyncGet", [], [], ["H", "H", "f", "f"])

    def ZSpectr_PulseSeqSyncSet(self, Pulse_Sequence_Nr: np.uint16, Nr_Periods: np.uint32):
        """
        ZSpectr.PulseSeqSyncSet
        Sets the configuration of the pulse sequence synchronization feature in the Advanced section of the Z Spectroscopy module.
        Pulse sequence allows running a high speed digital pulse sequence (if the Pulse Generation module is licensed) synchronized with the individual stages of the Z Spectroscopy measurement.
        Arguments: 
        - Pulse Sequence Nr. (unsigned int16) is the pulse sequence number as configured in the Pulse Generation module. 0 means no change
        - Nr. Periods (unsigned int32) is the number of times the same pulse sequence is executed
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("ZSpectr.PulseSeqSyncSet", [Pulse_Sequence_Nr, Nr_Periods],
                              ["H", "I"], [])

    def ZSpectr_PulseSeqSyncGet(self):
        """
        ZSpectr.PulseSeqSyncGet
        Returns the configuration of the pulse sequence synchronization feature in the Advanced section of the Z Spectroscopy module.
        Pulse sequence allows running a high speed digital pulse sequence (if the Pulse Generation module is licensed) synchronized with the individual stages of the Z Spectroscopy measurement.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        - Pulse Sequence Nr. (unsigned int16) is the pulse sequence number as configured in the Pulse Generation module. 0 means no change
        - Nr. Periods (unsigned int32) is the number of times the same pulse sequence is executed
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("ZSpectr.PulseSeqSyncGet", [], [], ["H", "I"])

    def Piezo_TiltSet(self, Tilt_X_deg, Tilt_Y_deg):
        """
        Piezo.TiltSet
        Configures the tilt correction parameters.
        Arguments: 
        -- Tilt X (deg) (float32) sets by which angle to correct the tilt in the X direction
        -- Tilt Y (deg) (float32) sets by which angle to correct the tilt in the Y direction
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Piezo.TiltSet", [Tilt_X_deg, Tilt_Y_deg], ["f", "f"], [])

    def Piezo_TiltGet(self):
        """
        Piezo.TiltGet
        Returns the tilt correction parameters.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Tilt X (deg) (float32) indicates by which angle to correct the tilt in the X direction
        -- Tilt Y (deg) (float32) indicates by which angle to correct the tilt in the Y direction
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Piezo.TiltGet", [], [], ["f", "f"])

    def Piezo_RangeSet(self, Range_X_m, Range_Y_m, Range_Z_m):
        """
        Piezo.RangeSet
        Sets the piezo range (m) values for all 3 axes (X, Y, Z).
        Changing the range will also change the sensitivity (HV gain will remain unchanged).
        Arguments: 
        -- Range X (m) (float32)
        -- Range Y (m) (float32)
        -- Range Z (m) (float32)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Piezo.RangeSet", [Range_X_m, Range_Y_m, Range_Z_m], ["f", "f", "f"], [])

    def Piezo_RangeGet(self):
        """
        Piezo.RangeGet
        Returns the piezo range (m) values for all 3 axes (X, Y, Z).
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Range X (m) (float32)
        -- Range Y (m) (float32)
        -- Range Z (m) (float32)
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Piezo.RangeGet", [], [], ["f", "f", "f"])

    def Piezo_SensSet(self, Calibration_X_mPerV, Calibration_Y_mPerV, Calibration_Z_mPerV):
        """
        Piezo.SensSet
        Sets the piezo sensitivity (m/V) values for all 3 axes (X, Y, Z).
        Changing the sensitivity will also change the range (HV gain will remain unchanged).
        Arguments: 
        -- Calibration X (m/V) (float32)
        -- Calibration Y (m/V) (float32)
        -- Calibration Z (m/V) (float32)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Piezo.SensSet", [Calibration_X_mPerV, Calibration_Y_mPerV, Calibration_Z_mPerV],
                              ["f", "f", "f"], [])

    def Piezo_SensGet(self):
        """
        Piezo.SensGet
        Returns the piezo sensitivity (m/V) values for all 3 axes (X, Y, Z).
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Calibration X (m/V) (float32)
        -- Calibration Y (m/V) (float32)
        -- Calibration Z (m/V) (float32)
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Piezo.SensGet", [], [], ["f", "f", "f"])

    def Piezo_DriftCompSet(self, Compensation_on_off, Vx_m_s, Vy_m_s, Vz_m_s, Sat_Lim):
        """
        Piezo.DriftCompSet
        Configures the drift compensation parameters.
        Arguments: 
        -- Compensation on/off (unsigned int32) activates or deactivates the drift compensation
        -- Vx (m/s) (float32) is the linear speed applied to the X piezo to compensate the drift
        -- Vy (m/s) (float32) is the linear speed applied to the Y piezo to compensate the drift
        -- Vz (m/s) (float32) is the linear speed applied to the Z piezo to compensate the drift
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Piezo.DriftCompSet", [Compensation_on_off, Vx_m_s, Vy_m_s, Vz_m_s, Sat_Lim],
                              ["I", "f", "f", "f", "f"], [])

    def Piezo_DriftCompGet(self):
        """
        Piezo.DriftCompGet
        Returns the drift compensation settings and information.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Compensation status (unsigned int32) indicates whether the drift compensation is On or Off
        -- Vx (m/s) (float32) is the linear speed applied to the X piezo to compensate the drift
        -- Vy (m/s) (float32) is the linear speed applied to the Y piezo to compensate the drift
        -- Vz (m/s) (float32) is the linear speed applied to the Z piezo to compensate the drift
        -- X saturated status (unsigned int32) indicates if the X drift correction reached 10Percent of the piezo range. When this happens, the drift compensation stops for this axis and its LED turns on. To reactivate the compensation, switch the drift compensation off and on
        -- Y saturated status (unsigned int32) indicates if the Y drift correction reached 10Percent of the piezo range. When this happens, the drift compensation stops for this axis and its LED turns on. To reactivate the compensation, switch the drift compensation off and on
        -- Z saturated status (unsigned int32) indicates if the Z drift correction reached 10Percent of the piezo range. When this happens, the drift compensation stops for this axis and its LED turns on. To reactivate the compensation, switch the drift compensation off and on
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Piezo.DriftCompGet", [], [], ["I", "f", "f", "f", "I", "I", "I", "f"])

    def Piezo_CalibrGet(self):
        """
        Piezo.CalibrGet
        Returns the piezo calibration values for all 3 axes (X, Y, Z).
        The calibration returned is for the low voltage signals, i.e. the +/-10V signals before the HV amplifier.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Calibration X (m/V) (float32)
        -- Calibration Y (m/V) (float32)
        -- Calibration Z (m/V) (float32)
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Piezo.CalibrGet", [], [], ["f", "f", "f"])

    def Piezo_HVAInfoGet(self):
        """
        Piezo.HVAInfoGet
        Returns the HVA gain readout information.
        If the HVA gain readout is not enabled, this function returns a warning.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Gain AUX (float32)
        -- Gain X (float32) 
        -- Gain Y (float32) 
        -- Gain Z (float32) 
        -- X/Y enabled status(unsigned int32)
        -- Z enabled status (unsigned int32) 
        -- AUX enabled status (unsigned int32)
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Piezo.HVAInfoGet", [], [], ["f", "f", "f", "f", "I", "I", "I"])

    def Piezo_HVAStatusLEDGet(self):
        """
        Piezo.HVAStatusLEDGet
        Returns the HVA LED status readout information.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Overheated status(unsigned int32)
        -- HV supply status (unsigned int32) 
        -- High temperature status (unsigned int32)
        -- Output connector status (unsigned int32)
        -- Error described in the Response message&gt;Body section
        
        Scan
        """
        return self.quickSend("Piezo.HVAStatusLEDGet", [], [], ["I", "I", "I", "I"])

    def Scan_Action(self, Scan_action, Scan_direction):
        """
        Scan.Action
        Starts, stops, pauses or resumes a scan.
        Arguments: 
        -- Scan action (unsigned int16) sets which action to perform, where 0=Start, 1=Stop, 2=Pause, 3=Resume, 4=Freeze, 5=Unfreeze, 6=Go to Center 
        -- Scan direction (unsigned int32) that if 1, scan direction is set to up. If 0, direction is down
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Scan.Action", [Scan_action, Scan_direction], ["H", "I"], [])

    def Scan_StatusGet(self):
        """
        Scan.StatusGet
        Returns if the scan is running or not.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Scan status (unsigned int32) means that if it is 1, scan is running. If 0, scan is not running
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Scan.StatusGet", [], [], ["I"])

    def Scan_WaitEndOfScan(self, Timeout_ms):
        """
        Scan.WaitEndOfScan
        Waits for the End-of-Scan.
        This function returns only when an End-of-Scan or timeout occurs (whichever occurs first).
        Arguments: 
        -- Timeout (ms) (int) sets how many milliseconds this function waits for an End-of-Scan. If –1, it waits indefinitely
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Timeout status status (unsigned int32) means that if it is 1, the function timed-out. If 0, it didn’t time-out
        -- File path size (unsigned int32) is the number of bytes corresponding to the File path string
        -- File path (string) returns the path where the data file was automatically saved (if auto-save was on). If no file was saved at the End-of-Scan, it returns an empty path
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Scan.WaitEndOfScan", [Timeout_ms], ["i"], ["I", "I", "*-c"])

    def Scan_FrameSet(self, Center_X_m, Center_Y_m, Width_m, Height_m, Angle_deg):
        """
        Scan.FrameSet
        Configures the scan frame parameters.
        Arguments: 
        -- Center X (m) (float32) is the X position of the scan frame center
        -- Center Y (m) (float32) is the Y position of the scan frame center
        -- Width (m) (float32) is the width of the scan frame
        -- Height (m) (float32) is the height of the scan frame
        -- Angle (deg) (float32) is the angle of the scan frame (positive angle means clockwise rotation)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Scan.FrameSet", [Center_X_m, Center_Y_m, Width_m, Height_m, Angle_deg],
                              ["f", "f", "f", "f", "f"], [])

    def Scan_FrameGet(self):
        """
        Scan.FrameGet
        Returns the scan frame parameters.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Center X (m) (float32) is the X position of the scan frame center
        -- Center Y (m) (float32) is the Y position of the scan frame center
        -- Width (m) (float32) is the width of the scan frame
        -- Height (m) (float32) is the height of the scan frame
        -- Angle (deg) (float32) is the angle of the scan frame (positive angle means clockwise rotation)
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("Scan.FrameGet", [], [], ["f", "f", "f", "f", "f"])

    def Scan_BufferSet(self, Channel_indexes, Pixels, Lines):
        """
        Scan.BufferSet
        Configures the scan buffer parameters.
        Arguments: 
        -- Number of channels (int) is the number of recorded channels. It defines the size of the Channel indexes array
        -- Channel indexes (1D array int) are the indexes of recorded channels. The indexes are comprised between 0 and 23 for the 24 signals assigned in the Signals Manager.
        To get the signal name and its corresponding index in the list of the 128 available signals in the Nanonis Controller, use the <i>Signals.InSlotsGet</i> function
        -- Pixels (int) is the number of pixels per line.
        In the scan control module this value is coerced to the closest multiple of 16, because the scan data is sent from the RT to the host in packages of 16 pixels
        -- Lines (int) is the number of scan lines.
        Be aware that if the chain button to keep the scan resolution ratio in the scan control module is active and the number of lines is set to 0 or left unconnected, the number of lines will automatically coerce to keep the scan resolution ratio according to the new number of pixels.
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Scan.BufferSet", [Channel_indexes, Pixels, Lines],
                              ["+*i", "i", "i"], [])

    def Scan_BufferGet(self):
        """
        Scan.BufferGet
        Returns the scan buffer parameters.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Number of channels (int) is the number of recorded channels. It defines the size of the Channel indexes array
        -- Channel indexes (1D array int) are the indexes of recorded channels. The indexes are comprised between 0 and 23 for the 24 signals assigned in the Signals Manager.
        To get the signal name and its corresponding index in the list of the 128 available signals in the Nanonis Controller, use the <i>Signals.InSlotsGet</i> function
        -- Pixels (int) is the number of pixels per line
        -- Lines (int) is the number of scan lines
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Scan.BufferGet", [], [], ["i", "*i", "i", "i"])

    def Scan_PropsSet(self, Continuous_scan, Bouncy_scan, Autosave, Series_name,
                      Comment, Modules_names):
        """
        Scan.PropsSet
        Configures some of the scan parameters.
        Arguments: 
        -- Continuous scan (unsigned int32) sets whether the scan continues or stops when a frame has been completed. 0 means no change, 1 is On, and 2 is Off
        -- Bouncy scan (unsigned int32) sets whether the scan direction changes when a frame has been completed. 0 means no change, 1 is On, and 2 is Off
        -- Autosave (unsigned int32) defines the save behavior when a frame has been completed. "All" saves all the future images. "Next" only saves the next frame. 0 means no change, 1 is All, 2 is Next, and 3 sets this feature Off
        -- Series name size (int) is the size in bytes of the Series name string
        -- Series name (string) is base name used for the saved images
        -- Comment size (int) is the size in bytes of the Comment string
        -- Comment (string) is comment saved in the file
         - Modules names size (int) is the size in bytes of the modules array. These are the modules whose
        parameters are saved in the header of the files
        - Modules names number (int) is the number of elements of the modules names array
        - Modules names (1D array string) is an array of modules names strings, where each string comes
        prepended by its size in bytes
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Scan.PropsSet",
                              [Continuous_scan, Bouncy_scan, Autosave, Series_name, Comment, Modules_names],
                              ["I", "I", "I", "+*c", "+*c", "+*c"], [])

    def Scan_PropsGet(self):
        """
        Scan.PropsGet
        Returns some of the scan parameters.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Continuous scan (unsigned int32) indicates whether the scan continues or stops when a frame has been completed. 0 means Off, and 1 is On
        -- Bouncy scan (unsigned int32) indicates whether the scan direction changes when a frame has been completed. 0 means Off, and 1 is On
        -- Autosave (unsigned int32) defines the save behavior when a frame has been completed. "All" saves all the future images. "Next" only saves the next frame. 0 is All, 1 is Next, and 2 means Off
        -- Series name size (int) is the size in bytes of the Series name string
        -- Series name (string) is base name used for the saved images
        -- Comment size (int) is the size in bytes of the Comment string
        -- Comment (string) is comment saved in the file
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Scan.PropsGet", [], [], ["I", "I", "I", "i", "*-c", "i", "*-c"])

    def Scan_SpeedSet(self, Forward_linear_speed_m_s, Backward_linear_speed_m_s, Forward_time_per_line_s,
                      Backward_time_per_line_s, Keep_parameter_constant, Speed_ratio):
        """
        Scan.SpeedSet
        Configures the scan speed parameters.
        Arguments: 
        -- Forward linear speed (m/s) (float32) 
        -- Backward linear speed (m/s) (float32) 
        -- Forward time per line (s) (float32) 
        -- Backward time per line (s) (float32) 
        -- Keep parameter constant (unsigned int16) defines which speed parameter to keep constant, where 0 means no change, 1 keeps the linear speed constant, and 2 keeps the time per line constant
        -- Speed ratio (float32) defines the backward tip speed related to the forward speed
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Scan.SpeedSet",
                              [Forward_linear_speed_m_s, Backward_linear_speed_m_s, Forward_time_per_line_s,
                               Backward_time_per_line_s, Keep_parameter_constant, Speed_ratio],
                              ["f", "f", "f", "f", "H", "f"], [])

    def Scan_SpeedGet(self):
        """
        Scan.SpeedGet
        Returns the scan speed parameters.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Forward linear speed (m/s) (float32) 
        -- Backward linear speed (m/s) (float32) 
        -- Forward time per line (s) (float32) 
        -- Backward time per line (s) (float32) 
        -- Keep parameter constant (unsigned int16) defines which speed parameter to keep constant, where 0 keeps the linear speed constant, and 1 keeps the time per line constant
        -- Speed ratio (float32) is the backward tip speed related to the forward speed
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Scan.SpeedGet", [], [], ["f", "f", "f", "f", "H", "f"])

    def Scan_FrameDataGrab(self, Channel_index, Data_direction):
        """
        Scan.FrameDataGrab
        Returns the scan data of the selected frame.
        Arguments: 
        -- Channel index (unsigned int32) selects which channel to get the data from. 
        The channel must be one of the acquired channels. The list of acquired channels while scanning can be configured by the function <i>Scan.BufferSet</i>
        -- Data direction (unsigned int32) selects the data direction, where 1 is forward, and 0 is backward
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Channels name size (int) is the size in bytes of the Channel name string
        -- Channel name (string) is the name of the channel selected by Channel index
        -- Scan data rows (int) defines the number of rows of the Scan data array
        -- Scan data columns (int) defines the number of columns of the Scan data array
        -- Scan data (2D array float32) returns the scan frame data of the selected channel
        -- Scan direction (unsigned int32) is the scan direction, where 1 is up, and 0 is down
        -- Error described in the Response message&gt;Body section
        
        Follow Me
        """
        return self.quickSend("Scan.FrameDataGrab", [Channel_index, Data_direction], ["I", "I"],
                              ["i", "*-c", "i", "i", "2f", "I"])

    def Scan_XYPosGet(self, Wait_newest_data):
        """
        Scan.XYPosGet
        Returns the values of the X and Y signals.
        Arguments: 
        - Wait for newest data (unsigned int32) selects whether the function returns the next available signal value or if it waits for a full period of new data. If False, this function returns a value 0 to Tap seconds after being called. If True, the function discards the first oversampled signal value received but returns the second value received. Thus, the function returns a value Tap to 2*Tap seconds after being called. It could be 0=False or 1=True
        
        Return arguments (if Send response back flag is set to True when sending request message):
        - X (m) (float32)
        - Y (m) (float32) 
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Scan.XYPosGet", [Wait_newest_data], ["I"],
                              ["f", "f"])

    def Scan_Save(self, Wait_until_saved, Timeout_ms):
        """
        Scan.Save
        Saves the current scan databuffer into file. If Wait Until Saved is True, this function returns only when the data has been saved or timeout occurs (whichever occurs first).
        Arguments: 
        - Wait until saved (unsigned int32) means that if it is 1, this function waits for the scan data to be saved
        - Timeout (ms) (int32) sets how many milliseconds to wait for the data to be saved. If it is set to –1, it will wait indefinitely        
        Return arguments (if Send response back flag is set to True when sending request message):
        - Timed out? (unsigned int32) indicates if a timeout occurred (=1) while waiting for the data to be saved
        --Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Scan.Save", [Wait_until_saved, Timeout_ms], ["I", "i"],
                              ["I"])

    def Scan_BackgroundPaste(self, Wait_until_pasted, Timeout_ms):
        """
        Scan.BackgroundPaste
        Pastes the current scan databuffer into the background. If Wait Until Pasted is True, this function returns only when the data has been pasted or timeout occurs (whichever occurs first).
        Arguments: 
        - Wait until pasted (unsigned int32) means that if it is 1, this function waits for the scan data to be pasted
        - Timeout (ms) (int32) sets how many milliseconds to wait for the data to be pasted. If it is set to –1, it will wait indefinitely        
        Return arguments (if Send response back flag is set to True when sending request message):
        - Timed out? (unsigned int32) indicates if a timeout occurred (=1) while waiting for the data to be pasted
        --Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Scan.BackgroundPaste", [Wait_until_pasted, Timeout_ms], ["I", "i"],
                              ["I"])

    def Scan_BackgroundDelete(self, Wait_until_deleted, Timeout_ms, Which_background):
        """
        Scan.BackgroundDelete
        Deletes the data from the last pasted background or from all backgrounds. If Wait Until Deletef is True, this function
        returns only when the data has been deleted or timeout occurs (whichever occurs first).
        Arguments: 
        - Wait until deleted (unsigned int32) means that if it is 1, this function waits for the scan data to be deleted
        - Timeout (ms) (int32) sets how many milliseconds to wait for the data to be deleted. If it is set to –1, it will wait indefinitely        
        - Which background to delete (unsigned int32) selects if the latest background is deleted (=0), or if all
            backgrounds are deleted (=1)
        Return arguments (if Send response back flag is set to True when sending request message):
        - Timed out? (unsigned int32) indicates if a timeout occurred (=1) while waiting for the data to be deleted
        --Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Scan.BackgroundDelete", [Wait_until_deleted, Timeout_ms, Which_background], ["I", "i", "I"],
                              ["I"])

    def FolMe_XYPosSet(self, X_m, Y_m, Wait_end_of_move):
        """
        FolMe.XYPosSet
        Moves the tip.
        This function moves the tip to the specified X and Y target coordinates (in meters). It moves at the speed specified by the "Speed" parameter in the Follow Me mode of the Scan Control module. 
        This function will return when the tip reaches its destination or if the movement stops.
        Arguments: 
        -- X (m) (float64) sets the target X position of the tip
        -- Y (m) (float64) sets the target Y position of the tip
        -- Wait end of move (unsigned int32) selects whether the function immediately (_0) or if it waits until the target is reached or the movement is stopped (_1) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("FolMe.XYPosSet", [X_m, Y_m, Wait_end_of_move], ["d", "d", "I"], [])

    def FolMe_XYPosGet(self, Wait_for_newest_data):
        """
        FolMe.XYPosGet
        Returns the X,Y tip coordinates (oversampled during the Acquisition Period time, Tap).
        Arguments: 
        -- Wait for newest data (unsigned int32) selects whether the function returns the next available signal value or if it waits for a full period of new data. 
        If 0, this function returns a value 0 to Tap seconds after being called. 
        If 1, the function discards the first oversampled signal value received but returns the second value received. Thus, the function returns a value Tap to 2*Tap seconds after being called
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- X (m) (float64) is the current X position of the tip
        -- Y (m) (float64) is the current Y position of the tip
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("FolMe.XYPosGet", [Wait_for_newest_data], ["I"], ["d", "d"])

    def FolMe_SpeedSet(self, Speed_m_s, Custom_speed):
        """
        FolMe.SpeedSet
        Configures the tip speed when moving in Follow Me mode.
        Arguments: 
        -- Speed (m/s) (float32) sets the surface speed in Follow Me mode
        -- Custom speed (unsigned int32) sets whether custom speed setting is used for Follow Me mode (_1) or if scan speed is used (_0)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("FolMe.SpeedSet", [Speed_m_s, Custom_speed], ["f", "I"], [])

    def FolMe_SpeedGet(self):
        """
        FolMe.SpeedGet
        Returns the tip speed when moving in Follow Me mode.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Speed (m/s) (float32) is the surface speed in Follow Me mode
        -- Custom speed (unsigned int32) returns whether custom speed setting is used for Follow Me mode (_1) or if scan speed is used (_0)
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("FolMe.SpeedGet", [], [], ["f", "I"])

    def FolMe_OversamplSet(self, Oversampling):
        """
        FolMe.OversamplSet
        Sets the oversampling of the acquired data when the tip is moving in Follow Me mode.
        Arguments: 
        -- Oversampling (int)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("FolMe.OversamplSet", [Oversampling], ["i"], [])

    def FolMe_OversamplGet(self):
        """
        FolMe.OversamplGet
        Returns the oversampling and rate of the acquired data when the tip is moving in Follow Me mode.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Oversampling (int)
        -- Sampling rate (Samples/s) (float32)
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("FolMe.OversamplGet", [], [], ["i", "f"])

    def FolMe_Stop(self):
        """
        FolMe.Stop
        Stops the tip movement in Follow Me mode.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("FolMe.Stop", [], [], [])

    def FolMe_PSOnOffGet(self):
        """
        FolMe.PSOnOffGet
        Returns if Point & Shoot is enabled or disabled in Follow Me mode.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Point & Shoot status (unsigned int32) returns whether Point & Shoot is enabled (_1) or disabled (_0)
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("FolMe.PSOnOffGet", [], [], ["I"])

    def FolMe_PSOnOffSet(self, Point_And_Shoot_status):
        """
        FolMe.PSOnOffSet
        Enables or disables Point & Shoot in Follow Me mode.
        Arguments:
        -- Point & Shoot status (unsigned int32) enables (_1) or disables (_0) Point & Shoot
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("FolMe.PSOnOffSet", [Point_And_Shoot_status], ["I"], [])

    def FolMe_PSExpGet(self):
        """
        FolMe.PSExpGet
        Returns the Point & Shoot experiment selected in Follow Me mode.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Point & Shoot experiment (unsigned int16) returns the selected Point & Shoot experiment
        -- Size of the list of experiments (int) is the full size in bytes of the List of experiments string array
        -- Number of experiments (int) is the number of elements of the List of experiments string array
        -- List of experiments (1D array string) returns the list of experiments available in the Pattern section. The size of each string item comes right before it as integer 32
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("FolMe.PSExpGet", [], [], ["H", "i", "i", "*+c"])

    def FolMe_PSExpSet(self, Point_And_Shoot_experiment):
        """
        FolMe.PSExpSet
        Sets the Point & Shoot experiment selected in Follow Me mode.
        Arguments:
        -- Point & Shoot experiment (unsigned int16) returns the selected Point & Shoot experiment
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("FolMe.PSExpSet", [Point_And_Shoot_experiment], ["H"], [])

    def FolMe_PSPropsGet(self):
        """
        FolMe.PSPropsGet
        Returns the Point & Shoot configuration in Follow Me mode.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Auto resume (unsigned int32) returns if the scan resumes after running the experiment (_1) or if it remains paused (_0)
        -- Use own basename (unsigned int32) returns if the file basename is the one defined in the experiment module (i.e. in Bias Spectroscopy) (_1) or if it uses the basename configured in Point & Shoot (_0)
        -- Basename size (int) is the size in bytes of the Basename string
        -- Basename (string) returns the basename defined in Point & Shoot
        -- External VI path size (int) is the size in bytes of the External VI path string
        -- External VI path (string) returns the path of the External VI selected in Point & Shoot
        -- Pre-measure delay (s) (float32) is the time to wait on each point before performing the experiment
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("FolMe.PSPropsGet", [], [], ["I", "I", "i", "*-c", "i", "*-c", "f"])

    def FolMe_PSPropsSet(self, Auto_resume, Use_own_basename, Basename,
                         External_VI_path, Pre_measure_delay_s):
        """
        FolMe.PSPropsSet
        Sets the Point & Shoot configuration in Follow Me mode.
        Arguments:
        -- Auto resume (unsigned int32) sets if the scan resumes after running the experiment (_1) or if it remains paused (_2). A value_0 means no change.
        -- Use own basename (unsigned int32) sets if the file basename is the one defined in the experiment module (i.e. in Bias Spectroscopy) (_1) or if it uses the basename configured in Point & Shoot (_2). A value_0 means no change.
        -- Basename size (int) is the size in bytes of the Basename string
        -- Basename (string) sets the basename in Point & Shoot
        -- External VI path size (int) is the size in bytes of the External VI path string
        -- External VI path (string) sets the path of the External VI selected in Point & Shoot
        -- Pre-measure delay (s) (float32) is the time to wait on each point before performing the experiment
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        Tip Move Recorder
        """
        return self.quickSend("FolMe.PSPropsSet",
                              [Auto_resume, Use_own_basename, Basename,
                               External_VI_path, Pre_measure_delay_s], ["I", "I", "+*c", "+*c", "f"], [])

    def TipRec_BufferSizeSet(self, Buffer_size):
        """
        TipRec.BufferSizeSet
        Sets the buffer size of the Tip Move Recorder. This function clears the graph.
        Arguments:
        -- Buffer size (int) is the number of data elements in the Tip Move Recorder
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("TipRec.BufferSizeSet", [Buffer_size], ["i"], [])

    def TipRec_BufferSizeGet(self):
        """
        TipRec.BufferSizeGet
        Returns the buffer size of the Tip Move Recorder.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Buffer size (int) is the number of data elements in the Tip Move Recorder
        -- Error described in the Response message&gt;Body section
        
        
        
        
        """
        return self.quickSend("TipRec.BufferSizeGet", [], [], ["i"])

    def TipRec_BufferClear(self):
        """
        TipRec.BufferClear
        Clears the buffer of the Tip Move Recorder.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("TipRec.BufferClear", [], [], [])

    def TipRec_DataGet(self):
        """
        TipRec.DataGet
        Returns the indexes and values of the channels acquired while the tip is moving in Follow Me mode (displayed in the Tip Move Recorder).
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Number of channels (int) is the number of recorded channels. It defines the size of the Channel indexes array
        -- Channel indexes (1D array int) are the indexes of recorded channels. The indexes are comprised between 0 and 23 for the 24 signals assigned in the Signals Manager.
        To get the signal name and its corresponding index in the list of the 128 available signals in the Nanonis Controller, use the <i>Signals.InSlotsGet</i> function
        -- Data rows (int) defines the number of rows of the Data array
        -- Data columns (int) defines the number of columns of the Data array
        -- Data (2D array float32) returns the recorded data while moving the tip 
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("TipRec.DataGet", [], [], ["i", "*i", "i", "i", "2f"])

    def TipRec_DataSave(self, Clear_buffer, Basename):
        """
        TipRec.DataSave
        Saves the data acquired in Follow Me mode (displayed in the Tip Move Recorder) to a file.
        Arguments: 
        -- Clear buffer (unsigned int32) clears the buffer after saving the data. 0 means Off, and 1 means On
        -- Basename size (int) is the number of bytes of the Basename string
        -- Basename (string) defines the basename of the file where the data are saved. If empty, the basename will be the one used in the last save operation
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        Pattern
        """
        return self.quickSend("TipRec.DataSave", [Clear_buffer, Basename], ["I", "+*c"], [])

    def Pattern_ExpOpen(self):
        """
        Pattern.ExpOpen
        Opens the selected grid experiment.
        This is required to configure the experiment and be able to start it.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Pattern.ExpOpen", [], [], [])

    def Pattern_ExpStart(self, Pattern):
        """
        Pattern.ExpStart
        Starts the selected grid experiment.
        Before using this function, select the experiment through <i>Pattern.PropsSet</i>, and be sure to have it open in the software or through the function <i>Pattern.ExpOpen</i>. Otherwise it will give an error saying that the experiment has not been configured yet.
        Arguments: 
        -- Pattern (unsigned int16) switches the active pattern to this value before starting the grid experiment. 0 means no change, 1 means Grid, 2 means Line, and 3 means Cloud
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Pattern.ExpStart", [Pattern], ["H"], [])

    def Pattern_ExpPause(self, Pause_Resume):
        """
        Pattern.ExpPause
        Pauses or resumes the selected grid experiment.
        Arguments: 
        -- Pause/Resume (unsigned int32) where 1 means Pause and 0 means Resume
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Pattern.ExpPause", [Pause_Resume], ["I"], [])

    def Pattern_ExpStop(self):
        """
        Pattern.ExpStop
        Stops the selected grid experiment.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Pattern.ExpStop", [], [], [])

    def Pattern_ExpStatusGet(self):
        """
        Pattern.ExpStatusGet
        Returns the status of the selected grid experiment.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Status (unsigned int32) indicates if the experiment is running (_1) or not (_0)
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Pattern.ExpStatusGet", [], [], ["I"])

    def Pattern_GridSet(self, Set_active_pattern, Number_of_points_in_X, Number_of_points_in_Y, Grid_Scan_frame,
                        Center_X_m, Center_Y_m, Width_m, Height_m, Angle_deg):
        """
        Pattern.GridSet
        Sets the grid size parameters.
        Arguments:
        -- Set active pattern (unsigned int32) defines if the pattern switches to Grid, in case it was not Grid already. 0 means Off, and 1 means On
        -- Number of points in X (int) is the number of points in X that defines the grid
        -- Number of points in Y (int) is the number of points in Y that defines the grid
        -- Grid_Scan frame (unsigned int32) defines if the grid size should be set like the scan frame size. 0 means No, and 1 means Yes
        -- Center X (m) (float32) is the X coordinate of the center of the grid
        -- Center Y (m) (float32) is the Y coordinate of the center of the grid
        -- Width (m) (float32) is the width of the grid
        -- Height (m) (float32) is the height of the grid
        -- Angle (deg) (float32) is the rotation angle of the grid
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Pattern.GridSet",
                              [Set_active_pattern, Number_of_points_in_X, Number_of_points_in_Y, Grid_Scan_frame,
                               Center_X_m, Center_Y_m, Width_m, Height_m, Angle_deg],
                              ["I", "i", "i", "I", "f", "f", "f", "f", "f"], [])

    def Pattern_GridGet(self):
        """
        Pattern.GridGet
        Returns the grid size parameters.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Number of points in X (int) is the number of points in X that defines the grid
        -- Number of points in Y (int) is the number of points in Y that defines the grid
        -- Center X (m) (float32) is the X coordinate of the center of the grid
        -- Center Y (m) (float32) is the Y coordinate of the center of the grid
        -- Width (m) (float32) is the width of the grid
        -- Height (m) (float32) is the height of the grid
        -- Angle (deg) (float32) is the rotation angle of the grid
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Pattern.GridGet", [], [], ["i", "i", "f", "f", "f", "f", "f"])

    def Pattern_LineSet(self, Set_active_pattern, Number_of_points, Line_Scan_frame, Line_Point_1_X_m, Line_Point_1_Y_m,
                        Line_Point_2_X_m, Line_Point_2_Y_m):
        """
        Pattern.LineSet
        Sets the line size parameters.
        Arguments:
        -- Set active pattern (unsigned int32) defines if the pattern switches to Line, in case it was not Line already. 0 means Off, and 1 means On
        -- Number of points (int) is the number of points that defines the line
        -- Line_Scan frame (unsigned int32) defines if the line size should be set equal to the scan frame diagonal. 0 means No, and 1 means Yes
        -- Line Point 1 X (m) (float32) is the X coordinate of one of the two points that define the line
        -- Line Point 1 Y (m) (float32) is the Y coordinate of one of the two points that define the line
        -- Line Point 2 X (m) (float32) is the X coordinate of one of the two points that define the line
        -- Line Point 2 Y (m) (float32) is the Y coordinate of one of the two points that define the line
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Pattern.LineSet",
                              [Set_active_pattern, Number_of_points, Line_Scan_frame, Line_Point_1_X_m,
                               Line_Point_1_Y_m, Line_Point_2_X_m, Line_Point_2_Y_m],
                              ["I", "i", "I", "f", "f", "f", "f"], [])

    def Pattern_LineGet(self):
        """
        Pattern.LineGet
        Returns the line size parameters.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Number of points (int) is the number of points that defines the line
        -- Line Point 1 X (m) (float32) is the X coordinate of one of the two points that define the line
        -- Line Point 1 Y (m) (float32) is the Y coordinate of one of the two points that define the line
        -- Line Point 2 X (m) (float32) is the X coordinate of one of the two points that define the line
        -- Line Point 2 Y (m) (float32) is the Y coordinate of one of the two points that define the line
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Pattern.LineGet", [], [], ["i", "f", "f", "f", "f"])

    def Pattern_CloudSet(self, Set_active_pattern, Number_of_points, X_coordinates_m, Y_coordinates_m):
        """
        Pattern.CloudSet
        Configures a cloud of points.
        Arguments:
        -- Set active pattern (unsigned int32) defines if the pattern switches to Cloud, in case it was not Cloud already. 0 means Off, and 1 means On
        -- Number of points (int) is the number of points in the cloud
        -- X coordinates (m) (1D array float32) is a 1D array of the X coordinates of the points defining the cloud. Prepend the array size as int.
        -- Y coordinates (m) (1D array float32) is a 1D array of the Y coordinates of the points defining the cloud. Prepend the array size as int.
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Pattern.CloudSet",
                              [Set_active_pattern, Number_of_points, X_coordinates_m, Y_coordinates_m],
                              ["I", "i", "*f", "*f"], [])

    def Pattern_CloudGet(self):
        """
        Pattern.CloudGet
        Returns the cloud configuration.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Number of points (int) is the number of points in the cloud, and it defines the size of the 1D arrays for X and Y coordinates
        -- X coordinates (m) (1D array float32) is a 1D array of the X coordinates of the points defining the cloud
        -- Y coordinates (m) (1D array float32) is a 1D array of the Y coordinates of the points defining the cloud
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Pattern.CloudGet", [], [], ["i", "**f", "**f"])

    def Pattern_PropsSet(self, Selected_experiment, Basename,
                         External_VI_path, Pre_measure_delay_s, Save_scan_channels):
        """
        Pattern.PropsSet
        Sets the configuration of the Grid experiment section in the Scan module.
        Arguments: 
        -- Selected experiment size (int) is the number of bytes of the Selected experiment string
        -- Selected experiment (string) is the name of the selected experiment
        -- Basename size (int) is the number of bytes of the Basename string
        -- Basename (string) sets the basename of the saved files
        -- External VI path size (int) is the number of bytes of the External VI path string
        -- External VI path (string) sets the path of the External VI
        -- Pre-measure delay (s) (float32) is the time to wait on each point before performing the experiment
        -- Save scan channels (unsigned int32) sets if the scan channels are saved into the grid experiment file. 0 means Off, and 1 means On
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Pattern.PropsSet",
                              [Selected_experiment, Basename,
                               External_VI_path, Pre_measure_delay_s, Save_scan_channels],
                              ["+*c", "+*c", "+*c", "f", "I"], [])

    def Pattern_PropsGet(self):
        """
        Pattern.PropsGet
        Gets the configuration of the Grid experiment section in the Scan module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Size of the list of experiments (int) is the size in bytes of the List of experiments string array
        -- Number of experiments (int) is the number of elements of the List of experiments string array
        -- List of experiments (1D array string) returns the list of experiments available in the Pattern section. The size of each string item comes right before it as integer 32
        -- Selected experiment size (int) is the number of bytes of the Selected experiment string
        -- Selected experiment (string) returns the name of the selected experiment
        -- External VI path size (int) is the number of bytes of the External VI path string
        -- External VI path (string) returns the path of the External VI
        -- Pre-measure delay (s) (float32) is the time to wait on each point before performing the experiment
        -- Save scan channels (unsigned int32) indicates if the scan channels are saved into the grid experiment file. 0 means Off, and 1 means On
        -- Error described in the Response message&gt;Body section
        
        Marks in Scan
        """
        return self.quickSend("Pattern.PropsGet", [], [], ["i", "i", "*+c", "i", "*-c", "i", "*-c", "f", "I"])

    def Marks_PointDraw(self, X_coordinate_m, Y_coordinate_m, Text, Color):
        """
        Marks.PointDraw
        Draws text at the specified point of the scan frame.
        This function can be very useful to mark an important location in the scan image (i.e. the position where the Tip Shaper executed).
        Arguments: 
        -- X coordinate (m) (float32) defines the X coordinate in meters of the center of the text
        -- Y coordinate (m) (float32) defines the Y coordinate in meters of the center of the text
        -- Text size  (int) is the number of bytes corresponding to the Text to draw
        -- Text (string) sets the character/s to draw
        -- Color (unsigned int32) sets the RGB color of Text
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Marks.PointDraw", [X_coordinate_m, Y_coordinate_m, Text, Color],
                              ["f", "f", "+*c", "I"], [])

    def Marks_PointsDraw(self, nr_points, X_coordinate_m, Y_coordinate_m, Text, Color):
        """
        Marks.PointsDraw
        Draws text at the specified points of the scan frame.
        This function can be very useful to mark important locations in the scan image (i.e. the position where the Tip Shaper executed).
        Arguments: 
        -- Number of points (int) indicates the number of points to draw
        -- X coordinate (m) (1D array float32) defines the X coordinates in meters of the center of the text for the points to draw
        -- Y coordinate (m) (1D array float32) defines the Y coordinates in meters of the center of the text for the points to draw
        -- Text (1D array string) sets the character/s to draw at each point. 
        Each element of the array must be preceded by its size in bytes in Integer 32 (int) format
        -- Color (1D array unsigned int32) sets the RGB colors for the different points to draw
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Marks.PointsDraw", [nr_points, X_coordinate_m, Y_coordinate_m, Text, Color],
                              ["i", "*f", "*f", "+*c", "*I"], [])

    def Marks_LineDraw(self, Start_point_X_coordinate_m, Start_point_Y_coordinate_m, End_point_X_coordinate_m,
                       End_point_Y_coordinate_m, Color):
        """
        Marks.LineDraw
        Draws a line in the scan frame.
        Arguments: 
        -- Start point X coordinate (m) (float32) defines the X coordinate in meters of the starting point of the line
        -- Start point Y coordinate (m) (float32) defines the Y coordinate in meters of the starting point of the line
        -- End point X coordinate (m) (float32) defines the X coordinate in meters of the end point of the line
        -- End point Y coordinate (m) (float32) defines the Y coordinate in meters of the end point of the line
        -- Color (unsigned int32) sets the RGB color of the line
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Marks.LineDraw",
                              [Start_point_X_coordinate_m, Start_point_Y_coordinate_m, End_point_X_coordinate_m,
                               End_point_Y_coordinate_m, Color], ["f", "f", "f", "f", "I"], [])

    def Marks_LinesDraw(self, Number_of_lines, Start_point_X_coordinate_m, Start_point_Y_coordinate_m,
                        End_point_X_coordinate_m, End_point_Y_coordinate_m, Color):
        """
        Marks.LinesDraw
        Draws multiple lines in the scan frame.
        Arguments: 
        -- Number of lines (int) indicates the number of lines to draw
        -- Start point X coordinate (m) (1D array float32) defines the X coordinate in meters of the starting point of each line
        -- Start point Y coordinate (m) (1D array float32) defines the Y coordinate in meters of the starting point of each line
        -- End point X coordinate (m) (1D array float32) defines the X coordinate in meters of the end point of each line
        -- End point Y coordinate (m) (1D array float32) defines the Y coordinate in meters of the end point of each line
        -- Color (1D array unsigned int32) sets the RGB color of each line
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("Marks.LinesDraw",
                              [Number_of_lines, Start_point_X_coordinate_m, Start_point_Y_coordinate_m,
                               End_point_X_coordinate_m, End_point_Y_coordinate_m, Color],
                              ["i", "*f", "*f", "*f", "*f", "*I"], [])

    def Marks_PointsErase(self, Point_index):
        """
        Marks.PointsErase
        Erase the point specified by the index parameter from the scan frame.
        Arguments: 
        -- Point index (int) sets the index of the point to erase. The index is comprised between 0 and the total number of drawn points minus one. To see which point has which index, use the <i>Marks.PointsGet</i> function. Value -1 erases all points.
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Marks.PointsErase", [Point_index], ["i"], [])

    def Marks_LinesErase(self, Line_index):
        """
        Marks.LinesErase
        Erase the line specified by the index parameter from the scan frame.
        Arguments: 
        -- Line index (int) sets the index of the line to erase. The index is comprised between 0 and the total number of drawn lines minus one. To see which line has which index, use the <i>Marks.LinesGet</i> function. Value -1 erases all lines.
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Marks.LinesErase", [Line_index], ["i"], [])

    def Marks_PointsVisibleSet(self, Point_index, Show_hide):
        """
        Marks.PointsVisibleSet
        Show or hide the point specified by the index parameter.
        Arguments: 
        -- Point index (int) sets the index of the point to show or hide. The index is comprised between 0 and the total number of drawn points minus one. To see which point has which index, use the <i>Marks.PointsGet</i> function. Value -1 shows or hides all points.
        -- Show/hide (unsigned int16) defines if the point should be visible (_0) or invisible (_1)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("Marks.PointsVisibleSet", [Point_index, Show_hide], ["i", "H"], [])

    def Marks_LinesVisibleSet(self, Line_index, Show_hide):
        """
        Marks.LinesVisibleSet
        Show or hide the line specified by the index parameter.
        Arguments: 
        -- Line index (int) sets the index of the line to show or hide. The index is comprised between 0 and the total number of drawn lines minus one. To see which line has which index, use the <i>Marks.LinesGet</i> function. Value -1 shows or hides all lines.
        -- Show/hide (unsigned int16) defines if the line should be visible (_0) or invisible (_1)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Marks.LinesVisibleSet", [Line_index, Show_hide], ["i", "H"], [])

    def Marks_PointsGet(self):
        """
        Marks.PointsGet
        Returns the information of the points drawn in the scan frame.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Number of points (int) indicates the number of drawn points. This value is also the size of the 1D arrays returned afterwards
        -- X coordinate (m) (1D array float32) returns the X coordinates in meters of the center of the text for the drawn points
        -- Y coordinate (m) (1D array float32) returns the Y coordinates in meters of the center of the text for the drawn points
        -- Text size (int) is the number of bytes corresponding to the entire Text array
        -- Text (1D array string) returns the text drawn at each point. 
        Each element of the array is preceded by its size in bytes in Integer 32 (int) format
        -- Color (1D array unsigned int32) returns the RGB colors for the different drawn points
        -- Visible (1D array unsigned int32) returns if each point is visible (_1) or invisible (_0) in the scan frame
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("Marks.PointsGet", [], [], ["i", "**f", "**f", "i", "**c", "**I", "**I"])

    def Marks_LinesGet(self):
        """
        Marks.LinesGet
        Returns the information of the lines drawn in the scan frame.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Number of lines (int) indicates the number of drawn lines. This value is also the size of the 1D arrays returned afterwards
        -- Start point X coordinate (m) (1D array float32) returns the X coordinate in meters of the starting point of each line
        -- Start point Y coordinate (m) (1D array float32) returns the Y coordinate in meters of the starting point of each line
        -- End point X coordinate (m) (1D array float32) returns the X coordinate in meters of the end point of each line
        -- End point Y coordinate (m) (1D array float32) returns the Y coordinate in meters of the end point of each line
        -- Color (1D array unsigned int32) returns the RGB colors for the different drawn lines
        -- Visible (1D array unsigned int32) returns if each line is visible (_1) or invisible (_0) in the scan frame
        -- Error described in the Response message&gt;Body section
        
        Tip Shaper
        """
        return self.quickSend("Marks.LinesGet", [], [], ["i", "**f", "**f", "**f", "**f", "**I", "**I"])

    def MPass_Activate(self, On_Off):
        """
        MPass.Activate
        Activates Multi-Pass in the Scan Control module.
        Arguments:

        - On/Off(unsigned int32) defines if this function activates (1=On) Multi-Pass in the Scan Control module

        Return arguments (if Send response back flag is set to True when sending request message):
        - Error described in the Response message>Body section
        """
        return self.quickSend("MPass.Activate", [On_Off], ["I"], [])

    def MPass_Load(self, File_Path):
        """
        MPass.Load
        Loads a Multi-Pass configuration file (.mpas) in the Multi-Pass Configuration module.
        Arguments:

        - File path size (int) is the number of characters of the File path string
        - File path (string) is the path of the .mpas file to load. When leaving it empty, Multi-Pass loads the
        configuration saved in the Session settings file, if there is any.

        Return arguments (if Send response back flag is set to True when sending request message):
        - Error described in the Response message>Body section
        """
        return self.quickSend("MPass.Load", [File_Path], ["+*c"], [])

    def MPass_Save(self, File_Path):
        """
        MPass.Save
        Saves the current configuration in the Multi-Pass Configuration module into a Multi-Pass configuration file (.mpas).
         Arguments:

        - File path size (int) is the number of characters of the File path string
        - File path (string) is the path of the .mpas file to save. When leaving it empty, Multi-Pass saves the
        configuration into the Session settings file.

        Return arguments (if Send response back flag is set to True when sending request message):

        - Error described in the Response message>Body section
        """
        return self.quickSend("MPass.Save", [File_Path], ["+*c"], [])

    def TipShaper_Start(self, Wait_until_finished, Timeout_ms):
        """
        TipShaper.Start
        Starts the tip shaper procedure.
        Arguments:
        -- Wait until finished (unsigned int32) defines if this function waits (1_True) until the Tip Shaper procedure stops.
        -- Timeout (ms) (int) sets the number of milliseconds to wait if Wait until Finished is set to True. 
        A value equal to -1 means waiting forever.
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("TipShaper.Start", [Wait_until_finished, Timeout_ms], ["I", "i"], [])

    def TipShaper_PropsSet(self, Switch_Off_Delay, Change_Bias, Bias_V, Tip_Lift_m, Lift_Time_1_s, Bias_Lift_V,
                           Bias_Settling_Time_s, Lift_Height_m, Lift_Time_2_s, End_Wait_Time_s, Restore_Feedback):
        """
        TipShaper.PropsSet
        Sets the configuration of the tip shaper procedure.
        Arguments:
        -- Switch Off Delay (float32) is the time during which the Z position is averaged right before switching the Z-Controller off.
        -- Change Bias (unsigned int32) decides whether the Bias value is applied (0_no change, 1_True, 2_False) right before the first Z ramping.
        -- Bias (V) (float32) is the value applied to the Bias signal if Change Bias is True.
        -- Tip Lift (m) (float32) defines the relative height the tip is going to ramp for the first time (from the current Z position).
        -- Lift Time 1 (s) (float32) defines the time to ramp Z from the current Z position by the Tip Lift amount.
        -- Bias Lift (V) (float32) is the Bias voltage applied just after the first Z ramping.
        -- Bias Settling Time (s) (float32) is the time to wait after applying the Bias Lift value, and it is also the time to wait after applying Bias (V) before ramping Z for the first time.
        -- Lift Height (m) (float32) defines the height the tip is going to ramp for the second time.
        -- Lift Time 2 (s) (float32) is the given time to ramp Z in the second ramping.
        -- End Wait Time (s) (float32) is the time to wait after restoring the initial Bias voltage (just after finishing the second ramping).
        -- Restore Feedback (unsigned int32) defines whether the initial Z-Controller status is restored (0_no change, 1_True, 2_False) at the end of the tip shaper procedure.
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("TipShaper.PropsSet",
                              [Switch_Off_Delay, Change_Bias, Bias_V, Tip_Lift_m, Lift_Time_1_s, Bias_Lift_V,
                               Bias_Settling_Time_s, Lift_Height_m, Lift_Time_2_s, End_Wait_Time_s, Restore_Feedback],
                              ["f", "I", "f", "f", "f", "f", "f", "f", "f", "f", "I"], [])

    def TipShaper_PropsGet(self):
        """
        TipShaper.PropsGet
        Returns the configuration of the tip shaper procedure.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Switch Off Delay (float32) is the time during which the Z position is averaged right before switching the Z-Controller off.
        -- Change Bias (unsigned int32) returns whether the Bias value is applied (0_False, 1_True) right before the first Z ramping.
        -- Bias (V) (float32) is the value applied to the Bias signal if Change Bias is True.
        -- Tip Lift (m) (float32) returns the relative height the tip is going to ramp for the first time (from the current Z position).
        -- Lift Time 1 (s) (float32) returns the time to ramp Z from the current Z position by the Tip Lift amount.
        -- Bias Lift (V) (float32) is the Bias voltage applied just after the first Z ramping.
        -- Bias Settling Time (s) (float32) is the time to wait after applying the Bias Lift value, and it is also the time to wait after applying Bias (V) before ramping Z for the first time.
        -- Lift Height (m) (float32) returns the height the tip is going to ramp for the second time.
        -- Lift Time 2 (s) (float32) is the given time to ramp Z in the second ramping.
        -- End Wait Time (s) (float32) is the time to wait after restoring the initial Bias voltage (just after finishing the second ramping).
        -- Restore Feedback (unsigned int32) returns whether the initial Z-Controller status is restored (0_False, 1_True) at the end of the tip shaper procedure.
        -- Error described in the Response message&gt;Body section
        
        Coarse Motion
        """
        return self.quickSend("TipShaper.PropsGet", [], [], ["f", "I", "f", "f", "f", "f", "f", "f", "f", "f", "I"])

    def Motor_StartMove(self, Direction, Number_of_steps, Group, Wait_until_finished):
        """
        Motor.StartMove
        Moves the coarse positioning device (motor, piezo actuator…).
        Arguments:
        -- Direction (unsigned int32) selects in which direction to move. Note that depending on your motor controller and setup only the Z axis or even only Z- may work. 
        Valid values are 0_X+, 1_X-, 2_Y+, 3_Y-, 4_Z+, 5_Z-
        -- Number of steps (unsigned int16) defines the number of steps to move in the specified direction
        -- Group (unsigned int32) is the selection of the groups defined in the motor control module. If the motor doesn’t support the selection of groups, set it to 0. 
        Valid values are 0_Group 1, 1_Group 2, 2_Group 3, 3_Group 4, 4_Group 5, 5_Group 6
        -- Wait until finished (unsigned int32) defines if this function only returns (1_True) when the motor reaches its destination or the movement stops
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Motor.StartMove", [Direction, Number_of_steps, Group, Wait_until_finished],
                              ["I", "H", "I", "I"], [])

    def Motor_StartClosedLoop(self, Absolute_relative, Target_Xm, Target_Ym, Target_Zm, Wait_until_finished):
        """
        Motor.StartClosedLoop
        Moves the coarse positioning device (motor, piezo actuator…) in closed loop. This is not supported by all motor control modules.
        Arguments:
        -- Absolute/relative (unsigned int32) selects if moving in relative (0_rel) or in absolute (1_abs) movement
        -- Target X(m) (float64) is the X target position to move in meters
        -- Target Y(m) (float64) is the Y target position to move in meters
        -- Target Z(m) (float64) is the Z target position to move in meters
        -- Wait until finished (unsigned int32) defines if this function only returns (1_True) when the motor reaches its destination or the movement stops
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        <font size_"24">
        """
        return self.quickSend("Motor.StartClosedLoop",
                              [Absolute_relative, Target_Xm, Target_Ym, Target_Zm, Wait_until_finished],
                              ["I", "d", "d", "d", "I"], [])

    def Motor_StopMove(self):
        """
        Motor.StopMove
        Stops the motor motion.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Motor.StopMove", [], [], [])

    def Motor_PosGet(self):
        """
        Motor.PosGet
        Returns the positions of the motor control module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- X(m) (float64) is the X position in meters
        -- Y(m) (float64) is the Y position in meters
        -- Z(m) (float64) is the Z position in meters
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Motor.PosGet", [], [], ["d", "d", "d"])

    def Motor_StepCounterGet(self, Reset_X, Reset_Y, Reset_Z):
        """
        Motor.StepCounterGet
        Returns the step counter values of X, Y, and Z.
        This function also allows to reset the step counters after reading their values through the inputs Reset X, Reset Y, and Reset Z.
        Currently this function is only available in Attocube ANC150 devices.
        Arguments: 
        -- Reset X (unsigned int32) resets the Step Counter X after reading its value. 0 means False, and 1 means True
        -- Reset Y (unsigned int32) resets the Step Counter Y after reading its value. 0 means False, and 1 means True
        -- Reset Z (unsigned int32) resets the Step Counter Z after reading its value. 0 means False, and 1 means True
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Step counter X (int)
        -- Step counter Y (int)
        -- Step counter Z (int)
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("Motor.StepCounterGet", [Reset_X, Reset_Y, Reset_Z], ["I", "I", "I"], ["i", "i", "i"])

    def Motor_FreqAmpGet(self):
        """
        Motor.FreqAmpGet
        Returns the frequency (Hz) and amplitude (V) of the motor control module.
        This function is only available for PD5, PMD4, and Attocube ANC150 devices.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Frequency (Hz) (float32) 
        -- Amplitude (V) (float32) 
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Motor.FreqAmpGet", [], [], ["f", "f"])

    def Motor_FreqAmpSet(self, Frequency_Hz, Amplitude_V, Axis):
        """
        Motor.FreqAmpSet
        Sets the frequency (Hz) and amplitude (V) of the motor control module.
        This function is only available for PD5, PMD4, and Attocube ANC150 devices.
        Arguments: 
        -- Frequency (Hz) (float32) 
        -- Amplitude (V) (float32) 
        -- Axis (unsigned int16) defines which axis these parameters will be applied to. 0 means All, 1 means X, 2 means Y, 3 means Z
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        
        
        Generic Sweeper
        """
        return self.quickSend("Motor.FreqAmpSet", [Frequency_Hz, Amplitude_V, Axis], ["f", "f", "H"], [])

    def GenSwp_AcqChsSet(self, Channel_indexes: list, Channel_names: list):
        """
        GenSwp.AcqChsSet
        Sets the list of recorded channels of the Generic Sweeper.
        Arguments: 
        -- Number of channels (int) is the number of recorded channels. It defines the size of the Channel indexes array
        -- Channel indexes (1D array int) are the indexes of recorded channels. The indexes correspond to the list of Measurement in the Nanonis software.
        To get the Measurements  names use the <i>Signals.MeasNamesGet </i>function
        --Channel names size (int) is the size in bytes of the channel names array. These are the names of the recorded channels
        -- Channel names number (int) is the number of elements of the channel names array
        -- Channel names (1D array string) is an array of channel names strings, where each string comes prepended by its size in bytes
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("GenSwp.AcqChsSet", [Channel_indexes, Channel_names], ["+*i", "*+c"], [])

    def GenSwp_AcqChsGet(self):
        """
        GenSwp.AcqChsGet
        Returns the list of recorded channels of the Generic Sweeper.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Number of channels (int) is the number of recorded channels. It defines the size of the Channel indexes array
        -- Channel indexes (1D array int) are the indexes of the recorded channels. The indexes correspond to the list of Measurement in the Nanonis software.
        To get the Measurements  names use the <i>Signals.MeasNamesGet </i>function
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("GenSwp.AcqChsGet", [], [], ["i", "*i"])

    def GenSwp_SwpSignalSet(self, Sweep_channel_name):
        """
        GenSwp.SwpSignalSet
        Sets the Sweep signal in the Generic Sweeper.
        Arguments: 
        -- Sweep channel name size (int) is the number of characters of the sweep channel name string
        -- Sweep channel name (string) is the name of the signal selected for the sweep channel
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("GenSwp.SwpSignalSet", [Sweep_channel_name], ["+*c"], [])

    def GenSwp_SwpSignalGet(self):
        """
        GenSwp.SwpSignalGet
        Returns the selected Sweep signal in the Generic Sweeper.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Sweep channel name size (int) is the number of characters of the sweep channel name string
        -- Sweep channel name (string) is the name of the signal selected for the sweep channel
        -- Channels names size (int) is the size in bytes of the Channels names string array
        -- Number of channels (int) is the number of elements of the Channels names string array
        -- Channels names (1D array string) returns the list of channels names. The size of each string item comes right before it as integer 32
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("GenSwp.SwpSignalGet", [], [], ["i", "*-c", "i", "i", "*+c"])

    def GenSwp_LimitsSet(self, Lower_limit, Upper_limit):
        """
        GenSwp.LimitsSet
        Sets the limits of the Sweep signal in the Generic Sweeper.
        Arguments: 
        -- Lower limit (float32) defines the lower limit of the sweep range
        -- Upper limit (float32) defines the upper limit of the sweep range
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("GenSwp.LimitsSet", [Lower_limit, Upper_limit], ["f", "f"], [])

    def GenSwp_LimitsGet(self):
        """
        GenSwp.LimitsGet
        Returns the limits of the Sweep signal in the Generic Sweeper.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Lower limit (float32) defines the lower limit of the sweep range
        -- Upper limit (float32) defines the upper limit of the sweep range
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("GenSwp.LimitsGet", [], [], ["f", "f"])

    def GenSwp_PropsSet(self, Initial_Settling_time_ms, Maximum_slew_rate_units_s, Number_of_steps, Period_ms,
                        Autosave, Save_dialog_box, Settling_time_ms):
        """
        GenSwp.PropsSet
        Sets the configuration of the parameters in the Generic Sweeper.
        Arguments: 
        -- Initial Settling time (ms) (float32) 
        -- Maximum slew rate (units/s) (float32) 
        -- Number of steps (int) defines the number of steps of the sweep. 0 points means no change
        -- Period (ms) (unsigned int16) where 0 means no change
        -- Autosave (int) defines if the sweep is automatically saved, where -1_no change, 0_Off, 1_On
        -- Save dialog box (int) defines if the save dialog box shows up or not, where -1_no change, 0_Off, 1_On
        -- Settling time (ms) (float32) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("GenSwp.PropsSet",
                              [Initial_Settling_time_ms, Maximum_slew_rate_units_s, Number_of_steps, Period_ms,
                               Autosave, Save_dialog_box, Settling_time_ms], ["f", "f", "i", "H", "i", "i", "f"], [])

    def GenSwp_PropsGet(self):
        """
        GenSwp.PropsGet
        Returns the configuration of the parameters in the Generic Sweeper.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Initial Settling time (ms) (float32) 
        -- Maximum slew rate (units/s) (float32) 
        -- Number of steps (int) defines the number of steps of the sweep
        -- Period (ms) (unsigned int16) 
        -- Autosave (unsigned int32) defines if the sweep is automatically saved, where 0_Off, 1_On
        -- Save dialog box (unsigned int32) defines if the save dialog box shows up or not, where 0_Off, 1_On
        -- Settling time (ms) (float32) 
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("GenSwp.PropsGet", [], [], ["f", "f", "i", "H", "I", "I", "f"])

    def GenSwp_Start(self, Get_data, Sweep_direction, Save_base_name, Reset_signal, Z_Controller):
        """
        GenSwp.Start
        Starts the sweep in the Generic Sweeper.
        Arguments: 
        -- Get data (unsigned int32) defines if the function returns the sweep data (1_True) or not (0_False) 
        -- Sweep direction (unsigned int32) defines if the sweep starts from the lower limit (_1) or from the upper limit (_0)
        -- Save base name string size (int) defines the number of characters of the Save base name string
        -- Save base name (string) is the basename used by the saved files. If empty string, there is no change
        -- Reset signal (unsigned int32) where 0_Off, 1_On
        -- Z-Controller (unsigned int16) where 0=no change, 1=turn off, 2=don’t turn off
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Channels names size (int) is the size in bytes of the Channels names string array
        -- Number of channels (int) is the number of elements of the Channels names string array
        -- Channels names (1D array string) returns the list of channels names. The size of each string item comes right before it as integer 32
        -- Data rows (int) defines the numer of rows of the Data array
        -- Data columns (int) defines the numer of columns of the Data array
        -- Data (2D array float32) returns the sweep data
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("GenSwp.Start",
                              [Get_data, Sweep_direction, Save_base_name, Reset_signal, Z_Controller],
                              ["I", "I", "+*c", "I", "H"], ["i", "i", "*+c", "i", "i", "2f"])

    def GenSwp_Stop(self):
        """
        GenSwp.Stop
        Stops the sweep in the Generic Sweeper module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("GenSwp.Stop", [], [], [])

    def GenSwp_Open(self):
        """
        GenSwp.Open
        Opens the Generic Sweeper module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("GenSwp.Open", [], [], [])

    def HSSwp_AcqChsSet(self, Channel_Indexes:list):
        """
        HSSwp.AcqChsSet
        Sets the list of recorded channels of the High-Speed Sweeper.

        Arguments:

        - Number of channels (int) is the number of recorded channels. It defines the size of the Channel indexes array
        - Channel indexes (1D array int) are the indexes of recorded channels.
        To obtain a list of the available channels, use the HSSwp.AcqChsGet function.

        Return arguments (if Send response back flag is set to True when sending request message):

        - Error described in the Response message>Body section

        """
        return self.quickSend("HSSwp.AcqChsSet", [Channel_Indexes], ["+*i"], [])

    def HSSwp_AcqChsGet(self):
        """
        HSSwp.AcqChsGet
        Returns the list of recorded channels of the High-Speed Sweeper.

        Arguments: None

        Return arguments (if Send response back flag is set to True when sending request message):

        - Number of channels (int) is the number of recorded channels. It defines the size of the Channel indexes array
        - Channel indexes (1D array int) are the indexes of the recorded channels. The indexes correspond to the indices in the Available Channels indexes array.
        - Available Channels names size (int) is the size in bytes of the available channels names array
        - Available Channels names number (int) is the number of elements of the available channels names array
        - Available Channels names (1D array string) returns an array of channel names strings, where each string
        comes prepended by its size in bytes
        - Number of available channels (int) is the number of available channels. It defines the size of the
        Available Channels indexes array
        - Available Channels indexes (1D array int) are the indexes of channels available for acquisition.
        - Error described in the Response message>Body section
        """
        return self.quickSend("HSSwp.AcqChsGet", [], [], ["i", "*I", "i", "i", "*+c", "i", "*i"])

    def HSSwp_AutoReverseSet(self, OnOff, Condition, Signal, Threshold, LinkToOne, Condition2, Signal2, Threshold2):
        """
        HSSwp.AutoReverseSet
        Sets the auto-reverse configuration of the sweep axis in the High-Speed Sweeper.

        Arguments:

        - On/Off (int) defines if the auto-reverse functionality is on or off, where 0=Off, 1=On
        - Condition (int) defines if the signal must be greater or less than the threshold for the reverse condition to
        activate, where 0 = >, 1 = <
        - Signal (int) sets the signal for the reverse condition. The list of available signals is the same as the
        acquisition signals (see HSSwp.AcqChsGet function).
         - Threshold (float32) defines the threshold to which the signal is compared.
        - Linkage to 1 (int) defines the linkage of the 2nd reverse condition to the first condition. Possible values: 0 =
        Off (no 2nd condition), 1 = OR (condition 1 or 2 must be met), 2 = AND (conditions 1 and 2 must be met at
        the same time), 3 = THEN (condition 1 must be met first, then condition 2).
        - Condition 2 (int) defines if the signal must be greater or less than the threshold for the 2nd reverse condition
        to activate, where 0 = >, 1 = <
        - Signal 2 (int) sets the signal for the 2nd reverse condition. The list of available signals is the same as the
        acquisition signals (see HSSwp.AcqChsGet function).
        - Threshold 2 (float32) defines the threshold to which the signal 2 is compared.

        Return arguments (if Send response back flag is set to True when sending request message):

        - Error described in the Response message>Body section

        """
        return self.quickSend("HSSwp.AutoReverseSet",
                              [OnOff, Condition, Signal, Threshold, LinkToOne, Condition2, Signal2, Threshold2],
                              ["i", "i", "i", "f", "i", "i", "i", "f"], [])

    def HSSwp_AutoReverseGet(self):
        """
        HSSwp.AutoReverseGet
        Returns the auto-reverse configuration of the sweep axis in the High-Speed Sweeper.

        Arguments: None

        Return arguments (if Send response back flag is set to True when sending request message):

        - On/Off (int) specifies if the auto-reverse functionality is on or off, where 0=Off, 1=On
        - Condition (int) specifies if the signal must be greater or less than the threshold for the reverse condition to
        activate, where 0 = >, 1 = <
        - Signal (int) is the signal for the reverse condition. The list of available signals is the same as the acquisition
        signals (see HSSwp.AcqChsGet function).
        - Threshold (float32) is the threshold to which the signal is compared.
        - Linkage to 1 (int) specifies the linkage of the 2nd reverse condition to the first condition. Possible values: 0
        = Off (no 2nd condition), 1 = OR (condition 1 or 2 must be met), 2 = AND (conditions 1 and 2 must be met
        at the same time), 3 = THEN (condition 1 must be met first, then condition 2).
        - Condition 2 (int) specifies if the signal must be greater or less than the threshold for the 2nd reverse
        condition to activate, where 0 = >, 1 = <
        - Signal 2 (int) is the signal for the 2nd reverse condition. The list of available signals is the same as the
        acquisition signals (see HSSwp.AcqChsGet function).
        - Threshold 2 (float32) is the threshold to which the signal 2 is compared.
        - Error described in the Response message>Body section
        """
        return self.quickSend("HSSwp.AutoReverseGet", [], [], ["i", "i", "i", "f", "i", "i", "i", "f"])

    def HSSwp_EndSettlSet(self, Threshold):
        """
        HSSwp.EndSettlSet
        Sets the end settling time in the High-Speed Sweeper.

        Arguments:

        - Threshold (float32) defines the end settling time in seconds

        Return arguments (if Send response back flag is set to True when sending request message):

        - Error described in the Response message>Body section
        """
        return self.quickSend("HSSwp.EndSettlSet", [Threshold], ["f"], [])

    def HSSwp_EndSettlGet(self):
        """
        HSSwp.EndSettlGet
        Returns the end settling time in the High-Speed Sweeper.

        Arguments: None

        Return arguments (if Send response back flag is set to True when sending request message):

        - Threshold (float32) is the end settling time in seconds
        - Error described in the Response message>Body section
        """
        return self.quickSend("HSSwp.EndSettlGet", [], [], ["f"])

    def HSSwp_NumSweepsSet(self, Number_Of_Sweeps, Continuous):
        """
        HSSwp.NumSweepsSet
        Sets the number of sweeps in the High-Speed Sweeper.

        Arguments:
        - Number of sweeps (unsigned int32) sets the number of sweeps (ignored when continuous is set)
        - Continuous (int) sets the continuous sweep mode, where 0=Off, 1=On

        Return arguments (if Send response back flag is set to True when sending request message):

        - Error described in the Response message>Body section
        """
        return self.quickSend("HSSwp.NumSweepsSet", [Number_Of_Sweeps, Continuous], ["I", "i"], [])

    def HSSwp_NumSweepsGet(self):
        """
        HSSwp.NumSweepsGet
        Returns the number of sweeps in the High-Speed Sweeper.

        Arguments: None

        Return arguments (if Send response back flag is set to True when sending request message):

        - Number of sweeps (unsigned int32) is the number of sweeps
        - Continuous (int) specifies the continuous sweep mode, where 0=Off, 1=On
        - Error described in the Response message>Body section
        """
        return self.quickSend("HSSwp.NumSweepsGet", [], [], ["I", "i"])

    def HSSwp_ResetSignalsSet(self, ResetSignals):
        """
        HSSwp.ResetSignalsSet
        Specifies if the sweep and step signals should be reset to their initial values at the end of the sweep in the High- Speed Sweeper.

        Arguments:

        - Reset Signals (int) defines if the sweep and step signals are reset at the end of the sweep, where 0=Off, 1=On

        Return arguments (if Send response back flag is set to True when sending request message):

         - Error described in the Response message>Body section
        """
        return self.quickSend("HSSwp.ResetSignalsSet", [ResetSignals], ["i"], [])

    def HSSwp_ResetSignalsGet(self):
        """
        HSSwp.ResetSignalsGet
        Returns if the sweep and step signals are reset to their initial values at the end of the sweep in the High-Speed Sweeper.

        Arguments: None

        Return arguments (if Send response back flag is set to True when sending request message):

        - Reset Signals (int) returns if the sweep and step signals are reset at the end of the sweep, where 0=Off, 1=On
        - Error described in the Response message>Body section
        """
        return self.quickSend("HSSwp.ResetSignalsGet", [], [], ["i"])

    def HSSwp_SaveBasenameSet(self, Basename):
        """
        HSSwp.SaveBasenameSet
        Sets the save basename in the High-Speed Sweeper.

        Arguments:

        - Basename size (int) is the size (number of characters) of the basename string
        - Basename (string) is the base name used for the saved sweeps

        Return arguments (if Send response back flag is set to True when sending request message to the server):

        - Error described in the Response message>Body section
        """
        return self.quickSend("HSSwp.SaveBasenameSet", [Basename], ["+*c"], [])

    def HSSwp_SaveBasenameGet(self):
        """

        HSSwp.SaveBasenameGet
        Returns the save basename in the High-Speed Sweeper.

        Arguments: None

        Return arguments (if Send response back flag is set to True when sending request message to the server):

        - Basename size (int) is the size (number of characters) of the basename string
        - Basename (string) is the base name used for the saved sweeps
        - Error described in the Response message>Body section

        """
        return self.quickSend("HSSwp.SaveBasenameGet", [], [], ["i", "*-c"])

    def HSSwp_SaveDataSet(self, SaveData):
        """
        HSSwp.SaveDataSet

        Specifies if the data acquired in the High-Speed Sweeper is saved or not.

        Arguments:

        - Save Data (int) defines if the data is saved, where 0=Off, 1=On

         Return arguments (if Send response back flag is set to True when sending request message):

         - Error described in the Response message>Body section
        """
        return self.quickSend("HSSwp.SaveDataSet", [SaveData], ["i"], [])

    def HSSwp_SaveDataGet(self):
        """
        HSSwp.SaveDataGet
        Returns if the data acquired in the High-Speed Sweeper is saved or not.

        Arguments: None

        Return arguments (if Send response back flag is set to True when sending request message):

        - Save Data (int) returns if the data is saved, where 0=Off, 1=On
        - Error described in the Response message>Body section
        """
        return self.quickSend("HSSwp.SaveDataGet", [], [], ["i"])

    def HSSwp_SaveOptionsSet(self, Comment, ModulesNames):
        """
        HSSwp.SaveOptionsSet
        Sets save options in the High-Speed Sweeper.

        Arguments:
        - Comment size (int) is the size (number of characters) of the comment string
        - Comment (string) is the comment saved in the header of the files. If empty string, there is no change
        - Modules names size (int) is the size in bytes of the modules array. These are the modules whose
        parameters are saved in the header of the files
        - Modules names number (int) is the number of elements of the modules names array
        - Modules names (1D array string) is an array of modules names strings, where each string comes
        prepended by its size in bytes

        """
        return self.quickSend("HSSwp.SaveOptionsSet", [Comment, ModulesNames], ["+*c", "+*c"], [])

    def HSSwp_SaveOptionsGet(self):
        """
        HSSwp.SaveOptionsGet
        Returns the saving options of the High-Speed Sweeper.

        Arguments: None

        Return arguments (if Send response back flag is set to True when sending request message to the server):

        - Comment size (int) is the size (number of characters) of the comment string
        - Comment (string) is the comment saved in the header of the files
        - Modules parameters size (int) is the size in bytes of the modules parameters array. These are the modules
        parameters saved in the header of the files
        - Modules parameters number (int) is the number of elements of the modules parameters array
        - Modules parameters (1D array string) is an array of modules names strings, where each string comes
        prepended by its size in bytes.
        - Error described in the Response message>Body section
        """
        return self.quickSend("HSSwp.SaveOptionsGet", [], [], ["i", "*-c", "i", "i", "*+c"])

    def HSSwp_Start(self, Wait_Until_Done, Timeout):
        """
        HSSwp.Start
        Starts a sweep in the High-Speed Sweeper module.
        When Send response back is set to True, it returns immediately afterwards.

        Arguments:

        - Wait until done (int) specifies whether the function waits with sending back the return arguments until the sweep is finished, where 0=Off (don’t wait), 1=On (wait)
        - Timeout (int) sets the wait timeout in milliseconds. Use -1 for indefinite wait. The Timeout is ignored when wait until done is off.

        Return arguments (if Send response back flag is set to True when sending request message):

        - Error described in the Response message>Body section
        """
        return self.quickSend("HSSwp.Start", [Wait_Until_Done, Timeout], ["i", "i"], [])

    def HSSwp_Stop(self):
        """
        HSSwp.Stop
        Stops the sweep in the High-Speed Sweeper module.

        Arguments: None

        Return arguments (if Send response back flag is set to True when sending request message):

        - Error described in the Response message>Body section
        """
        return self.quickSend("HSSwp.Stop", [], [], [])

    def HSSwp_StatusGet(self):
        """
        HSSwp.StatusGet
        Returns the status of the High-Speed Sweeper.

        Arguments: None

        Return arguments (if Send response back flag is set to True when sending request message):

        - Status (unsigned int32) is status of the High-Speed Sweeper, where 0=Stopped, 1=Running
        - Error described in the Response message>Body section
        """
        return self.quickSend("HSSwp.StatusGet", [], [], ["I"])

    def HSSwp_SwpChSigListGet(self):
        """
        HSSwp.SwpChSigListGet
        Returns the list of available signals for the Sweep channel of the High-Speed Sweeper.

        Arguments: None

        Return arguments (if Send response back flag is set to True when sending request message to the server):

        - Signal names size (int) is the size in bytes of the signal names array
        - Signal names number (int) is the number of elements of the signal names array
         - Signal names (1D array string) is an array of signal names strings, where each string comes prepended by its size in bytes.
        - Number of signals (int) is the number of available sweep signals. It defines the size of the Available Channels indexes array
        - Signal indexes (1D array int) are the indexes of signals available for the sweep channel.
        - Error described in the Response message>Body section
        """
        return self.quickSend("HSSwp.SwpChSigListGet", [], [], ["+*c", "+*i"])

    def HSSwp_SwpChSignalSet(self, Sweep_Signal_Index, Timed_Sweep):
        """
        HSSwp.SwpChSignalSet
        Sets the Sweep Channel signal in the High-Speed Sweeper.

        Arguments:

        - Sweep signal index (int) is the index of the Sweep Signal. Use the HSSwp.SwpChSigListGet function to obtain a list of available sweep signals.
        - Timed Sweep (int) enables or disables timed sweep mode. When on, the Sweep channel is ignored. 0=Off (sweep signal), 1=On (timed sweep)

        Return arguments (if Send response back flag is set to True when sending request message):

        - Error described in the Response message>Body section
        """
        return self.quickSend("HSSwp.SwpChSignalSet", [Sweep_Signal_Index, Timed_Sweep], ["i", "i"], [])

    def HSSwp_SwpChSignalGet(self):
        """
        HSSwp.SwpChSignalGet
        Returns the Sweep Channel signal in the High-Speed Sweeper.

        Arguments: None

        Return arguments (if Send response back flag is set to True when sending request message):

        - Sweep signal index (int) is the index of the Sweep Signal. Use the HSSwp.SwpChSigListGet function to obtain a list of available sweep signals.
        - Timed Sweep (int) specifies if timed sweep mode is enabled, where 0=Off (sweep signal), 1=On (timed sweep)
        - Error described in the Response message>Body section

        """
        return self.quickSend("HSSwp.SwpChSignalGet", [], [], ["i", "i"])

    def HSSwp_SwpChLimitsSet(self, Relative_Limits, Start, Stop):
        """
        HSSwp.SwpChLimitsSet
        Sets the limits of the Sweep Channel in the High-Speed Sweeper.

        Arguments:

        - Relative Limits (int) specifies if the limits are absolute or relative to the current sweep signal value. Possible values are 0=Absolute limits, 1=Relative limits.
        - Start (float32) defines the value where the sweep starts
        - Stop (float32) defines the value where the sweep stops

        Return arguments (if Send response back flag is set to True when sending request message):

         - Error described in the Response message>Body section
        """
        return self.quickSend("HSSwp.SwpChLimitsSet", [Relative_Limits, Start, Stop], ["i", "f", "f"], [])

    def HSSwp_SwpChLimitsGet(self):
        """
        HSSwp.SwpChLimitsGet
        Returns the limits of the Sweep Channel in the High-Speed Sweeper.

        Arguments: None

        Return arguments (if Send response back flag is set to True when sending request message):

        - Relative Limits (int) specifies if the limits are absolute or relative to the current sweep signal value. Possible values are 0=Absolute limits, 1=Relative limits.
        - Start (float32) defines the value where the sweep starts
        - Stop (float32) defines the value where the sweep stops
        - Error described in the Response message>Body section
        """
        return self.quickSend("HSSwp.SwpChLimitsGet", [], [], ["i", "f", "f"])

    def HSSwp_SwpChNumPtsSet(self, Number_Of_Points):
        """
        HSSwp.SwpChNumPtsSet
        Sets the number of points for the Sweep Channel in the High-Speed Sweeper.

        Arguments:

        - Number of points (unsigned int32) sets the number of points of the sweep.

        Return arguments (if Send response back flag is set to True when sending request message):

        - Error described in the Response message>Body section
        """
        return self.quickSend("HSSwp.SwpChNumPtsSet", [Number_Of_Points], ["I"], [])

    def HSSwp_SwpChNumPtsGet(self):
        """
        HSSwp.SwpChNumPtsGet
        Returns the number of points for the Sweep Channel in the High-Speed Sweeper.

        Arguments: None

        Return arguments (if Send response back flag is set to True when sending request message):

        - Number of points (int) returns the number of points of the sweep
        - Error described in the Response message>Body section

        """
        return self.quickSend("HSSwp.SwpChNumPtsGet", [], [], ["i"])

    def HSSwp_SwpChTimingSet(self, Initial_Settling_Time, Settling_Time, Integration_Time, Max_Slew_Time):
        """
        HSSwp.SwpChTimingSet
        Sets the timing parameters of the Sweep Channel in the High-Speed Sweeper.

        Arguments:

        - Initial settling time (s) (float32)
        - Settling time (s) (float32)
         - Integration time (s) (float32)
        - Maximum slew rate (units/s) (float32)

        Return arguments (if Send response back flag is set to True when sending request message):

        - Error described in the Response message>Body section
        """
        return self.quickSend("HSSwp.SwpChTimingSet", [Initial_Settling_Time, Settling_Time, Integration_Time, Max_Slew_Time],
                              ["f", "f", "f", "f"], [])

    def HSSwp_SwpChTimingGet(self):
        """
        HSSwp.SwpChTimingGet
        Returns the timing parameters of the Sweep Channel in the High-Speed Sweeper.

        Arguments: None

        Return arguments (if Send response back flag is set to True when sending request message):

        - Initial settling time (s) (float32)
        - Settling time (s) (float32)
        - Integration time (s) (float32)
        - Maximum slew rate (units/s) (float32)
        - Error described in the Response message>Body section

        """
        return self.quickSend("HSSwp.SwpChTimingGet", [], [], ["f", "f", "f", "f"])

    def HSSwp_SwpChBwdSwSet(self, Bwd_Sweep):
        """
        HSSwp.SwpChBwdSwSet
        Enables or disables the backward sweep for the sweep channel in the High-Speed Sweeper.

        Arguments:

        - Bwd Sweep (unsigned int32) defines if the backward sweep is enabled, where 0=Off, 1=On

        Return arguments (if Send response back flag is set to True when sending request message):

        - Error described in the Response message>Body section
        """
        return self.quickSend("HSSwp.SwpChBwdSwSet", [Bwd_Sweep], ["I"], [])

    def HSSwp_SwpChBwdSwGet(self):
        """
        HSSwp.SwpChBwdSwGet
        Returns if the backward sweep of the sweep channel in the High-Speed Sweeper is enabled or not.

        Arguments: None

        Return arguments (if Send response back flag is set to True when sending request message):

        - Bwd Sweep (unsigned int32) specifies if the backward sweep is enabled, where 0=Off, 1=On
        - Error described in the Response message>Body section
        """
        return self.quickSend("HSSwp.SwpChBwdSwGet", [], [], ["I"])

    def HSSwp_SwpChBwdDelaySet(self, Bwd_Delay):
        """
        HSSwp.SwpChBwdDelaySet
        Sets the delay between forward and backward sweep of the sweep channel in the High-Speed Sweeper.
         Arguments:

        - Bwd Delay (float32) sets the delay between forward and backward sweep in seconds.

        Return arguments (if Send response back flag is set to True when sending request message):

        - Error described in the Response message>Body section
        """
        return self.quickSend("HSSwp.SwpChBwdDelaySet", [Bwd_Delay], ["f"], [])

    def HSSwp_SwpChBwdDelayGet(self):
        """
        HSSwp.SwpChBwdDelayGet
        Returns the delay between forward and backward sweep of the sweep channel in the High-Speed Sweeper.

        Arguments: None

        Return arguments (if Send response back flag is set to True when sending request message):

        - Bwd Delay (float32) is the delay between forward and backward sweep in seconds
        - Error described in the Response message>Body section
        """
        return self.quickSend("HSSwp.SwpChBwdDelayGet", [], [], ["f"])

    def HSSwp_ZCtrlOffSet(self, Z_Controller_Off, Z_Controller_Index, Z_Averaging_Time, Z_Offset, Z_Control_Time):
        """
        HSSwp.ZCtrlOffSet
        Sets the Z-Controller behavior for the duration of the sweep in the High-Speed Sweeper.

        Arguments:
        - Z-Controller Off (int) defines if the Z-Controller should be switched off during the sweep, where -1=no change, 0=switch off, 1=don’t switch
        - Z-Controller index (int) specifies which Z-Controller to switch off, where 0=no change, 1=Z-Controller of tip 1, 2-4=Z-Controllers tips 2-4 (multiprobe systems only)
        - Z Averaging Time (float32) sets the time (in seconds) to average the Z position before switching off the Z- controller
        - Z Offset (float32) sets the Z offset (in meters) by which the tip is retracted after switching off the controller
        - Z Control Time (float32) sets the time (in seconds) to wait after switching the Z-Controller back on (in
        case it was switched off)

        Return arguments (if Send response back flag is set to True when sending request message):

        - Error described in the Response message>Body section

        """
        return self.quickSend("HSSwp.ZCtrlOffSet",
                              [Z_Controller_Off, Z_Controller_Index, Z_Averaging_Time, Z_Offset, Z_Control_Time],
                              ["i", "i", "f", "f", "f"], [])

    def HSSwp_ZCtrlOffGet(self):
        """
        HSSwp.ZCtrlOffGet
        Returns the Z-Controller behavior for the duration of the sweep in the High-Speed Sweeper.

        Arguments: None

        Return arguments (if Send response back flag is set to True when sending request message):

        - Z-Controller Off (int) defines if the Z-Controller is switched off during the sweep, where 0=switch off, 1=don’t switch
        - Z-Controller Index (int) defines which Z-Controller is switched off during the sweep, where 1=Z- Controller of tip 1, 2-4=Z-Controllers tips 2-4 (multiprobe systems only)
        - Z Averaging Time (float32) is the time (in seconds) to average the Z position before switching off the Z- controller
        - Z Offset (float32) is the Z offset (in meters) by which the tip is retracted after switching off the controller
        - Z Control Time (float32) is the time (in seconds) to wait after switching the Z-Controller back on (in case
        it was switched off)
        - Error described in the Response message>Body section
        """
        return self.quickSend("HSSwp.ZCtrlOffGet", [], [], ["i", "i", "f", "f", "f"])

    def GenPICtrl_OnOffSet(self, Controller_status):
        """
        GenPICtrl.OnOffSet
        Switches the Generic PI Controller On or Off.
        Arguments: 
        -- Controller status (unsigned int32) switches the controller Off (_0) or On (_1)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("GenPICtrl.OnOffSet", [Controller_status], ["I"], [])

    def GenPICtrl_OnOffGet(self):
        """
        GenPICtrl.OnOffGet
        Returns the status of the Generic PI Controller..
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Controller status (unsigned int32) indicates if the controller is Off (_0) or On (_1)
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("GenPICtrl.OnOffGet", [], [], ["I"])

    def GenPICtrl_AOValSet(self, Output_value):
        """
        GenPICtrl.AOValSet
        Sets the output signal value of the User Output controlled by the Generic PI controller.
        Arguments:
        -- Output value (float32)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("GenPICtrl.AOValSet", [Output_value], ["f"], [])

    def GenPICtrl_AOValGet(self):
        """
        GenPICtrl.AOValGet
        Gets the output signal value of the User Output controlled by the Generic PI controller.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Output value (float32)
        -- Error described in the Response message&gt;Body section
        """
        return self.quickSend("GenPICtrl.AOValGet", [], [], ["f"])

    def GenPICtrl_AOPropsSet(self, Signal_name, Units, Upper_limit, Lower_limit,
                             Calibration_per_volt, Offset_in_physical_units):
        """
        GenPICtrl.AOPropsSet
        Sets the properties of the User Output controlled by the Generic PI controller.
        Arguments: 
        -- Signal name size (int) is the number of characters of the Signal name string
        -- Signal name (string) is the name of the selected output
        -- Units size (int) is the number of characters of the Units string
        -- Units (string) sets the physical units of the selected output
        -- Upper limit (float32) defines the upper physical limit of the user output
        -- Lower limit (float32) defines the lower physical limit of the user output
        -- Calibration per volt (float32) 
        -- Offset in physical units (float32) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("GenPICtrl.AOPropsSet",
                              [Signal_name, Units, Upper_limit, Lower_limit,
                               Calibration_per_volt, Offset_in_physical_units],
                              ["+*c", "+*c", "f", "f", "f", "f"], [])

    def GenPICtrl_AOPropsGet(self):
        """
        GenPICtrl.AOPropsGet
        Gets the properties of the User Output controlled by the Generic PI controller.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Signal name size (int) is the number of characters of the Signal name string
        -- Signal name (string) is the name of the selected output
        -- Units size (int) is the number of characters of the Units string
        -- Units (string) returns the physical units of the selected output
        -- Upper limit (float32) returns the upper physical limit of the user output
        -- Lower limit (float32) returns the lower physical limit of the user output
        -- Calibration per volt (float32) 
        -- Offset in physical units (float32) 
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("GenPICtrl.AOPropsGet", [], [], ["i", "*-c", "i", "*-c", "f", "f", "f", "f"])

    def GenPICtrl_ModChSet(self, Output_index):
        """
        GenPICtrl.ModChSet
        Sets the index of the User Output controlled by the Generic PI controller.
        Arguments: 
        -- Output index (int) sets the output index to be used, which could be any value from 1 to the number of available outputs
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        """
        return self.quickSend("GenPICtrl.ModChSet", [Output_index], ["i"], [])

    def GenPICtrl_ModChGet(self):
        """
        GenPICtrl.ModChGet
        Gets the index of the User Output controlled by the Generic PI controller.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Output index (int) returns the output index to be used, which could be any value from 1 to the number of available outputs. 0 means that no output is selected
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("GenPICtrl.ModChGet", [], [], ["i"])

    def GenPICtrl_DemodChSet(self, Input_index, AC_mode):
        """
        GenPICtrl.DemodChSet
        Sets the index of the signal demodulated by the Generic PI controller.
        Arguments: 
        -- Input index (int) is comprised between 0 and 127 for the physical inputs, physical outputs, and internal channels. To see which signal has which index, see <i>Signals.NamesGet</i> function. Value -1 means no change
        -- AC mode (unsigned int16) sets the AC parameter. 0 means no change, 1 means AC is On, and 2 means AC is Off
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("GenPICtrl.DemodChSet", [Input_index, AC_mode], ["i", "H"], [])

    def GenPICtrl_DemodChGet(self):
        """
        GenPICtrl.DemodChGet
        Gets the index of the signal demodulated by the Generic PI controller.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Input index (int) is comprised between 0 and 127 for the physical inputs, physical outputs, and internal channels. To see which signal has which index, see <i>Signals.NamesGet</i> function
        -- Error described in the Response message&gt;Body section
        
        
        
        
        """
        return self.quickSend("GenPICtrl.DemodChGet", [], [], ["i"])

    def GenPICtrl_PropsSet(self, Setpoint, P_gain, Time_constant, Slope):
        """
        GenPICtrl.PropsSet
        Gets the properties of the Generic PI controller.
        Arguments: 
        -- Setpoint (float32) 
        -- P gain (float32) 
        -- Time constant (float32) 
        -- Slope (unsigned int16) where 0 means no change, 1 means Positive, and 2 means Negative
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("GenPICtrl.PropsSet", [Setpoint, P_gain, Time_constant, Slope], ["f", "f", "f", "H"], [])

    def GenPICtrl_PropsGet(self):
        """
        GenPICtrl.PropsGet
        Gets the properties of the Generic PI controller.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Setpoint (float32) 
        -- P gain (float32) 
        -- Time constant (float32) 
        -- Slope (unsigned int16) where 0 means Negative and 1 means Positive 
        -- Error described in the Response message&gt;Body section
        
        
        
        Atom Tracking
        """
        return self.quickSend("GenPICtrl.PropsGet", [], [], ["f", "f", "f", "H"])

    def AtomTrack_CtrlSet(self, AT_control, Status):
        """
        AtomTrack.CtrlSet
        Turns the selected Atom Tracking control (modulation, controller or drift measurement) On or Off.
        Arguments: 
        -- AT control (unsigned int16) sets which control to switch. 0 means Modulation, 1 means Controller, and 2 means Drift Measurement
        -- Status (unsigned int16) switches the selected control Off (_0) or On (_1)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("AtomTrack.CtrlSet", [AT_control, Status], ["H", "H"], [])

    def AtomTrack_StatusGet(self, AT_control):
        """
        AtomTrack.StatusGet
        Returns the status of the selected Atom Tracking control (modulation, controller or drift measurement).
        Arguments: 
        -- AT control (unsigned int16) sets which control to read the status from. 0 means Modulation, 1 means Controller, and 2 means Drift Measurement
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Status (unsigned int16) returns the status of the selected control, where 0 means Off and 1 means On
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("AtomTrack.StatusGet", [AT_control], ["H"], ["H"])

    def AtomTrack_PropsSet(self, Integral_gain, Frequency_Hz, Amplitude_m, Phase_deg, Switch_Off_delay_s):
        """
        AtomTrack.PropsSet
        Sets the Atom Tracking parameters.
        Arguments: 
        -- Integral gain (float32) is the gain of the Atom Tracking controller
        -- Frequency (Hz) (float32) is the frequency of the modulation
        -- Amplitude (m) (float32) is the amplitude of the modulation
        -- Phase (deg) (float32) is the phase of the modulation
        -- Switch Off delay (s) (float32) means that before turning off the controller, the position is averaged over this time delay. The averaged position is then applied. This leads to reproducible positions when switching off the Atom Tracking controller 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        """
        return self.quickSend("AtomTrack.PropsSet",
                              [Integral_gain, Frequency_Hz, Amplitude_m, Phase_deg, Switch_Off_delay_s],
                              ["f", "f", "f", "f", "f"], [])

    def AtomTrack_PropsGet(self):
        """
        AtomTrack.PropsGet
        Returns the Atom Tracking parameters.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Integral gain (float32) is the gain of the Atom Tracking controller
        -- Frequency (Hz) (float32) is the frequency of the modulation
        -- Amplitude (m) (float32) is the amplitude of the modulation
        -- Phase (deg) (float32) is the phase of the modulation
        -- Switch Off delay (s) (float32) means that before turning off the controller, the position is averaged over this time delay. The averaged position is then applied. This leads to reproducible positions when switching off the Atom Tracking controller 
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("AtomTrack.PropsGet", [], [], ["f", "f", "f", "f", "f"])

    def AtomTrack_QuickCompStart(self, AT_control):
        """
        AtomTrack.QuickCompStart
        Starts the Tilt or Drift compensation.
        Arguments: 
        -- AT control (unsigned int16) sets if Tilt (_0) or Drift (_1) compensations starts
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("AtomTrack.QuickCompStart", [AT_control], ["H"], [])

    def AtomTrack_DriftComp(self):
        """
        AtomTrack.DriftComp
        Applies the Drift measurement to the Drift compensation and turns On the compensation.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        Lock-In
        """
        return self.quickSend("AtomTrack.DriftComp", [], [], [])

    def LockIn_ModOnOffSet(self, Modulator_number, Lock_In_OndivOff):
        """
        LockIn.ModOnOffSet
        Turns the specified Lock-In modulator on or off.
        Arguments:
        -- Modulator number (int) is the number that specifies which modulator to use. It starts from number 1 (_Modulator 1)
        -- Lock-In On/Off (unsigned int32) turns the specified modulator on or off, where 0_Off and 1_On  
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("LockIn.ModOnOffSet", [Modulator_number, Lock_In_OndivOff], ["i", "I"], [])

    def LockIn_ModOnOffGet(self, Modulator_number):
        """
        LockIn.ModOnOffGet
        Returns if the specified Lock-In modulator is turned on or off.
        Arguments:
        -- Modulator number (int) is the number that specifies which modulator to use. It starts from number 1 (_Modulator 1)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Lock-In On/Off (unsigned int32) returns if the specified modulator is turned on or off, where 0_Off and 1_On  
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("LockIn.ModOnOffGet", [Modulator_number], ["i"], ["I"])

    def LockIn_ModSignalSet(self, Modulator_number, Modulator_Signal_Index):
        """
        LockIn.ModSignalSet
        Selects the modulated signal of  the specified Lock-In modulator.
        Arguments:
        -- Modulator number (int) is the number that specifies which modulator to use. It starts from number 1 (_Modulator 1)
        -- Modulator Signal Index (int) is the signal index out of the list of 128 signals available in the software.  
        To get a list of the available signals, use the <i>Signals.NamesGet</i> function.
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("LockIn.ModSignalSet", [Modulator_number, Modulator_Signal_Index], ["i", "i"], [])

    def LockIn_ModSignalGet(self, Modulator_number):
        """
        LockIn.ModSignalGet
        Returns the modulated signal of  the specified Lock-In modulator.
        Arguments:
        -- Modulator number (int) is the number that specifies which modulator to use. It starts from number 1 (_Modulator 1)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Modulator Signal Index (int) is the signal index out of the list of 128 signals available in the software.  
        To get a list of the available signals, use the <i>Signals.NamesGet</i> function 
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("LockIn.ModSignalGet", [Modulator_number], ["i"], ["i"])

    def LockIn_ModPhasRegSet(self, Modulator_number, Phase_Register_Index):
        """
        LockIn.ModPhasRegSet
        Sets the phase register index of the specified Lock-In modulator.
        Each modulator can work on any phase register (frequency). Use this function to assign the modulator to one of the 8 available phase registers (index 1-8). 
        Use the <i>LockIn.ModPhaFreqSet</i> function to set the frequency of the phase registers.
        Arguments:
        -- Modulator number (int) is the number that specifies which modulator to use. It starts from number 1 (_Modulator 1)
        -- Phase Register Index (int) is the index of the phase register of the specified Lock-In modulator. Valid values are index 1 to 8.  
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("LockIn.ModPhasRegSet", [Modulator_number, Phase_Register_Index], ["i", "i"], [])

    def LockIn_ModPhasRegGet(self, Modulator_number):
        """
        LockIn.ModPhasRegGet
        Returns the phase register index of the specified Lock-In modulator.
        Each modulator can work on any phase register (frequency generator). 
        Use the <i>LockIn.ModPhaseRegFreqGet</i> function to get the frequency of the phase registers.
        Arguments:
        -- Modulator number (int) is the number that specifies which modulator to use. It starts from number 1 (_Modulator 1)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Phase Register Index (int) is the index of the phase register of the specified Lock-In modulator. Valid values are index 1 to 8 
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("LockIn.ModPhasRegGet", [Modulator_number], ["i"], ["i"])

    def LockIn_ModHarmonicSet(self, Modulator_number, Harmonic_):
        """
        LockIn.ModHarmonicSet
        Sets the harmonic of the specified Lock-In modulator.
        The modulator is bound to a phase register (frequency generator), but it can work on harmonics. Harmonic 1 is the base frequency (the frequency of the frequency generator).
        Arguments:
        -- Modulator number (int) is the number that specifies which modulator to use. It starts from number 1 (_Modulator 1)
        -- Harmonic  (int) is the harmonic of the specified Lock-In modulator. Valid values start from 1 (_base frequency)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("LockIn.ModHarmonicSet", [Modulator_number, Harmonic_], ["i", "i"], [])

    def LockIn_ModHarmonicGet(self, Modulator_number):
        """
        LockIn.ModHarmonicGet
        Returns the harmonic of the specified Lock-In modulator.
        The modulator is bound to a phase register (frequency generator), but it can work on harmonics. Harmonic 1 is the base frequency (the frequency of the frequency generator).
        Arguments:
        -- Modulator number (int) is the number that specifies which modulator to use. It starts from number 1 (_Modulator 1)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Harmonic  (int) is the harmonic of the specified Lock-In modulator. Valid values start from 1 (_base frequency)
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("LockIn.ModHarmonicGet", [Modulator_number], ["i"], ["i"])

    def LockIn_ModPhasSet(self, Modulator_number, Phase_deg_):
        """
        LockIn.ModPhasSet
        Sets the modulation phase offset of the specified Lock-In modulator.
        Arguments:
        -- Modulator number (int) is the number that specifies which modulator to use. It starts from number 1 (_Modulator 1)
        -- Phase (deg)  (float32) is the modulation phase offset of the specified Lock-In modulator
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("LockIn.ModPhasSet", [Modulator_number, Phase_deg_], ["i", "f"], [])

    def LockIn_ModPhasGet(self, Modulator_number):
        """
        LockIn.ModPhasGet
        Returns the modulation phase offset of the specified Lock-In modulator.
        Arguments:
        -- Modulator number (int) is the number that specifies which modulator to use. It starts from number 1 (_Modulator 1)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Phase (deg)  (float32) is the modulation phase offset of the specified Lock-In modulator
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("LockIn.ModPhasGet", [Modulator_number], ["i"], ["f"])

    def LockIn_ModAmpSet(self, Modulator_number, Amplitude_):
        """
        LockIn.ModAmpSet
        Sets the modulation amplitude of the specified Lock-In modulator.
        Arguments:
        -- Modulator number (int) is the number that specifies which modulator to use. It starts from number 1 (_Modulator 1)
        -- Amplitude  (float32) is the modulation amplitude of the specified Lock-In modulator
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("LockIn.ModAmpSet", [Modulator_number, Amplitude_], ["i", "f"], [])

    def LockIn_ModAmpGet(self, Modulator_number):
        """
        LockIn.ModAmpGet
        Returns the modulation amplitude of the specified Lock-In modulator.
        Arguments:
        -- Modulator number (int) is the number that specifies which modulator to use. It starts from number 1 (_Modulator 1)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Amplitude  (float32) is the modulation amplitude of the specified Lock-In modulator
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("LockIn.ModAmpGet", [Modulator_number], ["i"], ["f"])

    def LockIn_ModPhasFreqSet(self, Modulator_number, Frequency_Hz_):
        """
        LockIn.ModPhasFreqSet
        Sets the frequency of the specified Lock-In phase register/modulator.
        The Lock-in module has a total of 8 frequency generators / phase registers. Each modulator and demodulator can be bound to one of the phase registers.
        This function sets the frequency of one of the phase registers.
        Arguments:
        -- Modulator number (int) is the number that specifies which phase register/modulator to use. It starts from number 1 (_Modulator 1)
        -- Frequency (Hz)  (float64) is the frequency of the specified Lock-In phase register
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        """
        return self.quickSend("LockIn.ModPhasFreqSet", [Modulator_number, Frequency_Hz_], ["i", "d"], [])

    def LockIn_ModPhasFreqGet(self, Modulator_number):
        """
        LockIn.ModPhasFreqGet
        Returns the frequency of the specified Lock-In phase register/modulator.
        The Lock-in module has a total of 8 frequency generators / phase registers. Each modulator and demodulator can be bound to one of the phase registers.
        This function gets the frequency of one of the phase registers.
        Arguments:
        -- Modulator number (int) is the number that specifies which phase register/modulator to use. It starts from number 1 (_Modulator 1)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Frequency (Hz)  (float64) is the frequency of the specified Lock-In phase register
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("LockIn.ModPhasFreqGet", [Modulator_number], ["i"], ["d"])

    def LockIn_DemodSignalSet(self, Demodulator_number, Demodulator_Signal_Index):
        """
        LockIn.DemodSignalSet
        Selects the demodulated signal of  the specified Lock-In demodulator.
        Arguments:
        -- Demodulator number (int) is the number that specifies which demodulator to use. It starts from number 1 (_Demodulator 1)
        -- Demodulator Signal Index (int) is the signal index out of the list of 128 signals available in the software.  
        To get a list of the available signals, use the <i>Signals.NamesGet</i> function.
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("LockIn.DemodSignalSet", [Demodulator_number, Demodulator_Signal_Index], ["i", "i"], [])

    def LockIn_DemodSignalGet(self, Demodulator_number):
        """
        LockIn.DemodSignalGet
        Returns the demodulated signal of  the specified Lock-In demodulator.
        Arguments:
        -- Demodulator number (int) is the number that specifies which demodulator to use. It starts from number 1 (_Demodulator 1)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Demodulator Signal Index (int) is the signal index out of the list of 128 signals available in the software.  
        To get a list of the available signals, use the <i>Signals.NamesGet</i> function 
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("LockIn.DemodSignalGet", [Demodulator_number], ["i"], ["i"])

    def LockIn_DemodHarmonicSet(self, Demodulator_number, Harmonic_):
        """
        LockIn.DemodHarmonicSet
        Sets the harmonic of the specified Lock-In demodulator.
        The demodulator demodulates the input signal at the specified harmonic overtone of the frequency generator. Harmonic 1 is the base frequency (the frequency of the frequency generator).
        Arguments:
        -- Demodulator number (int) is the number that specifies which demodulator to use. It starts from number 1 (_Demodulator 1)
        -- Harmonic  (int) is the harmonic of the specified Lock-In demodulator. Valid values start from 1 (_base frequency)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("LockIn.DemodHarmonicSet", [Demodulator_number, Harmonic_], ["i", "i"], [])

    def LockIn_DemodHarmonicGet(self, Demodulator_number):
        """
        LockIn.DemodHarmonicGet
        Returns the harmonic of the specified Lock-In demodulator.
        The demodulator demodulates the input signal at the specified harmonic overtone of the frequency generator. Harmonic 1 is the base frequency (the frequency of the frequency generator).
        Arguments:
        -- Demodulator number (int) is the number that specifies which demodulator to use. It starts from number 1 (_Demodulator 1)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Harmonic  (int) is the harmonic of the specified Lock-In demodulator. Valid values start from 1 (_base frequency)
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("LockIn.DemodHarmonicGet", [Demodulator_number], ["i"], ["i"])

    def LockIn_DemodHPFilterSet(self, Demodulator_number, HP_Filter_Order, HP_Filter_Cutoff_Frequency_Hz):
        """
        LockIn.DemodHPFilterSet
        Sets the properties of the high-pass filter applied to the demodulated signal of the specified demodulator.
        The high-pass filter is applied on the demodulated signal before the actual demodulation. It is used to get rid of DC or low-frequency components which could result in undesired components close to the modulation frequency on the demodulator output signals (X,Y).
        Arguments:
        -- Demodulator number (int) is the number that specifies which demodulator to use. It starts from number 1 (_Demodulator 1)
        -- HP Filter Order (int) is the high-pass filter order. Valid values are from -1 to 8, where -1_no change, 0_filter off.
        -- HP Filter Cutoff Frequency (Hz) (float32) is the high-pass filter cutoff frequency in Hz, where 0 _ no change.
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("LockIn.DemodHPFilterSet",
                              [Demodulator_number, HP_Filter_Order, HP_Filter_Cutoff_Frequency_Hz], ["i", "i", "f"], [])

    def LockIn_DemodHPFilterGet(self, Demodulator_number):
        """
        LockIn.DemodHPFilterGet
        Returns the properties of the high-pass filter applied to the demodulated signal of the specified demodulator.
        The high-pass filter is applied on the demodulated signal before the actual demodulation. It is used to get rid of DC or low-frequency components which could result in undesired components close to the modulation frequency on the demodulator output signals (X,Y).
        Arguments:
        -- Demodulator number (int) is the number that specifies which demodulator to use. It starts from number 1 (_Demodulator 1)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- HP Filter Order (int) is the high-pass filter order. Valid values are from 0 to 8, where 0_filter off
        -- HP Filter Cutoff Frequency (Hz) (float32) is the high-pass filter cutoff frequency in Hz
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("LockIn.DemodHPFilterGet", [Demodulator_number], ["i"], ["i", "f"])

    def LockIn_DemodLPFilterSet(self, Demodulator_number, LP_Filter_Order, LP_Filter_Cutoff_Frequency_Hz):
        """
        LockIn.DemodLPFilterSet
        Sets the properties of the low-pass filter applied to the demodulated signal of the specified demodulator.
        The low-pass filter is applied on the demodulator output signals (X,Y) to remove undesired components. Lower cut-off frequency means better suppression of undesired frequency components, but longer response time (time constant) of the filter. 
        Arguments:
        -- Demodulator number (int) is the number that specifies which demodulator to use. It starts from number 1 (_Demodulator 1)
        -- LP Filter Order (int) is the low-pass filter order. Valid values are from -1 to 8, where -1_no change, 0_filter off.
        -- LP Filter Cutoff Frequency (Hz) (float32) is the low-pass filter cutoff frequency in Hz, where 0 _ no change.
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("LockIn.DemodLPFilterSet",
                              [Demodulator_number, LP_Filter_Order, LP_Filter_Cutoff_Frequency_Hz], ["i", "i", "f"], [])

    def LockIn_DemodLPFilterGet(self, Demodulator_number):
        """
        LockIn.DemodLPFilterGet
        Returns the properties of the low-pass filter applied to the demodulated signal of the specified demodulator.
        The low-pass filter is applied on the demodulator output signals (X,Y) to remove undesired components. Lower cut-off frequency means better suppression of undesired frequency components, but longer response time (time constant) of the filter. 
        Arguments:
        -- Demodulator number (int) is the number that specifies which demodulator to use. It starts from number 1 (_Demodulator 1)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- LP Filter Order (int) is the low-pass filter order. Valid values are from -1 to 8, where -1_no change, 0_filter off.
        -- LP Filter Cutoff Frequency (Hz) (float32) is the low-pass filter cutoff frequency in Hz, where 0 _ no change.
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("LockIn.DemodLPFilterGet", [Demodulator_number], ["i"], ["i", "f"])

    def LockIn_DemodPhasRegSet(self, Demodulator_number, Phase_Register_Index):
        """
        LockIn.DemodPhasRegSet
        Sets the phase register index of the specified Lock-In demodulator.
        Each demodulator can work on any phase register (frequency). Use this function to assign the demodulator to one of the 8 available phase registers (index 1-8). 
        Use the <i>LockIn.ModPhaFreqSet</i> function to set the frequency of the phase registers.
        Arguments:
        -- Demodulator number (int) is the number that specifies which demodulator to use. It starts from number 1 (_Demodulator 1)
        -- Phase Register Index (int) is the index of the phase register of the specified Lock-In demodulator. Valid values are index 1 to 8.  
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("LockIn.DemodPhasRegSet", [Demodulator_number, Phase_Register_Index], ["i", "i"], [])

    def LockIn_DemodPhasRegGet(self, Demodulator_number):
        """
        LockIn.DemodPhasRegGet
        Returns the phase register index of the specified Lock-In demodulator.
        Each demodulator can work on any phase register (frequency). Use the <i>LockIn.ModPhaFreqSet</i> function to set the frequency of the phase registers.
        Arguments:
        -- Demodulator number (int) is the number that specifies which demodulator to use. It starts from number 1 (_Demodulator 1)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Phase Register Index (int) is the index of the phase register of the specified Lock-In demodulator. Valid values are index 1 to 8.  
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("LockIn.DemodPhasRegGet", [Demodulator_number], ["i"], ["i"])

    def LockIn_DemodPhasSet(self, Demodulator_number, Phase_deg_):
        """
        LockIn.DemodPhasSet
        Sets the reference phase of the specified Lock-In demodulator.
        Arguments:
        -- Demodulator number (int) is the number that specifies which demodulator to use. It starts from number 1 (_Demodulator 1)
        -- Phase (deg)  (float32) is the reference phase of the specified Lock-In demodulator
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("LockIn.DemodPhasSet", [Demodulator_number, Phase_deg_], ["i", "f"], [])

    def LockIn_DemodPhasGet(self, Demodulator_number):
        """
        LockIn.DemodPhasGet
        Returns the reference phase of the specified Lock-In demodulator.
        Arguments:
        -- Demodulator number (int) is the number that specifies which demodulator to use. It starts from number 1 (_Demodulator 1)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Phase (deg)  (float32) is the reference phase of the specified Lock-In demodulator
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("LockIn.DemodPhasGet", [Demodulator_number], ["i"], ["f"])

    def LockIn_DemodSyncFilterSet(self, Demodulator_number, Sync_Filter_):
        """
        LockIn.DemodSyncFilterSet
        Switches the synchronous (Sync) filter of the specified demodulator On or Off.
        The synchronous filter is applied on the demodulator output signals (X,Y) after the low-pass filter. It is very good in suppressing harmonic components (harmonics of the demodulation frequency), but does not suppress other frequencies.
        The sync filter does not output a continuous signal, it only updates the value after each period of the demodulation frequency.
        Arguments:
        -- Demodulator number (int) is the number that specifies which demodulator to use. It starts from number 1 (_Demodulator 1)
        -- Sync Filter  (unsigned int32) switches the synchronous filter of the specified demodulator on or off, where 0_Off and 1_On  
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("LockIn.DemodSyncFilterSet", [Demodulator_number, Sync_Filter_], ["i", "I"], [])

    def LockIn_DemodSyncFilterGet(self, Demodulator_number):
        """
        LockIn.DemodSyncFilterGet
        Returns the status (on/off) of the synchronous (Sync) filter of the specified demodulator.
        The synchronous filter is applied on the demodulator output signals (X,Y) after the low-pass filter. It is very good in suppressing harmonic components (harmonics of the demodulation frequency), but does not suppress other frequencies.
        The sync filter does not output a continuous signal, it only updates the value after each period of the demodulation frequency.
        Arguments:
        -- Demodulator number (int) is the number that specifies which demodulator to use. It starts from number 1 (_Demodulator 1)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Sync Filter  (unsigned int32) is the synchronous filter of the specified demodulator, where 0_Off and 1_On  
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("LockIn.DemodSyncFilterGet", [Demodulator_number], ["i"], ["I"])

    def LockIn_DemodRTSignalsSet(self, Demodulator_number, RT_Signals_):
        """
        LockIn.DemodRTSignalsSet
        Sets the signals available for acquisition on the real-time system from the specified demodulator.
        Arguments:
        -- Demodulator number (int) is the number that specifies which demodulator to use. It starts from number 1 (_Demodulator 1)
        -- RT Signals  (unsigned int32) sets which signals from the specified demodulator should be available on the Real-time system. 0 sets the available RT Signals to X/Y, 1 sets them to R/phi.
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("LockIn.DemodRTSignalsSet", [Demodulator_number, RT_Signals_], ["i", "I"], [])

    def LockIn_DemodRTSignalsGet(self, Demodulator_number):
        """
        LockIn.DemodRTSignalsGet
        Returns which the signals are available for acquisition on the real-time system from the specified demodulator.
        Arguments:
        -- Demodulator number (int) is the number that specifies which demodulator to use. It starts from number 1 (_Demodulator 1)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        -- RT Signals  (unsigned int32) returns which signals from the specified demodulator are available on the Real-time system. 0 means X/Y, and 1 means R/phi.
        -- Error described in the Response message&gt;Body section
        
        Lock-In Frequency Sweep
        """
        return self.quickSend("LockIn.DemodRTSignalsGet", [Demodulator_number], ["i"], ["I"])

    def LockInFreqSwp_Open(self):
        """
        LockInFreqSwp.Open
        Opens the Transfer function (Lock-In Frequency Sweep) module.
        The transfer function does not run when its front panel is closed. To automate measurements it might be required to open the module first using this VI.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("LockInFreqSwp.Open", [], [], [])

    def LockInFreqSwp_Start(self, Get_Data, Direction):
        """
        LockInFreqSwp.Start
        Starts a Lock-In frequency sweep.
        Arguments:
        -- Get Data (unsigned int32) defines if the function returns the recorder channels and data
        -- Direction (unsigned int32) sets the direction of the frequency sweep. 0 means sweep down (from upper limit to lower limit) and 1 means sweep up (from lower limit to upper limit)
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Channels names size (int) is the size in bytes of the recorder channels  names array
        -- Channels names number (int) is the number of elements of the recorded channels names array
        -- Channels names (1D array string) returns the array of recorded channel names (strings), where each string comes prepended by its size in bytes
        -- Data rows (int) is the number of rows of the returned data array (the first row is the swept frequency, and each additional row contains the data of each recorded channel )
        -- Data columns (int) is the number of recorded points (number of steps plus 1)
        -- Data (2D array float32) returns the recorded data. The number of rows is defined by <i>Data rows</i>, and the number of columns is defined by <i>Data columns</i>
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("LockInFreqSwp.Start", [Get_Data, Direction], ["I", "I"],
                              ["i", "i", "*+c", "i", "i", "2f"])

    def LockInFreqSwp_SignalSet(self, Sweep_signal_index):
        """
        LockInFreqSwp.SignalSet
        Sets the sweep signal used in the Lock-In frequency sweep module.
        Arguments:
        -- Sweep signal index (int) sets the sweep signal index out of the list of sweep signals to use, where -1 means no signal selected
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("LockInFreqSwp.SignalSet", [Sweep_signal_index], ["i"], [])

    def LockInFreqSwp_SignalGet(self):
        """
        LockInFreqSwp.SignalGet
        Returns the sweep signal used in the Lock-In frequency sweep module.
        Arguments:
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Sweep signal index (int) is the sweep signal index selected out of the list of sweep signals, where -1 means no signal selected
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("LockInFreqSwp.SignalGet", [], [], ["i"])

    def LockInFreqSwp_LimitsSet(self, Lower_limit_Hz, Upper_limit_Hz):
        """
        LockInFreqSwp.LimitsSet
        Sets the frequency limits in the Lock-In frequency sweep module.
        Arguments:
        -- Lower limit (Hz) (float32) sets the lower frequency limit in Hz
        -- Upper limit (Hz) (float32) sets the lower frequency limit in Hz
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("LockInFreqSwp.LimitsSet", [Lower_limit_Hz, Upper_limit_Hz], ["f", "f"], [])

    def LockInFreqSwp_LimitsGet(self):
        """
        LockInFreqSwp.LimitsGet
        Returns the frequency limits in the Lock-In frequency sweep module.
        Arguments:
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Lower limit (Hz) (float32) is the lower frequency limit in Hz
        -- Upper limit (Hz) (float32) is the lower frequency limit in Hz
        -- Error described in the Response message&gt;Body section
        """
        return self.quickSend("LockInFreqSwp.LimitsGet", [], [], ["f", "f"])

    def LockInFreqSwp_PropsSet(self, Number_of_steps, Integration_periods, Minimum_integration_time_s, Settling_periods,
                               Minimum_Settling_time_s, Autosave, Save_dialog, Basename):
        """
        LockInFreqSwp.PropsSet
        Sets the configuration of the Transfer Function (Lock-In frequency sweep) module.
        Arguments:
        -- Number of steps (unsigned int16) is the number of frequency steps over the sweep range (logarithmic distribution). The number of data points _ number of steps + 1. If set to 0, the number of steps is left unchanged
        -- Integration periods (unsigned int16) is the number of Lock in periods to average for one measurement. 
        -- Minimum integration time (s) (float32) is the minimum integration time in seconds to average each measurement
        -- Settling periods (unsigned int16) is the number of Lock in periods to wait before acquiring data at each point of the sweep
        -- Minimum Settling time (s) (float32) is the minimum settling time in seconds to wait before acquiring data at each point of the sweep
        -- Autosave (unsigned int32) automatically saves the data at end of sweep
        -- Save dialog (unsigned int32) will open a dialog box when saving the data
        -- Basename size (int) is the size (number of characters) of the basename string
        -- Basename (string) is the basename of the saved files
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("LockInFreqSwp.PropsSet",
                              [Number_of_steps, Integration_periods, Minimum_integration_time_s, Settling_periods,
                               Minimum_Settling_time_s, Autosave, Save_dialog, Basename],
                              ["H", "H", "f", "H", "f", "I", "I", "+*c"], [])

    def LockInFreqSwp_PropsGet(self):
        """
        LockInFreqSwp.PropsGet
        Returns the configuration of the Transfer Function (Lock-In frequency sweep) module.
        Arguments:
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Number of steps (unsigned int16) is the number of frequency steps over the sweep range (logarithmic distribution). The number of data points _ number of steps + 1
        -- Integration periods (unsigned int16) is the number of Lock in periods to average for one measurement. 
        -- Minimum integration time (s) (float32) is the minimum integration time in seconds to average each measurement
        -- Settling periods (unsigned int16) is the number of Lock in periods to wait before acquiring data at each point of the sweep
        -- Minimum Settling time (s) (float32) is the minimum settling time in seconds to wait before acquiring data at each point of the sweep
        -- Autosave (unsigned int32) automatically saves the data at end of sweep
        -- Save dialog (unsigned int32) will open a dialog box when saving the data
        -- Basename size (int) is the size (number of characters) of the basename string
        -- Basename (string) is the basename of the saved files
        -- Error described in the Response message&gt;Body section
        
        PLL modules
        """
        return self.quickSend("LockInFreqSwp.PropsGet", [], [], ["H", "H", "f", "H", "f", "I", "I", "i", "*-c"])

    def PLL_InpCalibrSet(self, Modulator_index, Calibration_mdivV):
        """
        PLL.InpCalibrSet
        Sets the input calibration of the oscillation control module.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        -- Calibration (m/V) (float32) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("PLL.InpCalibrSet", [Modulator_index, Calibration_mdivV], ["i", "f"], [])

    def PLL_InpCalibrGet(self, Modulator_index):
        """
        PLL.InpCalibrGet
        Returns the input calibration of the oscillation control module.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Calibration (m/V) (float32) 
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("PLL.InpCalibrGet", [Modulator_index], ["i"], ["f"])

    def PLL_InpRangeSet(self, Modulator_index, Input_range_m):
        """
        PLL.InpRangeSet
        Sets the input range of the oscillation control module.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        -- Input range (m) (float32) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("PLL.InpRangeSet", [Modulator_index, Input_range_m], ["i", "f"], [])

    def PLL_InpRangeGet(self, Modulator_index):
        """
        PLL.InpRangeGet
        Returns the input range of the oscillation control module.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Input range (m) (float32) 
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("PLL.InpRangeGet", [Modulator_index], ["i"], ["f"])

    def PLL_InpPropsSet(self, Modulator_index, Differential_input, OneDiv10_divider):
        """
        PLL.InpPropsSet
        Sets the input parameters of the oscillation control module.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        -- Differential input (unsigned int16) where 0 is Off and 1 is On
        -- 1/10 divider (unsigned int16) where 0 is Off and 1 is On
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("PLL.InpPropsSet", [Modulator_index, Differential_input, OneDiv10_divider],
                              ["i", "H", "H"], [])

    def PLL_InpPropsGet(self, Modulator_index):
        """
        PLL.InpPropsGet
        Returns the input parameters of the oscillation control module.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Differential input (unsigned int16) where 0 is Off and 1 is On
        -- 1/10 divider (unsigned int16) where 0 is Off and 1 is On
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("PLL.InpPropsGet", [Modulator_index], ["i"], ["H", "H"])

    def PLL_AddOnOffSet(self, Modulator_index, Add):
        """
        PLL.AddOnOffSet
        Sets the status of the Add external signal to the output.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        -- Add (unsigned int32) where 0 is Off and 1 is On
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("PLL.AddOnOffSet", [Modulator_index, Add], ["i", "I"], [])

    def PLL_AddOnOffGet(self, Modulator_index):
        """
        PLL.AddOnOffGet
        Returns the status of the Add external signal to the output.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Add (unsigned int32) where 0 is Off and 1 is On
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("PLL.AddOnOffGet", [Modulator_index], ["i"], ["I"])

    def PLL_OutOnOffSet(self, Modulator_index, PLL_output):
        """
        PLL.OutOnOffSet
        Sets the status of the PLL output.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        -- PLL output (unsigned int32) where 0 is Off and 1 is On
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("PLL.OutOnOffSet", [Modulator_index, PLL_output], ["i", "I"], [])

    def PLL_OutOnOffGet(self, Modulator_index):
        """
        PLL.OutOnOffGet
        Returns the status of the PLL output.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- PLL output (unsigned int32) where 0 is Off and 1 is On
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("PLL.OutOnOffGet", [Modulator_index], ["i"], ["I"])

    def PLL_ExcRangeSet(self, Modulator_index, Output_range):
        """
        PLL.ExcRangeSet
        Sets the excitation range of the oscillation control module.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        -- Output range (unsigned int16) where 0 is 10V, 1 is 1V, 2 is 0.1V, 3 is 0.01V, and 4 is 0.001V
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("PLL.ExcRangeSet", [Modulator_index, Output_range], ["i", "H"], [])

    def PLL_ExcRangeGet(self, Modulator_index):
        """
        PLL.ExcRangeGet
        Returns the excitation range of the oscillation control module.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Output range (unsigned int16) where 0 is 10V, 1 is 1V, 2 is 0.1V, 3 is 0.01V, and 4 is 0.001V
        -- Error described in the Response message&gt;Body section
        
        
        
        
        
        """
        return self.quickSend("PLL.ExcRangeGet", [Modulator_index], ["i"], ["H"])

    def PLL_ExcitationSet(self, Modulator_index, Excitation_value_V):
        """
        PLL.ExcitationSet
        Sets the current excitation value (i.e. the drive amplitude) of the oscillation control module.
        This functions works only if the amplitude controller is switched Off.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        -- Excitation value (V) (float32) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("PLL.ExcitationSet", [Modulator_index, Excitation_value_V], ["i", "f"], [])

    def PLL_ExcitationGet(self, Modulator_index):
        """
        PLL.ExcitationGet
        Returns the current excitation value (i.e. the drive amplitude) of the oscillation control module.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Excitation value (V) (float32) 
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("PLL.ExcitationGet", [Modulator_index], ["i"], ["f"])

    def PLL_AmpCtrlSetpntSet(self, Modulator_index, Setpoint_m):
        """
        PLL.AmpCtrlSetpntSet
        Sets the amplitude controller setpoint.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        -- Setpoint (m) (float32) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("PLL.AmpCtrlSetpntSet", [Modulator_index, Setpoint_m], ["i", "f"], [])

    def PLL_AmpCtrlSetpntGet(self, Modulator_index):
        """
        PLL.AmpCtrlSetpntGet
        Returns the amplitude controller setpoint.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Setpoint (m) (float32) 
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("PLL.AmpCtrlSetpntGet", [Modulator_index], ["i"], ["f"])

    def PLL_AmpCtrlOnOffSet(self, Modulator_index, Status):
        """
        PLL.AmpCtrlOnOffSet
        Switches the amplitude controller On or Off.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        -- Status (unsigned int32) where 0 is Off and 1 is On
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("PLL.AmpCtrlOnOffSet", [Modulator_index, Status], ["i", "I"], [])

    def PLL_AmpCtrlOnOffGet(self, Modulator_index):
        """
        PLL.AmpCtrlOnOffGet
        Returns the status of the amplitude controller.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Status (unsigned int32) where 0 is Off and 1 is On
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("PLL.AmpCtrlOnOffGet", [Modulator_index], ["i"], ["I"])

    def PLL_AmpCtrlGainSet(self, Modulator_index, P_gain_Vdivm, Time_constant_s):
        """
        PLL.AmpCtrlGainSet
        Sets the amplitude controller gains and timing parameters.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        -- P gain (V/m) (float32) 
        -- Time constant (s) (float32) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("PLL.AmpCtrlGainSet", [Modulator_index, P_gain_Vdivm, Time_constant_s], ["i", "f", "f"],
                              [])

    def PLL_AmpCtrlGainGet(self, Modulator_index):
        """
        PLL.AmpCtrlGainGet
        Returns the amplitude controller gains and timing parameters.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- P gain (V/m)  (float32) 
        -- Time constant (s) (float32) 
        -- Integral gain (V/m/s)  (float32) 
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("PLL.AmpCtrlGainGet", [Modulator_index], ["i"], ["f", "f", "f"])

    def PLL_AmpCtrlBandwidthSet(self, Modulator_index, Bandwidth_Hz):
        """
        PLL.AmpCtrlBandwidthSet
        Sets the amplitude controller bandwidth of the oscillation control module.
        This function uses the current Q factor and the amplitude to excitation ratio. These parameters can be identified through the Frequency Sweep module and they should be previously applied in the PLL Setup tool in order this function to get correctly the bandwidth.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        -- Bandwidth (Hz) (float32) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("PLL.AmpCtrlBandwidthSet", [Modulator_index, Bandwidth_Hz], ["i", "f"], [])

    def PLL_AmpCtrlBandwidthGet(self, Modulator_index):
        """
        PLL.AmpCtrlBandwidthGet
        Returns the amplitude controller bandwidth of the oscillation control module.
        This function uses the current Q factor and the amplitude to excitation ratio. These parameters can be identified through the Frequency Sweep module and they should be previously applied in the PLL Setup tool in order this function to get correctly the bandwidth.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Bandwidth (Hz) (float32) 
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("PLL.AmpCtrlBandwidthGet", [Modulator_index], ["i"], ["f"])

    def PLL_PhasCtrlOnOffSet(self, Modulator_index, Status):
        """
        PLL.PhasCtrlOnOffSet
        Switches the phase controller On or Off.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        -- Status (unsigned int32) where 0 is Off and 1 is On
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("PLL.PhasCtrlOnOffSet", [Modulator_index, Status], ["i", "I"], [])

    def PLL_PhasCtrlOnOffGet(self, Modulator_index):
        """
        PLL.PhasCtrlOnOffGet
        Returns the status of the phase controller.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Status (unsigned int32) where 0 is Off and 1 is On
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("PLL.PhasCtrlOnOffGet", [Modulator_index], ["i"], ["I"])

    def PLL_PhasCtrlGainSet(self, Modulator_index, P_gain_Hzdivdeg, Time_constant_s):
        """
        PLL.PhasCtrlGainSet
        Sets the phase controller gains and timing parameters.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        -- P gain (Hz/deg)  (float32) 
        -- Time constant (s) (float32) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("PLL.PhasCtrlGainSet", [Modulator_index, P_gain_Hzdivdeg, Time_constant_s],
                              ["i", "f", "f"], [])

    def PLL_PhasCtrlGainGet(self, Modulator_index):
        """
        PLL.PhasCtrlGainGet
        Returns the phase controller gains and timing parameters.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- P gain (Hz/deg) (float32) 
        -- Time constant (s) (float32) 
        -- Integral gain (Hz/deg/s) (float32) 
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("PLL.PhasCtrlGainGet", [Modulator_index], ["i"], ["f", "f"])

    def PLL_PhasCtrlBandwidthSet(self, Modulator_index, Bandwidth_Hz):
        """
        PLL.PhasCtrlBandwidthSet
        Sets the phase controller bandwidth of the oscillation control module.
        This function uses the current Q factor. This parameter can be identified through the Frequency Sweep module and it should be previously applied in the PLL Setup tool in order this function to get correctly the bandwidth.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        -- Bandwidth (Hz) (float32) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("PLL.PhasCtrlBandwidthSet", [Modulator_index, Bandwidth_Hz], ["i", "f"], [])

    def PLL_PhasCtrlBandwidthGet(self, Modulator_index):
        """
        PLL.PhasCtrlBandwidthGet
        Returns the phase controller bandwidth of the oscillation control module.
        This function uses the current Q factor. This parameter can be identified through the Frequency Sweep module and it should be previously applied in the PLL Setup tool in order this function to get correctly the bandwidth.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Bandwidth (Hz) (float32) 
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("PLL.PhasCtrlBandwidthGet", [Modulator_index], ["i"], ["f"])

    def PLL_FreqRangeSet(self, Modulator_index, Frequency_range_Hz):
        """
        PLL.FreqRangeSet
        Sets the frequency range of the oscillation control module.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        -- Frequency range (Hz) (float32) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("PLL.FreqRangeSet", [Modulator_index, Frequency_range_Hz], ["i", "f"], [])

    def PLL_FreqRangeGet(self, Modulator_index):
        """
        PLL.FreqRangeGet
        Returns the frequency range of the oscillation control module.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Frequency range (Hz) (float32) 
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("PLL.FreqRangeGet", [Modulator_index], ["i"], ["f"])

    def PLL_CenterFreqSet(self, Modulator_index, Center_frequency_Hz):
        """
        PLL.CenterFreqSet
        Sets the center frequency of the oscillation control module.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        -- Center frequency (Hz) (float64) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("PLL.CenterFreqSet", [Modulator_index, Center_frequency_Hz], ["i", "d"], [])

    def PLL_CenterFreqGet(self, Modulator_index):
        """
        PLL.CenterFreqGet
        Returns the center frequency of the oscillation control module.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Center frequency (Hz) (float64) 
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("PLL.CenterFreqGet", [Modulator_index], ["i"], ["d"])

    def PLL_FreqShiftSet(self, Modulator_index, Frequency_shift_Hz):
        """
        PLL.FreqShiftSet
        Sets the frequency shift of the oscillation control module.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        -- Frequency shift (Hz) (float32) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("PLL.FreqShiftSet", [Modulator_index, Frequency_shift_Hz], ["i", "f"], [])

    def PLL_FreqShiftGet(self, Modulator_index):
        """
        PLL.FreqShiftGet
        Returns the frequency shift of the oscillation control module.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Frequency shift (Hz) (float32) 
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("PLL.FreqShiftGet", [Modulator_index], ["i"], ["f"])

    def PLL_FreqShiftAutoCenter(self, Modulator_index):
        """
        PLL.FreqShiftAutoCenter
        Auto-centers frequency shift of the oscillation control module.
        It works like the corresponding button on the oscillation control module. It adds the current frequency shift to the center frequency and sets the frequency shift to zero.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("PLL.FreqShiftAutoCenter", [Modulator_index], ["i"], [])

    def PLL_FreqExcOverwriteSet(self, Modulator_index, Excitation_overwrite_signal_index,
                                Frequency_overwrite_signal_index):
        """
        PLL.FreqExcOverwriteSet
        Sets the signals to overwrite the Frequency Shift and/or Excitation signals of the oscillation control module.
        It works when the corresponding controller (phase, amplitude) is not active.
        To get a list of the available signals, see directly in the software or use the <i>Signals.NamesGet</i> function to get the full list of available signals.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        -- Excitation overwrite signal index (int), where value -2 means no change
        -- Frequency overwrite signal index (int), where value -2 means no change
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("PLL.FreqExcOverwriteSet",
                              [Modulator_index, Excitation_overwrite_signal_index, Frequency_overwrite_signal_index],
                              ["i", "i", "i"], [])

    def PLL_FreqExcOverwriteGet(self, Modulator_index):
        """
        PLL.FreqExcOverwriteGet
        Returns the signals to overwrite the Frequency Shift and/or Excitation signals of the oscillation control module.
        It works when the corresponding controller (phase, amplitude) is not active.
        To get a list of the available signals, see directly in the software or use the <i>Signals.NamesGet</i> function to get the full list of available signals.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Excitation overwrite signal index (int) 
        -- Frequency overwrite signal index (int) 
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("PLL.FreqExcOverwriteGet", [Modulator_index], ["i"], ["i", "i"])

    def PLL_DemodInputSet(self, Demodulator_index, Input_, Frequency_generator):
        """
        PLL.DemodInputSet
        Sets the input and the frequency generator of the selected demodulator.
        Arguments: 
        -- Demodulator index (unsigned int16) specifies which modulator or PLL to control. The valid values start from 1
        -- Input  (unsigned int16), where value 0 means no change
        -- Frequency generator (unsigned int16), where value 0 means no change
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("PLL.DemodInputSet", [Demodulator_index, Input_, Frequency_generator], ["H", "H", "H"],
                              [])

    def PLL_DemodInputGet(self, Demodulator_index):
        """
        PLL.DemodInputGet
        Returns the input and the frequency generator of the selected demodulator.
        Arguments: 
        -- Demodulator index (unsigned int16) specifies which modulator or PLL to control. The valid values start from 1
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Input  (unsigned int16) 
        -- Frequency generator (unsigned int16) 
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("PLL.DemodInputGet", [Demodulator_index], ["H"], ["H", "H"])

    def PLL_DemodHarmonicSet(self, Demodulator_index, Harmonic_):
        """
        PLL.DemodHarmonicSet
        Sets which harmonic of the input signal is selected in the PLL lock-in of the selected demodulator. 
        Harmonic 1 corresponds to the modulation frequency.
        Arguments: 
        -- Demodulator index (unsigned int16) specifies which modulator or PLL to control. The valid values start from 1
        -- Harmonic  (unsigned int16) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("PLL.DemodHarmonicSet", [Demodulator_index, Harmonic_], ["H", "H"], [])

    def PLL_DemodHarmonicGet(self, Demodulator_index):
        """
        PLL.DemodHarmonicGet
        Returns which harmonic of the input signal is selected in the PLL lock-in of the selected demodulator. 
        Harmonic 1 corresponds to the modulation frequency.
        Arguments: 
        -- Demodulator index (unsigned int16) specifies which modulator or PLL to control. The valid values start from 1
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Harmonic  (unsigned int16) 
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("PLL.DemodHarmonicGet", [Demodulator_index], ["H"], ["H"])

    def PLL_DemodPhasRefSet(self, Demodulator_index, Phase_reference_deg_):
        """
        PLL.DemodPhasRefSet
        Sets the phase reference of the selected demodulator. 
        Arguments: 
        -- Demodulator index (unsigned int16) specifies which modulator or PLL to control. The valid values start from 1
        -- Phase reference (deg)  (float32) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("PLL.DemodPhasRefSet", [Demodulator_index, Phase_reference_deg_], ["H", "f"], [])

    def PLL_DemodPhasRefGet(self, Demodulator_index):
        """
        PLL.DemodPhasRefGet
        Returns the phase reference of the selected demodulator. 
        Arguments: 
        -- Demodulator index (unsigned int16) specifies which modulator or PLL to control. The valid values start from 1
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Phase reference (deg)  (float32) 
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("PLL.DemodPhasRefGet", [Demodulator_index], ["H"], ["f"])

    def PLL_DemodFilterSet(self, Demodulator_index, Filter_order_):
        """
        PLL.DemodFilterSet
        Returns the filter order of the low-pass filter after the PLL lock-in for the selected demodulator. 
        Arguments: 
        -- Demodulator index (unsigned int16) specifies which modulator or PLL to control. The valid values start from 1
        -- Filter order  (unsigned int16) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("PLL.DemodFilterSet", [Demodulator_index, Filter_order_], ["H", "H"], [])

    def PLL_DemodFilterGet(self, Demodulator_index):
        """
        PLL.DemodFilterGet
        Returns the filter order of the low-pass filter after the PLL lock-in for the selected demodulator. 
        Arguments: 
        -- Demodulator index (unsigned int16) specifies which modulator or PLL to control. The valid values start from 1
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Filter order  (unsigned int16) 
        -- Error described in the Response message&gt;Body section
        
        
        
        PLL Frequency Sweep
        """
        return self.quickSend("PLL.DemodFilterGet", [Demodulator_index], ["H"], ["H"])

    def PLLFreqSwp_Open(self, Modulator_index):
        """
        PLLFreqSwp.Open
        Opens the PLL Frequency Sweep  module.
        Arguments:
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("PLLFreqSwp.Open", [Modulator_index], ["i"], [])

    def PLLFreqSwp_ParamsSet(self, Modulator_index, Number_of_points, Period_s, Settling_time_s):
        """
        PLLFreqSwp.ParamsSet
        Sets the parameters of a frequency sweep.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        -- Number of points (int) is the number of points for the frequency sweep
        -- Period (s) (float32) is the measurement time at each frequency value. The same value is also used as wait time at each value, so it is better to use higher values for high Q factors
        -- Settling time (s) (float32) is the time to wait after setting the frequency shift to the start position
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("PLLFreqSwp.ParamsSet", [Modulator_index, Number_of_points, Period_s, Settling_time_s],
                              ["i", "i", "f", "f"], [])

    def PLLFreqSwp_ParamsGet(self, Modulator_index):
        """
        PLLFreqSwp.ParamsGet
        Returns the parameters of a frequency sweep.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Number of points (int) is the number of points for the frequency sweep
        -- Period (s) (float32) is the measurement time at each frequency value. The same value is also used as wait time at each value, so it is better to use higher values for high Q factors
        -- Settling time (s) (float32) is the time to wait after setting the frequency shift to the start position
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("PLLFreqSwp.ParamsGet", [Modulator_index], ["i"], ["i", "f", "f"])

    def PLLFreqSwp_Start(self, Modulator_index, Get_data, Sweep_direction):
        """
        PLLFreqSwp.Start
        Starts a frequency sweep.
        Before using this function, set the center frequency and frequency range in the Oscillation Control module. Also, set the other parameters (number of points...) in the frequency sweep module.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        -- Get data (unsigned int32), where if true (_1), the function will return the recorded Channels, the Data and the Characteristic values 
        -- Sweep direction (unsigned int32), where if true (_1), the sweep is done from lower to upper limit, and if false (_0) is done from upper to lower limit.
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Channels names size (int) is the size in bytes of the Channels names string array
        -- Number of channels (int) is the number of elements of the Channels names string array
        -- Channels names (1D array string) returns the list of channels names. The size of each string item comes right before it as integer 32
        -- Data rows (int) defines the number of rows of the Data array
        -- Data columns (int) defines the number of columns of the Data array
        -- Data (2D array float32) returns the data
        -- Resonance frequency (Hz) (float64) 
        -- Q factor (float64) 
        -- Phase (deg) (float32) at the resonance frequency
        -- Amplitude to excitation quotient (nm/mV) (float32) 
        -- Fit length (int) is the number of samples used to draw the fit line when the Parameter Estimation Method for Q is Phase Slope
        -- Number of points (int) is the number of points distributed over the frequency range
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("PLLFreqSwp.Start", [Modulator_index, Get_data, Sweep_direction], ["i", "I", "I"],
                              ["i", "i", "*+c", "i", "i", "2f", "d", "d", "f", "f", "i", "i"])

    def PLLFreqSwp_Stop(self, Modulator_index):
        """
        PLLFreqSwp.Stop
        Stops the sweep in the PLL Frequency Sweep  module.
        Arguments:
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        PLL Phase Sweep
        """
        return self.quickSend("PLLFreqSwp.Stop", [Modulator_index], ["i"], [])

    def PLLPhasSwp_Start(self, Modulator_index, Get_data):
        """
        PLLPhasSwp.Start
        Starts a phase sweep.
        Arguments: 
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        -- Get data (unsigned int32), where if true (_1), the function will return the recorded Channels and the Data
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Channels names size (int) is the size in bytes of the Channels names string array
        -- Number of channels (int) is the number of elements of the Channels names string array
        -- Channels names (1D array string) returns the list of channels names. The size of each string item comes right before it as integer 32
        -- Data rows (int) defines the number of rows of the Data array
        -- Data columns (int) defines the number of columns of the Data array
        -- Data (2D array float32) returns the data
        -- Error described in the Response message&gt;Body section
        .
        """
        return self.quickSend("PLLPhasSwp.Start", [Modulator_index, Get_data], ["i", "I"],
                              ["i", "i", "*+c", "i", "i", "2f"])

    def PLLPhasSwp_Stop(self, Modulator_index):
        """
        PLLPhasSwp.Stop
        Stops the sweep in the PLL Phase Sweep  module.
        Arguments:
        -- Modulator index (int) specifies which modulator or PLL to control. The valid values start from 1
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        PLL Signal Analyzer
        """
        return self.quickSend("PLLPhasSwp.Stop", [Modulator_index], ["i"], [])

    def PLLSignalAnlzr_Open(self):
        """
        PLLSignalAnlzr.Open
        Opens the PLL Signal Analyzer.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("PLLSignalAnlzr.Open", [], [], [])

    def PLLSignalAnlzr_ChSet(self, Channel_index):
        """
        PLLSignalAnlzr.ChSet
        Sets the channel of the PLL Signal Analyzer.
        Arguments: 
        -- Channel index (int) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("PLLSignalAnlzr.ChSet", [Channel_index], ["i"], [])

    def PLLSignalAnlzr_ChGet(self):
        """
        PLLSignalAnlzr.ChGet
        Returns the channel of the PLL Signal Analyzer.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Channel index (int) 
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("PLLSignalAnlzr.ChGet", [], [], ["i"])

    def PLLSignalAnlzr_TimebaseSet(self, Timebase, Update_rate):
        """
        PLLSignalAnlzr.TimebaseSet
        Sets the Time Base and Update Rate of the PLL Signal Analyzer.
        Arguments: 
        -- Timebase (int) Base is the index out of the list of Time Base values. Use the <i>PLLSignalAnlzr.TimebaseGet</i> function to get a list of the available time bases. Value -1 means no change
        -- Update rate (int) is the graph update rate, where 1 corresponds to the fastest rate and higher values reduce update speed, TCP traffic and CPU load. Value -1 means no change
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("PLLSignalAnlzr.TimebaseSet", [Timebase, Update_rate], ["i", "i"], [])

    def PLLSignalAnlzr_TimebaseGet(self):
        """
        PLLSignalAnlzr.TimebaseGet
        Returns the Time Base and Update Rate of the PLL Signal Analyzer.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Timebase (int) Base is the index out of the list of Time Base values. Use the <i>PLLSignalAnlzr.TimebaseGet</i> function to get a list of the available time bases. Value -1 means no change
        -- Update rate (int) is the graph update rate, where 1 corresponds to the fastest rate and higher values reduce update speed, TCP traffic and CPU load. Value -1 means no change
        -- Timebases size (int) is the size in bytes of the timebases array
        -- Timebases number (int) is the number of elements of the timebases array
        -- Timebases (1D array string) returns an array of timebases strings, where each string comes prepended by its size in bytes
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("PLLSignalAnlzr.TimebaseGet", [], [], ["i", "i", "i", "i", "*+c"])

    def PLLSignalAnlzr_TrigAuto(self):
        """
        PLLSignalAnlzr.TrigAuto
        Sets the trigger parameters to pre-defined values in the PLL Signal Analyzer.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("PLLSignalAnlzr.TrigAuto", [], [], [])

    def PLLSignalAnlzr_TrigRearm(self):
        """
        PLLSignalAnlzr.TrigRearm
        Rearms the trigger in the PLL Signal Analyzer.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("PLLSignalAnlzr.TrigRearm", [], [], [])

    def PLLSignalAnlzr_TrigSet(self, Trigger_mode, Trigger_source, Trigger_slope, Trigger_level, Trigger_position_s,
                               Arming_mode):
        """
        PLLSignalAnlzr.TrigSet
        Sets the trigger configuration in the PLL Signal Analyzer.
        Arguments: 
        -- Trigger mode (unsigned int16) sets the trigger mode, where 0_no change, 1_Immediate, and 2_Level
        -- Trigger source (int) set the signal index on which the trigger works.
        The list of available signals is returned by the <i>PLLSignalAnlzr.FFTPropsGet</i> function
        -- Trigger slope (unsigned int16) sets the triggering direction, where 0_no change, 1_Rising, and 2_Falling
        -- Trigger level (float64) sets the trigger level 
        -- Trigger position (s) (float64) sets the trigger position
        -- Arming mode (unsigned int16) sets whether the trigger is automatically (_2) or manually rearmed (_1). Value 0 means no change
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("PLLSignalAnlzr.TrigSet",
                              [Trigger_mode, Trigger_source, Trigger_slope, Trigger_level, Trigger_position_s,
                               Arming_mode], ["H", "i", "H", "d", "d", "H"], [])

    def PLLSignalAnlzr_TrigGet(self):
        """
        PLLSignalAnlzr.TrigGet
        Returns the trigger configuration in the PLL Signal Analyzer.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Trigger mode (unsigned int16) sets the trigger mode, where 0_no change, 1_Immediate, and 2_Level
        -- Trigger source (int) set the signal index on which the trigger works.
        The list of available signals is returned by the <i>PLLSignalAnlzr.FFTPropsGet</i> function
        -- Trigger slope (unsigned int16) sets the triggering direction, where 0_no change, 1_Rising, and 2_Falling
        -- Trigger level (float64) sets the trigger level 
        -- Trigger position (s) (float64) sets the trigger position
        -- Arming mode (unsigned int16) sets whether the trigger is automatically (_2) or manually rearmed (_1). Value 0 means no change
        -- Trigger source signals list size (int) is the size in bytes of the trigger source signals array
        -- Trigger source signals list number (int) is the number of elements of the trigger source signals array
        -- Trigger source signals list (1D array string) returns an array of trigger source signals, where each string comes prepended by its size in bytes
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("PLLSignalAnlzr.TrigGet", [], [], ["H", "i", "H", "d", "d", "H", "i", "i", "*+c"])

    def PLLSignalAnlzr_OsciDataGet(self):
        """
        PLLSignalAnlzr.OsciDataGet
        Returns the oscilloscope graph data from the PLL Signal Analyzer.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Data t0 (float64) is the timestamp of the 1st acquired point
        -- Data dt (float64) is the time distance between two acquired points
        -- Data Y size (int) is the number of data points in Data Y
        -- Data Y (1D array float64) is the data acquired in the oscilloscope
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("PLLSignalAnlzr.OsciDataGet", [], [], ["d", "d", "i", "*+d"])

    def PLLSignalAnlzr_FFTPropsSet(self, FFT_window, Averaging_mode, Weighting_mode, Count):
        """
        PLLSignalAnlzr.FFTPropsSet
        Sets the configuration in the spectrum section of the PLL Signal Analyzer.
        Arguments: 
        -- FFT window (unsigned int16) is the window function applied to the timed signal before calculating the Power Spectral Density. The indexes of the possible FFT windows are as follows: 
        0_no change, 1_None, 2_Hanning, 3_Hamming, 4_Blackman-Harris, 5_Exact Blackman, 6_Blackman, 7_Flat Top, 8_4 Term B-Harris, 9_7 Term B-Harris, and 10_Low Sidelobe
        -- Averaging mode (unsigned int16) where 0 is no change, 1 is None, 2 is Vector, 3 is RMS, and 4 is Peak Hold
        -- Weighting mode (unsigned int16) where 0 is no change, 1 is Linear, and 2 is Exponential
        -- Count (int) specifies the number of averages used for RMS and Vector averaging. 0 means no change.
        If weighting mode is Exponential, the averaging process is continuous and new spectral data have a higher weighting than older ones. 
        If weighting mode is Linear, the averaging combines count spectral records with equal weighting and then stops
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("PLLSignalAnlzr.FFTPropsSet", [FFT_window, Averaging_mode, Weighting_mode, Count],
                              ["H", "H", "H", "i"], [])

    def PLLSignalAnlzr_FFTPropsGet(self):
        """
        PLLSignalAnlzr.FFTPropsGet
        Returns the configuration in the spectrum section of the PLL Signal Analyzer.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- FFT window (unsigned int16) is the window function applied to the timed signal before calculating the Power Spectral Density. The indexes of the possible FFT windows are as follows: 
        0_None, 1_Hanning, 2_Hamming, 3_Blackman-Harris, 4_Exact Blackman, 5_Blackman, 6_Flat Top, 7_4 Term B-Harris, 8_7 Term B-Harris, and 9_Low Sidelobe
        -- Averaging mode (unsigned int16) where 0 is None, 1 is Vector, 2 is RMS, and 3 is Peak Hold
        -- Weighting mode (unsigned int16) where 0 is Linear, and 1 is Exponential
        -- Count (int) indicates the number of averages used for RMS and Vector averaging. 
        If weighting mode is Exponential, the averaging process is continuous and new spectral data have a higher weighting than older ones. 
        If weighting mode is Linear, the averaging combines count spectral records with equal weighting and then stops
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("PLLSignalAnlzr.FFTPropsGet", [], [], ["H", "H", "H", "i"])

    def PLLSignalAnlzr_FFTAvgRestart(self):
        """
        PLLSignalAnlzr.FFTAvgRestart
        Restarts the averaging in the spectrum section of the PLL Signal Analyzer.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("PLLSignalAnlzr.FFTAvgRestart", [], [], [])

    def PLLSignalAnlzr_FFTDataGet(self):
        """
        PLLSignalAnlzr.FFTDataGet
        Returns the spectrum graph data from the PLL Signal Analyzer.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Data f0 (float64) is the frequency of the 1st acquired point
        -- Data df (float64) is the frequency distance between two acquired points
        -- Data Y size (int) is the number of data points in Data Y
        -- Data Y (1D array float64) is the data acquired in the spectrum section
        -- Error described in the Response message&gt;Body section
        
        
        PLL Zoom FFT
        """
        return self.quickSend("PLLSignalAnlzr.FFTDataGet", [], [], ["d", "d", "i", "*d"])

    def PLLZoomFFT_Open(self):
        """
        PLLZoomFFT.Open
        Opens the PLL Zoom FFT module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("PLLZoomFFT.Open", [], [], [])

    def PLLZoomFFT_ChSet(self, Channel_index):
        """
        PLLZoomFFT.ChSet
        Sets the channel of the PLL Zoom FFT module.
        Selecting a channel (PLL1 or PLL2) in the Zoom FFT module is only available when the Oscillation Control 2 module is licensed.
        Arguments: 
        -- Channel index (int) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("PLLZoomFFT.ChSet", [Channel_index], ["i"], [])

    def PLLZoomFFT_ChGet(self):
        """
        PLLZoomFFT.ChGet
        Returns the channel of the PLL Zoom FFT module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Channel index (int) 
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("PLLZoomFFT.ChGet", [], [], ["i"])

    def PLLZoomFFT_AvgRestart(self):
        """
        PLLZoomFFT.AvgRestart
        Restarts the averaging in the PLL Zoom FFT module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("PLLZoomFFT.AvgRestart", [], [], [])

    def PLLZoomFFT_PropsSet(self, FFT_window, Averaging_mode, Weighting_mode, Count):
        """
        PLLZoomFFT.PropsSet
        Sets the configuration of the PLL Zoom FFT module.
        Arguments: 
        -- FFT window (unsigned int16) is the window function applied to the timed signal before calculating the Power Spectral Density. The indexes of the possible FFT windows are as follows: 
        0_no change, 1_None, 2_Hanning, 3_Hamming, 4_Blackman-Harris, 5_Exact Blackman, 6_Blackman, 7_Flat Top, 8_4 Term B-Harris, 9_7 Term B-Harris, and 10_Low Sidelobe
        -- Averaging mode (unsigned int16) where 0 is no change, 1 is None, 2 is Vector, 3 is RMS, and 4 is Peak Hold
        -- Weighting mode (unsigned int16) where 0 is no change, 1 is Linear, and 2 is Exponential
        -- Count (int) specifies the number of averages used for RMS and Vector averaging. 0 means no change.
        If weighting mode is Exponential, the averaging process is continuous and new spectral data have a higher weighting than older ones. 
        If weighting mode is Linear, the averaging combines count spectral records with equal weighting and then stops
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("PLLZoomFFT.PropsSet", [FFT_window, Averaging_mode, Weighting_mode, Count],
                              ["H", "H", "H", "i"], [])

    def PLLZoomFFT_PropsGet(self):
        """
        PLLZoomFFT.PropsGet
        Returns the configuration of the PLL Zoom FFT module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- FFT window (unsigned int16) is the window function applied to the timed signal before calculating the Power Spectral Density. The indexes of the possible FFT windows are as follows: 
        0_None, 1_Hanning, 2_Hamming, 3_Blackman-Harris, 4_Exact Blackman, 5_Blackman, 6_Flat Top, 7_4 Term B-Harris, 8_7 Term B-Harris, and 9_Low Sidelobe
        -- Averaging mode (unsigned int16) where 0 is None, 1 is Vector, 2 is RMS, and 3 is Peak Hold
        -- Weighting mode (unsigned int16) where 0 is Linear, and 1 is Exponential
        -- Count (int) indicates the number of averages used for RMS and Vector averaging. 
        If weighting mode is Exponential, the averaging process is continuous and new spectral data have a higher weighting than older ones. 
        If weighting mode is Linear, the averaging combines count spectral records with equal weighting and then stops
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("PLLZoomFFT.PropsGet", [], [], ["H", "H", "H", "i"])

    def PLLZoomFFT_DataGet(self):
        """
        PLLZoomFFT.DataGet
        Returns the data from the PLL Zoom FFT module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Data f0 (float64) is the frequency of the 1st acquired point
        -- Data df (float64) is the frequency distance between two acquired points
        -- Data Y size (int) is the number of data points in Data Y
        -- Data Y (1D array float64) is the acquired data 
        -- Error described in the Response message&gt;Body section
        
        OC Sync module
        
        """
        return self.quickSend("PLLZoomFFT.DataGet", [], [], ["d", "d", "i", "*d"])

    def OCSync_AnglesSet(self, Channel_1_on_angle_deg, Channel_1_off_angle_deg, Channel_2_on_angle_deg,
                         Channel_3_off_angle_deg):
        """
        OCSync.AnglesSet
        Sets the angle values used in the OC Sync module for digital channel 1 and 2.
        The On angle is the angle of the Oscillation Control output (excitation) at which the corresponding digital channel is set to high.
        The Off angle is the angle of the Oscillation Control output (excitation) at which the corresponding digital channel is set to low.
        Arguments: 
        -- Channel 1 on angle (deg) (float32) 
        -- Channel 1 off angle (deg) (float32) 
        -- Channel 2 on angle (deg) (float32) 
        -- Channel 3 off angle (deg) (float32) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("OCSync.AnglesSet",
                              [Channel_1_on_angle_deg, Channel_1_off_angle_deg, Channel_2_on_angle_deg,
                               Channel_3_off_angle_deg], ["f", "f", "f", "f"], [])

    def OCSync_AnglesGet(self):
        """
        OCSync.AnglesGet
        Returns the angle values used in the OC Sync module for digital channel 1 and 2.
        The On angle is the angle of the Oscillation Control output (excitation) at which the corresponding digital channel is set to high.
        The Off angle is the angle of the Oscillation Control output (excitation) at which the corresponding digital channel is set to low.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Channel 1 on angle (deg) (float32) 
        -- Channel 1 off angle (deg) (float32) 
        -- Channel 2 on angle (deg) (float32) 
        -- Channel 3 off angle (deg) (float32) 
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OCSync.AnglesGet", [], [], ["f", "f", "f", "f"])

    def OCSync_LinkAnglesSet(self, Link_angles_Channel_1, Link_angles_Channel_2):
        """
        OCSync.LinkAnglesSet
        Sets the status of the Link functionality in the OC Sync module for digital channel 1 and 2.
        When Link Angles is set, the difference between Off angle and On angle is kept constant and only On angle can be modified.
        When Unlink Angles is set, both angles can be set independently.
        When No Change is set, this function won't modify the status of the corresponding Link button in the OC Sync module. 
        Arguments: 
        -- Link angles Channel 1 (unsigned int32), where 0_no change, 1_Link Angles, and 2_Unlink angles
        -- Link angles Channel 2 (unsigned int32), where 0_no change, 1_Link Angles, and 2_Unlink angles
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("OCSync.LinkAnglesSet", [Link_angles_Channel_1, Link_angles_Channel_2], ["I", "I"], [])

    def OCSync_LinkAnglesGet(self):
        """
        OCSync.LinkAnglesGet
        Returns the status of the Link functionality in the OC Sync module for digital channel 1 and 2.
        When Link Angles is used, the difference between Off angle and On angle is kept constant and only On angle can be modified.
        When Unlink Angles is used, both angles can be set independently.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Link angles Channel 1 (unsigned int32), where 0_ Unlink angles, and 1_Link Angles
        -- Link angles Channel 2 (unsigned int32), where 0_ Unlink angles, and 1_Link Angles
        -- Error described in the Response message&gt;Body section
        
        Script
        """
        return self.quickSend("OCSync.LinkAnglesGet", [], [], ["I", "I"])

    def Script_Load(self, Script_file_path, Load_session):
        """
        Script.Load
        Loads a script in the script module.
        Arguments:
        -- Script file path size (int) is the number of characters of the script file path string
        -- Script file path (string) is the path of the script file to load
        -- Load session (unsigned int32) automatically loads the scripts from the session file bypassing the script file path argument, where 0_False and 1_True  
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Script.Load", [Script_file_path, Load_session], ["+*c", "I"],
                              [])

    def Script_Save(self, Script_file_path, Save_session):
        """
        Script.Save
        Saves the current script in the specified .ini file.
        Arguments:
        -- Script file path size (int) is the number of characters of the script file path string
        -- Script file path (string) is the path of the script file to save
        -- Save session (unsigned int32) automatically saves the current script into the session file bypassing the script file path argument, where 0_False and 1_True  
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Script.Save", [Script_file_path, Save_session], ["+*c", "I"],
                              [])

    def Script_Deploy(self, Script_index):
        """
        Script.Deploy
        Deploys a script in the script module.
        Arguments: 
        -- Script index (int) sets the script to deploy and covers a range from 0 (first script) to the total number of scripts minus one. A value of -1 sets the currently selected script to deploy.
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Script.Deploy", [Script_index], ["i"], [])

    def Script_Undeploy(self, Script_index):
        """
        Script.Undeploy
        Undeploys a script in the script module.
        Arguments: 
        -- Script index (int) sets the script to undeploy and covers a range from 0 (first script) to the total number of scripts minus one. A value of -1 sets the currently selected script to undeploy.
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Script.Undeploy", [Script_index], ["i"], [])

    def Script_Run(self, Script_index, Wait_until_script_finishes):
        """
        Script.Run
        Runs a script in the script module.
        Arguments: 
        -- Script index (int) sets the script to run and covers a range from 0 (first script) to the total number of scripts minus one. A value of -1 sets the currently selected script to run.
        -- Wait until script finishes (unsigned int32), where 0_False and 1_True 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Script.Run", [Script_index, Wait_until_script_finishes], ["i", "I"], [])

    def Script_Stop(self):
        """
        Script.Stop
        Stops the running script in the script module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Script.Stop", [], [], [])

    def Script_ChsGet(self, Acquire_buffer):
        """
        Script.ChsGet
        Returns the list of acquired channels in the Script module.
        Arguments: 
        -- Acquire buffer (unsigned int16) sets the Acquire Buffer number from which to read the list of channels. Valid values are 1 (_Acquire Buffer 1) and 2 (_Acquire Buffer 2).
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Number of channels (int) is the number of recorded channels. It defines the size of the Channel indexes array
        -- Channel indexes (1D array int) are the indexes of recorded channels. The indexes are comprised between 0 and 23 for the 24 signals assigned in the Signals Manager.
        To get the signal name and its corresponding index in the list of the 128 available signals in the Nanonis Controller, use the <i>Signals.InSlotsGet</i> function
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Script.ChsGet", [Acquire_buffer], ["H"], ["i", "*i"])

    def Script_ChsSet(self, Acquire_buffer, Channel_indexes):
        """
        Script.ChsSet
        Sets the list of acquired channels in the Script module.
        Arguments: 
        -- Acquire buffer (unsigned int16) sets the Acquire Buffer number from which to set the list of channels. Valid values are 1 (_Acquire Buffer 1) and 2 (_Acquire Buffer 2).
        -- Number of channels (int) is the number of recorded channels. It defines the size of the Channel indexes array
        -- Channel indexes (1D array int) are the indexes of recorded channels. The indexes are comprised between 0 and 23 for the 24 signals assigned in the Signals Manager.
        To get the signal name and its corresponding index in the list of the 128 available signals in the Nanonis Controller, use the <i>Signals.InSlotsGet</i> function
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Script.ChsSet", [Acquire_buffer, Channel_indexes], ["H", "+*i"],
                              [])

    def Script_DataGet(self, Acquire_buffer, Sweep_number):
        """
        Script.DataGet
        Returns the data acquired in the Script module.
        Arguments: 
        -- Acquire buffer (unsigned int16) sets the Acquire Buffer number from which to read the acquired data. Valid values are 1 (_Acquire Buffer 1) and 2 (_Acquire Buffer 2).
        -- Sweep number (int) selects the sweep this function will return the data from. Each sweep is configured as such in the script and it corresponds to each plot displayed in the graphs of the Script module. The sweep numbers start at 0.
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Data rows (int) defines the number of rows of the Data array
        -- Data columns (int) defines the number of columns of the Data array
        -- Data (2D array float32) returns the script data
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Script.DataGet", [Acquire_buffer, Sweep_number], ["H", "i"], ["i", "i", "2f"])

    def Script_Autosave(self, Acquire_buffer, Sweep_number, All_sweeps_to_same_file):
        """
        Script.Autosave
        Saves automatically to file the data stored in the Acquire Buffers after running a script in the Script module.
        Arguments: 
        -- Acquire buffer (unsigned int16) sets the Acquire Buffer number from which to save the data. 
        Valid values are 0 (_Acquire Buffer 1 & Acquire Buffer 2), 1 (_Acquire Buffer 1), and 2 (_Acquire Buffer 2).
        -- Sweep number (int) selects the sweep this function will save the data for. 
        Each sweep is configured as such in the script and it corresponds to each plot displayed in the graphs of the Script module. 
        The sweep numbers start at 0. A value of -1 saves all acquired sweeps.
        -- All sweeps to same file (unsigned int32) decides if all sweeps defined by the Sweep number parameter are saved to the same file (_1) or not (_0).
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        Interferometer
        """
        return self.quickSend("Script.Autosave", [Acquire_buffer, Sweep_number, All_sweeps_to_same_file],
                              ["H", "i", "I"], [])

    def Interf_CtrlOnOffSet(self, Status):
        """
        Interf.CtrlOnOffSet
        Switches the interferometer controller On or Off.
        Arguments: 
        -- Status (unsigned int32) switches the interferometer controller Off (_0) or On (_1)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Interf.CtrlOnOffSet", [Status], ["I"], [])

    def Interf_CtrlOnOffGet(self):
        """
        Interf.CtrlOnOffGet
        Returns the status of the interferometer controller.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Status (unsigned int32) indicates whether the interferometer controller is Off (_0) or On (_1)
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Interf.CtrlOnOffGet", [], [], ["I"])

    def Interf_CtrlPropsSet(self, Integral, Proportional, Sign):
        """
        Interf.CtrlPropsSet
        Sets the properties of the interferometer controller.
        Arguments: 
        -- Integral (float32) sets the integral gain of the controller
        -- Proportional (float32) sets the proportional gain of the controller
        -- Sign (unsigned int32) sets the sign of the controller. If 0, means negative, and if 1 means positive
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Interf.CtrlPropsSet", [Integral, Proportional, Sign], ["f", "f", "I"], [])

    def Interf_CtrlPropsGet(self):
        """
        Interf.CtrlPropsGet
        Returns the properties of the interferometer controller.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Integral (float32) returns the integral gain of the controller
        -- Proportional (float32) returns the proportional gain of the controller
        -- Sign (unsigned int32) returns the sign of the controller. If 0, means negative, and if 1 means positive
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Interf.CtrlPropsGet", [], [], ["f", "f", "I"])

    def Interf_WPiezoSet(self, W_piezo):
        """
        Interf.WPiezoSet
        Sets the position of the W-piezo.
        To change the position of the W-piezo, the interferometer controller must be switched Off.
        Arguments: 
        -- W-piezo (float32) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Interf.WPiezoSet", [W_piezo], ["f"], [])

    def Interf_WPiezoGet(self):
        """
        Interf.WPiezoGet
        Returns the position of the W-piezo.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- W-piezo (float32) 
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Interf.WPiezoGet", [], [], ["f"])

    def Interf_ValGet(self):
        """
        Interf.ValGet
        Returns the interferometer value.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Interferometer value (float32) 
        -- Error described in the Response message&gt;Body section
        """
        return self.quickSend("Interf.ValGet", [], [], ["f"])

    def Interf_CtrlCalibrOpen(self):
        """
        Interf.CtrlCalibrOpen
        Opens the calibration panel for the interferometer controller.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Interf.CtrlCalibrOpen", [], [], [])

    def Interf_CtrlReset(self):
        """
        Interf.CtrlReset
        Resets the interferometer controller.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Interf.CtrlReset", [], [], [])

    def Interf_CtrlNullDefl(self):
        """
        Interf.CtrlNullDefl
        Applies null deflection to the interferometer controller.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        Laser module
        """
        return self.quickSend("Interf.CtrlNullDefl", [], [], [])

    def Laser_OnOffSet(self, Status):
        """
        Laser.OnOffSet
        Switches the laser On or Off.
        Arguments: 
        -- Status (unsigned int32) switches the laser Off (_0) or On (_1)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Laser.OnOffSet", [Status], ["I"], [])

    def Laser_OnOffGet(self):
        """
        Laser.OnOffGet
        Returns the status of the laser.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Status (unsigned int32) indicates whether the laser is Off (_0) or On (_1)
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Laser.OnOffGet", [], [], ["I"])

    def Laser_PropsSet(self, Laser_Setpoint):
        """
        Laser.PropsSet
        Sets the laser properties.
        Arguments: 
        -- Laser Setpoint (float32) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Laser.PropsSet", [Laser_Setpoint], ["f"], [])

    def Laser_PropsGet(self):
        """
        Laser.PropsGet
        Returns the laser properties.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Laser Setpoint (float32) 
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Laser.PropsGet", [], [], ["f"])

    def Laser_PowerGet(self):
        """
        Laser.PowerGet
        Returns the laser power.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Laser power (float32) 
        -- Error described in the Response message&gt;Body section
        
        Beam Deflection
        """
        return self.quickSend("Laser.PowerGet", [], [], ["f"])

    def BeamDefl_HorConfigSet(self, Name, Units, Calibration, Offset):
        """
        BeamDefl.HorConfigSet
        Sets the configuration of the horizontal deflection.
        Arguments: 
        -- Name size (int) is the number of bytes of the Name string
        -- Name (string) is the name of the signal
        -- Units size (int) is the number of bytes of the Units string
        -- Units (string) is the physical units of the signal
        -- Calibration (float32) 
        -- Offset (float32) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("BeamDefl.HorConfigSet", [Name, Units, Calibration, Offset],
                              ["+*c", "+*c", "f", "f"], [])

    def BeamDefl_HorConfigGet(self):
        """
        BeamDefl.HorConfigGet
        Returns the configuration of the horizontal deflection.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Name size (int) is the number of bytes of the Name string
        -- Name (string) is the name of the signal
        -- Units size (int) is the number of bytes of the Units string
        -- Units (string) is the physical units of the signal
        -- Calibration (float32) 
        -- Offset (float32) 
        -- Error described in the Response message&gt;Body section
        
        
        
        
        
        
        """
        return self.quickSend("BeamDefl.HorConfigGet", [], [], ["i", "*-c", "i", "*-c", "f", "f"])

    def BeamDefl_VerConfigSet(self, Name, Units, Calibration, Offset):
        """
        BeamDefl.VerConfigSet
        Sets the configuration of the vertical deflection.
        Arguments: 
        -- Name size (int) is the number of bytes of the Name string
        -- Name (string) is the name of the signal
        -- Units size (int) is the number of bytes of the Units string
        -- Units (string) is the physical units of the signal
        -- Calibration (float32) 
        -- Offset (float32) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("BeamDefl.VerConfigSet", [Name, Units, Calibration, Offset],
                              ["+*c", "+*c", "f", "f"], [])

    def BeamDefl_VerConfigGet(self):
        """
        BeamDefl.VerConfigGet
        Returns the configuration of the vertical deflection.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Name size (int) is the number of bytes of the Name string
        -- Name (string) is the name of the signal
        -- Units size (int) is the number of bytes of the Units string
        -- Units (string) is the physical units of the signal
        -- Calibration (float32) 
        -- Offset (float32) 
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("BeamDefl.VerConfigGet", [], [], ["i", "*-c", "i", "*-c", "f", "f"])

    def BeamDefl_IntConfigSet(self, Name, Units, Calibration, Offset):
        """
        BeamDefl.IntConfigSet
        Sets the configuration of the intensity signal.
        Arguments: 
        -- Name size (int) is the number of bytes of the Name string
        -- Name (string) is the name of the signal
        -- Units size (int) is the number of bytes of the Units string
        -- Units (string) is the physical units of the signal
        -- Calibration (float32) 
        -- Offset (float32) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        """
        return self.quickSend("BeamDefl.IntConfigSet", [Name, Units, Calibration, Offset],
                              ["+*c", "+*c", "f", "f"], [])

    def BeamDefl_IntConfigGet(self):
        """
        BeamDefl.IntConfigGet
        Returns the configuration of the intensity signal.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Name size (int) is the number of bytes of the Name string
        -- Name (string) is the name of the signal
        -- Units size (int) is the number of bytes of the Units string
        -- Units (string) is the physical units of the signal
        -- Calibration (float32) 
        -- Offset (float32) 
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("BeamDefl.IntConfigGet", [], [], ["i", "*-c", "i", "*-c", "f", "f"])

    def BeamDefl_AutoOffset(self, Deflection_signal):
        """
        BeamDefl.AutoOffset
        Auto-offsets the Beam Deflection signal.
        This function works like the corresponding buttons on the beam deflection module. It adds the current deflection value (vertical deflection, horizontal deflection or intensity) to the offset so the deflection signal is close to 0.
        Arguments: 
        -- Deflection signal (unsigned int16) selects the signal to correct the offset for. 0 means Horizontal, 1 means Vertical, and 2 means Intensity
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        Signals
        """
        return self.quickSend("BeamDefl.AutoOffset", [Deflection_signal], ["H"], [])

    def Signals_NamesGet(self):
        """
        Signals.NamesGet
        Returns the signals names list of the 128 signals available in the software.
        The 128 signals are physical inputs, physical outputs and internal channels. By searching in the list the channel’s name you are interested in, you can get its index (0-127).
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Signals names size (int) is the size in bytes of the signals names array
        -- Signals names number (int) is the number of elements of the signals names array
        -- Signals names (1D array string) returns an array of signals names strings, where each string comes prepended by its size in bytes
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Signals.NamesGet", [], [], ["i", "i", "*+c"])

    def Signals_CalibrGet(self, Signal_index):
        """
        Signals.CalibrGet
        Returns the calibration and offset of the selected signal.
        Arguments: 
        -- Signal index (int) is comprised between 0 and 127
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Calibration per volt (float32) 
        -- Offset in physical units (float32) 
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("Signals.CalibrGet", [Signal_index], ["i"], ["f", "f"])

    def Signals_RangeGet(self, Signal_index):
        """
        Signals.RangeGet
        Returns the range limits of the selected signal.
        Arguments: 
        -- Signal index (int) is comprised between 0 and 127
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Maximum limit (float32) 
        -- Minimum limit (float32) 
        -- Error described in the Response message&gt;Body section
        """
        return self.quickSend("Signals.RangeGet", [Signal_index], ["i"], ["f", "f"])

    def Signals_ValGet(self, Signal_index, Wait_for_newest_data):
        """
        Signals.ValGet
        Returns the current value of the selected signal (oversampled during the Acquisition Period time, Tap).
        Signal measurement principle:
        The signal is continuously oversampled with the Acquisition Period time, Tap, specified in the TCP receiver module. Every Tap second, the oversampled data is "published". This VI function waits for the next oversampled data to be published and returns its value. Calling this function does not trigger a signal measurement; it waits for data to be published! Thus, this function returns a value 0 to Tap second after being called.
        An important consequence is that if you change a signal and immediately call this function to read a measurement you might get "old" data (i.e. signal data measured before you changed the signal). The solution to get only new data is to set Wait for newest data to True. In this case, the first published data is discarded and only the second one is returned.
        Arguments: 
        -- Signal index (int) is comprised between 0 and 127
        -- Wait for newest data (unsigned int32) selects whether the function returns the next available signal value or if it waits for a full period of new data. If False, this function returns a value 0 to Tap seconds after being called. If True, the function discard the first oversampled signal value received but returns the second value received. Thus, the function returns a value Tap to 2*Tap seconds after being called. It could be 0_False or 1_True
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Signal value (float32) is the value of the selected signal in physical units
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Signals.ValGet", [Signal_index, Wait_for_newest_data], ["i", "I"], ["f"])

    def Signals_ValsGet(self, Signals_indexes, Wait_for_newest_data):
        """
        Signals.ValsGet
        Returns the current values of the selected signals (oversampled during the Acquisition Period time, Tap).
        Arguments: 
        -- Signals indexes size (int) is the size of the Signals indexes array
        -- Signals indexes (1D array int) sets the selection of signals indexes, comprised between 0 and 127
        -- Wait for newest data (unsigned int32) selects whether the function returns the next available signal value or if it waits for a full period of new data. If False, this function returns a value 0 to Tap seconds after being called. If True, the function discard the first oversampled signal value received but returns the second value received. Thus, the function returns a value Tap to 2*Tap seconds after being called. It could be 0_False or 1_True
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Signals values size (int) is the size of the Signals values array
        -- Signals values (1D array float32) returns the values of the selected signals in physical units
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Signals.ValsGet", [Signals_indexes, Wait_for_newest_data],
                              ["+*i", "I"], ["i", "*f"])

    def Signals_MeasNamesGet(self):
        """
        Signals.MeasNamesGet
        Returns the list of measurement channels names available in the software.
        Important Note: The Measurement channels don't correspond to the Signals. Measurement channels are used in sweepers whereas the Signals are used by the graphs and other modules.
        By searching in the list the channels's names you are interested in, you can know its index. This index is then used e.g. to get/set the recorded channels in Sweepers, for example by using the <i>GenSwp.ChannelsGet</i> and <i>GenSwp.ChannelsSet</i> functions for the 1D Sweeper.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Measurement channels list size (int) is the size in bytes of the Measurement channels list array
        -- Number of Measurement channels (int) is the number of elements of the Measurement channels list array
        -- Measurement channels list (1D array string) returns an array of names, where each array element is preceded by its size in bytes
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Signals.MeasNamesGet", [], [], ["i", "i", "*+c"])

    def Signals_AddRTGet(self):
        """
        Signals.AddRTGet
        Returns the list of names of additional RT signals available, and the names of the signals currently assigned to the Internal 23 and 24 signals.
        This can be found in the Signals Manager. But this assignment does not mean that they are available in the software. 
        In order to have them in the list of 24 signals to display in the graphs and to acquire in some modules, Internal 23 and 24 must be in turn assigned to one of the 24 slots of the Signals Manager. This can be done programmatically through the <i>Signals.InSlotSet</i> function.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Additional RT signals names size (int) is the size in bytes of the Additional RT signals names array
        -- Number of Additional RT signals (int) is the number of elements of the Additional RT signals names array
        -- Additional RT signals names (1D array string) returns the list of additional RT signals which can be assigned to Internal 23 and 24. Each array element is preceded by its size in bytes
        -- Additional RT signal 1 (string) is the name of the RT signal assigned to the Internal 23 signal
        -- Additional RT signal 2 (string) is the name of the RT signal assigned to the Internal 24 signal
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Signals.AddRTGet", [], [], ["i", "i", "*+c", "i", "*-c", "i", "*-c"])

    def Signals_AddRTSet(self, Additional_RT_signal_1, Additional_RT_signal_2):
        """
        Signals.AddRTSet
        Assigns additional RT signals to the Internal 23 and 24 signals in the Signals Manager.
        This function links advanced RT signals to Internal 23 and Internal 24, but in order to have them in the list of 24 signals to display in the graphs and to acquire in the modules, Internal 23 and 24 must be assigned to one of the 24 slots of the Signals Manager. This can be done programmatically through the <i>Signals.InSlotSet</i> function.
        Arguments:
        -- Additional RT signal 1 (int) is the index of the RT signal assigned to the Internal 23 signal
        -- Additional RT signal 2 (int) is the index of the RT signal assigned to the Internal 24 signal
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        User Inputs
        """
        return self.quickSend("Signals.AddRTSet", [Additional_RT_signal_1, Additional_RT_signal_2], ["i", "i"], [])

    def UserIn_CalibrSet(self, Input_index, Calibration_per_volt, Offset_in_physical_units):
        """
        UserIn.CalibrSet
        Sets the calibration of the selected user input.
        Arguments: 
        -- Input index (int) sets the input to be used, where index could be any value from 1 to the available inputs
        -- Calibration per volt (float32) 
        -- Offset in physical units (float32) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        User Outputs
        """
        return self.quickSend("UserIn.CalibrSet", [Input_index, Calibration_per_volt, Offset_in_physical_units],
                              ["i", "f", "f"], [])

    def UserOut_ModeSet(self, Output_index, Output_mode):
        """
        UserOut.ModeSet
        Sets the mode (User Output, Monitor, Calculated signal) of the selected user output channel.
        Arguments: 
        -- Output index (int) sets the output to be used, where index could be any value from 1 to the number of available outputs
        -- Output mode (unsigned int16) sets the output mode of the selected output, where 0_User Output, 1_Monitor, 2_Calc.Signal
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("UserOut.ModeSet", [Output_index, Output_mode], ["i", "H"], [])

    def UserOut_ModeGet(self, Output_index):
        """
        UserOut.ModeGet
        Returns the mode (User Output, Monitor, Calculated signal) of the selected user output channel.
        Arguments: 
        -- Output index (int) sets the output to be used, where index could be any value from 1 to the number of available outputs
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Output mode (unsigned int16) returns the output mode of the selected output, where 0_User Output, 1_Monitor, 2_Calc.Signal, 3_Override
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("UserOut.ModeGet", [Output_index], ["i"], ["H"])

    def UserOut_MonitorChSet(self, Output_index, Monitor_channel_index):
        """
        UserOut.MonitorChSet
        Sets the monitor channel of the selected output channel.
        Arguments: 
        -- Output index (int) sets the output to be used, where index could be any value from 1 to the number of available outputs
        -- Monitor channel index (int) sets the index of the channel to monitor. The index is comprised between 0 and 127 for the physical inputs, physical outputs, and internal channels. To see which signal has which index, see <i>Signals.NamesGet</i> function
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("UserOut.MonitorChSet", [Output_index, Monitor_channel_index], ["i", "i"], [])

    def UserOut_MonitorChGet(self, Output_index):
        """
        UserOut.MonitorChGet
        Returns the monitor channel of the selected output channel.
        Arguments: 
        -- Output index (int) sets the output to be used, where index could be any value from 1 to the number of available outputs
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Monitor channel index (int) returns the index of the channel to monitor. The index is comprised between 0 and 127 for the physical inputs, physical outputs, and internal channels. To see which signal has which index, see <i>Signals.NamesGet</i> function
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("UserOut.MonitorChGet", [Output_index], ["i"], ["i"])

    def UserOut_ValSet(self, Output_index, Output_value):
        """
        UserOut.ValSet
        Sets the value of the selected user output channel.
        Arguments: 
        -- Output index (int) sets the output to be used, where index could be any value from 1 to the number of available outputs
        -- Output value (float32) is the value applied to the selected user output in physical units
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("UserOut.ValSet", [Output_index, Output_value], ["i", "f"], [])

    def UserOut_CalibrSet(self, Output_index, Calibration_per_volt, Offset_in_physical_units):
        """
        UserOut.CalibrSet
        Sets the calibration of the selected user output or monitor channel.
        Arguments: 
        -- Output index (int) sets the output to be used, where index could be any value from 1 to the number of available outputs
        -- Calibration per volt (float32) 
        -- Offset in physical units (float32) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("UserOut.CalibrSet", [Output_index, Calibration_per_volt, Offset_in_physical_units],
                              ["i", "f", "f"], [])

    def UserOut_CalcSignalNameSet(self, Output_index, Calculated_signal_name):
        """
        UserOut.CalcSignalNameSet
        Sets the Calculated Signal name of the selected output channel.
        Arguments: 
        -- Output index (int) sets the output to be used, where index could be any value from 1 to the number of available outputs
        -- Calculated signal name size (int) is the number of characters of the Calculated signal name string
        -- Calculated signal name (string) is the name of the calculated signal configured for the selected output
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("UserOut.CalcSignalNameSet",
                              [Output_index, Calculated_signal_name], ["i", "+*c"], [])

    def UserOut_CalcSignalNameGet(self, Output_index):
        """
        UserOut.CalcSignalNameGet
        Returns the Calculated Signal name of the selected output channel.
        Arguments: 
        -- Output index (int) sets the output to be used, where index could be any value from 1 to the number of available outputs
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Calculated signal name size (int) is the number of characters of the Calculated signal name string
        -- Calculated signal name (string) is the name of the calculated signal configured for the selected output
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("UserOut.CalcSignalNameGet", [Output_index], ["i"], ["i", "*-c"])

    def UserOut_CalcSignalConfigSet(self, Output_index, Signal_1, Operation, Signal_2):
        """
        UserOut.CalcSignalConfigSet
        Sets the configuration of the Calculated Signal for the selected output channel.
        The configuration is a math operation between 2 signals, or the logarithmic value of one signal.
        The possible values for the math operation are: 
        0_None, 1_Add, 1_Subtract, 3_Multiply, 4_Divide, 6_Log
        
        Arguments: 
        -- Output index (int) sets the output to be used, where index could be any value from 1 to the number of available outputs
        -- Signal 1 (unsigned int16) is the signal index (from 0 to 127) used as the first signal of the formula. 
        -- Operation (unsigned int16) is the math operation. 
        -- Signal 2 (unsigned int16) is the signal index (from 0 to 127) used as the second signal of the formula.
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        -- 
        
        """
        return self.quickSend("UserOut.CalcSignalConfigSet", [Output_index, Signal_1, Operation, Signal_2],
                              ["i", "H", "H", "H"], [])

    def UserOut_CalcSignalConfigGet(self, Output_index):
        """
        UserOut.CalcSignalConfigGet
        Returns the configuration of the Calculated Signal for the selected output channel.
        The configuration is a math operation between 2 signals, or the logarithmic value of one signal.
        The possible values for the math operation are: 
        0_None, 1_Add, 1_Subtract, 3_Multiply, 4_Divide, 6_Log
        
        Arguments: 
        -- Output index (int) sets the output to be used, where index could be any value from 1 to the number of available outputs
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Signal 1 (unsigned int16) is the signal index (from 0 to 127) used as the first signal of the formula. 
        -- Operation (unsigned int16) is the math operation. 
        -- Signal 2 (unsigned int16) is the signal index (from 0 to 127) used as the second signal of the formula.
        -- Error described in the Response message&gt;Body section
        
        
        
        
        
        """
        return self.quickSend("UserOut.CalcSignalConfigGet", [Output_index], ["i"], ["H", "H", "H"])

    def UserOut_LimitsSet(self, Output_index, Upper_limit, Lower_limit):
        """
        UserOut.LimitsSet
        Sets the physical limits (in calibrated units) of the selected output channel.
        Arguments: 
        -- Output index (int) sets the output to be used, where index could be any value from 1 to the number of available outputs
        -- Upper limit (float32) defines the upper physical limit of the user output
        -- Lower limit (float32) defines the lower physical limit of the user output
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("UserOut.LimitsSet", [Output_index, Upper_limit, Lower_limit], ["i", "f", "f"], [])

    def UserOut_LimitsGet(self, Output_index):
        """
        UserOut.LimitsGet
        Returns the physical limits (in calibrated units) of the selected output channel.
        Arguments: 
        -- Output index (int) sets the output to be used, where index could be any value from 1 to the number of available outputs
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Upper limit (float32) defines the upper physical limit of the user output
        -- Lower limit (float32) defines the lower physical limit of the user output
        -- Error described in the Response message&gt;Body section 
        
        
        
        
        
        Digital Lines
        """
        return self.quickSend("UserOut.LimitsGet", [Output_index], ["i"], ["f", "f"])

    def DigLines_PropsSet(self, Digital_line, Port, Direction, Polarity):
        """
        DigLines.PropsSet
        Configures the properties of a digital line.
        Arguments: 
        -- Digital line (unsigned int32) defines the line to configure, from 1 to 8
        -- Port (unsigned int32) selects the digital port, where 0_Port A, 1_Port B, 2_Port C, 3_Port D 
        -- Direction (unsigned int32) is the direction of the selected digital line, where 0_Input, 1_Output
        -- Polarity (unsigned int32), where 0_Low active, 1_High active
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("DigLines.PropsSet", [Digital_line, Port, Direction, Polarity], ["I", "I", "I", "I"], [])

    def DigLines_OutStatusSet(self, Port, Digital_line, Status):
        """
        DigLines.OutStatusSet
        Sets the status of a digital output line.
        Arguments: 
        -- Port (unsigned int32) selects the digital port, where 0_Port A, 1_Port B, 2_Port C, 3_Port D
        -- Digital line (unsigned int32) defines the output line to configure, from 1 to 8
        -- Status (unsigned int32) sets whether the output is active or inactive, where 0_Inactive, 1_Active
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("DigLines.OutStatusSet", [Port, Digital_line, Status], ["I", "I", "I"], [])

    def DigLines_TTLValGet(self, Port):
        """
        DigLines.TTLValGet
        Reads the actual TTL voltages present at the pins of the selected port.
        Arguments: 
        -- Port (unsigned int16) selects the digital port, where 0_Port A, 1_Port B, 2_Port C, 3_Port D
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- TTL voltages size (int) is the size of the TTL voltages array
        -- TTL voltages (1D array unsigned int32) sets whether the output is active or inactive, where 0_Inactive, 1_Active
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("DigLines.TTLValGet", [Port], ["H"], ["i", "*I"])

    def DigLines_Pulse(self, Port, Digital_lines, Pulse_width_s, Pulse_pause_s, Number_of_pulses,
                       Wait_until_finished):
        """
        DigLines.Pulse
        Configures and starts the pulse generator on the selected digital outputs.
        Arguments: 
        -- Port (unsigned int16) selects the digital port, where 0_Port A, 1_Port B, 2_Port C, 3_Port D
        -- Digital lines size (int) is the size of the Digital lines array
        -- Digital lines (1D array unsigned int8) defines the output lines to pulse, from 1 to 8
        -- Pulse width (s) (float32) defines how long the outputs are active
        -- Pulse pause (s) (float32) defines how long the outputs are inactive
        -- Number of pulses (int) defines how many pulses to generate, where valid values are from 1 to 32767
        -- Wait until finished (unsigned int32), if True this function waits until all pulses have been generated before the response is sent back, where 0_False, 1_True
         
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        Data Logger
        """
        return self.quickSend("DigLines.Pulse",
                              [Port, Digital_lines, Pulse_width_s, Pulse_pause_s, Number_of_pulses,
                               Wait_until_finished], ["H", "+*b", "f", "f", "i", "I"], [])

    def DataLog_Open(self):
        """
        DataLog.Open
        Opens the Data Logger module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("DataLog.Open", [], [], [])

    def DataLog_Start(self):
        """
        DataLog.Start
        Starts the acquisition in the Data Logger module.
        Before using this function, select the channels to record in the Data Logger.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("DataLog.Start", [], [], [])

    def DataLog_Stop(self):
        """
        DataLog.Stop
        Stops the acquisition in the Data Logger module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("DataLog.Stop", [], [], [])

    def DataLog_StatusGet(self):
        """
        DataLog.StatusGet
        Returns the status parameters from the Data Logger module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Start time size (int) returns the number of bytes corresponding to the Start time string
        -- Start time (string) returns a timestamp of the moment when the acquisition started
        -- Acquisition elapsed hours (unsigned int16) returns the number of hours already passed since the acquisition started
        -- Acquisition elapsed minutes (unsigned int16) returns the number of minutes displayed on the Data Logger
        -- Acquisition elapsed seconds (float32) returns the number of seconds displayed on the Data Logger
        -- Stop time size (int) returns the number of bytes corresponding to the Stop time string
        -- Stop time (string) returns a timestamp of the moment when the acquisition Stopped
        -- Saved file path size (int) returns the number of bytes corresponding to the Saved file path string
        -- Saved file path (string) returns the path of the last saved file
        -- Saved points (int) returns the number of points (averaged samples) already saved into file. 
        This parameter updates while running the acquisition, every time a file is saved
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("DataLog.StatusGet", [], [], ["i", "*-c", "H", "H", "f", "i", "*-c", "i", "*-c", "i"])

    def DataLog_ChsSet(self, Channel_indexes):
        """
        DataLog.ChsSet
        Sets the list of recorded channels in the Data Logger module.
        Arguments: 
        -- Number of channels (int) is the number of recorded channels. It defines the size of the Channel indexes array
        -- Channel indexes (1D array int) are the indexes of recorded channels. The indexes are comprised between 0 and 23 for the 24 signals assigned in the Signals Manager.
        To get the signal name and its corresponding index in the list of the 128 available signals in the Nanonis Controller, use the <i>Signals.InSlotsGet</i> function
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("DataLog.ChsSet", [Channel_indexes], ["+*i"], [])

    def DataLog_ChsGet(self):
        """
        DataLog.ChsGet
        Returns the list of recorded channels in the Data Logger module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Number of channels (int) is the number of recorded channels. It defines the size of the Channel indexes array
        -- Channel indexes (1D array int) are the indexes of recorded channels. The indexes are comprised between 0 and 23 for the 24 signals assigned in the Signals Manager.
        To get the signal name and its corresponding index in the list of the 128 available signals in the Nanonis Controller, use the <i>Signals.InSlotsGet</i> function
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("DataLog.ChsGet", [], [], ["i", "*i"])

    def DataLog_PropsSet(self, Acquisition_mode, Acquisition_duration_hours, Acquisition_duration_minutes,
                         Acquisition_duration_seconds, Averaging, Basename, Comment, List_of_modules):
        """
        DataLog.PropsSet
        Sets the acquisition configuration and the save options in the Data Logger module.
        Arguments:
        -- Acquisition mode (unsigned int16) means that if Timed (_2), the selected channels are acquired during the acquisition duration time or until the user presses the Stop button. 
        If Continuous (_1), the selected channels are acquired continuously until the user presses the Stop button.
        If 0, the is no change in the acquisition mode.
        The acquired data are saved every time the averaged samples buffer reaches 25.000 samples and when the acquisition stops
        -- Acquisition duration( hours) (int) sets the number of hours the acquisition should last. Value -1 means no change
        -- Acquisition duration (minutes) (int) sets the number of minutes. Value -1 means no change
        -- Acquisition duration (seconds) (float32) sets the number of seconds. Value -1 means no change
        -- Averaging (int) sets how many data samples (received from the real-time system) are averaged for one data point saved into file. By increasing this value, the noise might decrease, and fewer points per seconds are recorded.
        Use 0 to skip changing this parameter
        -- Basename size (int) is the size in bytes of the Basename string
        -- Basename (string) is base name used for the saved images
        -- Comment size (int) is the size in bytes of the Comment string
        -- Comment (string) is comment saved in the file
        -- Size of the list of moduless (int) is the size in bytes of the List of modules string array
        -- Number of modules (int) is the number of elements of the List of modules string array
        -- List of modules (1D array string) sets the modules names whose parameters will be saved in the header of the files. The size of each string item should come right before it as integer 32
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("DataLog.PropsSet",
                              [Acquisition_mode, Acquisition_duration_hours, Acquisition_duration_minutes,
                               Acquisition_duration_seconds, Averaging, Basename, Comment,
                               List_of_modules],
                              ["H", "i", "i", "f", "i", "+*c", "+*c", "+*c"], [])

    def DataLog_PropsGet(self):
        """
        DataLog.PropsGet
        Returns the acquisition configuration and the save options in the Data Logger module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Acquisition mode (unsigned int16) means that if Timed (_1), the selected channels are acquired during the acquisition duration time or until the user presses the Stop button. 
        If Continuous (_0), the selected channels are acquired continuously until the user presses the Stop button.
        The acquired data are saved every time the averaged samples buffer reaches 25.000 samples and when the acquisition stops
        -- Acquisition duration( hours) (int) returns the number of hours the acquisition lasts
        -- Acquisition duration (minutes) (int) returns the number of minutes
        -- Acquisition duration (seconds) (float32) returns the number of seconds
        -- Averaging (int) returns how many data samples (received from the real-time system) are averaged for one data point saved into file
        -- Basename size (int) returns the size in bytes of the Basename string
        -- Basename (string) returns the base name used for the saved images
        -- Comment size (int) returns the size in bytes of the Comment string
        -- Comment (string) returns the comment saved in the file
        -- Error described in the Response message&gt;Body section
        
        TCP Logger
        """
        return self.quickSend("DataLog.PropsGet", [], [], ["H", "i", "i", "f", "i", "i", "*-c", "i", "*-c"])

    def TCPLog_Start(self):
        """
        TCPLog.Start
        Starts the acquisition in the TCP Logger module.
        Before using this function, select the channels to record in the TCP Logger.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("TCPLog.Start", [], [], [])

    def TCPLog_Stop(self):
        """
        TCPLog.Stop
        Stops the acquisition in the TCP Logger module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("TCPLog.Stop", [], [], [])

    def TCPLog_ChsSet(self, Channel_indexes):
        """
        TCPLog.ChsSet
        Sets the list of recorded channels in the TCP Logger module.
        Arguments: 
        -- Number of channels (int) is the number of recorded channels. It defines the size of the Channel indexes array
        -- Channel indexes (1D array int) are the indexes of recorded channels. The indexes are comprised between 0 and 23 for the 24 signals assigned in the Signals Manager.
        To get the signal name and its corresponding index in the list of the 128 available signals in the Nanonis Controller, use the <i>Signals.InSlotsGet</i> function
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("TCPLog.ChsSet", [Channel_indexes], ["*i"], [])

    def TCPLog_OversamplSet(self, Oversampling_value):
        """
        TCPLog.OversamplSet
        Sets the oversampling value in the TCP Logger.
        Arguments: 
        -- Oversampling value (int) sets the oversampling index, where index could be any value from 0 to 1000
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("TCPLog.OversamplSet", [Oversampling_value], ["i"], [])

    def TCPLog_StatusGet(self):
        """
        TCPLog.StatusGet
        Returns the current status of the TCP Logger.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Status (int) returns an index which corresponds to one of the following status: 0_disconnected, 1_idle, 2_start, 3_stop, 4_running, 5_TCP connect, 6_TCP disconnect, 7_buffer overflow
        
        -- Error described in the Response message&gt;Body section
        
        Oscilloscope High Resolution
        """
        return self.quickSend("TCPLog.StatusGet", [], [], ["i"])

    def OsciHR_ChSet(self, Channel_index):
        """
        OsciHR.ChSet
        Sets the channel index of the Oscilloscope High Resolution.
        Arguments: 
        -- Channel index (int) sets the channel to be used, where index could be any value from 0 to 15
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.ChSet", [Channel_index], ["i"], [])

    def OsciHR_ChGet(self):
        """
        OsciHR.ChGet
        Returns the channel index of the Oscilloscope High Resolution.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Channel index (int) returns the channel used in the Oscilloscope High Resolution
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.ChGet", [], [], ["i"])

    def OsciHR_OversamplSet(self, Oversampling_index):
        """
        OsciHR.OversamplSet
        Sets the oversampling index of the Oscilloscope High Resolution.
        Choosing to acquire data at lower rate than the maximum 1MS/s allows for an improved S/N ratio and also increases the time window for the acquisition for a given number of samples.
        Arguments: 
        -- Oversampling index (int) sets the oversampling index, where index could be any value from 0 to 10
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.OversamplSet", [Oversampling_index], ["i"], [])

    def OsciHR_OversamplGet(self):
        """
        OsciHR.OversamplGet
        Returns the oversampling index of the Oscilloscope High Resolution.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Oversampling index (int) gets the oversampling index, where index could be any value from 0 to 10
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.OversamplGet", [], [], ["i"])

    def OsciHR_CalibrModeSet(self, Calibration_mode):
        """
        OsciHR.CalibrModeSet
        Sets the calibration mode of the Oscilloscope High Resolution.
        Select between Raw Values or Calibrated Values. This setting affects the data displayed in the graph, and trigger level and hysteresis values. 
        Arguments: 
        -- Calibration mode (unsigned int16), where 0_Raw values and 1_Calibrated values
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.CalibrModeSet", [Calibration_mode], ["H"], [])

    def OsciHR_CalibrModeGet(self):
        """
        OsciHR.CalibrModeGet
        Returns the calibration mode of the Oscilloscope High Resolution.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Calibration mode (unsigned int16), where 0_Raw values and 1_Calibrated values
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.CalibrModeGet", [], [], ["H"])

    def OsciHR_SamplesSet(self, Number_of_samples):
        """
        OsciHR.SamplesSet
        Sets the number of samples to acquire in the Oscilloscope High Resolution.
        Arguments: 
        -- Number of samples (int)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.SamplesSet", [Number_of_samples], ["i"], [])

    def OsciHR_SamplesGet(self):
        """
        OsciHR.SamplesGet
        Returns the number of samples to acquire in the Oscilloscope High Resolution.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Number of samples (int)
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.SamplesGet", [], [], ["i"])

    def OsciHR_PreTrigSet(self, Pre_Trigger_samples, Pre_Trigger_s):
        """
        OsciHR.PreTrigSet
        Sets the Pre-Trigger Samples or Seconds in the Oscilloscope High Resolution.
        If Pre-Trigger (s) is NaN or Inf or below 0, Pre-Trigger Samples is taken into account instead of seconds.
        Arguments: 
        -- Pre-Trigger samples (unsigned int32)
        -- Pre-Trigger (s) (float64)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.PreTrigSet", [Pre_Trigger_samples, Pre_Trigger_s], ["I", "d"], [])

    def OsciHR_PreTrigGet(self):
        """
        OsciHR.PreTrigGet
        Returns the Pre-Trigger Samples in the Oscilloscope High Resolution.
        If Pre-Trigger (s) is NaN or Inf or below 0, Pre-Trigger Samples is taken into account instead of seconds.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Pre-Trigger samples (int)
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.PreTrigGet", [], [], ["i"])

    def OsciHR_Run(self):
        """
        OsciHR.Run
        Starts the Oscilloscope High Resolution module.
        The Oscilloscope High Resolution module does not run when its front panel is closed. To automate measurements it might be required to run the module first using this function.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.Run", [], [], [])

    def OsciHR_OsciDataGet(self, Data_to_get, Timeout_s):
        """
        OsciHR.OsciDataGet
        Returns the graph data from the Oscilloscope High Resolution.
        Arguments: 
        -- Data to get (unsigned int16), where 0_Current returns the currently displayed data and 1_Next trigger waits for the next trigger to retrieve data
        -- Timeout (s) (float64), tip
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Data t0 size (int) is the number of characters of the Data t0 string
        -- Data t0 (string) is the timestamp of the 1st acquired point
        -- Data dt (float64) is the time distance between two acquired points
        -- Data Y size (int) is the number of data points in Data Y
        -- Data Y (1D array float32) is the data acquired in the oscilloscope
        -- Timeout (unsigned int32) is 0 when no timeout occurred, and 1 when a timeout occurred
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.OsciDataGet", [Data_to_get, Timeout_s], ["H", "d"],
                              ["i", "*-c", "d", "i", "*f", "I"])

    def OsciHR_TrigModeSet(self, Trigger_mode):
        """
        OsciHR.TrigModeSet
        Sets the trigger mode in the Oscilloscope High Resolution.
        Arguments: 
        -- Trigger mode (unsigned int16), 0_Immediate means triggering immediately whenever the current data set is received by the host software, 1_Level where the trigger detection is performed on the non-averaged raw channel data (1MS/s), and 2_Digital where the trigger detection on the LS-DIO channels is performed at 500kS/s. Trigger detection on the HS-DIO channels is performed at 10MS/s
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.TrigModeSet", [Trigger_mode], ["H"], [])

    def OsciHR_TrigModeGet(self):
        """
        OsciHR.TrigModeGet
        Returns the trigger mode in the Oscilloscope High Resolution.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Trigger mode (unsigned int16), where 0_Immediate, 1_Level, and 2_Digital
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.TrigModeGet", [], [], ["H"])

    def OsciHR_TrigLevChSet(self, Level_trigger_channel_index):
        """
        OsciHR.TrigLevChSet
        Sets the Level Trigger Channel index in the Oscilloscope High Resolution.
        Trigger detection is performed on the non-averaged raw channel data.
        Arguments: 
        -- Level trigger channel index (int) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.TrigLevChSet", [Level_trigger_channel_index], ["i"], [])

    def OsciHR_TrigLevChGet(self):
        """
        OsciHR.TrigLevChGet
        Returns the Level Trigger Channel index in the Oscilloscope High Resolution.
        Trigger detection is performed on the non-averaged raw channel data.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Level trigger channel index (int) 
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.TrigLevChGet", [], [], ["i"])

    def OsciHR_TrigLevValSet(self, Level_trigger_value):
        """
        OsciHR.TrigLevValSet
        Sets the Level Trigger value in the Oscilloscope High Resolution.
        Arguments: 
        -- Level trigger value (float64) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        """
        return self.quickSend("OsciHR.TrigLevValSet", [Level_trigger_value], ["d"], [])

    def OsciHR_TrigLevValGet(self):
        """
        OsciHR.TrigLevValGet
        Returns the Level Trigger value in the Oscilloscope High Resolution.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Level trigger value (float64) 
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.TrigLevValGet", [], [], ["d"])

    def OsciHR_TrigLevHystSet(self, Level_trigger_Hysteresis):
        """
        OsciHR.TrigLevHystSet
        Sets the Level Trigger Hysteresis in the Oscilloscope High Resolution.
        Arguments: 
        -- Level trigger Hysteresis (float64) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.TrigLevHystSet", [Level_trigger_Hysteresis], ["d"], [])

    def OsciHR_TrigLevHystGet(self):
        """
        OsciHR.TrigLevHystGet
        Returns the Level Trigger Hysteresis in the Oscilloscope High Resolution.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Level trigger Hysteresis (float64) 
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.TrigLevHystGet", [], [], ["d"])

    def OsciHR_TrigLevSlopeSet(self, Level_trigger_slope):
        """
        OsciHR.TrigLevSlopeSet
        Sets the Level Trigger Slope in the Oscilloscope High Resolution.
        Arguments: 
        -- Level trigger slope (unsigned int16), where 0_Rising and 1_Falling 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.TrigLevSlopeSet", [Level_trigger_slope], ["H"], [])

    def OsciHR_TrigLevSlopeGet(self):
        """
        OsciHR.TrigLevSlopeGet
        Returns the Level Trigger Slope in the Oscilloscope High Resolution.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Level trigger slope (unsigned int16), where 0_Rising and 1_Falling 
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.TrigLevSlopeGet", [], [], ["H"])

    def OsciHR_TrigDigChSet(self, Digital_trigger_channel_index):
        """
        OsciHR.TrigDigChSet
        Sets the Digital Trigger Channel in the Oscilloscope High Resolution.
        Trigger detection on the LS-DIO channels is performed at 500kS/s. Trigger detection on the HS-DIO channels is performed at 10MS/s.
        Arguments: 
        -- Digital trigger channel index (int), where index can be any value from 0 to 35. Low Speed Port A lines are indexes 0 to 7, Low Speed Port B lines are indexes 8 to 15, Low Speed Port C lines are indexes 16 to 23, Low Speed Port D lines are indexes 24 to 31, and High Speed Port lines are indexes 32 to 35
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.TrigDigChSet", [Digital_trigger_channel_index], ["i"], [])

    def OsciHR_TrigDigChGet(self):
        """
        OsciHR.TrigDigChGet
        Returns the Digital Trigger Channel in the Oscilloscope High Resolution.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Digital trigger channel index (int), where index can be any value from 0 to 35. Low Speed Port A lines are indexes 0 to 7, Low Speed Port B lines are indexes 8 to 15, Low Speed Port C lines are indexes 16 to 23, Low Speed Port D lines are indexes 24 to 31, and High Speed Port lines are indexes 32 to 35
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.TrigDigChGet", [], [], ["i"])

    def OsciHR_TrigArmModeSet(self, Trigger_arming_mode):
        """
        OsciHR.TrigArmModeSet
        Sets the Trigger Arming Mode in the Oscilloscope High Resolution.
        Arguments: 
        -- Trigger arming mode (unsigned int16), where 0_Single shot means recording the next available data and stopping acquisition. and 1_Continuous means recording every available data and automatically re-triggers the acquisition
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.TrigArmModeSet", [Trigger_arming_mode], ["H"], [])

    def OsciHR_TrigArmModeGet(self):
        """
        OsciHR.TrigArmModeGet
        Returns the Trigger Arming Mode in the Oscilloscope High Resolution.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Trigger arming mode (unsigned int16), where 0_Single shot means recording the next available data and stopping acquisition. and 1_Continuous means recording every available data and automatically re-triggers the acquisition
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.TrigArmModeGet", [], [], ["H"])

    def OsciHR_TrigDigSlopeSet(self, Digital_trigger_slope):
        """
        OsciHR.TrigDigSlopeSet
        Sets the Digital Trigger Slope in the Oscilloscope High Resolution.
        Arguments: 
        -- Digital trigger slope (unsigned int16), where 0_Rising and 1_Falling 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.TrigDigSlopeSet", [Digital_trigger_slope], ["H"], [])

    def OsciHR_TrigDigSlopeGet(self):
        """
        OsciHR.TrigDigSlopeGet
        Returns the Digital Trigger Slope in the Oscilloscope High Resolution.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Digital trigger slope (unsigned int16), where 0_Rising and 1_Falling 
        -- Error described in the Response message&gt;Body section
        """
        return self.quickSend("OsciHR.TrigDigSlopeGet", [], [], ["H"])

    def OsciHR_TrigRearm(self):
        """
        OsciHR.TrigRearm
        Rearms the trigger in the Oscilloscope High Resolution module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.TrigRearm", [], [], [])

    def OsciHR_PSDShow(self, Show_PSD_section):
        """
        OsciHR.PSDShow
        Shows or hides the PSD section of the Oscilloscope High Resolution.
        Arguments: 
        -- Show PSD section (unsigned int32), where 0_Hide and 1_Show 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("OsciHR.PSDShow", [Show_PSD_section], ["I"], [])

    def OsciHR_PSDWeightSet(self, PSD_Weighting):
        """
        OsciHR.PSDWeightSet
        Sets the PSD Weighting in the Oscilloscope High Resolution.
        Arguments: 
        -- PSD Weighting (unsigned int16), where 0_Linear means that the averaging combines Count spectral records with equal weighting and then stops, whereas 1_Exponential means that the averaging process is continuous and new spectral data have a higher weighting than older ones
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.PSDWeightSet", [PSD_Weighting], ["H"], [])

    def OsciHR_PSDWeightGet(self):
        """
        OsciHR.PSDWeightGet
        Returns the PSD Weighting in the Oscilloscope High Resolution.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- PSD Weighting (unsigned int16), where 0_Linear means that the averaging combines Count spectral records with equal weighting and then stops, whereas 1_Exponential means that the averaging process is continuous and new spectral data have a higher weighting than older ones
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.PSDWeightGet", [], [], ["H"])

    def OsciHR_PSDWindowSet(self, PSD_window_type):
        """
        OsciHR.PSDWindowSet
        Sets the PSD Window Type in the Oscilloscope High Resolution.
        Arguments: 
        -- PSD window type (unsigned int16) is the window function applied to the timed signal before calculating the power spectral density, where 0_None, 1_Hanning, 2_Hamming, etc
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        """
        return self.quickSend("OsciHR.PSDWindowSet", [PSD_window_type], ["H"], [])

    def OsciHR_PSDWindowGet(self):
        """
        OsciHR.PSDWindowGet
        Returns the PSD Window Type in the Oscilloscope High Resolution.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- PSD window type (unsigned int16) is the window function applied to the timed signal before calculating the power spectral density, where 0_None, 1_Hanning, 2_Hamming, etc
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.PSDWindowGet", [], [], ["H"])

    def OsciHR_PSDAvrgTypeSet(self, PSD_averaging_type):
        """
        OsciHR.PSDAvrgTypeSet
        Sets the PSD Averaging Type in the Oscilloscope High Resolution.
        Arguments: 
        -- PSD averaging type (unsigned int16), where 0_None, 1_Vector, 2_RMS, 3_Peak hold
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.PSDAvrgTypeSet", [PSD_averaging_type], ["H"], [])

    def OsciHR_PSDAvrgTypeGet(self):
        """
        OsciHR.PSDAvrgTypeGet
        Returns the PSD Averaging Type in the Oscilloscope High Resolution.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- PSD averaging type (unsigned int16), where 0_None, 1_Vector, 2_RMS, 3_Peak hold
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.PSDAvrgTypeGet", [], [], ["H"])

    def OsciHR_PSDAvrgCountSet(self, PSD_averaging_count):
        """
        OsciHR.PSDAvrgCountSet
        Sets the PSD Averaging Count used by the RMS and Vector averaging types in the Oscilloscope High Resolution.
        Arguments: 
        -- PSD averaging count (int)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.PSDAvrgCountSet", [PSD_averaging_count], ["i"], [])

    def OsciHR_PSDAvrgCountGet(self):
        """
        OsciHR.PSDAvrgCountGet
        Returns the PSD Averaging Count used by the RMS and Vector averaging types in the Oscilloscope High Resolution.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- PSD averaging count (int)
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.PSDAvrgCountGet", [], [], ["i"])

    def OsciHR_PSDAvrgRestart(self):
        """
        OsciHR.PSDAvrgRestart
        Restarts the PSD averaging process in the Oscilloscope High Resolution module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("OsciHR.PSDAvrgRestart", [], [], [])

    def OsciHR_PSDDataGet(self, Data_to_get, Timeout_s):
        """
        OsciHR.PSDDataGet
        Returns the Power Spectral Density data from the Oscilloscope High Resolution.
        Arguments:
        -- Data to get (unsigned int16), where 0_Current returns the currently displayed data and 1_Next trigger waits for the next trigger to retrieve data
        -- Timeout (s) (float64), where -1 means waiting forever

        Return arguments (if Send response back flag is set to True when sending request message):

        -- Data f0 (float64) is the x coordinate of the 1st acquired point
        -- Data df (float64) is the frequency distance between two acquired points
        -- Data Y size (int) is the number of data points in Data Y
        -- Data Y (1D array float64) is the PSD data acquired in the oscilloscope
        -- Timeout (unsigned int32) is 0 when no timeout occurred, and 1 when a timeout occurred
        -- Error described in the Response message&gt;Body section
        """
        return self.quickSend("OsciHR.PSDDataGet",
                              [Data_to_get, Timeout_s],
                              ["H", "d"],
                              ["d", "d", "i", "*d", "I"])

    def Osci1T_ChSet(self, ChannelIndex):
        """
        Oscilloscope 1-Channel
        Osci1T.ChSet
        Sets the channel to display in the Oscilloscope 1-Channel.
        Arguments:
        -- Channel index (int) sets the channel to be used, where the index is comprised between 0 and 23, and it corresponds to the list of signals assigned to the 24 slots in the Signals Manager.

        To get the signal name and its corresponding index in the list of the 128 available signals in the Nanonis Controller, use the <i>Signals.InSlotsGet</i> function

        Return arguments (if Send response back flag is set to True when sending request message):

        -- Error described in the Response message&gt;Body section
        """
        return self.quickSend("Osci1T.ChSet", [ChannelIndex], ["i"], [])

    def Osci1T_ChGet(self):
        """
        Osci1T.ChGet
        Returns the channel displayed in the Oscilloscope 1-Channel.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):

        -- Channel index (int) returns the channel used, where the index is comprised between 0 and 23, and it corresponds to the list of signals assigned to the 24 slots in the Signals Manager.
        To get the signal name and its corresponding index in the list of the 128 available signals in the Nanonis Controller, use the <i>Signals.InSlotsGet</i> function
        -- Error described in the Response message&gt;Body section

        """
        return self.quickSend("Osci1T.ChGet", [], [], ["i"])

    def Osci1T_TimebaseSet(self, TimebaseIndex):
        """
        Osci1T.TimebaseSet
        Sets the timebase in the Oscilloscope 1-Channel.
        To set the timebase, use the <i>Osci1T.TimebaseGet</i>  function first to obtain a list of available timebases. Then, use the index of the desired timebase as input to this function.
        The available timebases depend on the RT frequency and the RT oversampling.
        Arguments:
        -- Timebase index (int)

        Return arguments (if Send response back flag is set to True when sending request message):

        -- Error described in the Response message&gt;Body section
        """
        return self.quickSend("Osci1T.TimebaseSet", [TimebaseIndex], ["i"], [])

    def Osci1T_TimebaseGet(self):

        """
        Osci1T.TimebaseGet
        Returns the timebase in the Oscilloscope 1-Channel.
        The available timebases depend on the RT frequency and the RT oversampling.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):

        -- Timebase index (int) returns the index of the selected timebase
        -- Number of timebases (int) returns the number of elements in the Timebases array
        -- Timebases (s) (1D array float32) returns an array of the timebases values in seconds
        -- Error described in the Response message&gt;Body section

        """
        return self.quickSend("Osci1T.TimebaseSet", [], [], ["i", "i", "*f"])

    def Osci1T_TrigSet(self, TriggerMode, TriggerSlope, TriggerLevel, TriggerHysteresis):
        """
        Osci1T.TrigSet
        Sets the trigger configuration in the Oscilloscope 1-Channel.
        Arguments:
        -- Trigger mode (unsigned int16) sets the triggering mode. For Immediate mode (_0) no further configuration is required. 1 means Level, and 2 means Auto
        -- Trigger slope (unsigned int16) sets whether to trigger on rising (_1) or falling (_0) slope of the signal
        -- Trigger level (float64) sets the value the signal must cross (in the direction specified in slope) to trigger
        -- Trigger hysteresis (float64) is used to prevent noise from causing a false trigger.
        For a rising edge trigger slope, the signal must pass below (level – hysteresis) before a trigger level crossing is detected.
        For a falling edge trigger slope, the signal must pass above (level + hysteresis) before a trigger level crossing is detected

        Return arguments (if Send response back flag is set to True when sending request message):

        -- Error described in the Response message&gt;Body section

        """
        return self.quickSend("Osci1T.TrigSet", [TriggerMode, TriggerSlope, TriggerLevel, TriggerHysteresis],
                              ["H", "H", "f", "f"], [])

    def Osci1T_TrigGet(self, TriggerMode, TriggerChannel, TriggerSlope, TriggerLevel, TriggerHysterstis, TriggerPos):
        """
        Osci1T.TrigGet
        Returns the trigger configuration in the Oscilloscope 1-Channel.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):

        -- Trigger mode (unsigned int16) returns the triggering mode. 0 means Immediate mode, 1 means Level, and 2 means Auto
        -- Trigger slope (unsigned int16) returns whether to trigger on rising (_1) or falling (_0) slope of the signal
        -- Trigger level (float64) returns the value the signal must cross (in the direction specified in slope) to trigger
        -- Trigger hysteresis (float64) is used to prevent noise from causing a false trigger.
        For a rising edge trigger slope, the signal must pass below (level – hysteresis) before a trigger level crossing is detected.
        For a falling edge trigger slope, the signal must pass above (level + hysteresis) before a trigger level crossing is detected
        -- Error described in the Response message&gt;Body section
        """
        return self.quickSend("Osci1T.TrigGet",
                              [TriggerMode, TriggerChannel, TriggerSlope, TriggerLevel, TriggerHysterstis, TriggerPos],
                              ["H", "H", "d", "d"], [])

    def Osci1T_Run(self):
        """
        Osci1T.Run
        Starts the Oscilloscope 1-Channel.
        This module does not run when its front panel is closed. To automate measurements it is required to run the module first using this function.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):

        -- Error described in the Response message&gt;Body section
        """
        return self.quickSend("Osci1T.Run", [], [], [])

    def Osci1T_DataGet(self, DataToGet):
        """
        Osci1T.DataGet
        Returns the graph data from the Oscilloscope 1-Channel.
        Arguments:
        -- Data to get (unsigned int16), where 0_Current returns the currently displayed data, 1_Next trigger waits for the next trigger to retrieve data, and 2_wait 2 triggers

        Return arguments (if Send response back flag is set to True when sending request message):

        -- Data t0 (float64) is the timestamp of the 1st acquired point
        -- Data dt (float64) is the time distance between two acquired points
        -- Data Y size (int) is the number of data points in Data Y
        -- Data Y (1D array float64) is the data acquired in the oscilloscope
        -- Error described in the Response message&gt;Body section
        """
        return self.quickSend("Osci1T.DataGet", [DataToGet], ["H"], ["d", "d", "i", "*d"])

    def Osci2T_ChSet(self, ChannelAIndex, ChannelBIndex):
        """
        Oscilloscope 1-Channel
        Osci2T.ChSet
        Sets the channel to display in the Oscilloscope 1-Channel.
        Arguments:
        -- Channel index (int) sets the channel to be used, where the index is comprised between 0 and 23, and it corresponds to the list of signals assigned to the 24 slots in the Signals Manager.

        To get the signal name and its corresponding index in the list of the 128 available signals in the Nanonis Controller, use the <i>Signals.InSlotsGet</i> function

        Return arguments (if Send response back flag is set to True when sending request message):

        -- Error described in the Response message&gt;Body section
        """
        return self.quickSend("Osci1T.ChSet", [ChannelAIndex, ChannelBIndex], ["i", "i"], [])

    def Osci2T_ChGet(self):
        """
        Osci2T.ChGet
        Returns the channel displayed in the Oscilloscope 1-Channel.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):

        -- Channel index (int) returns the channel used, where the index is comprised between 0 and 23, and it corresponds to the list of signals assigned to the 24 slots in the Signals Manager.
        To get the signal name and its corresponding index in the list of the 128 available signals in the Nanonis Controller, use the <i>Signals.InSlotsGet</i> function
        -- Error described in the Response message&gt;Body section

        """
        return self.quickSend("Osci1T.ChGet", [], [], ["i", "i"])

    def Osci2T_TimebaseSet(self, TimebaseIndex):
        """
        Osci2T.TimebaseSet
        Sets the timebase in the Oscilloscope 1-Channel.
        To set the timebase, use the <i>Osci1T.TimebaseGet</i>  function first to obtain a list of available timebases. Then, use the index of the desired timebase as input to this function.
        The available timebases depend on the RT frequency and the RT oversampling.
        Arguments:
        -- Timebase index (int)

        Return arguments (if Send response back flag is set to True when sending request message):

        -- Error described in the Response message&gt;Body section
        """
        return self.quickSend("Osci1T.TimebaseSet", [TimebaseIndex], ["H"], [])

    def Osci2T_TimebaseGet(self):
        """
        Osci2T.TimebaseGet
        Returns the timebase in the Oscilloscope 1-Channel.
        The available timebases depend on the RT frequency and the RT oversampling.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):

        -- Timebase index (int) returns the index of the selected timebase
        -- Number of timebases (int) returns the number of elements in the Timebases array
        -- Timebases (s) (1D array float32) returns an array of the timebases values in seconds
        -- Error described in the Response message&gt;Body section

        """
        return self.quickSend("Osci1T.TimebaseSet", [], [], ["H", "i", "*f"])

    def Osci2T_OversamplSet(self, OversamplIndex):
        """
        Osci2T.OversamplSet
        Sets the oversampling in the Oscilloscope 2-Channels.
        Arguments:

        - Oversampling index (unsigned int16) defines how many integer number of samples each data point is averaged over. Index 0 means 50 samples, index 1 means 20, index 2 means 10, index 3 means 5, index 4 means 2, and index 5 means 1 sample (so no averaging)

        Return arguments (if Send response back flag is set to True when sending request message):

        - Error described in the Response message>Body section
                """
        return self.quickSend("Osci2T.OversamplSet", [OversamplIndex], ["H"], [])

    def Osci2T_OversamplGet(self):
        """
        Osci2T.OversamplGet
        Returns the oversampling in the Oscilloscope 2-Channels.

        Arguments: None

        Return arguments (if Send response back flag is set to True when sending request message):

        - Oversampling index (unsigned int16) defines how many integer number of samples each data point is averaged over. Index 0 means 50 samples, index 1 means 20, index 2 means 10, index 3 means 5, index 4 means 2, and index 5 means 1 sample (so no averaging)
        - Error described in the Response message>Body section
        """
        return self.quickSend("Osci2T.OversamplSet", [], [], ["H"])

    def Osci2T_TrigSet(self, TriggerMode, TrigChannel, TriggerSlope, TriggerLevel, TriggerHysteresis, TrigPosition):
        """
        Osci2T.TrigSet
        Sets the trigger configuration in the Oscilloscope 1-Channel.
        Arguments:
        -- Trigger mode (unsigned int16) sets the triggering mode. For Immediate mode (_0) no further configuration is required. 1 means Level, and 2 means Auto
        -- Trigger slope (unsigned int16) sets whether to trigger on rising (_1) or falling (_0) slope of the signal
        -- Trigger level (float64) sets the value the signal must cross (in the direction specified in slope) to trigger
        -- Trigger hysteresis (float64) is used to prevent noise from causing a false trigger.
        For a rising edge trigger slope, the signal must pass below (level – hysteresis) before a trigger level crossing is detected.
        For a falling edge trigger slope, the signal must pass above (level + hysteresis) before a trigger level crossing is detected

        Return arguments (if Send response back flag is set to True when sending request message):

        -- Error described in the Response message&gt;Body section

        """
        return self.quickSend("Osci2T.TrigSet",
                              [TriggerMode, TrigChannel, TriggerSlope, TriggerLevel, TriggerHysteresis, TrigPosition],
                              ["H", "H", "H", "d", "d", "d"], [])

    def Osci2T_TrigGet(self, TriggerMode, TriggerChannel, TriggerSlope, TriggerLevel, TriggerHysterstis, TriggerPos):
        """
        Osci2T.TrigGet
        Returns the trigger configuration in the Oscilloscope 1-Channel.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):

        -- Trigger mode (unsigned int16) returns the triggering mode. 0 means Immediate mode, 1 means Level, and 2 means Auto
        -- Trigger slope (unsigned int16) returns whether to trigger on rising (_1) or falling (_0) slope of the signal
        -- Trigger level (float64) returns the value the signal must cross (in the direction specified in slope) to trigger
        -- Trigger hysteresis (float64) is used to prevent noise from causing a false trigger.
        For a rising edge trigger slope, the signal must pass below (level – hysteresis) before a trigger level crossing is detected.
        For a falling edge trigger slope, the signal must pass above (level + hysteresis) before a trigger level crossing is detected
        -- Error described in the Response message&gt;Body section
        """
        return self.quickSend("Osci2T.TrigGet",
                              [TriggerMode, TriggerChannel, TriggerSlope, TriggerLevel, TriggerHysterstis, TriggerPos],
                              ["H", "H", "H", "d", "d", "d"], [])

    def Osci2T_Run(self):
        """
        Osci2T.Run
        Starts the Oscilloscope 1-Channel.
        This module does not run when its front panel is closed. To automate measurements it is required to run the module first using this function.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):

        -- Error described in the Response message&gt;Body section
        """
        return self.quickSend("Osci2T.Run", [], [], [])

    def Osci2T_DataGet(self, DataToGet):
        """
        Osci2T.DataGet
        Returns the graph data from the Oscilloscope 1-Channel.
        Arguments:
        -- Data to get (unsigned int16), where 0_Current returns the currently displayed data, 1_Next trigger waits for the next trigger to retrieve data, and 2_wait 2 triggers

        Return arguments (if Send response back flag is set to True when sending request message):

        -- Data t0 (float64) is the timestamp of the 1st acquired point
        -- Data dt (float64) is the time distance between two acquired points
        -- Data Y size (int) is the number of data points in Data Y
        -- Data Y (1D array float64) is the data acquired in the oscilloscope
        -- Error described in the Response message&gt;Body section
        """
        return self.quickSend("Osci2T.DataGet", [DataToGet], ["H"], ["d", "d", "i", "*d", "i", "*d"])

    def SignalChart_Open(self):
        """
        SignalChart.Open
        Opens the Signal Chart module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("SignalChart.Open", [], [], [])

    def SignalChart_ChsSet(self, Channel__A__index, Channel__B__index):
        """
        SignalChart.ChsSet
        Sets the channels to display in the Signal Chart module.
        Arguments: 
        -- Channel  A  index (int) sets the channel A, where the index is comprised between 0 and 23, and it corresponds to the list of signals assigned to the 24 slots in the Signals Manager. 
        To get the signal name and its corresponding index in the list of the 128 available signals in the Nanonis Controller, use the <i>Signals.InSlotsGet</i> function
        -- Channel  B  index (int) sets the channel B, where the index is comprised between 0 and 23, and it corresponds to the list of signals assigned to the 24 slots in the Signals Manager. 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("SignalChart.ChsSet", [Channel__A__index, Channel__B__index], ["i", "i"], [])

    def SignalChart_ChsGet(self):
        """
        SignalChart.ChsGet
        Returns the channels to display in the Signal Chart module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Channel  A  index (int) sets the channel A, where the index is comprised between 0 and 23, and it corresponds to the list of signals assigned to the 24 slots in the Signals Manager. 
        To get the signal name and its corresponding index in the list of the 128 available signals in the Nanonis Controller, use the <i>Signals.InSlotsGet</i> function
        -- Channel  B  index (int) sets the channel B, where the index is comprised between 0 and 23, and it corresponds to the list of signals assigned to the 24 slots in the Signals Manager. 
        -- Error described in the Response message&gt;Body section
        
        
        Spectrum Analyzer
        """
        return self.quickSend("SignalChart.ChsGet", [], [], ["i", "i"])

    def SpectrumAnlzr_ChSet(self, Spectrum_Analyzer_instance, Channel__index):
        """
        SpectrumAnlzr.ChSet
        Sets the channel to display in the selected Spectrum Analyzer module.
        Arguments: 
        -- Spectrum Analyzer instance (int) selects the Spectrum Analyzer instance this function will apply changes to. Valid values are 1 for Spectrum Analyzer 1, and 2 for Spectrum Analyzer 2
        -- Channel  index (int) sets the channel to be used, where the index is comprised between 0 and 23, and it corresponds to the list of signals assigned to the 24 slots in the Signals Manager. 
        To get the signal name and its corresponding index in the list of the 128 available signals in the Nanonis Controller, use the <i>Signals.InSlotsGet</i> function
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("SpectrumAnlzr.ChSet", [Spectrum_Analyzer_instance, Channel__index], ["i", "i"], [])

    def SpectrumAnlzr_ChGet(self, Spectrum_Analyzer_instance):
        """
        SpectrumAnlzr.ChGet
        Returns the channel to display in the selected Spectrum Analyzer module.
        Arguments: 
        -- Spectrum Analyzer instance (int) selects the Spectrum Analyzer instance this function refers to. Valid values are 1 for Spectrum Analyzer 1, and 2 for Spectrum Analyzer 2
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Channel  index (int) returns the channel used, where the index is comprised between 0 and 23, and it corresponds to the list of signals assigned to the 24 slots in the Signals Manager. 
        To get the signal name and its corresponding index in the list of the 128 available signals in the Nanonis Controller, use the <i>Signals.InSlotsGet</i> function
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("SpectrumAnlzr.ChGet", [Spectrum_Analyzer_instance], ["i"], ["i"])

    def SpectrumAnlzr_FreqRangeSet(self, Spectrum_Analyzer_instance, Range__index):
        """
        SpectrumAnlzr.FreqRangeSet
        Sets the frequency range in the selected Spectrum Analyzer module.
        To set the frequency range, use <i>SpectrumAnlzr.FreqRangeGet</i> first to obtain a list of available frequency ranges. Then, use the index of the desired range as input to this function.
        The available frequency ranges depend on the RT frequency and the RT oversampling.
        Arguments: 
        -- Spectrum Analyzer instance (int) selects the Spectrum Analyzer instance this function will apply changes to. Valid values are 1 for Spectrum Analyzer 1, and 2 for Spectrum Analyzer 2
        -- Range  index (int) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("SpectrumAnlzr.FreqRangeSet", [Spectrum_Analyzer_instance, Range__index], ["i", "i"], [])

    def SpectrumAnlzr_FreqRangeGet(self, Spectrum_Analyzer_instance):
        """
        SpectrumAnlzr.FreqRangeGet
        Returns the frequency range in the selected Spectrum Analyzer module.
        The available frequency ranges depend on the RT frequency and the RT oversampling.
        Arguments: 
        -- Spectrum Analyzer instance (int) selects the Spectrum Analyzer instance this function refers to. Valid values are 1 for Spectrum Analyzer 1, and 2 for Spectrum Analyzer 2
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Range  index (int) is the index of the selected frequency range
        -- Number of frequency ranges (int) returns the number of elements in the Frequency ranges array
        -- Frequency ranges (Hz) (1D array float32) returns an array of the frequency ranges in Hz
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("SpectrumAnlzr.FreqRangeGet", [Spectrum_Analyzer_instance], ["i"], ["i", "i", "*f"])

    def SpectrumAnlzr_FreqResSet(self, Spectrum_Analyzer_instance, Resolution__index):
        """
        SpectrumAnlzr.FreqResSet
        Sets the frequency resolution in the selected Spectrum Analyzer module.
        To set the frequency resolution, use <i>SpectrumAnlzr.FreqResGet </i>first to obtain a list of available frequency resolutions. Then, use the index of the desired resolution as input to this function.
        Arguments: 
        -- Spectrum Analyzer instance (int) selects the Spectrum Analyzer instance this function will apply changes to. Valid values are 1 for Spectrum Analyzer 1, and 2 for Spectrum Analyzer 2
        -- Resolution  index (unsigned int16) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("SpectrumAnlzr.FreqResSet", [Spectrum_Analyzer_instance, Resolution__index], ["i", "H"],
                              [])

    def SpectrumAnlzr_FreqResGet(self, Spectrum_Analyzer_instance):
        """
        SpectrumAnlzr.FreqResGet
        Returns the frequency resolution in the selected Spectrum Analyzer module.
        Arguments: 
        -- Spectrum Analyzer instance (int) selects the Spectrum Analyzer instance this function refers to. Valid values are 1 for Spectrum Analyzer 1, and 2 for Spectrum Analyzer 2
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Resolution  index (unsigned int16) is the index of the selected frequency resolution
        -- Number of frequency resolutions (int) returns the number of elements in the Frequency resolutions array
        -- Frequency resolutions (Hz) (1D array float32) returns an array of the frequency resolutions in Hz
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("SpectrumAnlzr.FreqResGet", [Spectrum_Analyzer_instance], ["i"], ["H", "i", "*f"])

    def SpectrumAnlzr_FFTWindowSet(self, Spectrum_Analyzer_instance, FFT_window__index):
        """
        SpectrumAnlzr.FFTWindowSet
        Sets the FFT window in the selected Spectrum Analyzer module.
        The indexes of the possible FFT windows are as follows: 0_None, 1_Hanning, 2_Hamming, 3_Blackman-Harris, 4_Exact Blackman, 5_Blackman, 6_Flat Top, 7_4 Term B-Harris, 8_7 Term B-Harris, and 9_Low Sidelobe
        Arguments: 
        -- Spectrum Analyzer instance (int) selects the Spectrum Analyzer instance this function will apply changes to. Valid values are 1 for Spectrum Analyzer 1, and 2 for Spectrum Analyzer 2
        -- FFT window  index (unsigned int16) 
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("SpectrumAnlzr.FFTWindowSet", [Spectrum_Analyzer_instance, FFT_window__index], ["i", "H"],
                              [])

    def SpectrumAnlzr_FFTWindowGet(self, Spectrum_Analyzer_instance):
        """
        SpectrumAnlzr.FFTWindowGet
        Returns the FFT window selected in the selected Spectrum Analyzer module.
        The indexes of the possible FFT windows are as follows: 0_None, 1_Hanning, 2_Hamming, 3_Blackman-Harris, 4_Exact Blackman, 5_Blackman, 6_Flat Top, 7_4 Term B-Harris, 8_7 Term B-Harris, and 9_Low Sidelobe
        Arguments: 
        -- Spectrum Analyzer instance (int) selects the Spectrum Analyzer instance this function refers to. Valid values are 1 for Spectrum Analyzer 1, and 2 for Spectrum Analyzer 2
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- FFT window  index (unsigned int16) 
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("SpectrumAnlzr.FFTWindowGet", [Spectrum_Analyzer_instance], ["i"], ["H"])

    def SpectrumAnlzr_AveragSet(self, Spectrum_Analyzer_instance, Averaging_mode, Weighting_mode, Count):
        """
        SpectrumAnlzr.AveragSet
        Sets the averaging parameters in the selected Spectrum Analyzer module.
        Arguments: 
        -- Spectrum Analyzer instance (int) selects the Spectrum Analyzer instance this function will apply changes to. Valid values are 1 for Spectrum Analyzer 1, and 2 for Spectrum Analyzer 2
        -- Averaging mode (unsigned int16) where 0 is None, 1 is Vector, 2 is RMS, and 3 is Peak Hold
        -- Weighting mode (unsigned int16) where 0 is Linear and 1 is Exponential
        -- Count (unsigned int32) specifies the number of averages used for RMS and Vector averaging. 
        If weighting mode is Exponential, the averaging process is continuous and new spectral data have a higher weighting than older ones. 
        If weighting mode is Linear, the averaging combines count spectral records with equal weighting and then stops
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("SpectrumAnlzr.AveragSet",
                              [Spectrum_Analyzer_instance, Averaging_mode, Weighting_mode, Count], ["i", "H", "H", "I"],
                              [])

    def SpectrumAnlzr_AveragGet(self, Spectrum_Analyzer_instance):
        """
        SpectrumAnlzr.AveragGet
        Returns the averaging parameters in the selected Spectrum Analyzer module.
        Arguments: 
        -- Spectrum Analyzer instance (int) selects the Spectrum Analyzer instance this function refers to. Valid values are 1 for Spectrum Analyzer 1, and 2 for Spectrum Analyzer 2
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Averaging mode (unsigned int16) where 0 is None, 1 is Vector, 2 is RMS, and 3 is Peak Hold
        -- Weighting mode (unsigned int16) where 0 is Linear and 1 is Exponential
        -- Count (unsigned int32) specifies the number of averages used for RMS and Vector averaging. 
        If weighting mode is Exponential, the averaging process is continuous and new spectral data have a higher weighting than older ones. 
        If weighting mode is Linear, the averaging combines count spectral records with equal weighting and then stops
        -- Error described in the Response message&gt;Body section
        
        
        
        
        """
        return self.quickSend("SpectrumAnlzr.AveragGet", [Spectrum_Analyzer_instance], ["i"], ["H", "H", "I"])

    def SpectrumAnlzr_ACCouplingSet(self, Spectrum_Analyzer_instance, AC_coupling):
        """
        SpectrumAnlzr.ACCouplingSet
        Sets the AC coupling mode in the selected Spectrum Analyzer module.
        Use the associated <i>SpectrumAnlzr.DCGet</i> function to return the DC component when this method is activated.
        Arguments: 
        -- Spectrum Analyzer instance (int) selects the Spectrum Analyzer instance this function will apply changes to. Valid values are 1 for Spectrum Analyzer 1, and 2 for Spectrum Analyzer 2
        -- AC coupling (unsigned int32) switches the AC coupling Off (_0) or On (_1)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("SpectrumAnlzr.ACCouplingSet", [Spectrum_Analyzer_instance, AC_coupling], ["i", "I"], [])

    def SpectrumAnlzr_ACCouplingGet(self, Spectrum_Analyzer_instance):
        """
        SpectrumAnlzr.ACCouplingGet
        Returns the AC coupling mode in the selected Spectrum Analyzer module.
        Use the associated <i>SpectrumAnlzr.DCGet</i> function to return the DC component when this method is activated.
        Arguments: 
        -- Spectrum Analyzer instance (int) selects the Spectrum Analyzer instance this function refers to. Valid values are 1 for Spectrum Analyzer 1, and 2 for Spectrum Analyzer 2
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- AC coupling (unsigned int32) returns whether the AC coupling is Off (_0) or On (_1)
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("SpectrumAnlzr.ACCouplingGet", [Spectrum_Analyzer_instance], ["i"], ["I"])

    def SpectrumAnlzr_CursorPosSet(self, Spectrum_Analyzer_instance, Cursor_type, Position_X_Cursor_1_Hz,
                                   Position_X_Cursor_2_Hz):
        """
        SpectrumAnlzr.CursorPosSet
        Sets the position of the cursors in the selected Spectrum Analyzer module.
        Cursors 1 and 2 are used to define the frequency band. 
        Arguments: 
        -- Spectrum Analyzer instance (int) selects the Spectrum Analyzer instance this function will apply changes to. Valid values are 1 for Spectrum Analyzer 1, and 2 for Spectrum Analyzer 2
        -- Cursor type (unsigned int16) sets the type of cursor to display. 0 means x_y, 1 means dx_dy, 2 means x1_x2_dx, 3 means y1_y2_dy, 4 means RMS_df, and 5 means no change
        -- Position X Cursor 1 (Hz) (float64) sets the X position of cursor 1
        -- Position X Cursor 2 (Hz) (float64) sets the X position of cursor 2
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("SpectrumAnlzr.CursorPosSet",
                              [Spectrum_Analyzer_instance, Cursor_type, Position_X_Cursor_1_Hz, Position_X_Cursor_2_Hz],
                              ["i", "H", "d", "d"], [])

    def SpectrumAnlzr_CursorPosGet(self, Spectrum_Analyzer_instance, Cursor_type):
        """
        SpectrumAnlzr.CursorPosGet
        Returns the position of the cursors in the selected Spectrum Analyzer module.
        Cursors 1 and 2 are used to define the frequency band. 
        Arguments: 
        -- Spectrum Analyzer instance (int) selects the Spectrum Analyzer instance this function refers to. Valid values are 1 for Spectrum Analyzer 1, and 2 for Spectrum Analyzer 2
        -- Cursor type (unsigned int16) sets the type of cursor to display. 0 means x_y, 1 means dx_dy, 2 means x1_x2_dx, 3 means y1_y2_dy, 4 means RMS_df, and 5 means no change
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Position X Cursor 1 (Hz) (float64) returns the X position of cursor 1
        -- Position X Cursor 2 (Hz) (float64) returns the X position of cursor 2
        -- Position Y Cursor 1 (float64) returns the Y position of cursor 1
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("SpectrumAnlzr.CursorPosGet", [Spectrum_Analyzer_instance, Cursor_type], ["i", "H"],
                              ["d", "d", "d"])

    def SpectrumAnlzr_BandRMSGet(self, Spectrum_Analyzer_instance):
        """
        SpectrumAnlzr.BandRMSGet
        Returns the RMS value in the frequency band from the Spectrum Analyzer modules.
        By using this function the cursor type of the module is set to Band RMS if previously set to another type.
        Arguments: 
        -- Spectrum Analyzer instance (int) selects the Spectrum Analyzer instance this function refers to. Valid values are 1 for Spectrum Analyzer 1, and 2 for Spectrum Analyzer 2
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Band RMS (float64) 
        -- Minimum frequency (Hz) (float64) 
        -- Maximum frequency (Hz) (float64) 
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("SpectrumAnlzr.BandRMSGet", [Spectrum_Analyzer_instance], ["i"], ["d", "d", "d"])

    def SpectrumAnlzr_DCGet(self, Spectrum_Analyzer_instance):
        """
        SpectrumAnlzr.DCGet
        Returns the DC value from the Spectrum Analyzer modules if the AC coupling mode is activated.
        Arguments: 
        -- Spectrum Analyzer instance (int) selects the Spectrum Analyzer instance this function refers to. Valid values are 1 for Spectrum Analyzer 1, and 2 for Spectrum Analyzer 2
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- DC value (float64) 
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("SpectrumAnlzr.DCGet", [Spectrum_Analyzer_instance], ["i"], ["d"])

    def SpectrumAnlzr_Run(self, Spectrum_Analyzer_instance):
        """
        SpectrumAnlzr.Run
        Starts the Spectrum Analyzer modules.
        The Spectrum Analyzer does not run when its front panel is closed. To automate measurements it is required to run the module first using this function.
        Arguments: 
        -- Spectrum Analyzer instance (int) selects the Spectrum Analyzer instance this function refers to. Valid values are 1 for Spectrum Analyzer 1, and 2 for Spectrum Analyzer 2
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("SpectrumAnlzr.Run", [Spectrum_Analyzer_instance], ["i"], [])

    def SpectrumAnlzr_DataGet(self, Spectrum_Analyzer_instance, Periods, Amplitude_Percent, Frequency_Hz, Polarity,
                              Direction, Idle_value, Periods_again, Device, Idle_value_again, Device_again,
                              Channel_index, Status, Channel_index_again, Channel_index_again_again, Signal_index,
                              Channel_index_again_again_again, Channel_index_again_again_again_again,
                              Amplitude_Percent_again, Time_s, Polarity_again, Direction_again, AdddivZero,
                              Channel_index_again_again_again_again_again,
                              Channel_index_again_again_again_again_again_again, Shape,
                              Channel_index_again_again_again_again_again_again_again):
        """
        SpectrumAnlzr.DataGet
        Returns the data from the Spectrum Analyzer modules.
        Arguments: 
        -- Spectrum Analyzer instance (int) selects the Spectrum Analyzer instance this function refers to. Valid values are 1 for Spectrum Analyzer 1, and 2 for Spectrum Analyzer 2
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Data f0 (float64) is the x coordinate of the 1st acquired point
        -- Data df (float64) is the frequency distance between two acquired points
        -- Data Y size (int) is the number of data points in Data Y
        -- Data Y (1D array float64) is the data acquired in the Spectrum Analyzer
        -- Error described in the Response message&gt;Body section
        
        Function Generator 1-Channel
        FunGen1Ch.Start
        Starts the generation of the waveform on AO8 (SC4) or FAST AO (SC5) through the Function Generator module.
        Arguments: 
        -- Periods (int) is the number of periods to generate. Set -2 for continuous movement until Stop executes
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        FunGen1Ch.Stop
        Stops the generation of the waveform through the Function Generator module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        FunGen1Ch.StatusGet
        Gets the status of the waveform generation on AO8 (SC4) or FAST AO (SC5) through the Function Generator module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Status (unsigned int32) indicates if the generation is running (_1) or not (_0)
        -- Periods left (int) is the number of periods left to generate
        -- Error described in the Response message&gt;Body section
        
        
        
        FunGen1Ch.PropsSet
        Sets the amplitude, frequency, polarity, and direction of the waveform generated on AO8 (SC4) or FAST AO (SC5) through the Function Generator module.
        Arguments: 
        -- Amplitude (Percent) (float32) is the amplitude of the generated waveform in Percent, where 100Percent corresponds to +/- 10V at the output of the SC4/5
        -- Frequency (Hz) (float32) is the frequency of the generated waveform in Hz
        -- Polarity (unsigned int16) switches between positive and negative sign of the generated waveform. This will invert the waveform along the y axis. 0 means no change, 1 means Negative, and 2 means Positive
        -- Direction (unsigned int16) switches between forward and backward waveform. This will invert the waveform along the x axis (reverse the time). 0 means no change, 1 means Backward, and 2 means Forward
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        FunGen1Ch.PropsGet
        Returns the amplitude, frequency, polarity, and direction of the waveform generated on AO8 (SC4) or FAST AO (SC5) through the Function Generator module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Amplitude (Percent) (float32) is the amplitude of the generated waveform in Percent, where 100Percent corresponds to +/- 10V at the output of the SC4/5
        -- Frequency (Hz) (float32) is the frequency of the generated waveform in Hz
        -- Polarity (unsigned int16) is the positive (_0) or negative (_1) sign of the generated waveform
        -- Direction (unsigned int16) is the forward (_0) or backward (_1) direction of the generated waveform
        -- Error described in the Response message&gt;Body section
        
        
        FunGen1Ch.IdleSet
        Sets the idle value in the Function Generator module.
        The idle value is the value of AO8 (SC4) or FAST AO (SC5) when the function generator is not running.
        Arguments: 
        -- Idle value (float32)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        FunGen1Ch.IdleGet
        Returns the idle value in the Function Generator module.
        The idle value is the value of AO8 (SC4) or FAST AO (SC5) when the function generator is not running.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Idle value (float32)
        -- Error described in the Response message&gt;Body section
        
        Function Generator 2-Channels
        FunGen2Ch.Start
        Starts the generation of the waveforms on the FAST AO or any available analog output through the Function Generator 2-Channels module.
        Arguments: 
        -- Periods (int) is the number of periods to generate. Set -2 for continuous movement until Stop executes
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        FunGen2Ch.Stop
        Stops the generation of the waveform through the Function Generator 2-Channels module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        FunGen2Ch.StatusGet
        Returns the status of the waveforms generation in the Function Generator 2-Channels module.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Status (unsigned int32) indicates if the generation is running (_1) or not (_0)
        -- Periods left (int) is the number of periods left to generate
        -- Error described in the Response message&gt;Body section
        
        FunGen2Ch.IdleSet
        Sets the idle value in the Function Generator 2-Channels module.
        The idle value is the value of the FAST AO (for the selected SC5) when the function generator is not running.
        Arguments: 
        -- Device (int) selects the SC5 where the idle value will be applied. 0 corresponds to SC5 1, 1 corresponds to SC5 2, and so on
        -- Idle value (float32)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        FunGen2Ch.IdleGet
        Returns the idle value in the Function Generator 2-Channels module.
        The idle value is the value of the FAST AO (for the selected SC5) when the function generator is not running.
        Arguments: 
        -- Device (int) selects the SC5 the idle value will be read from. 0 corresponds to SC5 1, 1 corresponds to SC5 2, and so on
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Idle value (float32)
        -- Error described in the Response message&gt;Body section
        
        
        FunGen2Ch.OnOffSet
        Sets the status of the On/Off switch of the selected channel  in the Function Generator 2-Channels module.
        Arguments: 
        -- Channel index (int) selects the channel. Valid values are 1 for Channel 1 and 2 for Channel 2
        -- Status (unsigned int32) switches the channel Off (_0) or On(_1)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        FunGen2Ch.OnOffGet
        Returns the status of the On/Off switch of Channel 1 in the Function Generator 2-Channels module.
        Arguments: 
        -- Channel index (int) selects the channel. Valid values are 1 for Channel 1 and 2 for Channel 2
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Status (unsigned int32) returns whether the channel is Off (_0) or On(_1)
        -- Error described in the Response message&gt;Body section
        
        
        FunGen2Ch.SignalSet
        Sets the signal assigned to the selected channel in the Function Generator 2-Channels module.
        Arguments: 
        -- Channel index (int) selects the channel. Valid values are 1 for Channel 1 and 2 for Channel 2
        -- Signal index (int) where the possible values are: 0 for the Fast AO, 1 for AO1, 2 for AO2, 3 for AO3 and so on
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        FunGen2Ch.SignalGet
        Returns the signal assigned to the selected channel  in the Function Generator 2-Channels module.
        Arguments: 
        -- Channel index (int) selects the channel. Valid values are 1 for Channel 1 and 2 for Channel 2
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Signal index (int) where the values are: 0 for the Fast AO, 1 for AO1, 2 for AO2, 3 for AO3 and so on
        -- Error described in the Response message&gt;Body section
        
        
        
        FunGen2Ch.PropsSet
        Sets the amplitude, time, polarity, direction, and state of the Add/Zero switch of the waveform generated on the selected channel in the Function Generator 2-Channels module.
        Arguments: 
        -- Channel index (int) selects the channel. Valid values are 1 for Channel 1 and 2 for Channel 2
        -- Amplitude (Percent) (float32) is the amplitude in Percent of the waveform generated on Channel 1, where 100Percent corresponds to +/- 10V at the output of the SC5
        -- Time (s) (float32) is the time for each period of the generated waveforms in seconds. 
        The time is such, so that the frequency can be set in multiples of 0.4768 Hz up to 15.625 kHz
        -- Polarity (unsigned int16) switches between positive (_2) and negative (_1) sign of the waveform generated on Channel 1. If value_0, there is no change.
        This will invert the waveform along the y axis
        -- Direction (unsigned int16) switches between forward (_2) and backward (_1) waveforms.
        If value_0, there is no change.
        This will invert the waveforms along the x axis (reverse the time). This is applied to both channels
        -- Add/Zero (unsigned int16) means that when Zero (_2), the waveform is generated on Channel 1 around zero. When Add (_1), adds the waveform to the current Idle/DC value. If value_0, there is no change
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        FunGen2Ch.PropsGet
        Returns the amplitude, time, polarity, direction, and state of the Add/Zero switch of the waveform generated on the selected channel in the Function Generator 2-Channels module.
        Arguments: 
        -- Channel index (int) selects the channel. Valid values are 1 for Channel 1 and 2 for Channel 2
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Amplitude (Percent) (float32) is the amplitude in Percent of the waveform generated on Channel 1, where 100Percent corresponds to +/- 10V at the output of the SC5
        -- Time (s) (float32) is the time for each period of the generated waveforms in seconds. 
        The time is such, so that the frequency can be set in multiples of 0.4768 Hz up to 15.625 kHz
        -- Polarity (unsigned int16) switches between positive (_0) and negative (_1) sign of the waveform generated on Channel 1
        This will invert the waveform along the y axis
        -- Direction (unsigned int16) switches between forward (_0) and backward (_1) waveforms.
        This will invert the waveforms along the x axis (reverse the time). This is applied to both channels
        -- Add/Zero (unsigned int16) means that when Zero (_0), the waveform is generated on Channel 1 around zero. When Add (_1), adds the waveform to the current Idle/DC value
        -- Error described in the Response message&gt;Body section
        
        FunGen2Ch.WaveformSet
        Sets the shape of the waveform to generate on the selected channel in the Function Generator 2-Channels module.
        Possible values for the shape are: 0_linear bipolar, 1_linear unipolar, 2_quadratic bipolar, 3_quadratic unipolar, 4_triangle bipolar, 5_triangle unipolar, 6_square bipolar, 7_square unipolar, 8_sine bipolar, 9_sine unipolar
        Arguments: 
        -- Channel index (int) selects the channel. Valid values are 1 for Channel 1 and 2 for Channel 2
        -- Shape (unsigned int16)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        FunGen2Ch.WaveformGet
        Returns the shape of the waveform generated on the selected channel in the Function Generator 2-Channels module.
        Possible values for the shape are: 0_linear bipolar, 1_linear unipolar, 2_quadratic bipolar, 3_quadratic unipolar, 4_triangle bipolar, 5_triangle unipolar, 6_square bipolar, 7_square unipolar, 8_sine bipolar, 9_sine unipolar, 10_custom
        Arguments: 
        -- Channel index (int) selects the channel. Valid values are 1 for Channel 1 and 2 for Channel 2
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Shape (unsigned int16)
        -- Error described in the Response message&gt;Body section
        
        
        
        Utilities
        """
        return self.quickSend("SpectrumAnlzr.DataGet",
                              [Spectrum_Analyzer_instance, Periods, Amplitude_Percent, Frequency_Hz, Polarity,
                               Direction, Idle_value, Periods, Device, Idle_value, Device, Channel_index, Status,
                               Channel_index, Channel_index, Signal_index, Channel_index, Channel_index,
                               Amplitude_Percent, Time_s, Polarity, Direction, AdddivZero, Channel_index, Channel_index,
                               Shape, Channel_index],
                              ["i", "i", "f", "f", "H", "H", "f", "i", "i", "f", "i", "i", "I", "i", "i", "i", "i", "i",
                               "f", "f", "H", "H", "H", "i", "i", "H", "i"],
                              ["d", "d", "i", "*d", "I", "i", "f", "f", "H", "H", "f", "I", "i", "f", "I", "i", "f",
                               "f", "H", "H", "H", "H"])

    def Util_SessionPathGet(self):
        """
        Util.SessionPathGet
        Returns the session path.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Session path size (int) is the number of characters of the Session path string
        -- Session path (string) 
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Util.SessionPathGet", [], [], ["i", "*-c"])

    def Util_SettingsLoad(self, Settings_file_path, Load_session_settings):
        """
        Util.SettingsLoad
        Loads the settings from the specified .ini file.
        Arguments:
        -- Settings file path size (int) is the number of characters of the Settings file path string
        -- Settings file path (string) is the path of the settings file to load
        -- Load session settings (unsigned int32) automatically loads the current settings from the session file bypassing the settings file path argument, where 0_False and 1_True  
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Util.SettingsLoad", [Settings_file_path, Load_session_settings],
                              ["+*c", "I"], [])

    def Util_SettingsSave(self, Settings_file_path, Save_session_settings):
        """
        Util.SettingsSave
        Saves the current settings in the specified .ini file.
        Arguments:
        -- Settings file path size (int) is the number of characters of the Settings file path string
        -- Settings file path (string) is the path of the settings file to save
        -- Save session settings (unsigned int32) automatically saves the current settings into the session file bypassing the settings file path argument, where 0_False and 1_True  
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Util.SettingsSave", [Settings_file_path, Save_session_settings],
                              ["+*c", "I"], [])

    def Util_LayoutLoad(self, Layout_file_path, Load_session_layout):
        """
        Util.LayoutLoad
        Loads a layout from the specified .ini file.
        Arguments:
        -- Layout file path size (int) is the number of characters of the layout file path string
        -- Layout file path (string) is the path of the layout file to load
        -- Load session layout (unsigned int32) automatically loads the layout from the session file bypassing the layout file path argument, where 0_False and 1_True  
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Util.LayoutLoad", [Layout_file_path, Load_session_layout],
                              ["+*c", "I"], [])

    def Util_LayoutSave(self, Layout_file_path, Save_session_layout):
        """
        Util.LayoutSave
        Saves the current layout in the specified .ini file.
        Arguments:
        -- Layout file path size (int) is the number of characters of the layout file path string
        -- Layout file path (string) is the path of the layout file to save
        -- Save session layout (unsigned int32) automatically saves the current layout into the session file bypassing the layout file path argument, where 0_False and 1_True  
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Util.LayoutSave", [Layout_file_path, Save_session_layout],
                              ["+*c", "I"], [])

    def Util_Lock(self):
        """
        Util.Lock
        Locks the Nanonis software.
        Launches the Lock modal window, preventing the user to interact with the Nanonis software until unlocking it manually or through the <i>Util.UnLock</i> function.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Util.Lock", [], [], [])

    def Util_UnLock(self):
        """
        Util.UnLock
        Unlocks the Nanonis software.
        Closes the Lock modal window which prevents the user to interact with the Nanonis software.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Util.UnLock", [], [], [])

    def Util_RTFreqSet(self, RT_frequency):
        """
        Util.RTFreqSet
        Sets the Real Time controller frequency.
        Arguments:
        -- RT frequency (float32) is the Real Time frequency in Hz
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Util.RTFreqSet", [RT_frequency], ["f"], [])

    def Util_RTFreqGet(self):
        """
        Util.RTFreqGet
        Gets the Real Time controller frequency.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- RT frequency (float32) is the Real Time frequency in Hz
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Util.RTFreqGet", [], [], ["f"])

    def Util_AcqPeriodSet(self, Acquisition_Period_s):
        """
        Util.AcqPeriodSet
        Sets the Acquisition Period (s) in the TCP Receiver.
        Arguments:
        -- Acquisition Period (s) (float32)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Util.AcqPeriodSet", [Acquisition_Period_s], ["f"], [])

    def Util_AcqPeriodGet(self):
        """
        Util.AcqPeriodGet
        Gets the Acquisition Period (s) in the TCP Receiver.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Acquisition Period (s) (float32) 
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Util.AcqPeriodGet", [], [], ["f"])

    def Util_RTOversamplSet(self, RT_oversampling):
        """
        Util.RTOversamplSet
        Sets the Real-time oversampling in the TCP Receiver.
        The 24 signals are oversampled on the RT engine before they are sent to the host. The oversampling affects the maximum Spectrum Analyzer frequency and other displays.
        Arguments:
        -- RT oversampling (int)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("Util.RTOversamplSet", [RT_oversampling], ["i"], [])

    def APRFGen_RFOutOnOffSet(self, RF_Output: np.uint32):
        """
        APRFGen.RFOutOnOffSet
        Switches the RF Output On or Off.
        Arguments: 
        -- RF Output (unsigned int32) switches the RF Output Off (_0) or On (_1)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("APRFGen.RFOutOnOffSet", [RF_Output], ["I"], [])

    def APRFGen_RFOutOnOffGet(self):
        """
        APRFGen.RFOutOnOffGet
        Returns the status of the RF Output. 
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- RF Output (unsigned int32) indicates if the RF Output is Off (_0) or On (_1)
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("APRFGen.RFOutOnOffGet", [], [], ["I"])

    def APRFGen_FreqSet(self, Force_RF_On: np.uint32, Frequency_Hz: np.float32):
        """
        APRFGen.FreqSet
        Sets the Frequency value in the CW mode.
        Arguments: 
        -- Force RF Output On? (unsigned int32) defines if the RF Output is switched on (_1), in case it is off, or not (_0) before setting the Frequency
        -- Frequency (Hz) (float32)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("APRFGen.FreqSet", [Force_RF_On, Frequency_Hz], ["I", "f"], [])

    def APRFGen_FreqGet(self):
        """
        APRFGen.FreqGet
        Returns the Frequency value set in the CW mode.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Frequency (Hz) (float32)
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("APRFGen.FreqGet", [], [], ["f"])

    def APRFGen_PowerSet(self, Force_RF_On: np.uint32, Power_dBm: np.float32):
        """
        APRFGen.PowerSet
        Sets the Power value in the CW mode.
        Arguments: 
        -- Force RF Output On? (unsigned int32) defines if the RF Output is switched on (_1), in case it is off, or not (_0) before setting the Power
        -- Power (dBm) (float32)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("APRFGen.PowerSet", [Force_RF_On, Power_dBm], ["I", "f"], [])

    def APRFGen_PowerGet(self):
        """
        APRFGen.PowerGet
        Returns the Power value set in the CW mode.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Power (dBm) (float32)
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("APRFGen.PowerGet", [], [], ["f"])

    def APRFGen_SwpStop(self):
        """
        APRFGen.SwpStop
        Stops the running Sweep (Frequency, Power, or List) and switches the mode to CW.
        Arguments: 
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("APRFGen.SwpStop", [], [], [])

    def APRFGen_FreqSwpStart(self, Direction: np.uint32):
        """
        APRFGen.FreqSwpStart
        Starts a Frequency Sweep.
        Arguments: 
        -- Direction (unsigned int32) defines the sweep direction Up (_0) or Down (_1)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("APRFGen.FreqSwpStart", [Direction], ["I"], [])

    def APRFGen_FreqSwpLimitsSet(self, Lower_limit: np.float32, Upper_limit: np.float32):
        """
        APRFGen.FreqSwpLimitsSet
        Sets the limits of the Frequency Sweep in the RF Generator.
        Arguments: 
        -- Lower limit (float32) defines the lower limit of the sweep range
        -- Upper limit (float32) defines the upper limit of the sweep range
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("APRFGen.FreqSwpLimitsSet", [Lower_limit, Upper_limit], ["f", "f"], [])

    def APRFGen_FreqSwpLimitsGet(self):
        """
        APRFGen.FreqSwpLimitsGet
        Returns the limits of the Frequency Sweep in the RF Generator.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Lower limit (float32) defines the lower limit of the sweep range
        -- Upper limit (float32) defines the upper limit of the sweep range
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("APRFGen.FreqSwpLimitsGet", [], [], ["f", "f"])

    def APRFGen_FreqSwpPropsSet(self, Mode: np.uint16, Dwell_s: np.float32, Repetitions: np.float32,
                         Infinite: np.uint16, Points: np.int32, Off_s:np.float32, AutoOff:np.uint16):
        """
        APRFGen.FreqSwpPropsSet
        Sets the configuration of the Frequency Sweep in the RF Generator.
        Arguments: 
        -- Sweep mode (unsigned int16) where 0 points means no change, 1 is Linear, and 2 is Log
        -- Dwell time (s) (float32) is the amount of time in seconds the sweep plays each sweep point with the RF On
        -- Repetitions (float32) defines a finite number of sweep repetitions being played after triggering a sweep
        -- Infinite (unsigned int16) sets an infinite number of repetitions, where 0_no change, 1_On, 2_Off
        -- Points (int32) sets the number of sweep points
        -- Off time (s) (float32)  is the amount of time in seconds the sweep pauses with the RF Off before playing the next point
        -- Auto Off Time (unsigned int16) Enables or disables automatic Off (delay) Time selection. In automatic mode, Off Time is configured such that the transients between sweep points are blanked and do not appear at the RF output, where 0_no change, 1_On, 2_Off
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("APRFGen.FreqSwpPropsSet", [Mode, Dwell_s, Repetitions, Infinite, Points, Off_s, AutoOff],
                              ["H", "f", "f", "H", "i", "f", "H"], [])

    def APRFGen_FreqSwpPropsGet(self):
        """
        APRFGen.FreqSwpPropsGet
        Returns the configuration of the Frequency Sweep in the RF Generator.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Sweep mode (unsigned int16) where 1 is Linear, and 2 is Log
        -- Dwell time (s) (float32) is the amount of time in seconds the sweep plays each sweep point with the RF On
        -- Repetitions (float32) defines a finite number of sweep repetitions being played after triggering a sweep
        -- Infinite (unsigned int16) sets an infinite number of repetitions, where 1_On, 2_Off
        -- Points (int32) sets the number of sweep points
        -- Off time (s) (float32)  is the amount of time in seconds the sweep pauses with the RF Off before playing the next point
        -- Auto Off Time (unsigned int16) Enables or disables automatic Off (delay) Time selection. In automatic mode, Off Time is configured such that the transients between sweep points are blanked and do not appear at the RF output, where 1_On, 2_Off
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("APRFGen.FreqSwpPropsGet", [], [],
                              ["H", "f", "f", "H", "i", "f", "H"])

    def APRFGen_PowerSwpStart(self, Direction: np.uint32):
        """
        APRFGen.PowerSwpStart
        Starts a Power Sweep.
        Arguments: 
        -- Direction (unsigned int32) defines the sweep direction Up (_0) or Down (_1)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("APRFGen.PowerSwpStart", [Direction], ["I"], [])

    def APRFGen_PowerSwpLimitsSet(self, Lower_limit: np.float32, Upper_limit: np.float32):
        """
        APRFGen.PowerSwpLimitsSet
        Sets the limits of the Power Sweep in the RF Generator.
        Arguments: 
        -- Lower limit (float32) defines the lower limit of the sweep range
        -- Upper limit (float32) defines the upper limit of the sweep range
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("APRFGen.PowerSwpLimitsSet", [Lower_limit, Upper_limit], ["f", "f"], [])

    def APRFGen_PowerSwpLimitsGet(self):
        """
        APRFGen.PowerSwpLimitsGet
        Returns the limits of the Power Sweep in the RF Generator.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Lower limit (float32) defines the lower limit of the sweep range
        -- Upper limit (float32) defines the upper limit of the sweep range
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("APRFGen.PowerSwpLimitsGet", [], [], ["f", "f"])

    def APRFGen_PowerSwpPropsSet(self, Dwell_s: np.float32, Repetitions: np.float32,
                         Infinite: np.uint16, Points: np.int32, Off_s:np.float32, AutoOff:np.uint16):
        """
        APRFGen.PowerSwpPropsSet
        Sets the configuration of the Power Sweep in the RF Generator.
        Arguments: 
        -- Dwell time (s) (float32) is the amount of time in seconds the sweep plays each sweep point with the RF On
        -- Repetitions (float32) defines a finite number of sweep repetitions being played after triggering a sweep
        -- Infinite (unsigned int16) sets an infinite number of repetitions, where 0_no change, 1_On, 2_Off
        -- Points (int32) sets the number of sweep points
        -- Off time (s) (float32)  is the amount of time in seconds the sweep pauses with the RF Off before playing the next point
        -- Auto Off Time (unsigned int16) Enables or disables automatic Off (delay) Time selection. In automatic mode, Off Time is configured such that the transients between sweep points are blanked and do not appear at the RF output, where 0_no change, 1_On, 2_Off
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("APRFGen.PowerSwpPropsSet", [Dwell_s, Repetitions, Infinite, Points, Off_s, AutoOff],
                              ["f", "f", "H", "i", "f", "H"], [])

    def APRFGen_PowerSwpPropsGet(self):
        """
        APRFGen.PowerSwpPropsGet
        Returns the configuration of the Power Sweep in the RF Generator.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Dwell time (s) (float32) is the amount of time in seconds the sweep plays each sweep point with the RF On
        -- Repetitions (float32) defines a finite number of sweep repetitions being played after triggering a sweep
        -- Infinite (unsigned int16) sets an infinite number of repetitions, where 1_On, 2_Off
        -- Points (int32) sets the number of sweep points
        -- Off time (s) (float32)  is the amount of time in seconds the sweep pauses with the RF Off before playing the next point
        -- Auto Off Time (unsigned int16) Enables or disables automatic Off (delay) Time selection. In automatic mode, Off Time is configured such that the transients between sweep points are blanked and do not appear at the RF output, where 1_On, 2_Off
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("APRFGen.PowerSwpPropsGet", [], [],
                              ["f", "f", "H", "i", "f", "H"])

    def APRFGen_ListSwpStart(self, Direction: np.uint32):
        """
        APRFGen.ListSwpStart
        Starts a List Sweep.
        Arguments: 
        -- Direction (unsigned int32) defines the sweep direction Up (_0) or Down (_1)
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        
        """
        return self.quickSend("APRFGen.ListSwpStart", [Direction], ["I"], [])

    def APRFGen_ListSwpPropsSet(self, Signal:np.uint16, Values,
                         Infinite: np.uint16, Repetitions: np.float32, AutoOff:np.uint16):
        """
        APRFGen.ListSwpPropsSet
        Sets the configuration of the List Sweep in the RF Generator.
        Arguments: 
        -- Signal to Sweep (unsigned int16) is the parameter to sweep. Frequency is 1, Power is 2, Frequency & Power is 3. 0 means no change.
        -- Sweep Values Rows (int) defines the number of rows of the Sweep Values array
        -- Sweep Values Columns (int) defines the number of columns of the Sweep Values array. This should be set to 4.
        -- Sweep Values (2D array float32) defines the values applied at each sweep point, where each row contains a Frequency value (Hz), Power value (dBm), Dwell time (s), and Off time (s).
        -- Infinite (unsigned int16) sets an infinite number of repetitions, where 0_no change, 1_On, 2_Off
        -- Repetitions (float32) defines a finite number of sweep repetitions being played after triggering a sweep
        -- Auto Off Time (unsigned int16) Enables or disables automatic Off (delay) Time selection. In automatic mode, Off Time is configured such that the transients between sweep points are blanked and do not appear at the RF output, where 0_no change, 1_On, 2_Off
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("APRFGen.ListSwpPropsSet", [Signal, Values, Infinite, Repetitions, AutoOff],
                              ["H", "2f", "H", "f", "H"], [])

    def APRFGen_ListSwpPropsGet(self):
        """
        APRFGen.ListSwpPropsGet
        Returns the configuration of the List Sweep in the RF Generator.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Signal to Sweep (unsigned int16) is the parameter to sweep. Frequency is 1, Power is 2, Frequency & Power is 3.
        -- Sweep Values Rows (int) is the number of rows of the Sweep Values array
        -- Sweep Values Columns (int) is the number of columns of the Sweep Values array.
        -- Sweep Values (2D array float32) are the values applied at each sweep point, where each row contains a Frequency value (Hz), Power value (dBm), Dwell time (s), and Off time (s).
        -- Infinite (unsigned int16) sets an infinite number of repetitions, where 1_On, 2_Off
        -- Repetitions (float32) defines a finite number of sweep repetitions being played after triggering a sweep
        -- Auto Off Time (unsigned int16) Enables or disables automatic Off (delay) Time selection. In automatic mode, Off Time is configured such that the transients between sweep points are blanked and do not appear at the RF output, where 1_On, 2_Off
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("APRFGen.ListSwpPropsGet", [], [],
                              ["H", "i", "i", "2f", "H", "f", "H"])

    def APRFGen_TrigRearm(self):
        """
        APRFGen.TrigRearm
        Rearms the trigger.
        Arguments: 
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("APRFGen.TrigRearm", [], [], [])

    def APRFGen_TrigPropsSet(self, Edge: np.uint16, Delay_s: np.float32,
                         Source: np.uint16, Type: np.uint16, Event_Count:np.uint16, Mode:np.uint16):
        """
        APRFGen.TrigPropsSet
        Sets the configuration of the triggering in the RF Generator.
        Arguments: 
        -- Edge (unsigned int16) is the polarity of the external trigger, where 0_no change, 1_Rising, 2_Falling
        -- Delay (s) (float32) is the amount of time in seconds to delay the response to the external trigger
        -- Source (unsigned int16) where 0_no change, 1_Off (Immediate), 2_On (External Trigger)
        -- Type (unsigned int16) where 0_no change, 1_Complete Sweep, 2_Gated, 3_Single Point
                Complete Sweep: the sweep is fully executed when receiving the trigger
                Gated: the sweep is only executed while the trigger signal is high (rising) or low (falling). This only works with an external trigger source
                Single Point: one point of the sweep is executed when receiving the trigger
        -- Event Count (unsigned int16) where
                Setting the value to N means that only every Nth trigger event will be considered. 
                Setting it to one means will use every trigger event that does not occur during a running sweep.
        -- Mode (unsigned int16) where 0_no change, 1_Single Shot, 2_Continuous
        
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Error described in the Response message&gt;Body section
        
        
        """
        return self.quickSend("APRFGen.TrigPropsSet", [Edge, Delay_s, Source, Type, Event_Count, Mode],
                              ["H", "f", "H", "H", "H", "H"], [])

    def APRFGen_TrigPropsGet(self):
        """
        APRFGen.TrigPropsGet
        Returns the configuration of the triggering in the RF Generator.
        Arguments: None
        Return arguments (if Send response back flag is set to True when sending request message):
        
        -- Edge (unsigned int16) is the polarity of the external trigger, where 1_Rising, 2_Falling
        -- Delay (s) (float32) is the amount of time in seconds to delay the response to the external trigger
        -- Source (unsigned int16) where 1_Off (Immediate), 2_On (External Trigger)
        -- Type (unsigned int16) where 1_Complete Sweep, 2_Gated, 3_Single Point
                Complete Sweep: the sweep is fully executed when receiving the trigger
                Gated: the sweep is only executed while the trigger signal is high (rising) or low (falling). This only works with an external trigger source
                Single Point: one point of the sweep is executed when receiving the trigger
        -- Event Count (unsigned int16) where
                Setting the value to N means that only every Nth trigger event will be considered. 
                Setting it to one means will use every trigger event that does not occur during a running sweep.
        -- Mode (unsigned int16) where 1_Single Shot, 2_Continuous
        -- Error described in the Response message&gt;Body section
        
        """
        return self.quickSend("APRFGen.TrigPropsGet", [], [],
                              ["H", "f", "H", "H", "H", "H"])

"""
"""


