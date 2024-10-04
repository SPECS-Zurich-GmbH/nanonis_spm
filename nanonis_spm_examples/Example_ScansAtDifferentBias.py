#This example performs multiple scans,
#increasing the bias voltage by a defined increment after each scan.

import nanonis_spm
import time
import socket

connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
connection.connect(("localhost",6501))

nanonisInstance = nanonis_spm.Nanonis(connection)
nanonisInstance.returnDebugInfo(1)

Scan_Number=10
Scan_Autosave=1
Scan_Timeout=50000 #timeout in miliseconds to wait for the scan to finish
Bias_Incr=0.1

#Store the Bias value before scanning
Bias_BeforeScans=nanonisInstance.Bias_Get()[2][0]

#Configure the saving of the images
nanonisInstance.Scan_PropsSet(2,0,Scan_Autosave,"Example_ScanAtDiffBias","no comment",[])

#Run as many scans as defined by Scan_Number and add an increment to Bias after each scan
Bias_Value=Bias_BeforeScans
for scan in range(Scan_Number):
    nanonisInstance.Scan_Action(0,0)
    nanonisInstance.Scan_WaitEndOfScan(5000) #5 seconds timeout to wait for the scan to finish
    Bias_Value=Bias_Value+Bias_Incr
    nanonisInstance.Bias_Set(Bias_Value)
    
time.sleep(1)

#Restore Bias to the original value before scanning
nanonisInstance.Bias_Set(Bias_BeforeScans)

nanonisInstance.close()
