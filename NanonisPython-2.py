# Joris Keizer - Feb 2020
# Silicon Quantum Computing (sqc.com.au)
# Bare-bones Nanonis Scan.FrameDataGrab python example 

import numpy as np
import socket 
import bitstring
from ctypes import *

# class to store the data 
class scan_data(object):
	data = np.array([])
	channels = 0
	lines = 0
	pixels = 0

# open the TCP/IP connection
def TCPIP_open():
	global sock
	ip_addr = 'localhost'  
	port = 6501
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.connect((ip_addr, port))  

# close the TCP/IP connection
def TCPIP_close():
	sock.close()

# convert a integer -> hex string -> byte array
def int2byte(val,size=None):
	if size==16:
		msg_hex=f"{val:0{4}x}"                                        # 16bit, strip the 0x  
	else: 
		msg_hex=f"{val:0{8}x}"                                        # 32bit (default)  
	h = bytearray(int(len(msg_hex)/2))                                # define h as an array with size= number of bytes of the full message
	for k in range(int(len(msg_hex)/2)):                              # this loop runs the same number of iterations as bytes of the full message and fills h array
		t = bitstring.BitArray(hex=msg_hex[2*k:2*k+2])
		h[k] = t.uint
	return h

# convert a hex string to a 32 bit integer
def convert(s):
	i = int(s, 16)                   # convert from hex to a Python int
	cp = pointer(c_int32(i))         # make this into a c integer   
	fp = cast(cp, POINTER(c_int32))  # cast the int pointer to a float pointer
	return fp.contents.value         # dereference the pointer, get the float

# get the scan buffer
# we need the number of pixels and lines to calculate the size of the data block
def get_scan_buffer():
	Message=bytearray(b'Scan.BufferGet\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00')
	sock.send(Message)
	reply=sock.recv(1024)
	num_channels=convert(str(reply[40:44].hex()))
	scan_data.pixels = convert(str(reply[44+num_channels*4:48+num_channels*4].hex()))
	scan_data.lines = convert(str(reply[48+num_channels*4:52+num_channels*4].hex()))

# get and parse the scan data 
# default channel = z, default direction = forward 
def get_scan_data(chan=14, direc=1):	
	Message=bytearray(b'Scan.FrameDataGrab\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\x00\x01\x00\x00')+int2byte(chan)+int2byte(direc)
	sock.send(Message)
	# calculate the size of the data block
	data_size=4*scan_data.lines*scan_data.pixels
	reply = sock.recv(data_size+1024)
	# grab the size of the body and the channel name string
	# we need this to calculate the position where the scan data block start
	body_size=convert(str(reply[32:36].hex()))
	name_size=convert(str(reply[40:44].hex()))
	# make sure we indeed got the whole message
	while len(reply)<body_size:
		reply += sock_data.recv(data_size)
	data_array = np.frombuffer(reply[52+name_size:52+name_size+data_size], dtype=np.float32)
	scan_data.data = np.ndarray(shape=(scan_data.lines,scan_data.pixels),dtype='>f4', buffer=data_array) # '>f4' = convert from little to big endian float
	print(scan_data.data)

# main 
TCPIP_open()
get_scan_buffer()
get_scan_data()
TCPIP_close()