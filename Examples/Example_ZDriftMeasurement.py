#This example records the Z channel (i.e. the tip height) and 
#calculates the drift along this axis.
#The drift speed can then be applied to compensate for it.
#Before starting the measurement, the tip must be in contact with the sample
#and the Z-Controller must be running.

import nanonis_spm
import time
import keyboard
import numpy as np
import socket

connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
connection.connect(("localhost",6501))

nanonisInstance = nanonis_spm.Nanonis(connection)
nanonisInstance.returnDebugInfo(1)

Z_Drift_Duration=1 #the time the Z drift measurement is running (in minutes)
Z_Drift_Duration_Seconds=Z_Drift_Duration*60
Z_Drift_IterationTime=0.1 #how often we read the Z position to calculate drift (in seconds)
Z_Drift_Apply=True #if True, the Z drift is applied after the Z drift measurement

Z_Drift_Value=0 #meters/second
Z_Drift_Comp_Vz=0
Z_Drift_Finished=False
Stopped_Manually=False
Z_Drift_Lst=[]
Z_Pos_Lst=[]
Time_Lst=[]
Time=0


#Start the Z drift measurement by reading the Z position
#for as long as the Z_Drift_Duration time
#or until manually stopped (pressing the Spacebar)
while True:
    time.sleep(Z_Drift_IterationTime)
    Time=Time+Z_Drift_IterationTime
    Time_Lst.append(Time)
    Z_Pos_Lst.append(nanonisInstance.ZCtrl_ZPosGet()[2][0])
    #Calculate the linear fit and return the slope
    Z_Drift_Value=np.linalg.lstsq(np.vstack([np.array(Time_Lst),np.ones(len(np.array(Time_Lst)))]).T, np.array(Z_Pos_Lst), rcond=None)[0]
    Z_Drift_Lst.append(Z_Drift_Value[0])
    if Time>=Z_Drift_Duration_Seconds:
        Z_Drift_Finished=True
        break
    if keyboard.is_pressed(' '):
        Stopped_Manually=True
        break

#if Z_Drift_Apply is True, apply the calculated Z Drift to compensate for it
if Z_Drift_Apply==True:
    Z_Drift_Comp=nanonisInstance.Piezo_DriftCompGet()[2]
    Z_Drift_Comp_OnOff=Z_Drift_Comp[0] #Drift compensation status (on or off)
    if Z_Drift_Comp_OnOff==True:
        Z_Drift_Comp_Vz=Z_Drift_Comp[3]+Z_Drift_Value[0] #Current linear speed applied to the Z piezo
    else:
        Z_Drift_Comp_Vz=Z_Drift_Value[0]
    nanonisInstance.Piezo_DriftCompSet(1,Z_Drift_Comp[1],Z_Drift_Comp[2],Z_Drift_Comp_Vz,Z_Drift_Comp[7])


print("Z drift measurement finished is {}, Stopped Manually is {}, and the Z drift is {} m/s".format(Z_Drift_Finished,Stopped_Manually,Z_Drift_Comp_Vz))

nanonisInstance.close()
