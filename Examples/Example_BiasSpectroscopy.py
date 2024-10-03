#This example performs a bias spectroscopy using the Bias Spectroscopy module.
#It configures and runs Bias Spectroscopy and then saves the acquired data into a file by using its auto-save functionality.

import nanonis_spm
import time
import socket

connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
connection.connect(("localhost",6501))

nanonisInstance = nanonis_spm.Nanonis(connection)
nanonisInstance.returnDebugInfo(1)

Spectr_Channels=[0,24]  #Acquired channels: Current and Bias
Spectr_StartBias=-2
Spectr_StopBias=2
Spectr_NrPoints=256
ZCtrl_TipLift=0         #meters
ZCtrl_SwitchOffDelay=2  #seconds
AcqSignal_Bias=[]
AcqSignal_Current=[]

#Open the Bias Spectroscopy module
nanonisInstance.BiasSpectr_Open()

#Store the current Bias value and Spectroscopy timings
Bias_BeforeSpectr=nanonisInstance.Bias_Get()[2][0]
SpectrTimings_BeforeSpectr=nanonisInstance.BiasSpectr_TimingGet()[2]

#Configure the Bias Spectroscopy module
nanonisInstance.BiasSpectr_ChsSet(Spectr_Channels)
nanonisInstance.BiasSpectr_TimingSet(0,0,float("NaN"),float("NaN"),float("NaN"),float("NaN"),0,0) #NaN means no change
nanonisInstance.BiasSpectr_PropsSet(0,0,2,Spectr_NrPoints,float("NaN"),1,2) #set to autosave, no dialog window
nanonisInstance.BiasSpectr_AdvPropsSet(2,0,0,0)
nanonisInstance.BiasSpectr_LimitsSet(Spectr_StartBias,Spectr_StopBias)

#Get Z-Ctrl status before sweeping
ZCtrl_BeforeSpectr=nanonisInstance.ZCtrl_OnOffGet()[2][0]

#Set Z-Controller Tip Lift & Switch Off delay before switching it off
nanonisInstance.ZCtrl_TipLiftSet(ZCtrl_TipLift)
nanonisInstance.ZCtrl_SwitchOffDelaySet(ZCtrl_SwitchOffDelay)
time.sleep(0.1)

#Switch off Z-Ctrl before running the spectroscopy
nanonisInstance.ZCtrl_OnOffSet(0)

#Wait until Z-Ctrl is really switched off
#checking the status every 200ms (8 seconds timeout)
for WaitTime in range(40):
    time.sleep(0.2)
    if nanonisInstance.ZCtrl_OnOffGet()[2][0]==0:
        break

#Run Bias Spectroscopy
Spectr_AcquiredData=nanonisInstance.BiasSpectr_Start(1,"Example_BiasSpectroscopy")[2][5]
AcqSignal_Current=Spectr_AcquiredData[1]
AcqSignal_Bias=Spectr_AcquiredData[2]
    
#Restore Bias and Spectroscopy timings
nanonisInstance.Bias_Set(Bias_BeforeSpectr)
nanonisInstance.BiasSpectr_TimingSet(
    SpectrTimings_BeforeSpectr[0],
    SpectrTimings_BeforeSpectr[1],
    SpectrTimings_BeforeSpectr[2],
    SpectrTimings_BeforeSpectr[3],
    SpectrTimings_BeforeSpectr[4],
    SpectrTimings_BeforeSpectr[5],
    SpectrTimings_BeforeSpectr[6],
    SpectrTimings_BeforeSpectr[7])
time.sleep(0.1)

#Switch on-off Z-Ctrl according to the status before the sweep
nanonisInstance.ZCtrl_OnOffSet(ZCtrl_BeforeSpectr)

print("CURRENT")
print(AcqSignal_Current)
print("BIAS")
print(AcqSignal_Bias)

nanonisInstance.close()
