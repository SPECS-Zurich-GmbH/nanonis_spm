"""

IMPORTANT LEGAL DECLERATIONS

TODO:
-   Understand remaining functions
-   Look for improvements
-   Understand what's missing and start implementing

"""

import socket
import struct
import numpy as np


class Nanonis():

    def __init__(self):
        #enter IP and Port of Nanonis server
        self.TCP_IP = '192.168.236.1'
        self.TCP_PORT = 6501
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect( (self.TCP_IP, self.TCP_PORT) )

    def close(self):
        self.socket.close()

    
    def send(self, command, body_parts, body_type):

        zeroBuffer = bytearray(2)
        body = bytearray()
        response = True

        for i in range(len(body_parts)):
            body = body + struct.pack('>' + body_type[i], body_parts[i]) 

        body_size = len(body)

        message = bytearray(str(command).ljust(32, '\0').encode() + " " +
                                body_size.to_bytes(4, byteorder='big') + " " +
                                response.to_bytes(4, byteorder='big') + " " +
                                zeroBuffer +
                                body)

        self.socket.send(message)

        print(f"Sent message: {message}")

        Recv_Header = self.socket.recv(40) # read header - always 40 bytes
        Recv_BodySize = struct.unpack('>I', Recv_Header[32:36])[0] # get body size
        Recv_Body = self.socket.recv(Recv_BodySize) #read whole body
        #Here could check for validity of received body.
        return Recv_Body


    def parseResponse():
        return ""

    def execute():
        return ""
    



"""
command = "TestCommand"
bodyparts = [00000000, 00000000]
bodytype = 'i'

test = Nanonis()
Nanonis.send(command, bodyparts, bodytype)

"""



    
    