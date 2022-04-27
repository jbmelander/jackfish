#%%
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import sys
from labjack import ljm


#%%
class Jack():
    '''
    Initializes and controls input for Labjack T7.
    '''
    
    def __init__(self, aScanListNames=["AIN0", "AIN1"], scanRate=3000, scansPerRead=1000):
        # Store initialization arguments
        self.aScanListNames = aScanListNames
        self.numAddresses = len(aScanListNames)
        self.scanRate = scanRate
        self.scansPerRead = scansPerRead
        
        # Initialize ljm T7 handle
        self.handle = ljm.openS("T7", "ANY", "ANY")
        self.info = ljm.getHandleInfo(self.handle)
        self.print_handle_info()
        
        aScanList = ljm.namesToAddresses(self.numAddresses, aScanListNames)[0]

        # Ensure triggered stream is disabled.
        ljm.eWriteName(self.handle, "STREAM_TRIGGER_INDEX", 0)

        # Enabling internally-clocked stream.
        ljm.eWriteName(self.handle, "STREAM_CLOCK_SOURCE", 0)

        # All negative channels are single-ended, AIN0 and AIN1 ranges are
        # +/-10 V, stream settling is 0 (default) and stream resolution index
        # is 0 (default).
        aNames = ["AIN_ALL_RANGE", "STREAM_SETTLING_US",
                  "STREAM_RESOLUTION_INDEX"]
        aValues = [1.0,0,0]

        # Write the analog inputs' negative channels (when applicable), ranges,
        # stream settling time and stream resolution configuration.
        numFrames = len(aNames)
        ljm.eWriteNames(self.handle, numFrames, aNames, aValues)

    def print_handle_info(self):
        print("Opened a LabJack with Device type: %i, Connection type: %i,\n"
            "Serial number: %i, IP address: %s, Port: %i,\nMax bytes per MB: %i" %
            (self.info[0], self.info[1], self.info[2], ljm.numberToIP(self.info[3]), self.info[4], self.info[5]))

    def start_stream(self):
        try:
            # Configure and start stream
            scanRate = ljm.eStreamStart(self.handle, self.scansPerRead, self.numAddresses, self.aScanList, scanRate)
            print("\nStream started with a scan rate of %0.0f Hz." % scanRate)

            print("\nPerforming %i stream reads." % MAX_REQUESTS)
            start = datetime.now()
            totScans = 0
            totSkip = 0  # Total skipped samples

            i = 1
            agg = []
            while i <= MAX_REQUESTS:
                ret = ljm.eStreamRead(handle)
                aData = ret[0]
                bData = np.array(ret[0])
                agg = np.append(agg,bData)
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
        except ljm.LJMError:
            ljme = sys.exc_info()[1]
            print(ljme)
        except Exception:
            e = sys.exc_info()[1]
            print(e)

#%%

jack = Jack()
# %%
ljm.getHandleInfo(jack.handle)
# %%
