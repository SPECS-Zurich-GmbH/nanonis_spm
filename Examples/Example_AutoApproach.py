#Automatic approach implemented using Nanonis Programming Interface functions.
#This can be used if you want to execute special functions after each 
#motor step or if you want to control your motor remotely.

import nanonis_spm
import time
import keyboard
import socket

connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
connection.connect(("localhost",6501))

nanonisInstance = nanonis_spm.Nanonis(connection)
nanonisInstance.returnDebugInfo(1)

Motor_NrSteps=10 #number of steps to move toward the sample

#Fully withdraw the tip
nanonisInstance.ZCtrl_Withdraw(1,-1) #Wait until done

#Wait a bit after withdrawing the tip
time.sleep(0.2) #seconds
    
#Read the upper piezo range limit
Piezo_RangeLimit_Upper=nanonisInstance.ZCtrl_ZPosGet()[2][0]

#Calculate the lower piezo range limit
Piezo_RangeLimit_Lower=Piezo_RangeLimit_Upper*(-0.95)

#Start the auto-approach procedure
while True:
    #Switch on Z-Ctrl
    nanonisInstance.ZCtrl_OnOffSet(1)

    #Wait until Z-Ctrl is really switched on
    #checking the status every 10ms (2 seconds timeout)
    for WaitTime in range(200):
        time.sleep(0.01)
        if nanonisInstance.ZCtrl_OnOffGet()[2][0]==1:
            break

    #Read the Z position repeatedly until:
    #- surface reached=> new_Z >= previous_Z (controlled position)
    #- or Spacebar button is pressed to manually stop the procedure
    #- or the lower limit is reached
    Piezo_Position=float('inf')
    Surface_Reached=False
    Stopped_Manually=False
    while True:
        time.sleep(0.15)
        Piezo_Position_New=nanonisInstance.ZCtrl_ZPosGet()[2][0]
        if Piezo_Position_New>=Piezo_Position:
            Surface_Reached=True
            break
        if keyboard.is_pressed(' '):
            Stopped_Manually=True
            break
        if Piezo_Position_New<Piezo_RangeLimit_Lower:
            break
        else:
            Piezo_Position=Piezo_Position_New
            
    print("Surface_Reached is {} and Stopped Manually is {}".format(Surface_Reached,Stopped_Manually))
        
    #If surface reached or procedure manually stopped:
    #- withdraw the tip
    #- move the motor few steps toward the sample
    #- wait motor's end-of-move
    if Surface_Reached==True or Stopped_Manually==True:
        break
    else:    
        nanonisInstance.ZCtrl_Withdraw(1,-1) #Wait until done
        time.sleep(0.2) #seconds
        nanonisInstance.Motor_StartMove(5,Motor_NrSteps,0,1) #move in Z- direction and wait for it to finish

nanonisInstance.close()

