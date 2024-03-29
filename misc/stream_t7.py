import numpy as np
import matplotlib.pyplot as plt
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
MAX_REQUESTS = 10  # The number of eStreamRead calls that will be performed.

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
#aScanListNames = ["AIN0", "AIN1", "AIN2"]  # Scan list names to stream
aScanListNames = ["DIO0", "AIN0", "AIN1", "AIN2"]  # Scan list names to stream
numAddresses = len(aScanListNames)
aScanList = ljm.namesToAddresses(numAddresses, aScanListNames)[0]
scanRate = 10000
scansPerRead = int(scanRate/2)

# When streaming, negative channels and ranges can be configured for
# individual analog inputs, but the stream has only one settling time and
# resolution.

# LabJack T7 and other devices configuration

# Ensure triggered stream is disabled.
ljm.eWriteName(handle, "STREAM_TRIGGER_INDEX", 0)

# Enabling internally-clocked stream.
ljm.eWriteName(handle, "STREAM_CLOCK_SOURCE", 0)

# All negative channels are single-ended, AIN0 and AIN1 ranges are
# +/-10 V, stream settling is 0 (default) and stream resolution index
# is 0 (default).
aNames = ["AIN_ALL_RANGE", "STREAM_SETTLING_US",
        "STREAM_RESOLUTION_INDEX"]
aValues = [1.0, 6, 0]
# aNames = ["AIN_ALL_NEGATIVE_CH", "AIN_A", "AIN11_RANGE",
#           "STREAM_SETTLING_US", "STREAM_RESOLUTION_INDEX"]
# aValues = [ljm.constants.GND, 0.5, 0.5, 1, 0]

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
agg = []
while i <= MAX_REQUESTS:
    print('hello!')

    ret = ljm.eStreamRead(handle)

    print('bye!')

    aData = ret[0]
    agg = np.append(agg,np.array(aData))
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
# plt.pause(0.01) print("\nTotal scans = %i" % (totScans))
tt = (end - start).seconds + float((end - start).microseconds) / 1000000
print("Time taken = %f seconds" % (tt))
print("LJM Scan Rate = %f scans/second" % (scanRate))
print("Timed Scan Rate = %f scans/second" % (totScans / tt))
print("Timed Sample Rate = %f samples/second" % (totScans * numAddresses / tt))
print("Skipped scans = %0.0f" % (totSkip / numAddresses))

print("\nStop Stream")
ljm.eStreamStop(handle)

# Close handle
ljm.close(handle)

## Plot
agg_np = np.asarray(agg).reshape((-1,numAddresses)).T
#print(agg_np.shape)

x = np.arange(agg_np.shape[1])/scanRate*1000
fig,axs = plt.subplots(numAddresses, 1, sharex=True)
for i in range(numAddresses):
    axs[i].plot(x, agg_np[i], '-')
axs[numAddresses-1].set_xlabel('Time [ms]')
plt.show()