import os
import sys
import random
import json

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QApplication, QFileDialog, QInputDialog, QMessageBox
from PyQt5.QtGui import QMovie, QPixmap
from PyQt5.QtCore import QTimer
from cam_controller import CamUI
from daq_controller import DAQUI
import main_gui

from jackfish import utils
from jackfish.utils import Status

class MainUI(QtWidgets.QMainWindow, main_gui.Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainUI, self).__init__(parent)
        self.setupUi(self)
        
        image_dir = os.path.join(utils.ROOT_DIR,'assets/pike.jpg')
        self.label.setPixmap(QPixmap(image_dir))
        self.label.setScaledContents(True)
        self.label.setObjectName("label")

        self.save_dir = os.environ['HOME']
        self.expt_name = ""
        self.expt_path = os.environ['HOME']
        self.new_path_set = False

        self.modules = {}

        self.status = Status.STANDBY

        #### UI ####
        self.load_preset_push.clicked.connect(self.load_preset)
        self.set_save_dir_push.clicked.connect(lambda: self.set_save_dir(save_dir=None))
        self.set_expt_push.clicked.connect(self.set_experiment_name)
        self.set_expt_push.setEnabled(False)

        self.daq_init_push.clicked.connect(self.init_daq)
        self.cam_init_push.clicked.connect(self.init_cam)

        self.timer = QTimer()
        self.timer.timeout.connect(self.stop)
        self.timer_checkBox.clicked.connect(self.stop_timer)

        self.preview_push.setCheckable(True)
        self.preview_push.clicked.connect(self.control)

        self.record_push.setCheckable(True)
        self.record_push.clicked.connect(self.control)
        
        self.update_ui()
    
        #### Import presets ####
        self.load_preset(init=True)

    def load_preset(self, init=False):
        if init:
            preset_dict = {"main": {}, "cameras": {"Default": {}}, "DAQs": {"Default": {}}}
        else:
            presets_dir = os.path.join(utils.ROOT_DIR,'presets')

            json_fn, _ = QFileDialog.getOpenFileName(self, "Select preset json file.", presets_dir, "JSON files (*.json)")

            if json_fn == "":
                return
            else:
                with open(json_fn, 'r') as f:
                    preset_dict = json.load(f)

        main_presets = preset_dict['main']
        if "save_dir" in main_presets.keys():
            self.set_save_dir(save_dir=main_presets['save_dir'])

        self.cam_presets = preset_dict['cameras']
        self.cam_names = list(self.cam_presets.keys())

        self.daq_presets = preset_dict['DAQs']
        self.daq_names = list(self.daq_presets.keys())

        self.daq_names_drop.clear()
        self.daq_names_drop.addItems(self.daq_names)
        self.cam_names_drop.clear()
        self.cam_names_drop.addItems(self.cam_names)

    def set_save_dir(self, save_dir=None):
        # options = QFileDialog.Options()
        if save_dir is None:
            if self.save_dir is None:
                save_dir = QFileDialog.getExistingDirectory(self,"Select save directory")
            else:
                save_dir = QFileDialog.getExistingDirectory(self,"Select save directory", self.save_dir)

        if save_dir != "" and os.path.isdir(save_dir):
            self.save_dir = save_dir
            self.save_dir_lineEdit.setText(f'{self.save_dir}')
            self.new_path_set = False
            self.expt_name_lineEdit.setText('')
            self.expt_name = ""

            self.set_expt_push.setEnabled(True)
            self.update_ui()
    
    def set_experiment_name(self):
        expt_name,ok = QInputDialog.getText(self,'Enter unique experiment name','Experiment name:')
        if not ok:
            return
        if expt_name == "":
            return

        if expt_name in os.listdir(self.save_dir):
            msg = QMessageBox()
            msg.setWindowTitle("Redundant experiment name!")
            msg.setText(f"'{expt_name}' already exists as an experiment name in {self.save_dir}.")
            msg.exec_()
            return
        
        self.expt_name = expt_name

        if not (self.save_dir == "" or self.expt_name == ""):
            self.expt_name_lineEdit.setText(f'{self.expt_name}')
            self.expt_path = os.path.join(self.save_dir, self.expt_name)
            os.makedirs(self.expt_path, exist_ok=False)

            self.set_module_write_paths()

            self.new_path_set = True

            # Enable record button
            self.update_ui()

    def set_module_write_paths(self):
        for module in self.modules.values():
            module.set_write_path(dir=self.expt_path)

    def init_daq(self):
        daq_drop_index = self.daq_names_drop.currentIndex()
        daq_name = self.daq_names[daq_drop_index]
        daq_serial_number = self.daq_presets[daq_name]['serial_number'] if 'serial_number' in self.daq_presets[daq_name].keys() else None
        if daq_serial_number == "": daq_serial_number = None
        daq_attrs_json = self.daq_presets[daq_name]['attrs_json'] if 'attrs_json' in self.daq_presets[daq_name].keys() else None
        if daq_attrs_json == "": daq_attrs_json = None

        if daq_serial_number in [str(module.serial_number) for module in self.modules.values()]:
            title=f"DAQ initialization error"
            text=f"DAQ (serial number: {daq_serial_number}) is already initialized."
            utils.message_window(title, text)
            return

        barcode = random.randint(0, 2**31-1)
        daqUI = DAQUI(serial_number=daq_serial_number, device_name=daq_name, attrs_json_path=daq_attrs_json, parent=self, barcode=barcode)
        
        
        daqUI.set_write_path(dir=self.expt_path)
        daqUI.show()
        self.modules[barcode] = daqUI

        self.update_ui()

    def init_cam(self):
        cam_drop_index = self.cam_names_drop.currentIndex()
        cam_name = self.cam_names[cam_drop_index]
        cam_serial_number = self.cam_presets[cam_name]['serial_number'] if 'serial_number' in self.cam_presets[cam_name].keys() else None
        if cam_serial_number == "": cam_serial_number = None
        cam_attrs_json = self.cam_presets[cam_name]['attrs_json'] if 'attrs_json' in self.cam_presets[cam_name].keys() else None
        if cam_attrs_json == "": cam_attrs_json = None

        if cam_serial_number in [str(module.serial_number) for module in self.modules.values()]:
            title=f"Camera initialization error"
            text=f"Camera (serial number: {cam_serial_number}) is already initialized."
            utils.message_window(title, text)
            return

        barcode = random.randint(0, 2**31-1)
        camUI = CamUI(serial_number=cam_serial_number, device_name=cam_name, attrs_json_path=cam_attrs_json, parent=self, barcode=barcode)
        camUI.set_write_path(dir=self.expt_path)
        camUI.show()
        self.modules[barcode] = camUI

        self.update_ui()

    def control(self):
        record = (self.sender().text() == "Record")
        if self.status == Status.STANDBY:
            self.start(record)
        else:
            self.stop()

    def start(self, record=False):
        if record:
            if self.status == Status.PREVIEWING:
                self.stop()
            
            for module in self.modules.values():
                module.start(record=True)

            print('Record Started')
            self.status = Status.RECORDING
        else:
            for module in self.modules.values():
                module.start(record=False)

            print("Preview Started")
            self.status = Status.PREVIEWING
        
        if self.timer_checkBox.isChecked():
            timer_dur_in_min = float(self.timer_doubleSpinBox.value())
            timer_dur_in_ms = int(timer_dur_in_min * 60 * 1000)
            self.timer.start(timer_dur_in_ms)
        self.update_ui()

    def stop(self):
        for module in self.modules.values():
            module.stop()
        self.timer.stop()

        if self.status == Status.PREVIEWING: 
            print("Preview Finished")

        if self.status == Status.RECORDING:
            self.new_path_set = False
            print('Record Finished')
        
        self.status = Status.STANDBY
        self.update_ui()

    def stop_timer(self):
        self.timer.stop()

        self.update_ui()

    def update_ui(self):
        if self.status == Status.RECORDING: # If recording...
            self.load_preset_push.setEnabled(False)
            self.cam_init_push.setEnabled(False)
            self.daq_init_push.setEnabled(False)
            self.set_save_dir_push.setEnabled(False)
            self.set_expt_push.setEnabled(False)

            self.timer_doubleSpinBox.setEnabled(False)
            if self.timer.isActive():
                self.timer_checkBox.setEnabled(True)
            else:
                self.timer_checkBox.setEnabled(False)

            self.preview_push.setChecked(False)
            self.preview_push.setEnabled(False)
            self.preview_push.setStyleSheet("background-color: grey")

            self.record_push.setChecked(True)
            self.record_push.setEnabled(True)
            self.record_push.setStyleSheet("background-color: red")

        elif self.status == Status.PREVIEWING: # If previewing...
            self.load_preset_push.setEnabled(False)
            self.cam_init_push.setEnabled(False)
            self.daq_init_push.setEnabled(False)
            self.set_save_dir_push.setEnabled(True)
            self.set_expt_push.setEnabled(True)

            self.timer_doubleSpinBox.setEnabled(False)
            if self.timer.isActive():
                self.timer_checkBox.setEnabled(True)
            else:
                self.timer_checkBox.setEnabled(False)

            self.preview_push.setChecked(True)
            self.preview_push.setEnabled(True)
            self.preview_push.setStyleSheet("background-color: red")

            self.record_push.setChecked(False)
            self.record_push.setEnabled(True)
            self.record_push.setStyleSheet("background-color: green")

        elif self.status == Status.STANDBY: # If standby...
            self.load_preset_push.setEnabled(True)
            self.cam_init_push.setEnabled(True)
            self.daq_init_push.setEnabled(True)
            self.set_save_dir_push.setEnabled(True)
            self.set_expt_push.setEnabled(True)

            self.timer_checkBox.setEnabled(True)
            self.timer_doubleSpinBox.setEnabled(True)

            if len(self.modules) > 0: # If a camUI or daqUI is up...
                self.preview_push.setChecked(False)
                self.preview_push.setEnabled(True)
                self.preview_push.setStyleSheet("background-color: green")
            else:
                self.preview_push.setChecked(False)
                self.preview_push.setEnabled(False)
                self.preview_push.setStyleSheet("background-color: grey")

            if len(self.modules) > 0 and self.new_path_set: # If a camUI or daqUI is up and path is set...
                self.record_push.setChecked(False)
                self.record_push.setEnabled(True)
                self.record_push.setStyleSheet("background-color: green")
            else:
                self.record_push.setChecked(False)
                self.record_push.setEnabled(False)
                self.record_push.setStyleSheet("background-color: grey")
        else:
            utils.message_window(text="Invalid status.")

    def child_close_event(self, barcode):
        if barcode is not None and barcode in self.modules:
            self.modules.pop(barcode)
        if len(self.modules) == 0:
            if self.status == Status.PREVIEWING:
                self.preview()
            elif self.status == Status.RECORDING:
                self.record()
        self.update_ui()

    def closeEvent(self, event): # do not change name, super override
        for module in list(self.modules.values()): #list avoids runtime error of dict changing size during close
            module.close()

    # def preview(self):
    #     if self.status == Status.STANDBY:
    #         for module in self.modules.values():
    #             module.start(record=False)

    #         self.status = Status.PREVIEWING
    #         self.update_ui()
    #         print("Preview Started")
    #     elif self.status == Status.PREVIEWING: 
    #         for module in self.modules.values():
    #             module.stop()

    #         self.status = Status.STANDBY
    #         self.update_ui()
    #         print("Preview Finished")
    #     elif self.status == Status.RECORDING:
    #         utils.message_window(text="Cannot start preview while recording.")
    #     else:
    #         utils.message_window(text="Invalid status.")

    # def record(self):
    #     if self.status == Status.PREVIEWING:
    #         self.preview()
        
    #     if self.status == Status.STANDBY:
    #         for module in self.modules.values():
    #             module.start(record=True)

    #         self.status = Status.RECORDING
    #         self.update_ui()
    #         print('Record Started')
    #     elif self.status == Status.RECORDING:
    #         for module in self.modules.values():
    #             module.stop()

    #         self.new_path_set = False
    #         self.status = Status.STANDBY
    #         self.update_ui()
    #         print('Record Finished')
    #     elif self.status == Status.PREVIEWING:
    #         utils.message_window(text="Cannot start recording while previewing.")
    #     else:
    #         utils.message_window(text="Invalid status.")

    # def stop2(self):
    #     if self.status == Status.PREVIEWING:
    #         self.preview()
    #     elif self.status == Status.RECORDING:
    #         self.record()
    #     else:
    #         print("Nothing to stop.")

def main():
    app = QApplication(sys.argv)
    form = MainUI()
    form.show()
    app.exec_()


if __name__ == '__main__':

    main()
