import sys
import os
import time
import json
import numpy as np

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QApplication

from jackfish.devices.daqs.labjack import LabJack
from daq_gui import Ui_DAQWindow

class DAQUI(QtWidgets.QFrame, Ui_DAQWindow):
    def __init__(self, serial_number=None, device_name=None, attrs_json_path=None, parent=None, barcode=None):
        super(DAQUI, self).__init__(None)
        self.setupUi(self)

        self.parent = parent
        self.barcode = barcode

        # Initialize Labjack
        self.daq = LabJack(serial_number=serial_number, name=device_name)

        self.setWindowTitle(f'DAQ {self.daq.name} ({self.daq.serial_number})')

        # Parse attrs
        if attrs_json_path is not None:
            with open(attrs_json_path, 'r') as f:
                attrs_dict = json.load(f)

            if 'sample_rate' in attrs_dict.keys():
                self.sr_edit.setText(str(attrs_dict['sample_rate']))

            if 'read_chs' in attrs_dict.keys():
                read_chs = attrs_dict['read_chs']
                if isinstance(read_chs, list):
                    read_chs = ", ".join(read_chs)
                self.read_chan_edit.setText(read_chs)
            
            if 'trigger_chs' in attrs_dict.keys():
                trigger_chs = attrs_dict['trigger_chs']
                if isinstance(trigger_chs, list):
                    trigger_chs = ", ".join(trigger_chs)
                self.trigger_chan_edit.setText(trigger_chs)

        # Set Labjack Scanrate
        self.sr_edit.editingFinished.connect(self.set_scanrate)
        self.set_scanrate()

        # Labjack Scan channels
        self.read_chan_edit.editingFinished.connect(self.set_chans)
        self.set_chans()

        # Set Labjack Trigger channels
        self.trigger_chan_edit.editingFinished.connect(self.set_trigger_chans)
        self.set_trigger_chans()

        # LJ Cam Trigger button
        self.trigger_push.clicked.connect(self.trigger)


        # Labjack preview drop change
        self.chan_preview_drop.currentIndexChanged.connect(self.set_chan_preview)

        # Write path
        self.write_path = ""

        # Labjack preview
        self.preview_slider.setMinimum(0)
        self.preview_slider.setMaximum(20000)
        self.preview_slider.sliderReleased.connect(self.set_slider)

        self.data = [0]
        preview_plotItem = self.preview.getPlotItem()
        preview_plotItem.setLabel("bottom", "Time [ms]")
        self.preview_plotDataItem = preview_plotItem.plot()
        self.preview_plotDataItem.setData(self.data)
        self.preview.show()
        self.show_preview = False

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.preview_updater)

    def start(self, record=False):
        self.timer.start()
        if record:
            self.daq.start_stream(do_record=record, record_filepath=self.write_path, input_channels=self.input_channels, scanRate=self.scanrate, dataQ_len_sec=15)
            # self.daq.start_stream(do_record=record, record_filepath=self.write_path, input_channels=self.input_channels, scanRate=self.scanrate, dataQ_len_sec=15, socket_target=(None,25025))
        else:
            self.daq.start_stream(do_record=False, input_channels=self.input_channels, scanRate=self.scanrate, dataQ_len_sec=15)

    def stop(self):
        self.timer.stop()
        self.daq.stop_stream()

    def set_write_path(self, dir, file_name=None):
        self.timer.stop()
        if file_name is None:
            file_name = f'daq_{self.daq.name}_{self.daq.serial_number}.jfdaqdata'
        self.write_path = os.path.join(dir, file_name)
        print(f"DAQ write path: {self.write_path}")

    def set_scanrate(self):
        self.scanrate = int(self.sr_edit.text())

    def set_trigger_chans(self):
        channel_candidates = self.trigger_chan_edit.text().split(',')
        self.trigger_chans = {}
        for cc in channel_candidates:
            nickname_opening_bracket_idx = cc.find('<')
            nickname_closing_bracket_idx = cc.find('>')

            if nickname_opening_bracket_idx != -1:
                assert nickname_closing_bracket_idx != -1, "Improper closure of nickname for channel."
                assert nickname_closing_bracket_idx > nickname_opening_bracket_idx, "Nickname closure should come after opening."
                channel_name = cc[0:nickname_opening_bracket_idx].replace(" ", "")
                nickname = cc[nickname_opening_bracket_idx+1:nickname_closing_bracket_idx]
            else:
                assert nickname_closing_bracket_idx == -1
                channel_name = cc.replace(" ", "")
                nickname = channel_name
            assert channel_name not in self.trigger_chans.keys()
            assert nickname not in self.trigger_chans.values()
            self.trigger_chans[channel_name] = nickname

    def set_chans(self):
        channel_candidates = self.read_chan_edit.text().split(',')
        self.input_channels = {}
        for cc in channel_candidates:
            nickname_opening_bracket_idx = cc.find('<')
            nickname_closing_bracket_idx = cc.find('>')

            if nickname_opening_bracket_idx != -1:
                assert nickname_closing_bracket_idx != -1, "Improper closure of nickname for channel."
                assert nickname_closing_bracket_idx > nickname_opening_bracket_idx, "Nickname closure should come after opening."
                channel_name = cc[0:nickname_opening_bracket_idx].replace(" ", "")
                nickname = cc[nickname_opening_bracket_idx+1:nickname_closing_bracket_idx]
            else:
                assert nickname_closing_bracket_idx == -1
                channel_name = cc.replace(" ", "")
                nickname = channel_name
            assert channel_name not in self.input_channels.keys()
            assert nickname not in self.input_channels.values()
            self.input_channels[channel_name] = nickname

        self.chan_preview_drop.clear()
        self.chan_preview_drop.addItems(['None'] + [f'{k} <{v}>' for k,v in self.input_channels.items()])

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

            self.data = list(self.daq.dataQ)[self.chan_preview_idx:-1:len(self.input_channels)]
            try:
                data_to_plot = self.data[-self.slider_val:]
                curve_t = np.arange(0, len(data_to_plot)) / self.scanrate * 1000 # ms
                self.preview_plotDataItem.setData(curve_t, data_to_plot)
            except:
                curve_t = np.arange(0, len(self.data)) / self.scanrate * 1000 # ms
                self.preview_plotDataItem.setData(curve_t, self.data)
            self.preview.show() 


    def trigger(self):
        write_states = np.ones(len(self.trigger_chans), dtype=int)
        self.daq.write(self.trigger_chans, write_states.tolist())
        time.sleep(0.05)
        self.daq.write(self.trigger_chans, (write_states*0).tolist())

    def closeEvent(self, event): # do not change name, super override
        self.daq.close()
        if self.barcode is not None:
            self.parent.daqUIs.pop(self.barcode)

def main():
    app = QApplication(sys.argv)
    form = DAQUI()
    form.show()
    app.exec_()

if __name__ == '__main__':
    main()