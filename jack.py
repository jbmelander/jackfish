import time#%%
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
    
    def __init__(self, aScanListNames=["AIN0", "AIN1"]):
        # Store initialization arguments
        self.aScanListNames = aScanListNames
        self.numAddresses = len(aScanListNames)
        self.data = []        
        self.streaming = False
        
        # Initialize ljm T7 handle
        self.handle = ljm.openS("T7", "ANY", "ANY")
        self.info = ljm.getHandleInfo(self.handle)
        self.print_handle_info()
        
        self.aScanList = ljm.namesToAddresses(self.numAddresses, aScanListNames)[0]

        # Ensure triggered stream is disabled.
        ljm.eWriteName(self.handle, "STREAM_TRIGGER_INDEX", 0)

        # Enabling internally-clocked stream.
        ljm.eWriteName(self.handle, "STREAM_CLOCK_SOURCE", 0)

        # All negative channels are single-ended, AIN0 and AIN1 ranges are
        # +/-10 V, stream settling is 0 (default) and stream resolution index
        # is 0 (default).
        aNames = ["AIN_ALL_RANGE", "STREAM_SETTLING_US",
                  "STREAM_RESOLUTION_INDEX"]
        aValues = [1.0,6,0]

        # Write the analog inputs' negative channels (when applicable), ranges,
        # stream settling time and stream resolution configuration.
        numFrames = len(aNames)
        ljm.eWriteNames(self.handle, numFrames, aNames, aValues)

    def write(self, names, vals):
        ljm.eWriteNames(self.handle, len(names), names, vals)
        # print('wrote {}'.format(name))

    def print_handle_info(self):
        print("Opened a LabJack with Device type: %i, Connection type: %i,\n"
            "Serial number: %i, IP address: %s, Port: %i,\nMax bytes per MB: %i" %
            (self.info[0], self.info[1], self.info[2], ljm.numberToIP(self.info[3]), self.info[4], self.info[5]))

    def start_stream(self, do_record=True, record_filepath="", scanRate=3000, scansPerRead=1000):
        self.do_record = do_record
        self.record_filepath = record_filepath
        try:
            # Configure and start stream
            scanRate = ljm.eStreamStart(self.handle, scansPerRead, self.numAddresses, self.aScanList, scanRate)
            print("\nStream started with a scan rate of %0.0f Hz." % scanRate)
            self.scanRate = scanRate
            self.scansPerRead = scansPerRead

            self.streaming = True #flag for recording status
            ljm.setStreamCallback(self.handle, self.stream_callback)

        except ljm.LJMError:
            ljme = sys.exc_info()[1]
            print(ljme)
        except Exception:
            e = sys.exc_info()[1]
            print(e)

    def stop_stream(self):
        self.stream_start_time = datetime.now() # maybe not the best
        try:
            print("\nStop Stream")
            self.streaming = False
            ljm.eStreamStop(self.handle)
            self.stream_end_time = datetime.now()
            
            recording_duration = self.stream_end_time - self.stream_start_time
            tt = recording_duration.seconds + float(recording_duration.microseconds) / 1000000
            print("Time taken = %f seconds" % (tt))
            print("LJM Scan Rate = %f scans/second" % (self.scanRate))
            print("Timed Scan Rate = %f scans/second" % (self.totScans / tt))
            print("Timed Sample Rate = %f samples/second" % (self.totScans * self.numAddresses / tt))
            print("Skipped scans = %0.0f" % (self.totSkip / self.numAddresses))

        except ljm.LJMError:
            ljme = sys.exc_info()[1]
            print(ljme)
        except Exception:
            e = sys.exc_info()[1]
            print(e)
        
    def stream_callback(self, arg):
        self.totScans = 0
        self.totSkip = 0  # Total skipped samples

        self.stream_start_time = datetime.now()
        while self.streaming:
            try:
                ret = ljm.eStreamRead(self.handle)
                data = ret[0]
                scans = len(data) / self.numAddresses
                self.totScans += scans

                # Count the skipped samples which are indicated by -9999 values. Missed
                # samples occur after a device's stream buffer overflows and are
                # reported after auto-recover mode ends.
                curSkip = data.count(-9999.0)
                self.totSkip += curSkip
                
                print("  Scans Skipped = %0.0f, Scan Backlogs: Device = %i, LJM = "
                    "%i" % (curSkip/self.numAddresses, ret[1], ret[2]))

                if self.do_record:
                    print('Writing')
                    with open(self.record_filepath, "a") as f:
                        f.write("\n")
                        f.write(str(ret[0]))
                
                self.data = np.append(self.data, data) #### TODO: make this a queue with fixed length so this doesn't blow up...
                 
            except ljm.LJMError:
                ljme = sys.exc_info()[1]
                print(ljme)
            except Exception:
                e = sys.exc_info()[1]
                print(e)
        else:
            print("Shutting off Stream Callback")
            

    
    def close(self):
        if self.streaming:
            self.stop_stream()
        ljm.close(self.handle)
        
    def plot_stream(self, data, numAddresses, scanRate):
        data_np = np.asarray(data).reshape((-1,numAddresses)).T

        x = np.arange(data_np.shape[1])/scanRate*1000
        fig,axs = plt.subplots(numAddresses, 1, sharex=True)
        for i in range(numAddresses):
            axs[i].plot(x, data_np[i], '-')
        axs[numAddresses-1].set_xlabel('Time [ms]')
        plt.show()
    
    def stream_for_duration(self, duration, scanRate=3000, scansPerRead=1000):
        '''
        duration: (float) duration of recording in seconds. Can't be too long or we'll run over memory.
        
        Returns agg, the recording.
        '''
        
        n_reads = duration * scanRate / scansPerRead
        
        try:
            # Configure and start stream
            scanRate = ljm.eStreamStart(self.handle, scansPerRead, self.numAddresses, self.aScanList, scanRate)
            print("\nStream started with a scan rate of %0.0f Hz." % scanRate)

            print("\nPerforming %i stream reads." % n_reads)
            start = datetime.now()
            totScans = 0
            totSkip = 0  # Total skipped samples

            i = 1
            agg = []
            while i <= n_reads:
                ret = ljm.eStreamRead(self.handle)
                aData = ret[0]
                agg = np.append(agg,np.array(aData))
                scans = len(aData) / self.numAddresses
                totScans += scans

                # Count the skipped samples which are indicated by -9999 values. Missed
                # samples occur after a device's stream buffer overflows and are
                # reported after auto-recover mode ends.
                curSkip = aData.count(-9999.0)
                totSkip += curSkip

                print("\neStreamRead %i" % i)
                ainStr = ""
                for j in range(0, self.numAddresses):
                    ainStr += "%s = %0.5f, " % (self.aScanListNames[j], aData[j])
                print("  1st scan out of %i: %s" % (scans, ainStr))
                print("  Scans Skipped = %0.0f, Scan Backlogs: Device = %i, LJM = "
                    "%i" % (curSkip/self.numAddresses, ret[1], ret[2]))
                i += 1

            end = datetime.now()
            # plt.pause(0.01) print("\nTotal scans = %i" % (totScans))
            tt = (end - start).seconds + float((end - start).microseconds) / 1000000
            print("Time taken = %f seconds" % (tt))
            print("LJM Scan Rate = %f scans/second" % (scanRate))
            print("Timed Scan Rate = %f scans/second" % (totScans / tt))
            print("Timed Sample Rate = %f samples/second" % (totScans * self.numAddresses / tt))
            print("Skipped scans = %0.0f" % (totSkip / self.numAddresses))
        except ljm.LJMError:
            ljme = sys.exc_info()[1]
            print(ljme)
        except Exception:
            e = sys.exc_info()[1]
            print(e)
        
        return agg

    
#%%



# jack = Jack(['FIO1','FIO2'])
# for i in range(100):
#     if i%2==0:
#         jack.write(['FIO3'],[0])
#         time.sleep(1)
#     else: 
#         jack.write(['FIO3'],[1])
#         time.sleep(1)

# jack.close()
