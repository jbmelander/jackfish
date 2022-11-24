import os
import sys
import random
import json

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QApplication, QFileDialog, QInputDialog, QMessageBox
from PyQt5.QtGui import QMovie, QPixmap
from PyQt5.QtCore import QSize
from cam_controller import CamUI
from daq_controller import DAQUI
import main_gui

from jackfish.utils import ROOT_DIR


class MainUI(QtWidgets.QMainWindow, main_gui.Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainUI, self).__init__(parent)
        self.setupUi(self)
        
        image_dir = os.path.join(ROOT_DIR,'assets/pike.jpg')
        self.label.setPixmap(QPixmap(image_dir))
        self.label.setScaledContents(True)
        self.label.setObjectName("label")

        self.save_dir = os.environ['HOME']
        self.expt_name = ""
        self.expt_path = os.environ['HOME']
        self.new_path_set = False

        self.daqUIs = {}
        self.camUIs = {}

        #### UI ####
        self.load_preset_push.clicked.connect(self.load_preset)
        self.set_save_dir_push.clicked.connect(lambda: self.set_save_dir(save_dir=None))
        self.set_expt_push.clicked.connect(self.set_experiment_name)
        self.set_expt_push.setEnabled(False)

        self.preview_push.setCheckable(True)
        self.preview_push.clicked.connect(self.preview)

        self.record_push.setCheckable(True)
        self.record_push.clicked.connect(self.record)
        
        self.update_preview_record_push_styles()
    
        self.daq_init_push.clicked.connect(self.init_daq)
        self.cam_init_push.clicked.connect(self.init_cam)

        #### Import presets ####
        self.load_preset(init=True)

    def load_preset(self, init=False):
        if init:
            preset_dict = {"main": {}, "cameras": {"Default": {}}, "DAQs": {"Default": {}}}
        else:
            presets_dir = os.path.join(ROOT_DIR,'presets')

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
            self.filepath_label.setText(f'{self.save_dir}')
            self.new_path_set = False

            self.set_expt_push.setEnabled(True)
            self.update_preview_record_push_styles()
    
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
            self.expt_name_label.setText(f'{self.expt_name}')
            self.expt_path = os.path.join(self.save_dir, self.expt_name)
            os.makedirs(self.expt_path, exist_ok=False)

            self.set_module_write_paths()

            self.new_path_set = True

            # Enable record button
            self.update_preview_record_push_styles()

    def update_preview_record_push_styles(self):
        # Preview Push
        if self.record_push.isChecked(): # If recording...
            self.preview_push.setEnabled(False)
            self.preview_push.setStyleSheet("background-color: grey")
        elif self.preview_push.isChecked(): # If previewing...
            self.preview_push.setEnabled(True)
            self.preview_push.setStyleSheet("background-color: red")
        elif len(self.daqUIs) > 0 or len(self.camUIs) > 0: # If a camUI or daqUI is up...
            self.preview_push.setEnabled(True)
            self.preview_push.setStyleSheet("background-color: green")
        else:
            self.preview_push.setEnabled(False)
            self.preview_push.setStyleSheet("background-color: grey")

        # Record Push
        if self.record_push.isChecked(): # If recording...
            self.record_push.setEnabled(True)
            self.record_push.setStyleSheet("background-color: red")
        elif (len(self.daqUIs) > 0 or len(self.camUIs) > 0) and self.new_path_set: # If a camUI or daqUI is up and path is set...
            self.record_push.setEnabled(True)
            self.record_push.setStyleSheet("background-color: green")
        else:
            self.record_push.setEnabled(False)
            self.record_push.setStyleSheet("background-color: grey")

    def set_module_write_paths(self):
        for daqUI in self.daqUIs.values():
            daqUI.set_write_path(dir=self.expt_path)
        for camUI in self.camUIs.values():
            camUI.set_video_out_path(dir=self.expt_path)

    def init_daq(self):
        daq_drop_index = self.daq_names_drop.currentIndex()
        daq_name = self.daq_names[daq_drop_index]
        daq_serial_number = self.daq_presets[daq_name]['serial_number'] if 'serial_number' in self.daq_presets[daq_name].keys() else None
        if daq_serial_number == "": daq_serial_number = None
        daq_attrs_json = self.daq_presets[daq_name]['attrs_json'] if 'attrs_json' in self.daq_presets[daq_name].keys() else None
        if daq_attrs_json == "": daq_attrs_json = None

        barcode = random.randint(0, 2**31-1)
        daqUI = DAQUI(serial_number=daq_serial_number, device_name=daq_name, attrs_json_path=daq_attrs_json, parent=self, barcode=barcode)
        daqUI.set_write_path(dir=self.expt_path)
        daqUI.show()
        self.daqUIs[barcode] = daqUI

        self.update_preview_record_push_styles()

    def init_cam(self):
        cam_drop_index = self.cam_names_drop.currentIndex()
        cam_name = self.cam_names[cam_drop_index]
        cam_serial_number = self.cam_presets[cam_name]['serial_number'] if 'serial_number' in self.cam_presets[cam_name].keys() else None
        if cam_serial_number == "": cam_serial_number = None
        cam_attrs_json = self.cam_presets[cam_name]['attrs_json'] if 'attrs_json' in self.cam_presets[cam_name].keys() else None
        if cam_attrs_json == "": cam_attrs_json = None

        barcode = random.randint(0, 2**31-1)
        camUI = CamUI(serial_number=cam_serial_number, device_name=cam_name, attrs_json_path=cam_attrs_json, parent=self, barcode=barcode)
        camUI.set_video_out_path(dir=self.expt_path)
        camUI.show()
        self.camUIs[barcode] = camUI

        self.update_preview_record_push_styles()

    def preview(self):
        state = self.preview_push.isChecked()
        if state:
            for daqUI in self.daqUIs.values():
                daqUI.start(record=False)

            for camUI in self.camUIs.values():
                camUI.start(record=False)

            self.update_preview_record_push_styles()
            print("Preview Started")
        else: 
            for daqUI in self.daqUIs.values():
                daqUI.stop()

            for camUI in self.camUIs.values():
                camUI.stop()

            self.update_preview_record_push_styles()
            print("Preview Finished")

    def record(self):
        state = self.record_push.isChecked()
        if state:
            if self.preview_push.isChecked(): # preview was on
                self.preview_push.click()

            for daqUI in self.daqUIs.values():
                daqUI.start(record=True)

            for camUI in self.camUIs.values():
                camUI.start(record=True)

            self.update_preview_record_push_styles()
            print('Experiment Started')
        else:
            for daqUI in self.daqUIs.values():
                daqUI.stop()

            for camUI in self.camUIs.values():
                camUI.stop()

            self.new_path_set = False
            self.update_preview_record_push_styles()
            print('Experiment Finished')

    def child_close_event(self):
        self.update_preview_record_push_styles()

    def closeEvent(self, event): # do not change name, super override
        for camUI in list(self.camUIs.values()): #list avoids runtime error of dict changing size during close
            camUI.close()

        for daqUI in list(self.daqUIs.values()):
            daqUI.close()

def main():
    app = QApplication(sys.argv)
    form = MainUI()
    form.show()
    app.exec_()


if __name__ == '__main__':

    main()
