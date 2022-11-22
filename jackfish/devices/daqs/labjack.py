import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import sys
from labjack import ljm
from collections import deque
import socket, atexit
import json

#%%
class LabJack():
    '''
    Initializes and controls input for Labjack T4/T7.
    '''
    
    def __init__(self, serial_number=None, name=None):
        self.name = name
        
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
            aValues = [10.0, 0, 0]

            # Configure FIO4 to FIO7 as digital I/O.
            ljm.eWriteName(self.handle, "DIO_INHIBIT", 0xFFF0F)
            ljm.eWriteName(self.handle, "DIO_ANALOG_ENABLE", 0x00000)
        else:
            # LabJack T7 and other devices configuration

            # Ensure triggered stream is disabled.
            ljm.eWriteName(self.handle, "STREAM_TRIGGER_INDEX", 0)

            # Enabling internally-clocked stream.
            ljm.eWriteName(self.handle, "STREAM_CLOCK_SOURCE", 0)

            # All analog input ranges are +/-1 V, stream settling is 6 
            # and stream resolution index is 0 (default).
            aNames = ["AIN_ALL_RANGE", "STREAM_SETTLING_US", "STREAM_RESOLUTION_INDEX", "AIN_ALL_NEGATIVE_CH"]
            aValues = [10.0, 6, 0, 199]

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

    def start_stream(self, do_record=True, record_filepath="", input_channels={"AIN0": "Input 0", "AIN1": "Input 1"}, scanRate=3000, scansPerRead=1000, dataQ_len_sec=15, socket_target=None):
        self.input_channels = input_channels
        if isinstance(self.input_channels, list):
             self.input_channels = {chan:chan for chan in self.input_channels}
        self.n_input_channels = len(self.input_channels)

        if self.n_input_channels == 0:
            return

        self.aScanList = ljm.namesToAddresses(self.n_input_channels, list(self.input_channels.keys()))[0]

        dataQ_len = int(dataQ_len_sec * scanRate * self.n_input_channels)
        self.dataQ = deque([0]*dataQ_len, maxlen=dataQ_len) #only for visualization; not for storing whole data

        self.do_record = do_record
        self.record_filepath = record_filepath
        if self.do_record:
            self.record_outfile = open(self.record_filepath, "a")

            header = {'input_channels':self.input_channels, 'scan_rate':scanRate}

            self.record_outfile.write(json.dumps(header) + "\n")
            self.record_outfile.flush()


        #### Socket stream ####
        self.socket_target = socket_target
        if self.socket_target is not None:
            host, port = self.socket_target
            self.host = host
            self.port = port
            # set defaults
            if host is None:
                host = '127.0.0.1'

            assert port is not None, 'The port must be specified when creating a client.'
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            addr = (host,port)

            # conn = socket.create_connection((host, port))

            # make sure that connection is closed on
            def cleanup():
                try:
                    self.client_socket.shutdown(socket.SHUT_RDWR)
                    self.client_socket.close()
                except (OSError, ConnectionResetError):
                    pass

            atexit.register(cleanup)

            # self.socket_outfile = self.client_socket.makefile('wb')
        ####

        try:
            # Configure and start stream
            scanRate = ljm.eStreamStart(self.handle, scansPerRead, self.n_input_channels, self.aScanList, scanRate)
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
        # self.stream_start_time = datetime.now() # maybe not the best
        if self.streaming:
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
                print("Timed Sample Rate = %f samples/second" % (self.totScans * self.n_input_channels / tt))
                print("Skipped scans = %0.0f" % (self.totSkip / self.n_input_channels))

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
                scans = len(data) / self.n_input_channels
                self.totScans += scans

                # Count the skipped samples which are indicated by -9999 values. Missed
                # samples occur after a device's stream buffer overflows and are
                # reported after auto-recover mode ends.
                curSkip = data.count(-9999.0)
                self.totSkip += curSkip
                
                print("  Scans Skipped = %0.0f, Scan Backlogs: Device = %i, LJM = "
                    "%i" % (curSkip/self.n_input_channels, ret[1], ret[2]))

                if self.socket_target is not None:
                    try:
                        data_to_send = data # should be changed as appropriate for use
                        data_to_send = bytes(data_to_send,'utf-8')
                        self.client_socket.sendto(data_to_send,('127.0.0.1',self.port))
                        # self.socket_outfile.write(bytes(str(data_to_send) + "\n"),'utf-8')
                        # self.socket_outfile.flush()
                    except BrokenPipeError:
                        # will happen if the other side disconnected
                        pass

                if self.do_record:
                    # print('Writing')
                    data_2d = np.asarray(data).reshape((-1, self.n_input_channels))
                    np.savetxt(self.record_outfile, data_2d, fmt='%.18e', newline='\n')
                    # self.record_outfile.write(str(data)[1:-1] + "\n") # [1:-1] removes square brackets
                    # self.record_outfile.flush()
                
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
                self.client_socket.close()
                # self.socket_outfile.close()
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
