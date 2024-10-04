#This example acquires one channel (i.e. the tip height) with
#a defined oversampling and logs the oversample value
#in a variable for as many samples as defined or until
#manually stopped (pressing the Spacebar)

import nanonis_spm
import time
import keyboard
import numpy as np
import socket

connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
connection.connect(("localhost",6501))

nanonisInstance = nanonis_spm.Nanonis(connection)
nanonisInstance.returnDebugInfo(1)

Acq_Finished=False
Stopped_Manually=False

Channel_Index=30        #tip height
Channel_Oversampling=10
Channel_NrSamples=2000
Channel_Values=[]
Channel_AccumulatedValue=0

#Start the acquisition and oversampling of the selected signal
#for as long as the defined number of samples
#or until manually stopped (pressing the Spacebar)
while True:
    Channel_AccumulatedValue=0
    for sample in range(Channel_Oversampling):
        Channel_AccumulatedValue=Channel_AccumulatedValue+nanonisInstance.Signals_ValGet(Channel_Index,0)[2][0]
    Channel_Values.append(Channel_AccumulatedValue/Channel_Oversampling)
    if len(Channel_Values)>=Channel_NrSamples:
        Acq_Finished=True
        break
    if keyboard.is_pressed(' '):
        Stopped_Manually=True
        break

print("Acquisition finished is {}, Stopped Manually is {}, and the number of acquired samples is {}".format(Acq_Finished,Stopped_Manually,len(Channel_Values)))
print(Channel_Values)

nanonisInstance.close()
