#This example switches between STM mode and AFM mode

import nanonis_spm
import time
import socket

connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
connection.connect(("localhost",6501))

nanonisInstance = nanonis_spm.Nanonis(connection)
nanonisInstance.returnDebugInfo(1)

Switch_To_AFM=1 # to AFM=1, to STM=0
ZController_TipLift=0.00000005 #meters
STM_ControllerName="log Current"
STM_Bias=1 
AFM_ControllerName="Frequency (neg)"
AFM_Bias=0
AFM_ModulatorIndex=1
AFM_ExcitationOut_OnOff=1
AFM_AmplController_OnOff=1
AFM_PhaseController_OnOff=0

#Pause Scan
nanonisInstance.Scan_Action(2,0)
time.sleep (0.1) #wait until X&Y positions are stable

#Set the TipLift in the Z-Controller
nanonisInstance.ZCtrl_TipLiftSet(ZController_TipLift)

#Switch off Z-Ctrl
nanonisInstance.ZCtrl_OnOffSet(0)

#Set the corresponding Z-Controller (STM or AFM) to be the active one
#if the ctrl name is found in the list of existing controls
Applied_ControllerName=""
Applied_ControllerIndex=0
Applied_Bias=0
ControllerNames=nanonisInstance.ZCtrl_CtrlListGet()[2][2]

if Switch_To_AFM==1:
    Applied_ControllerName=AFM_ControllerName
    Applied_Bias=AFM_Bias
else:
    Applied_ControllerName=STM_ControllerName
    Applied_Bias=STM_Bias

CtrlNameFound=False
CtrlName=""
for CtrlName in ControllerNames:
    if CtrlName==Applied_ControllerName:
        CtrlNameFound=True
        break
    else:
        Applied_ControllerIndex=Applied_ControllerIndex+1

if CtrlNameFound is True:
    nanonisInstance.ZCtrl_ActiveCtrlSet(Applied_ControllerIndex)

    #Set Bias to the corresponding value (STM or AFM) 
    nanonisInstance.Bias_Set(Applied_Bias)

    #Switch the excitation output
    if Switch_To_AFM==1:
        nanonisInstance.PLL_OutOnOffSet(AFM_ModulatorIndex,AFM_ExcitationOut_OnOff)

    time.sleep(0.05)

    #Switch the Amplitude Ctrl
    if Switch_To_AFM==1:
        nanonisInstance.PLL_AmpCtrlOnOffSet(AFM_ModulatorIndex,AFM_AmplController_OnOff)

    #Switch the Phase Ctrl
    if Switch_To_AFM==1:
        nanonisInstance.PLL_PhasCtrlOnOffSet(AFM_ModulatorIndex,AFM_PhaseController_OnOff)
        
    time.sleep(0.1)

    #Switch on-off Z-Ctrl
    nanonisInstance.ZCtrl_OnOffSet(1)
else:
    print ("The controller name can't be found in the list of available controllers")

nanonisInstance.close()
