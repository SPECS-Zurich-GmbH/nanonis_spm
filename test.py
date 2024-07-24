import nanonis_spm
import socket
import numpy as np

TCP_IP = '10.0.0.37'
TCP_PORT = 6501
socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
socket.connect((TCP_IP, TCP_PORT))





n = nanonis_spm.Nanonis(socket)


def parseHSSwp(vars):
    file1 = open("trash/Spectroscopy0001.fsb", "r")
    data = file1.read()


#TEST COMMAND
n.returnDebugInfo(1)
n.HSSwp_StatusGet()
