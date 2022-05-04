import os
import numpy as np
import time
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QApplication, QFileDialog, QInputDialog
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

        self.hist=self.cam_prev.getHistogramWidget()
        self.hist.sigLevelsChanged.connect(self.lev_changed)


        self.levels = [0,100]


        self.lj_chans = self.lj_chan_edit.text().split(',')
        self.lj = Jack(self.lj_chans)
        self.lj_chan_edit.editingFinished.connect(self.reset_lj_chans)
          
        self.set_path_push.clicked.connect(self.set_path)
        
        self.preview_push.setCheckable(True)
        self.preview_push.clicked.connect(self.preview)

        self.record_push.setCheckable(True)
        self.record_push.clicked.connect(self.record)
        self.write_push.clicked.connect(self.test_write)

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

        self.lj_chan_preview_drop.addItems(self.lj_chans)
    
    def lev_changed(self):
        self.levels = self.hist.getLevels()

    def reset_lj_chans(self):
        self.lj_chans = self.lj_chan_edit.text().split(',')
        self.lj_chan_preview_drop.clear()
        self.lj_chan_preview_drop.addItems(self.lj_chans)
        self.lj.close()
        self.lj=Jack(self.lj_chans)



    def closeEvent(self,event): # do not change name, super override
        self.lj.close()
        
    
    def test_write(self,names):
        for i in range(100):
            if i%2==0:
                self.lj.write(['FIO3'],[0])
                time.sleep(1)
            else: 
                self.lj.write(['FIO3'],[1])
                time.sleep(1)

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
        self.filepath = QFileDialog.getExistingDirectory(self,"Select save ddirectory")
        
        self.expt_name,ok = QInputDialog.getText(self,'Experiment name:','Experiment name:')
        if not ok: 
            while not ok:
                self.expt_name,ok = QInputDialog.getText(self,'Enter experiment name','Experiment name:')

        self.filepath_label.setText(self.filepath)
        self.cam.mp4_path=self.filepath

  
    def cam_updater(self):
        self.cam_prev.clear()
        self.frame = self.cam.grab()
        self.cam_prev.setImage(self.frame,autoLevels=False,levels=self.levels,autoHistogramRange=False)
        self.cam_prev.setLevels(self.levels[0],self.levels[1])


    def lj_updater(self):
        idx= self.lj_chan_preview_drop.currentIndex()
        print(type(idx))
        self.data = self.lj.data[idx:-1:2]
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
