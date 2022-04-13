"""
Demonstrates how to stream using the eStream functions.

Relevant Documentation:
 
LJM Library:
    LJM Library Installer:
        https://labjack.com/support/software/installers/ljm
    LJM Users Guide:
        https://labjack.com/support/software/api/ljm
    Opening and Closing:
        https://labjack.com/support/software/api/ljm/function-reference/opening-and-closing
    Constants:
        https://labjack.com/support/software/api/ljm/constants
    Stream Functions:
        https://labjack.com/support/software/api/ljm/function-reference/stream-functions
 
T-Series and I/O:
    Modbus Map:
        https://labjack.com/support/software/api/modbus/modbus-map
    Stream Mode: 
        https://labjack.com/support/datasheets/t-series/communication/stream-mode
    Analog Inputs:
        https://labjack.com/support/datasheets/t-series/ain

"""
from datetime import datetime
import sys

from labjack import ljm


MAX_REQUESTS = 2  # The number of eStreamRead calls that will be performed.

# Open first found LabJack
handle = ljm.openS("ANY", "ANY", "ANY")  # Any device, Any connection, Any identifier
#handle = ljm.openS("T7", "ANY", "ANY")  # T7 device, Any connection, Any identifier
#handle = ljm.openS("T4", "ANY", "ANY")  # T4 device, Any connection, Any identifier
#handle = ljm.open(ljm.constants.dtANY, ljm.constants.ctANY, "ANY")  # Any device, Any connection, Any identifier

info = ljm.getHandleInfo(handle)
print("Opened a LabJack with Device type: %i, Connection type: %i,\n"
      "Serial number: %i, IP address: %s, Port: %i,\nMax bytes per MB: %i" %
      (info[0], info[1], info[2], ljm.numberToIP(info[3]), info[4], info[5]))

deviceType = info[0]

# Stream Configuration
aScanListNames = ["AIN0", "AIN1", "AIN2"]  # Scan list names to stream
numAddresses = len(aScanListNames)
aScanList = ljm.namesToAddresses(numAddresses, aScanListNames)[0]
scanRate = 10000
scansPerRead = int(scanRate / 2)
aNames = ["AIN0_RANGE", "AIN1_RANGE", "AIN2_RANGE", "STREAM_SETTLING_US",
            "STREAM_RESOLUTION_INDEX"]
aValues = [0.5, 0.5, 0.5, 0, 0]


# Write the analog inputs' negative channels (when applicable), ranges,
# stream settling time and stream resolution configuration.
numFrames = len(aNames)
ljm.eWriteNames(handle, numFrames, aNames, aValues)







# Configure and start stream
scanRate = ljm.eStreamStart(handle, scansPerRead, numAddresses, aScanList, scanRate)
print("\nStream started with a scan rate of %0.0f Hz." % scanRate)

print("\nPerforming %i stream reads." % MAX_REQUESTS)
start = datetime.now()
totScans = 0
totSkip = 0  # Total skipped samples

i = 1
while i <= MAX_REQUESTS:
    ret = ljm.eStreamRead(handle)
    aData = ret[0]
    scans = len(aData) / numAddresses
    totScans += scans
    # Count the skipped samples which are indicated by -9999 values. Missed
    # samples occur after a device's stream buffer overflows and are
    # reported after auto-recover mode ends.
    curSkip = aData.count(-9999.0)
    totSkip += curSkip
    print("\neStreamRead %i" % i)
    ainStr = ""
    for j in range(0, numAddresses):
        ainStr += "%s = %0.5f, " % (aScanListNames[j], aData[j])
    print("  1st scan out of %i: %s" % (scans, ainStr))
    print("  Scans Skipped = %0.0f, Scan Backlogs: Device = %i, LJM = "
            "%i" % (curSkip/numAddresses, ret[1], ret[2]))
    i += 1

end = datetime.now()
ljm.eStreamStop(handle)

import matplotlib.pyplot as plt
import numpy as np

aData_np = np.asarray(aData).reshape((-1,3)).T
#aData_np = np.asarray(aData).reshape((3,-1))

x = np.arange(len(aData_np[0]))/scanRate*1000
fig,axs = plt.subplots(3,1,sharex=True)
axs[0].plot(x, aData_np[0], '-o')
axs[1].plot(x, aData_np[1], '-o')
axs[2].plot(x, aData_np[2], '-o')
fig.show()

ljm.close(handle)
