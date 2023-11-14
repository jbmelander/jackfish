import sys
import os
import time
import json
import numpy as np

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QFileDialog

from jackfish.devices.daqs.labjack import LabJack
from daq_gui import Ui_DAQWindow

from jackfish import utils
from jackfish.utils import Status

class DAQUI(QtWidgets.QFrame, Ui_DAQWindow):
    def __init__(self, serial_number=None, device_name=None, attrs_json_path=None, parent=None, barcode=None):
        super(DAQUI, self).__init__(None)
        self.setupUi(self)
        
        self.spr = 1000
        self.parent = parent
        self.barcode = barcode

        self.status = Status.STANDBY

        self.scanrate = 1

        # Initialize Labjack
        self.daq = LabJack(serial_number=serial_number, name=device_name)
        self.serial_number = self.daq.serial_number

        ### UI ###
        icon_path = os.path.join(utils.ROOT_DIR,'assets/icon.png')
        self.setWindowIcon(QIcon(icon_path))
        self.setWindowTitle(f'DAQ {self.daq.name} ({self.daq.serial_number})')
        # Parse attributes
        self.load_preset_push.clicked.connect(lambda: self.parse_attrs_json(attrs_json_path=None))
        # Set Labjack Scanrate
        self.sr_edit.editingFinished.connect(self.set_scanrate)
        # Set Labjack samp_per_read
        self.spr_edit.editingFinished.connect(self.set_spr)
        # Labjack Scan channels
        self.read_chan_edit.editingFinished.connect(self.set_chans)
        # Set Labjack Trigger channels
        self.trigger_chan_edit.editingFinished.connect(self.set_trigger_chans)
        # LJ Cam Trigger button
        self.trigger_push.clicked.connect(self.trigger)
        # Labjack preview drop change
        self.chan_preview_drop.currentIndexChanged.connect(self.set_chan_preview)
        ###

        self.parse_attrs_json(attrs_json_path)
        self.set_scanrate()
        self.set_chans()
        self.set_trigger_chans()

        # Write path
        self.write_path = ""

        # Labjack preview
        self.data = [0]
        preview_plotItem = self.preview.getPlotItem()
        preview_plotItem.setLabel("bottom", "Time [ms]")
        self.preview_plotDataItem = preview_plotItem.plot()
        self.preview_plotDataItem.setData(self.data)
        self.preview.show()
        self.show_preview = False

        self.preview_timer = QtCore.QTimer()
        self.preview_timer.timeout.connect(self.preview_updater)

        self.preview_slider.setMinimum(2)
        self.preview_slider.setMaximum(int(self.scanrate * 10)) # 10 seconds of data
        self.preview_slider.setValue(int(self.scanrate)) # 1 second of data
        self.preview_slider.sliderReleased.connect(self.set_slider)
        self.set_slider()

        self.update_ui()
    
    def set_spr(self):
        self.spr= int(self.spr_edit.text())

    def parse_attrs_json(self, attrs_json_path=None):
        if attrs_json_path is None:
            presets_dir = os.path.join(utils.ROOT_DIR,'presets')

            attrs_json_path, _ = QFileDialog.getOpenFileName(self, "Select DAQ preset json file.", presets_dir, "JSON files (*.json)")

            if attrs_json_path == "":
                return

        if attrs_json_path is not None:
            with open(attrs_json_path, 'r') as f:
                attrs_dict = json.load(f)

            if 'sample_rate' in attrs_dict.keys():
                self.sr_edit.setText(str(attrs_dict['sample_rate']))
                self.set_scanrate()

            if 'read_chs' in attrs_dict.keys():
                read_chs = attrs_dict['read_chs']
                if isinstance(read_chs, list):
                    read_chs = ", ".join(read_chs)
                self.read_chan_edit.setText(read_chs)
                self.set_chans()
            
            if 'trigger_chs' in attrs_dict.keys():
                trigger_chs = attrs_dict['trigger_chs']
                if isinstance(trigger_chs, list):
                    trigger_chs = ", ".join(trigger_chs)
                self.trigger_chan_edit.setText(trigger_chs)
                self.set_trigger_chans()

            if 'labjack_settings' in attrs_dict.keys():
                labjack_settings = attrs_dict['labjack_settings']
                # Write additional settings from attrs_json
                if labjack_settings is not None:
                    self.daq.set_attrs(labjack_settings)

    def start(self, record=False):

        n_channels = len(self.input_channels.keys())
        print(n_channels)
        print('0000')

        # Get text in the edit
        scansPerRead = int(self.spr)
        port = int(self.port_edit.text())

        if self.status != Status.STANDBY:
            utils.message_window("Error", "Currently recording or previewing.")
        self.preview_timer.start()


        if self.ip_checkbox.isChecked():
            if record:
                self.status = Status.RECORDING
                self.daq.start_stream(do_record=record, record_filepath=self.write_path, 
                                      input_channels=self.input_channels, 
                                      scanRate=self.scanrate, scansPerRead = scansPerRead, 
                                      preview_queue_len_sec=15, socket_target=('127.0.0.1', port))
            else:
                self.status = Status.PREVIEWING
                self.daq.start_stream(do_record=False, 
                                      input_channels=self.input_channels, 
                                      scanRate=self.scanrate, scansPerRead = scansPerRead, 
                                      preview_queue_len_sec=15, socket_target=('127.0.0.1', port))
        else:
            if record:
                self.status = Status.RECORDING
                self.daq.start_stream(do_record=record, record_filepath=self.write_path, 
                                      input_channels=self.input_channels, 
                                      scanRate=self.scanrate, scansPerRead = scansPerRead, 
                                      preview_queue_len_sec=15)
            else:
                self.status = Status.PREVIEWING
                self.daq.start_stream(do_record=False, 
                                      input_channels=self.input_channels, 
                                      scanRate=self.scanrate, scansPerRead = scansPerRead, 
                                      preview_queue_len_sec=15)

        self.update_ui()

    def stop(self):
        if self.status == Status.STANDBY:
            utils.message_window("Error", "Already on standby.")
        self.preview_timer.stop()
        self.daq.stop_stream()
        self.status = Status.STANDBY

        self.update_ui()

    def set_write_path(self, dir, file_name=None):
        self.preview_timer.stop()
        if file_name is None:
            file_name = f'daq_{self.daq.name}_{self.daq.serial_number}.jfdaqdata'
        self.write_path = os.path.join(dir, file_name)
        print(f"DAQ write path: {self.write_path}")

        self.update_ui()

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
        self.preview_timer.stop()

        self.slider_val = int(self.preview_slider.value())
        # self.cam_timer.start()
        self.preview_timer.start()

    def set_chan_preview(self):
        self.chan_preview_idx = self.chan_preview_drop.currentIndex()
        if self.chan_preview_idx == 0: # None
            self.daq.stop_collect_preview_queue()
            self.show_preview = False
        else:
            self.chan_preview_idx -= 1 # Not None; subtract index by 1 to correct for the None
            self.daq.start_collect_preview_queue()
            self.show_preview = True

    def preview_updater(self):
        if self.show_preview:

            self.data = list(self.daq.preview_queue)[self.chan_preview_idx:-1:len(self.input_channels)]
            try:
                data_to_plot = self.data[-self.slider_val:]
                curve_t = np.arange(0, len(data_to_plot)) / self.scanrate * 1000 # ms
                self.preview_plotDataItem.setData(curve_t, data_to_plot)
            except:
                print("Error in preview_updater")
                curve_t = np.arange(0, len(self.data)) / self.scanrate * 1000 # ms
                self.preview_plotDataItem.setData(curve_t, self.data)
            self.preview.show() 


    def trigger(self):
        write_states = np.ones(len(self.trigger_chans), dtype=int)
        self.daq.write(self.trigger_chans, write_states.tolist())
        time.sleep(0.05)
        self.daq.write(self.trigger_chans, (write_states*0).tolist())

    def update_ui(self):
        if self.status == Status.RECORDING: # If recording...
            self.load_preset_push.setEnabled(False)
            self.sr_edit.setEnabled(False)
            self.read_chan_edit.setEnabled(False)
            self.trigger_chan_edit.setEnabled(False)

        elif self.status == Status.PREVIEWING: # If previewing...
            self.load_preset_push.setEnabled(False)
            self.sr_edit.setEnabled(False)
            self.read_chan_edit.setEnabled(False)
            self.trigger_chan_edit.setEnabled(False)

        elif self.status == Status.STANDBY: # If standby...
            self.load_preset_push.setEnabled(True)
            self.sr_edit.setEnabled(True)
            self.read_chan_edit.setEnabled(True)
            self.trigger_chan_edit.setEnabled(True)
        else:
            utils.message_window(text="Invalid status.")

    def closeEvent(self, event): # do not change name, super override
        if self.status == Status.RECORDING: # If recording...
            event.ignore()
        elif self.status == Status.PREVIEWING: # If previewing...
            event.ignore()
        elif self.status == Status.STANDBY: # If standby...
            self.daq.close()
            self.parent.child_close_event(self.barcode)
        else:
            utils.message_window(text="Invalid status.")

        # if self.status != Status.STANDBY:
        #     self.stop()
        # self.daq.close()
        # self.parent.child_close_event(self.barcode)

def main():
    app = QApplication(sys.argv)
    form = DAQUI()
    form.show()
    app.exec_()

if __name__ == '__main__':
    main()
