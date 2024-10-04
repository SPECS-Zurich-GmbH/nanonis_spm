#This example applies bias voltage pulses at various Z positions

import nanonis_spm
import time
import numpy as np
import socket

connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
connection.connect(("localhost",6501))

nanonisInstance = nanonis_spm.Nanonis(connection)
nanonisInstance.returnDebugInfo(1)

Bias_PulseVolts=1
Bias_PulseWidth=0.1 #seconds
Z_Incr=0.000000001 #meters
Z_NrSteps=10
Z_SettlingTime=0.02 #seconds to wait after setting Z position
    
#Set Tip Lift to 0 in the Z-Controller
nanonisInstance.ZCtrl_TipLiftSet(0)

#Get Z-Ctrl status before pulsing
ZCtrl_BeforeSweep=nanonisInstance.ZCtrl_OnOffGet()[2][0]

#Switch off Z-Ctrl before pulsing
nanonisInstance.ZCtrl_OnOffSet(0)

#Wait until Z-Ctrl is really switched off
#checking the status every 10ms (2 seconds timeout)
for WaitTime in range(200):
    time.sleep(0.01)
    if nanonisInstance.ZCtrl_OnOffGet()[2][0]==0:
        break

#Start pulsing Bias and set Z position
Z_Pos=nanonisInstance.ZCtrl_ZPosGet()[2][0]
for point in range(Z_NrSteps):
    Z_Pos=Z_Pos+Z_Incr
    nanonisInstance.Bias_Pulse(
    1, #wait until done
    Bias_PulseWidth,
    Bias_PulseVolts,
    np.uint16(1), #Z-Ctrl on hold
    np.uint16(2)  #relative Bias voltage
    )
    nanonisInstance.ZCtrl_ZPosSet(Z_Pos)
    time.sleep(Z_SettlingTime)

#Switch on-off Z-Ctrl according to the status before pulsing
nanonisInstance.ZCtrl_OnOffSet(ZCtrl_BeforeSweep)

nanonisInstance.close()
