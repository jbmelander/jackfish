import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import sys
from labjack import ljm
from collections import deque
import socket, atexit

#%%
class Jack():
    '''
    Initializes and controls input for Labjack T4/T7.
    '''
    
    def __init__(self, serial_number=None):
        # Store initialization arguments
        self.dataQ = []
        self.collect_dataQ = False
        self.streaming = False
        
        # Initialize ljm T4/T7 handle
        self.handle = ljm.openS("TSERIES", "ANY", "ANY" if serial_number is None else serial_number)
        self.info = ljm.getHandleInfo(self.handle)
        self.deviceType = self.info[0]
        self.serial_number = self.info[2]
        self.print_handle_info()
        
        if self.deviceType == ljm.constants.dtT4:
            # LabJack T4 configuration

            # All analog input ranges are +/-1 V, stream settling is 0 (default) and
            # stream resolution index is 0 (default).
            aNames = ["AIN_ALL_RANGE", "STREAM_SETTLING_US", "STREAM_RESOLUTION_INDEX"]
            aValues = [1.0, 0, 0]
        else:
            # LabJack T7 and other devices configuration

            # Ensure triggered stream is disabled.
            ljm.eWriteName(self.handle, "STREAM_TRIGGER_INDEX", 0)

            # Enabling internally-clocked stream.
            ljm.eWriteName(self.handle, "STREAM_CLOCK_SOURCE", 0)

            # All analog input ranges are +/-1 V, stream settling is 6 
            # and stream resolution index is 0 (default).
            aNames = ["AIN_ALL_RANGE", "STREAM_SETTLING_US", "STREAM_RESOLUTION_INDEX"]
            aValues = [1.0, 6, 0]

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

    def start_stream(self, do_record=True, record_filepath="", aScanListNames=["AIN0", "AIN1"], scanRate=3000, scansPerRead=1000, dataQ_len_sec=15, socket_target=None):
        self.aScanListNames = aScanListNames
        self.numAddresses = len(aScanListNames)
        self.aScanList = ljm.namesToAddresses(self.numAddresses, aScanListNames)[0]

        dataQ_len = int(dataQ_len_sec * scanRate * self.numAddresses)
        self.dataQ = deque([0]*dataQ_len, maxlen=dataQ_len) #only for visualization; not for storing whole data

        self.do_record = do_record
        self.record_filepath = record_filepath
        if self.do_record:
            self.record_outfile = open(self.record_filepath, "a")

        #### Socket stream ####
        self.socket_target = socket_target
        if self.socket_target is not None:
            host, port = self.socket_target

            # set defaults
            if host is None:
                host = '127.0.0.1'

            assert port is not None, 'The port must be specified when creating a client.'

            conn = socket.create_connection((host, port))

            # make sure that connection is closed on
            def cleanup():
                try:
                    conn.shutdown(socket.SHUT_RDWR)
                    conn.close()
                except (OSError, ConnectionResetError):
                    pass

            atexit.register(cleanup)

            self.socket_outfile = conn.makefile('wb')
        ####

        try:
            # Configure and start stream
            scanRate = ljm.eStreamStart(self.handle, scansPerRead, self.numAddresses, self.aScanList, scanRate)
            print("\nLabjack stream started with a scan rate of %0.0f Hz." % scanRate)
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
            print("\nLabjack stream stopping")
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

                data_to_send = np.sum(data[::self.numAddresses])
                # Count the skipped samples which are indicated by -9999 values. Missed
                # samples occur after a device's stream buffer overflows and are
                # reported after auto-recover mode ends.
                curSkip = data.count(-9999.0)
                self.totSkip += curSkip
                
                print("  Scans Skipped = %0.0f, Scan Backlogs: Device = %i, LJM = "
                    "%i" % (curSkip/self.numAddresses, ret[1], ret[2]))

                if self.socket_target is not None:
                    try:
                        self.socket_outfile.write(str(data_to_send) + "\n")
                        self.socket_outfile.flush()
                    except BrokenPipeError:
                        # will happen if the other side disconnected
                        pass

                if self.do_record:
                    # print('Writing')
                    self.record_outfile.write("\n" + str(data))
                    self.record_outfile.flush()
                
                if self.collect_dataQ:
                    self.dataQ.extend(data)
                 
            except ljm.LJMError:
                ljme = sys.exc_info()[1]
                print(ljme)
            except Exception:
                e = sys.exc_info()[1]
                print(e)
        else:
            print("Shutting off Stream Callback")
            if self.socket_target is not None:
                self.socket_outfile.close()
            if self.do_record:
                self.record_outfile.close()
    
    def start_collect_dataQ(self):
        self.collect_dataQ = True
    def stop_collect_dataQ(self):
        self.collect_dataQ = False

    
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
