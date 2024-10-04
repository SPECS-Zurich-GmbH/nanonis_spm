#This example performs multiple Power Sweeps by using the Generic Sweeper
#to sweep the power in the RF Generator module multiple times with different limits

import nanonis_spm
import numpy
import socket
import time

connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
connection.connect(("localhost",6501))

nanonisInstance = nanonis_spm.Nanonis(connection)
nanonisInstance.returnDebugInfo(1)

#Generic Sweeper variables
Sweep_Start=[1,2,-1,-4]  #Sweep start values for the different sweeps to perfom 
Sweep_Stop=[5,3,2,1]   #(the list size determines the number of sweeps)
Sweep_NrPoints=[10,5,10,5]

#Generic Sweeper properties common to all sweeps
Sweep_InitSettling=300 #miliseconds
Sweep_Settling=200 #miliseconds
Sweep_Period=100 #miliseconds
Sweep_MaxSlewRate=20 #units/second
Sweep_Autosave=0
Sweep_ShowSaveDialog=0
Sweep_Basename=""

#Select the power signal as the signal to sweep
nanonisInstance.GenSwp_SwpSignalSet("Power (dBm)")

#Initialize the variables storing the acquired data
GenSweeper_Data_OneSweep=[]
GenSweeper_NrAcqChannels=nanonisInstance.GenSwp_AcqChsGet()[2][0]+1 #the swept channel is part of the acquired data
GenSweeper_Data_Total=[[]]*GenSweeper_NrAcqChannels

#Run the sweeps
for SweepIndex in range(len(Sweep_Start)):
    #Configure the Generic Sweeper properties
    nanonisInstance.GenSwp_PropsSet(
        Sweep_InitSettling,
        Sweep_MaxSlewRate,
        Sweep_NrPoints[SweepIndex],
        Sweep_Period,
        Sweep_Autosave,
        Sweep_ShowSaveDialog,
        Sweep_Settling)
    #Configure the Generic Sweeper limits
    nanonisInstance.GenSwp_LimitsSet(Sweep_Start[SweepIndex],Sweep_Stop[SweepIndex])
    #Run the Generic Sweeper
    GenSweeper_Data_OneSweep=nanonisInstance.GenSwp_Start(1,1,Sweep_Basename,0,0)[2]
    for SignalIdx in range(GenSweeper_NrAcqChannels):
        GenSweeper_Data_Total[SignalIdx]=GenSweeper_Data_Total[SignalIdx]+GenSweeper_Data_OneSweep[5][SignalIdx].tolist()
        
print(GenSweeper_Data_Total)

nanonisInstance.close()

