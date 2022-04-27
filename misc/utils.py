from labjack import ljm

class Expt:
    def __init__(self, savename, basepath="/home/jung/data/"):
        today = str(date.today())
        basepath = os.path.join(basepath, today)
        self.t0 = time.time()
        self.savename = savename
        self.expt_over = False

        self.lj_data = []
        self.lj_filepath = os.path.join(basepath, "{}.dat".format(savename))

        if os.path.exists(self.lj_filepath):
            print("Labjack .dat file detected at requested location")
            self.close_all()
            return
        else:
            pass

    def save(self):
        with open(self.lj_filepath, "a") as f:
            f.write("\n")
            f.write(self.lj_data)

    def init_labjack(self, scanlist, nburst, samplerate):

        self.lj_handle = ljm.openS(
            "ANY", "ANY", "ANY"
        )  # Any device, Any connection, Any identifier
        info = ljm.getHandleInfo(self.lj_handle)

        print(
            "Opened a LabJack with Device type: %i, Connection type: %i,\n"
            "Serial number: %i, IP address: %s, Port: %i,\nMax bytes per MB: %i"
            % (info[0], info[1], info[2], ljm.numberToIP(info[3]), info[4], info[5])
        )

        num_chans = len(scanlist)
        addresses = ljm.namesToAddresses(num_chans, scanlist)[0]

        scanRate = ljm.eStreamStart(
            self.lj_handle, nburst, num_chans, addresses, samplerate
        )

        if self.savename == "test":
            ljm.setStreamCallback(self.lj_handle, self.test_callback)
        else:
            ljm.setStreamCallback(self.lj_handle, self.save_callback)

    def get_avg_vel(self):
        d = self.lj_data
        d = np.array(d)

        a = d[0::5]
        b = d[1::5]

        aa = np.diff(a, axis=0)

        idx = np.where(aa == 1)[0]

        wf = len(np.where(b[idx] == 0)[0])
        wb = len(np.where(b[idx] == 1)[0])

        return wb - wf

    def save_callback(self, arg):
        while not self.expt_over:
            try:
                results = ljm.eStreamRead(self.lj_handle)
                self.lj_data = results[0]

                with open(self.lj_filepath, "a") as f:
                    f.write("\n")
                    f.write(str(results[0]))
            except:
                print("Stream Callback error. Please investigate me.")
        else:
            print("Shutting off Stream Callback")

    def test_callback(self, arg):
        """
        Don't save
        """
        while not self.expt_over:
            try:
                results = ljm.eStreamRead(self.lj_handle)
                self.lj_data = results[0]
            except:
                print("Stream Callback error. Please investigate me.")
        else:
            print("Shutting off Stream Callback")

    def close_all(self):
        self.expt_over = True

        core.quit()
        ljm.close(self.lj_handle)



