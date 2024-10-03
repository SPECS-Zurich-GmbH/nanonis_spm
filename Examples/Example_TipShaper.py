#This procedure is mostly used to shape a STM tip,
#dipping it into the sample and pulling it back slowly
#First ramp Z (usually to approach the tip), then apply a bias voltage, and
#finally ramp Z again (usually to withdraw the tip)

import nanonis_spm
import time
import numpy as np
import keyboard
import socket

connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
connection.connect(("localhost",6501))

nanonisInstance = nanonis_spm.Nanonis(connection)
nanonisInstance.returnDebugInfo(1)

BeforeRamp_ZCrl_SwitchOffDelay=0.2 #seconds
BeforeRamp_CurrentGain_Apply=True
BeforeRamp_CurrentGain_Index=0
BeforeRamp_Bias_Apply=True
BeforeRamp_Bias_Volts=1 
Ramp1_TipLift=-0.000000002 #meters
Ramp1_LiftTime=0.2 #seconds
Bias_Volts=2
Bias_SettlingTime=0.1 #seconds
Ramp2_TipLift=0.000000005 #meters
Ramp2_LiftTime=0.1 #seconds
AfterRamp_ZCrl_Restore=True
AfterRamp_WaitTime=0.1 #seconds

#Remember Z-Ctrl status, Bias, and Current gain before ramping
Original_ZCtrl=nanonisInstance.ZCtrl_OnOffGet()[2][0]
Original_CurrentGain_Index=nanonisInstance.Current_GainsGet()[2][3]
Original_Bias=nanonisInstance.Bias_Get()[2][0]

#Don't use built-in TipLift as it doesn't ramp
#and set Switch Off Delay
nanonisInstance.ZCtrl_TipLiftSet(0)
nanonisInstance.ZCtrl_SwitchOffDelaySet(BeforeRamp_ZCrl_SwitchOffDelay)

#Switch off Z-Ctrl before ramping
nanonisInstance.ZCtrl_OnOffSet(0)

#Wait until Z-Ctrl is really switched off
#checking the status every 100ms (2 seconds timeout)
for WaitTime in range(20):
    time.sleep(0.1)
    if nanonisInstance.ZCtrl_OnOffGet()[2][0]==0:
        break

#Apply the optional parameters
if BeforeRamp_CurrentGain_Apply==True:
    nanonisInstance.Current_GainSet(BeforeRamp_CurrentGain_Index,-1)
if BeforeRamp_Bias_Apply==True:
    nanonisInstance.Bias_Set(BeforeRamp_Bias_Volts)
    time.sleep(Bias_SettlingTime)

#Execute first Z ramp
Ramp1_Z=nanonisInstance.Signals_ValGet(30,True)[2][0]
Ramp1_Z_Comparison=(Ramp1_Z+Ramp1_TipLift)>Ramp1_Z
Ramp1_iterations=round(Ramp1_LiftTime/0.005)
Ramp1_Z_Incr=(Ramp1_Z+Ramp1_TipLift)/Ramp1_iterations
Ramp1_Z_Original=Ramp1_Z+Ramp1_TipLift

for i in range(Ramp1_iterations):
    time.sleep(0.005) #every 5 ms
    if i+1==Ramp1_iterations:
        break
    else:
        Ramp1_Z=Ramp1_Z+Ramp1_TipLift
    nanonisInstance.ZCtrl_ZPosSet(Ramp1_Z)

#Apply Bias   
nanonisInstance.Bias_Set(Bias_Volts)
time.sleep(Bias_SettlingTime)

#Execute second Z ramp
Ramp2_Z=nanonisInstance.Signals_ValGet(30,True)[2][0]
Ramp2_Z_Comparison=(Ramp2_Z+Ramp2_TipLift)>Ramp2_Z
Ramp2_iterations=round(Ramp2_LiftTime/0.005)
Ramp2_Z_Incr=(Ramp2_Z+Ramp2_TipLift)/Ramp2_iterations
Ramp2_Z_Original=Ramp2_Z+Ramp2_TipLift

for i in range(Ramp2_iterations):
    time.sleep(0.005) #every 5 ms
    if i+1==Ramp2_iterations:
        break
    else:
        Ramp2_Z=Ramp2_Z+Ramp2_TipLift
    nanonisInstance.ZCtrl_ZPosSet(Ramp2_Z)
    
#Restore parameters
if BeforeRamp_Bias_Apply==True:
    nanonisInstance.Bias_Set(Original_Bias)
    time.sleep(Bias_SettlingTime)
if BeforeRamp_CurrentGain_Apply==True:
    nanonisInstance.Current_GainSet(Original_CurrentGain_Index,-1)
time.sleep(AfterRamp_WaitTime)
if AfterRamp_ZCrl_Restore==True:
    nanonisInstance.ZCtrl_OnOffSet(Original_ZCtrl)

nanonisInstance.close()
