#This example performs a custom Z sweep.
#The selected channels are acquired at each Z sweep point.

import nanonis_spm
import time
import socket

connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
connection.connect(("localhost",6501))

nanonisInstance = nanonis_spm.Nanonis(connection)
nanonisInstance.returnDebugInfo(1)

Sweep_Distance=0.0000005
Sweep_NrPoints=10
Sweep_Incr=Sweep_Distance/Sweep_NrPoints
Sweep_SettlingTime=0.2 #seconds to wait after sweeping to a point
Sweep_AcqSignals=[0,30] #signals to acquire, Current & Z
AcqSignal_Current=[]
AcqSignal_Z=[]

#Get Z-Ctrl status before sweeping
ZCtrl_BeforeSweep=nanonisInstance.ZCtrl_OnOffGet()[2][0]

#Switch off Z-Ctrl before sweeping
nanonisInstance.ZCtrl_OnOffSet(0)

#Wait until Z-Ctrl is really switched off
#checking the status every 100ms (2 seconds timeout)
for WaitTime in range(20):
    time.sleep(0.1)
    if nanonisInstance.ZCtrl_OnOffGet()[2][0]==0:
        break

#Get current Z position
Sweep_Value=nanonisInstance.ZCtrl_SetpntGet()[2][0]

#Sweep Z & acquire signals
for point in range(Sweep_NrPoints-1):
    Sweep_Value=Sweep_Value+Sweep_Incr
    nanonisInstance.ZCtrl_ZPosSet(Sweep_Value)
    time.sleep(Sweep_SettlingTime)
    AcqSignal_Current.append(nanonisInstance.Signals_ValsGet(Sweep_AcqSignals, True)[2][1][0])
    AcqSignal_Z.append(nanonisInstance.Signals_ValsGet(Sweep_AcqSignals, True)[2][1][1])

#Switch on-off Z-Ctrl according to the status before the sweep
nanonisInstance.ZCtrl_OnOffSet(ZCtrl_BeforeSweep)

print("CURRENT")
print(AcqSignal_Current)
print("Z")
print(AcqSignal_Z)

nanonisInstance.close()
