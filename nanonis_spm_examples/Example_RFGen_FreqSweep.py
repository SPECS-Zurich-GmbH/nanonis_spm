#This example performs a Frequency Sweep using the built-in functionality
#in the RF Generator module

import nanonis_spm
import socket
import time

connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
connection.connect(("localhost",6501))

nanonisInstance = nanonis_spm.Nanonis(connection)
nanonisInstance.returnDebugInfo(1)

Limit_Lower=2000000    #Hz
Limit_Higher=10000000  #Hz
Points=10
Mode=1                 #Linear
Dwell=0.25             #s
Repetitions=1
Infinite=2             #Off
OffTime=0              #s
AutoOffTime=1          #On
Direction=0            #Sweep Up

#Initialize the frequency to the lower limit of the frequency sweep range
nanonisInstance.APRFGen_FreqSet(0,Limit_Lower)

#Switch on the RF Output
nanonisInstance.APRFGen_RFOutOnOffSet(1)

time.sleep(2)

#Configure the limits and properties of the Frequency Sweep mode
nanonisInstance.APRFGen_FreqSwpLimitsSet(Limit_Lower,Limit_Higher)
nanonisInstance.APRFGen_FreqSwpPropsSet(Mode,Dwell,Repetitions,Infinite,Points,OffTime,AutoOffTime)

#Start a Frequency Sweep
nanonisInstance.APRFGen_FreqSwpStart(Direction)

nanonisInstance.close()
