#This example perfoms force-distance measurement with offset compensation.
#It requires the PLL module to run and
#setting up the Z-Spectroscopy configuration

import nanonis_spm
import time
import socket

connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
connection.connect(("localhost",6501))

nanonisInstance = nanonis_spm.Nanonis(connection)
nanonisInstance.returnDebugInfo(1)

ZCtrl_TipLift=0
ZCtrl_SettlingTime=0.05 #seconds to wait after switching off the Z-Ctrl
    
#Set Tip Lift to 0 in the Z-Controller
nanonisInstance.ZCtrl_TipLiftSet(ZCtrl_TipLift)

#Get Z-Ctrl status
ZCtrl_BeforeSweep=nanonisInstance.ZCtrl_OnOffGet()[2][0]

#Switch off Z-Ctrl
nanonisInstance.ZCtrl_OnOffSet(0)

#Wait until Z-Ctrl is really switched off
#checking the status every 10ms (2 seconds timeout)
for WaitTime in range(200):
    time.sleep(0.01)
    if nanonisInstance.ZCtrl_OnOffGet()[2][0]==0:
        break

#Wait after switching off the Z-Ctrl
time.sleep(ZCtrl_SettlingTime)

#Auto-center the frequency shift in the PLL module
nanonisInstance.PLL_FreqShiftAutoCenter(0)

#Run the Z-Spectroscopy measurement
nanonisInstance.ZSpectr_Start(0,"")

#Switch on-off Z-Ctrl according to the status before pulsing
nanonisInstance.ZCtrl_OnOffSet(ZCtrl_BeforeSweep)

nanonisInstance.close()
