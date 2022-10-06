import sys
import os
import time
import numpy as np

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QApplication

from jack import Jack
from daq_gui import Ui_DAQWindow

class DAQUI(QtWidgets.QFrame, Ui_DAQWindow):
    def __init__(self, parent=None):
        super(DAQUI, self).__init__(None)
        self.setupUi(self)

        self.parent = parent

        # Set Labjack Scanrate
        self.sr_edit.editingFinished.connect(self.set_scanrate)
        self.set_scanrate()

        # Labjack Scan channels
        self.chans = self.read_chan_edit.text().split(',')
        self.read_chan_edit.editingFinished.connect(self.set_chans)

        self.chan_preview_drop.addItems(['None'] + self.chans)

        # Set Labjack Trigger channels
        self.trigger_chan_edit.editingFinished.connect(self.set_trigger_chans)
        self.set_trigger_chans()

        # LJ Cam Trigger button
        self.trigger_push.clicked.connect(self.trigger)

        # Initialize Labjack
        self.daq = Jack()

        # Labjack preview drop change
        self.chan_preview_drop.currentIndexChanged.connect(self.set_chan_preview)

        # Write path
        self.write_path = ""

        # Labjack preview
        self.preview_slider.setMinimum(0)
        self.preview_slider.setMaximum(20000)
        self.preview_slider.sliderReleased.connect(self.set_slider)

        self.data = [0]
        self.curve = self.preview.getPlotItem().plot()
        self.curve.setData(self.data)
        self.preview.show()
        self.show_preview = False

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.preview_updater)

    def start(self, record=False):
        self.timer.start()
        if record:
            self.daq.start_stream(do_record=record, record_filepath=self.write_path, aScanListNames=self.chans, scanRate=self.scanrate, dataQ_len_sec=15)
        else:
            self.daq.start_stream(do_record=False, aScanListNames=self.chans, scanRate=self.scanrate, dataQ_len_sec=15)

    def stop(self):
        self.timer.stop()
        self.daq.stop_stream()

    def set_write_path(self, dir, file_name=None):
        self.timer.stop()
        if file_name is None:
            file_name = f'daq_{self.daq.serial_number}.csv'
        self.write_path = os.path.join(dir, file_name)
        print(f"DAQ write path: {self.write_path}")

    def set_scanrate(self):
        self.scanrate = int(self.sr_edit.text())

    def set_trigger_chans(self):
        self.trigger_chans = self.trigger_chan_edit.text().split(',')

    def set_chans(self):
        self.chans = self.read_chan_edit.text().split(',')
        self.chan_preview_drop.clear()
        self.chan_preview_drop.addItems(['None'] + self.chans)

    def set_slider(self):
        # self.cam_timer.stop()
        self.timer.stop()

        self.slider_val = int(self.preview_slider.value())
        # self.cam_timer.start()
        self.timer.start()

    def set_chan_preview(self):
        self.chan_preview_idx = self.chan_preview_drop.currentIndex()
        if self.chan_preview_idx == 0: # None
            self.daq.stop_collect_dataQ()
            self.show_preview = False
        else:
            self.chan_preview_idx -= 1 # Not None; subtract index by 1 to correct for the None
            self.daq.start_collect_dataQ()
            self.show_preview = True

    def preview_updater(self):
        if self.show_preview:

            self.data = list(self.daq.dataQ)[self.chan_preview_idx:-1:len(self.chans)]
            try:
                self.curve.setData(self.data[-self.slider_val:])
            except:
                self.curve.setData(self.data)
            self.preview.show() 


    def trigger(self):
        write_states = np.ones(len(self.trigger_chans), dtype=int)
        self.daq.write(self.trigger_chans, write_states.tolist())
        time.sleep(0.05)
        self.daq.write(self.trigger_chans, (write_states*0).tolist())

    def closeEvent(self, event): # do not change name, super override
        self.daq.close()
        # TODO: Destroy handle to self in parent MainUI's daqUIs list.

def main():
    app = QApplication(sys.argv)
    form = DAQUI()
    form.show()
    app.exec_()

if __name__ == '__main__':
    main()
