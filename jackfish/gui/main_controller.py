import os
import sys
import random
import json

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QApplication, QFileDialog, QInputDialog
from PyQt5.QtGui import QMovie, QPixmap
from PyQt5.QtCore import QSize
from cam_controller import CamUI
from daq_controller import DAQUI

import main_gui

class MainUI(QtWidgets.QMainWindow, main_gui.Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainUI, self).__init__(parent)
        self.setupUi(self)
        jackfish_dir = os.path.realpath(os.path.dirname(__file__))
        title_path = os.path.join(jackfish_dir,'../../assets/title.gif')
        gif = QMovie(title_path)
        self.title_gif_label.setMovie(gif)
        gif.start()
        
        image_dir = os.path.join(jackfish_dir,'../../assets/jf.jpg')
        self.label.setPixmap(QPixmap(image_dir))
        self.label.setScaledContents(True)
        self.label.setObjectName("label")

        self.main_dir = os.environ['HOME']
        self.expt_name = ""
        self.exp_path = os.environ['HOME']

        self.daqUIs = {}
        self.camUIs = {}

        #### Import presets ####
        self.load_preset(init=True)

        #### UI ####
        self.load_preset_push.clicked.connect(self.load_preset)
        self.set_path_push.clicked.connect(self.query_and_set_module_write_paths)

        self.preview_push.setCheckable(True)
        self.preview_push.clicked.connect(self.preview)

        self.record_push.setCheckable(True)
        self.record_push.clicked.connect(self.record)
    
        self.daq_init_push.clicked.connect(self.init_daq)
        self.cam_init_push.clicked.connect(self.init_cam)

    def load_preset(self, init=False):
        if init:
            preset_dict = {"main": {}, "cameras": {"Default": {}}, "DAQs": {"Default": {}}}
        else:
            jackfish_dir = os.path.realpath(os.path.dirname(__file__))
            presets_dir = os.path.join(jackfish_dir,'presets')

            json_fn, _ = QFileDialog.getOpenFileName(self, "Select preset json file.", presets_dir, "JSON files (*.json)")

            if json_fn == "":
                return
            else:
                with open(json_fn, 'r') as f:
                    preset_dict = json.load(f)

        main_presets = preset_dict['main']
        if "default_dir" in main_presets.keys():
            self.main_dir = main_presets['default_dir']

        self.cam_presets = preset_dict['cameras']
        self.cam_names = list(self.cam_presets.keys())

        self.daq_presets = preset_dict['DAQs']
        self.daq_names = list(self.daq_presets.keys())

        self.daq_names_drop.clear()
        self.daq_names_drop.addItems(self.daq_names)
        self.cam_names_drop.clear()
        self.cam_names_drop.addItems(self.cam_names)

    def query_and_set_module_write_paths(self):
        # options = QFileDialog.Options()
        self.main_dir = QFileDialog.getExistingDirectory(self,"Select save directory")
        
        self.expt_name,ok = QInputDialog.getText(self,'Enter experiment name','Experiment name:')
        if not ok:
            self.expt_name = ""
            
        if not (self.main_dir == "" or self.expt_name == ""):
            self.filepath_label.setText(f'{self.main_dir} >>> {self.expt_name}')
            self.exp_path = os.path.join(self.main_dir,self.expt_name)
            os.makedirs(self.exp_path, exist_ok=True)

            self.set_module_write_paths()

            # Enable record button
            self.record_push.setEnabled(True)

    def set_module_write_paths(self):
        for daqUI in self.daqUIs.values():
            daqUI.set_write_path(dir=self.exp_path)
        for camUI in self.camUIs.values():
            camUI.set_video_out_path(dir=self.exp_path)

    def init_daq(self):
        daq_drop_index = self.daq_names_drop.currentIndex()
        daq_name = self.daq_names[daq_drop_index]
        daq_serial_number = self.daq_presets[daq_name]['serial_number'] if 'serial_number' in self.daq_presets[daq_name].keys() else None
        if daq_serial_number == "": daq_serial_number = None
        daq_attrs_json = self.daq_presets[daq_name]['attrs_json'] if 'attrs_json' in self.daq_presets[daq_name].keys() else None
        if daq_attrs_json == "": daq_attrs_json = None

        barcode = random.randint(0, 2**31-1)
        daqUI = DAQUI(serial_number=daq_serial_number, device_name=daq_name, attrs_json_path=daq_attrs_json, parent=self, barcode=barcode)
        daqUI.set_write_path(dir=self.exp_path)
        daqUI.show()
        self.daqUIs[barcode] = daqUI

    def init_cam(self):
        cam_drop_index = self.cam_names_drop.currentIndex()
        cam_name = self.cam_names[cam_drop_index]
        cam_serial_number = self.cam_presets[cam_name]['serial_number'] if 'serial_number' in self.cam_presets[cam_name].keys() else None
        if cam_serial_number == "": cam_serial_number = None
        cam_attrs_json = self.cam_presets[cam_name]['attrs_json'] if 'attrs_json' in self.cam_presets[cam_name].keys() else None
        if cam_attrs_json == "": cam_attrs_json = None

        barcode = random.randint(0, 2**31-1)
        camUI = CamUI(serial_number=cam_serial_number, device_name=cam_name, attrs_json_path=cam_attrs_json, parent=self, barcode=barcode)
        camUI.set_video_out_path(dir=self.exp_path)
        camUI.show()
        self.camUIs[barcode] = camUI

    def preview(self):
        state = self.preview_push.isChecked()
        if state:
            for daqUI in self.daqUIs.values():
                daqUI.start(record=False)

            for camUI in self.camUIs.values():
                camUI.start(record=False)

            print("Preview Started")
        else: 
            for daqUI in self.daqUIs.values():
                daqUI.stop()

            for camUI in self.camUIs.values():
                camUI.stop(record=False)

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

            print('Experiment Started')
        else:
            for daqUI in self.daqUIs.values():
                daqUI.stop()

            for camUI in self.camUIs.values():
                camUI.stop(record=True)

            self.record_push.setEnabled(False)

            print('Experiment Finished')

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
