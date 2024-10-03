#This example performs a custom bias sweep. You can create an array of
#Bias voltages and it will record the selected channels at each Bias voltage.

import nanonis_spm
import time
import socket

connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
connection.connect(("localhost",6501))

nanonisInstance = nanonis_spm.Nanonis(connection)
nanonisInstance.returnDebugInfo(1)

Sweep_StartBias=1
Sweep_StopBias=2
Sweep_NrPoints=10
Sweep_BiasIncr=(Sweep_StopBias-Sweep_StartBias)/(Sweep_NrPoints-1)
Sweep_SettlingTime=0.2 #seconds to wait after sweeping to a point
Sweep_AcqSignals=[0,24] #signals to acquire, Current & Bias
AcqSignal_Current=[]
AcqSignal_Bias=[]

#Create array with Sweep Bias values
Sweep_BiasValues=[]
for point in range(Sweep_NrPoints):
    BiasValue=point*Sweep_BiasIncr+Sweep_StartBias
    Sweep_BiasValues.append(BiasValue)
    
#Set Bias to Sweep Start value
nanonisInstance.Bias_Set(Sweep_StartBias)

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
    
#Sweep Bias & acquire signals
for point in range(Sweep_NrPoints):
    nanonisInstance.Bias_Set(Sweep_BiasValues[point])
    time.sleep(Sweep_SettlingTime)
    AcqSignal_Current.append(nanonisInstance.Signals_ValsGet(Sweep_AcqSignals, True)[2][1][0])
    AcqSignal_Bias.append(nanonisInstance.Signals_ValsGet(Sweep_AcqSignals, True)[2][1][1])


#Switch on-off Z-Ctrl according to the status before the sweep
nanonisInstance.ZCtrl_OnOffSet(ZCtrl_BeforeSweep)

print("CURRENT")
print(AcqSignal_Current)
print("BIAS")
print(AcqSignal_Bias)

nanonisInstance.close()
