#This example performs a sweep of the selected Lock-In (LI) Frequency Generator.
#It creates an array of frequency values within a certain range, it waits Settling Time,
#and it acquires and averages the selected channels.

import nanonis_spm
import time
import socket
import keyboard
import numpy as np

connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
connection.connect(("localhost",6501))

nanonisInstance = nanonis_spm.Nanonis(connection)
nanonisInstance.returnDebugInfo(1)

Sweep_LI_Index=1          #index of LI Freq. Gen. to sweep
Sweep_LI_Start=1000
Sweep_LI_Stop=10000
Sweep_NrPoints=5
Sweep_LI_Incr=(Sweep_LI_Stop-Sweep_LI_Start)/(Sweep_NrPoints-1)
Sweep_InitSettlingTime=1  #seconds to wait before starting the sweep
Averaging=4               #number of samples to average
Sweep_SettlingTime=1      #seconds to wait after sweeping to each point
Sweep_AcqSignals=[86,87]  #signals to acquire, LI Demod. 1 X&Y
Acq_Signal_1=[]
Acq_Signal_2=[]

#Create array with Sweep LI Frequency values
Sweep_Freq_Values=[]
for point in range(Sweep_NrPoints):
    FreqValue=point*Sweep_LI_Incr+Sweep_LI_Start
    Sweep_Freq_Values.append(FreqValue)
    
#Set LI to Sweep Start value
nanonisInstance.LockIn_ModPhasFreqSet(Sweep_LI_Index, Sweep_LI_Start)

#Wait before starting the sweep
time.sleep(Sweep_InitSettlingTime)

#Sweep the LI Frequency, run the acquisition and averaging of the selected signals
#for as long as the defined number of sweep points
#or until manually stopped (pressing the Spacebar)
AveragedValues=[]
Acq_Finished=False
Stopped_Manually=False
Counter=0
while True:
    AccumulatedValues=np.array([0.0,0.0])
    nanonisInstance.LockIn_ModPhasFreqSet(Sweep_LI_Index,Sweep_Freq_Values[Counter])
    time.sleep(Sweep_SettlingTime)
    for sample in range(Averaging):
        AccumulatedValues[0]=AccumulatedValues[0]+nanonisInstance.Signals_ValsGet(Sweep_AcqSignals,0)[2][1][0][0]
        AccumulatedValues[1]=AccumulatedValues[1]+nanonisInstance.Signals_ValsGet(Sweep_AcqSignals,0)[2][1][1][0]
    AveragedValues.append(AccumulatedValues/Averaging)
    if len(AveragedValues)>=Sweep_NrPoints:
        Acq_Finished=True
        break
    if keyboard.is_pressed(' '):
        Stopped_Manually=True
        break
    Counter=Counter+1

for idx in range(len(AveragedValues)):
    Acq_Signal_1.append(AveragedValues[idx][0])
    Acq_Signal_2.append(AveragedValues[idx][1])
 
print("ACQUIRED SIGNAL 1")
print(Acq_Signal_1)
print("ACQUIRED SIGNAL 2")
print(Acq_Signal_2)

nanonisInstance.close()
