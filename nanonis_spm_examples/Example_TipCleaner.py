#Moves the tip to a specified location and performs Bias pulses there
#Useful to try to clean the tip
#without affecting the sample at the current position


import nanonis_spm
import time
import numpy as np
import keyboard
import socket

connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
connection.connect(("localhost",6501))

nanonisInstance = nanonis_spm.Nanonis(connection)
nanonisInstance.returnDebugInfo(1)

XY_GoToPos=[-0.0000000013,0.0000000035] #meters
XY_StayAtCurrentPos=False
BiasPulse_Volts=0.5
BiasPulse_Width=0.2 #seconds
BiasPulse_ZCtrl=1 #hold the Z-Ctrl
BiasPulse_NrPulses=5
BiasPulse_Pause=0.2 #seconds to wait between pulses
    
#Return the tip position
XY_CurrentPos=nanonisInstance.FolMe_XYPosGet(1)[2]

#If clean the tip at the current position, skip moving the tip
if XY_StayAtCurrentPos==False:
    nanonisInstance.FolMe_XYPosSet(XY_GoToPos[0],XY_GoToPos[1],1)

#Start pulsing Bias
for pulse in range(BiasPulse_NrPulses):
    nanonisInstance.Bias_Pulse(
    1, #wait until done
    BiasPulse_Width,
    BiasPulse_Volts,
    np.uint16(BiasPulse_ZCtrl), #Z-Ctrl on hold
    np.uint16(1)  #absolute Bias voltage
    )
    time.sleep(BiasPulse_Pause)
    #Stop pulsing if the Spacebar button is pressed
    if keyboard.is_pressed(' '): 
        break

#Move to the original position
if XY_StayAtCurrentPos==False:
    nanonisInstance.FolMe_XYPosSet(XY_CurrentPos[0],XY_CurrentPos[1],1)

nanonisInstance.close()
