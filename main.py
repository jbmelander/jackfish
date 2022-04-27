import os
import numpy as np
import time
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QApplication, QFileDialog
from PyQt5.QtGui import QPixmap, QImage
from functools import partial
import sys
from cam import FJCam
from jack import Jack
import gui

class FLUI(QtWidgets.QMainWindow, gui.Ui_MainWindow):
    def __init__(self, parent=None):
        super(FLUI, self).__init__(parent)
        self.setupUi(self)

        self.cam=FJCam()       
        self.lj = Jack(['AIN1','FIO2'])
          
        self.set_path_push.clicked.connect(self.set_path)
        
        self.preview_push.setCheckable(True)
        self.preview_push.clicked.connect(self.preview)

        self.record_push.setCheckable(True)
        self.record_push.clicked.connect(self.record)

        self.data = [0]
        self.curve = self.lj_prev.getPlotItem().plot()
        self.curve.setData(self.data)
        self.lj_prev.show()

        self.cam_timer = QtCore.QTimer()
        self.cam_timer.timeout.connect(self.cam_updater)
        self.lj_timer = QtCore.QTimer()
        self.lj_timer.timeout.connect(self.lj_updater)
    
        self.lj_prev_slider.setMinimum(0)
        self.lj_prev_slider.setMaximum(20000)
        self.lj_prev_slider.sliderReleased.connect(self.set_lj_slider)
    
    def record(self):
        state = self.record_push.isChecked()
        if state:
            self.cam_timer.stop()
            self.lj_timer.stop()
            self.lj.start_stream(record_filepath=os.path.expanduser('~/data.minjo'))

            self.cam.rec(300)
            self.record_push.toggle()
            self.lj.stop_stream()

        

    def set_lj_slider(self):
        self.cam_timer.stop()
        self.lj_timer.stop()

        self.lj_slider_val = int(self.lj_prev_slider.value())
        self.cam_timer.start()
        self.lj_timer.start()

    def preview(self):
        state = self.preview_push.isChecked()
        if state:
            self.cam_timer.start()
            self.lj_timer.start()
            self.lj.start_stream(do_record=False)


        else:
            self.cam_timer.stop()
            self.lj_timer.stop()
            self.lj.stop_stream()


    def set_path(self):
        self.cam_timer.stop()
        self.lj_timer.stop()
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getSaveFileName(self,"QFileDialog.getOpenFileName()", "","All Files (*)", options=options)

        if fileName:
            print(fileName)

        self.filepath = fileName
        self.filepath_label.setText(self.filepath)
        self.cam.mp4_path=self.filepath

  
    def cam_updater(self):
        self.cam_prev.clear()
        self.frame = self.cam.grab()
        self.cam_prev.setImage(self.frame)

    def lj_updater(self):
        self.data = self.lj.data[0:-1:2]
        try:
            self.curve.setData(self.data[-self.lj_slider_val:])
        except:
            self.curve.setData(self.data)
        self.lj_prev.show()         

def main():
    app = QApplication(sys.argv)
    form = FLUI()
    form.show()
    app.exec_()


if __name__ == '__main__':
    main()
