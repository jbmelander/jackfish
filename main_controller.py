import os
import sys
import random

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QApplication, QFileDialog, QInputDialog

from cam_controller import CamUI
from daq_controller import DAQUI

import main_gui

class MainUI(QtWidgets.QMainWindow, main_gui.Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainUI, self).__init__(parent)
        self.setupUi(self)

        #### Main UI ####

        self.main_dir = ""
        self.expt_name = ""
        self.exp_path = os.environ['HOME']

        self.set_path_push.clicked.connect(self.query_and_set_module_write_paths)

        self.preview_push.setCheckable(True)
        self.preview_push.clicked.connect(self.preview)

        self.record_push.setCheckable(True)
        self.record_push.clicked.connect(self.record)
    
        #### DAQ ####

        self.daqUIs = {}

        self.init_daq_push.clicked.connect(self.init_daq)

        #### Camera ####

        self.cam_names = ['Left', 'Top']
        self.cam_serial_numbers = ['20243354', '22248111']
        self.camUIs = {}

        self.init_cam0_push.clicked.connect(self.init_cam0)
        self.init_cam1_push.clicked.connect(self.init_cam1)

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
        barcode = random.randint(0, 2**31-1)
        daqUI = DAQUI(parent=self, barcode=barcode)
        daqUI.set_write_path(dir=self.exp_path)
        daqUI.show()
        self.daqUIs[barcode] = daqUI

    def init_cam0(self):
        self.init_camera_module(cam_index=self.cam_serial_numbers[0], attrs_json_path=None)

    def init_cam1(self):
        self.init_camera_module(cam_index=self.cam_serial_numbers[1], attrs_json_path=None)

    def init_camera_module(self, cam_index, attrs_json_path=None):
        barcode = random.randint(0, 2**31-1)
        camUI = CamUI(cam_index=cam_index, attrs_json_path=attrs_json_path, parent=self, barcode=barcode)
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
