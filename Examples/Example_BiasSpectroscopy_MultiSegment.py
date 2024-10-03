#This example performs a bias spectroscopy consisting of several user-definable segments
#using the Bias Spectroscopy module.

import nanonis_spm
import time
import socket

connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
connection.connect(("localhost",6501))

nanonisInstance = nanonis_spm.Nanonis(connection)
nanonisInstance.returnDebugInfo(1)

Spectr_Channels=[0,24]  #Acquired channels: Current and Bias
Spectr_StartBias=[-1,-0.2,0.2,1.2]
Spectr_StopBias=[-0.2,0.2,1,2]
Spectr_NrPoints=[50,400,50,100]
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
nanonisInstance.BiasSpectr_AdvPropsSet(2,0,0,0)

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

#Run Bias Spectroscopy as many times as defined segments
SegmentIndex=0
for SegmentIndex in range(len(Spectr_StartBias)):
    nanonisInstance.BiasSpectr_PropsSet(
        0,0,2,Spectr_NrPoints[SegmentIndex],float("NaN"),1,2) #set to autosave, no dialog window
    nanonisInstance.BiasSpectr_LimitsSet(                     #set the segment limits
        Spectr_StartBias[SegmentIndex],Spectr_StopBias[SegmentIndex])
    Spectr_AcquiredData=nanonisInstance.BiasSpectr_Start(1,"Example_BiasSpectroscopy_MultiSegment")[2][5]
    AcqSignal_Current=AcqSignal_Current+Spectr_AcquiredData[1].tolist()
    AcqSignal_Bias=AcqSignal_Bias+Spectr_AcquiredData[2].tolist()
    time.sleep(0.2)

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
