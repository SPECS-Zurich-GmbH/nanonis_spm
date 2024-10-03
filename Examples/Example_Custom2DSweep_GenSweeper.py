#This example performs a 2D sweep using a User output and the Generic Sweeper.
#For each value of the User output (y axis)
#it will perform a Generic Sweep (x axis). 

import nanonis_spm
import numpy
import socket

connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
connection.connect(("localhost",6501))

nanonisInstance = nanonis_spm.Nanonis(connection)
nanonisInstance.returnDebugInfo(1)

#Configuration variables of the Generic Sweeper
#The acquired signals are configured in the Generic Sweeper module for this example
Sweep_X_Start=1
Sweep_X_Stop=2
Sweep_X_NrPoints=10
Sweep_X_InitSettling=300 #miliseconds
Sweep_X_Settling=200 #miliseconds
Sweep_X_Period=100 #miliseconds
Sweep_X_MaxSlewRate=20 #units/second
Sweep_X_Autosave=0
Sweep_X_ShowSaveDialog=0
Sweep_X_Basename=""

#Configuration variables of the 2nd dimension
Sweep_Y_UserOutputIndex=3
Sweep_Y_Start=3
Sweep_Y_Stop=4
Sweep_Y_NrPoints=2
Sweep_Y_Incr=(Sweep_Y_Stop-Sweep_Y_Start)/(Sweep_Y_NrPoints-1)

#Create array with Sweep values for the 2nd dimension
Sweep_Y_Values=[]
for point in range(Sweep_Y_NrPoints):
    Y_Value=point*Sweep_Y_Incr+Sweep_Y_Start
    Sweep_Y_Values.append(Y_Value)
    
#Configure the Generic Sweeper properties
nanonisInstance.GenSwp_PropsSet(
    Sweep_X_InitSettling,
    Sweep_X_MaxSlewRate,
    Sweep_X_NrPoints,
    Sweep_X_Period,
    Sweep_X_Autosave,
    Sweep_X_ShowSaveDialog,
    Sweep_X_Settling
    )

#Configure the Generic Sweeper limits
nanonisInstance.GenSwp_LimitsSet(Sweep_X_Start,Sweep_X_Stop)

#Run the 2D Sweep & acquire signals
GenSweeper_Data_ForOneYValue=[]
GenSweeper_NrAcqChannels=nanonisInstance.GenSwp_AcqChsGet()[2][0]+1 #the swept channel is part of the acquired data
GenSweeper_Data_Total=[[]]*GenSweeper_NrAcqChannels

for point in range(Sweep_Y_NrPoints):
    #Set the user output value configured for the 2nd dimension
    nanonisInstance.UserOut_ValSet(Sweep_Y_UserOutputIndex,Sweep_Y_Values[point])
    #Run the Generic Sweeper
    GenSweeper_Data_ForOneYValue=nanonisInstance.GenSwp_Start(1,1,Sweep_X_Basename,0,1)[2]
    for SignalIdx in range(GenSweeper_NrAcqChannels):
        GenSweeper_Data_Total[SignalIdx]=GenSweeper_Data_Total[SignalIdx]+GenSweeper_Data_ForOneYValue[5][SignalIdx].tolist()
        
print(GenSweeper_Data_Total)

nanonisInstance.close()
