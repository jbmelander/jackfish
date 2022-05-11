pimport os
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

        #### Labjack ####

        # Set Labjack Scanrate
        self.lj_sr_edit.editingFinished.connect(self.set_lj_scanrate)
        self.set_lj_scanrate()

        # Labjack Scan channels
        self.lj_chans = self.lj_chan_edit.text().split(',')
        self.lj_chan_edit.editingFinished.connect(self.reset_lj_chans)

        self.lj_chan_preview_drop.addItems(['None'] + self.lj_chans)

        # Set Labjack Trigger channels
        self.lj_cam_trigger_chan_edit.editingFinished.connect(self.set_lj_cam_trigger_chans)
        self.set_lj_cam_trigger_chans()

        # LJ Cam Trigger button
        self.lj_cam_trigger_push.clicked.connect(self.trigger_cams)

        # Initialize Labjack
        self.lj = Jack(self.lj_chans)

        # Labjack preview
        self.lj_prev_slider.setMinimum(0)
        self.lj_prev_slider.setMaximum(20000)
        self.lj_prev_slider.sliderReleased.connect(self.set_lj_slider)

        self.data = [0]
        self.curve = self.lj_prev.getPlotItem().plot()
        self.curve.setData(self.data)
        self.lj_prev.show()

        ################

        #### Camera ####

        # self.init_cam0_push.setCheckable(True)
        # self.init_cam0_push.clicked.connect(self.init_cam0)
        # self.init_cam1_push.setCheckable(True)
        # self.init_cam1_push.clicked.connect(self.init_cam1)

        if os.uname()[1] == "40hr-fitness":
            self.cam=FJCam(cam_index='20243354') # top camera

            # Init FT camera, set attributes, then disconnect so that Fictrac can use the cam.
            self.ft_cam=FJCam(cam_index='20243355') # side camera

        else: # Josh's one-camera setup
            self.cam=FJCam(cam_index=0)
            self.ft_cam = None

        self.hist=self.cam_prev.getHistogramWidget()
        self.hist.sigLevelsChanged.connect(self.lev_changed)

        self.levels = [0,100]

        self.cam_view_toggle.stateChanged.connect(self.set_cam_view)
        self.set_cam_view()

        ################

        self.set_path_push.clicked.connect(self.set_path)

        self.preview_push.setCheckable(True)
        self.preview_push.clicked.connect(self.preview)

        self.record_push.setCheckable(True)
        self.record_push.clicked.connect(self.record)

        self.cam_timer = QtCore.QTimer()
        self.cam_timer.timeout.connect(self.cam_updater)
        self.lj_timer = QtCore.QTimer()
        self.lj_timer.timeout.connect(self.lj_updater)
    

        self.shutdown_push.clicked.connect(self.shutdown)
    
    def set_cam_view(self):
        self.cam_view = self.cam_view_toggle.isChecked()

    def lev_changed(self):
        self.levels = self.hist.getLevels()

    def set_lj_scanrate(self):
        self.lj_scanrate = int(self.lj_sr_edit.text())

    def set_lj_cam_trigger_chans(self):
        self.lj_cam_trigger_chans = self.lj_cam_trigger_chan_edit.text().split(',')

    def reset_lj_chans(self):
        self.lj_chans = self.lj_chan_edit.text().split(',')
        self.lj_chan_preview_drop.clear()
        self.lj_chan_preview_drop.addItems(['None'] + self.lj_chans)
        self.lj.close()
        self.lj=Jack(self.lj_chans)


    def closeEvent(self,event): # do not change name, super override
        self.lj.close()

    def shutdown(self):
        # self.lj.close()
        self.cam.close()
        if self.ft_cam is not None:
            self.ft_cam.close()

    def trigger_cams(self):
        write_states = np.ones(len(self.lj_cam_trigger_chans), dtype=int)
        self.lj.write(self.lj_cam_trigger_chans, write_states.tolist())
        time.sleep(0.05)
        self.lj.write(self.lj_cam_trigger_chans, (write_states*0).tolist())

    # def test_write(self,names):
    #     for i in range(100):
    #         if i%2==0:
    #             self.lj.write(['FIO3'],[0])
    #             time.sleep(1)
    #         else: 
    #             self.lj.write(['FIO3'],[1])
    #             time.sleep(1)

    def preview(self):
        state = self.preview_push.isChecked()
        if state:
            self.lj_timer.start()
            self.lj.start_stream(do_record=False, scanRate=self.lj_scanrate)
            self.cam_timer.start()
            self.cam.start()
        else:
            print("Turning preview off")
            self.lj_timer.stop()
            self.lj.stop_stream()
            self.cam_timer.stop()
            self.cam.stop()

    def record(self):
        state = self.record_push.isChecked()
        if state:
            if self.preview_push.isChecked(): # preview was on
                self.preview_push.click()

            self.lj_timer.start()
            self.lj.start_stream(do_record=True, record_filepath=self.lj_write_path, scanRate=self.lj_scanrate)
            self.cam.start()
            self.cam.start_rec()

            print('Experiment Started')        
        else:
            self.lj_timer.stop()
            self.lj.stop_stream()
            self.cam.stop_rec()
            self.cam.stop()

            print('Experiment Finished')


    def set_lj_slider(self):
        self.cam_timer.stop()
        self.lj_timer.stop()

        self.lj_slider_val = int(self.lj_prev_slider.value())
        self.cam_timer.start()
        self.lj_timer.start()

    def set_path(self):
        self.cam_timer.stop()
        self.lj_timer.stop()

        options = QFileDialog.Options()
        self.filepath = QFileDialog.getExistingDirectory(self,"Select save directory")
        
        ok = False
        while not ok:
            self.expt_name,ok = QInputDialog.getText(self,'Enter experiment name','Experiment name:')
        

        self.filepath_label.setText(f'{self.filepath} >>> {self.expt_name}')
        exp_path = os.path.join(self.filepath,self.expt_name)
        os.mkdir(exp_path)

        self.cam.set_video_out_path(os.path.join(exp_path,f'{self.expt_name}.mp4'))
        self.lj_write_path=os.path.join(exp_path,f'{self.expt_name}.csv')

        print(self.lj_write_path)

    def cam_updater(self):
        self.cam_prev.clear()
        if self.cam_view:
            try:
                self.frame = self.cam.grab(wait=False)
                self.cam_prev.setImage(self.frame,autoLevels=False,levels=self.levels,autoHistogramRange=False)
                self.cam_prev.setLevels(self.levels[0],self.levels[1])
            except:
                pass

    def lj_updater(self):
        idx= self.lj_chan_preview_drop.currentIndex()

        if idx == 0: # None
            return
        else:
            idx -= 1 # Not None; subtract index by 1 to correct for the None

            self.data = self.lj.data[idx:-1:len(self.lj_chans)]
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
