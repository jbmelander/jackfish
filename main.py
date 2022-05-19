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
if os.uname()[1] == "40hr-fitness":
    from ftutil.ft_managers import FtManager

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
        self.lj_chan_edit.editingFinished.connect(self.set_lj_chans)

        self.lj_chan_preview_drop.addItems(['None'] + self.lj_chans)

        # Set Labjack Trigger channels
        self.lj_cam_trigger_chan_edit.editingFinished.connect(self.set_lj_cam_trigger_chans)
        self.set_lj_cam_trigger_chans()

        # LJ Cam Trigger button
        self.lj_cam_trigger_push.clicked.connect(self.trigger_cams)

        # Initialize Labjack
        self.lj = Jack()

        # Labjack preview drop change
        self.lj_chan_preview_drop.currentIndexChanged.connect(self.set_lj_chan_preview)

        # Labjack preview
        self.lj_prev_slider.setMinimum(0)
        self.lj_prev_slider.setMaximum(20000)
        self.lj_prev_slider.sliderReleased.connect(self.set_lj_slider)

        self.lj_data = [0]
        self.lj_curve = self.lj_prev.getPlotItem().plot()
        self.lj_curve.setData(self.lj_data)
        self.lj_prev.show()
        self.lj_show_preview = False

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
            # self.ft_cam.close()

            self.ft_params = {
                'bin' :    "/home/clandinin/src/fictrac/bin/fictrac",
                'config' : "/home/clandinin/src/fictrac/config.txt",
                'host' : '127.0.0.1',  # The server's hostname or IP address
                'port' : 33334,         # The port used by the server
                'frame_num_idx' : 0,
                'x_idx' : 14,
                'y_idx' : 15,
                'theta_idx' : 16,
                'timestamp_idx' : 21
            }

            self.cam1_trigger_toggle.stateChanged.connect(self.toggle_cam1_trigger)
            self.cam1_trigger_toggle.setChecked(self.ft_cam.cam.TriggerMode == 'On')

            self.launch_fictrac_toggle.stateChanged.connect(self.set_launch_fictrac)
            self.set_launch_fictrac()

        else: # Josh's one-camera setup
            self.cam=FJCam(cam_index=0)
            self.ft_cam = None

        self.hist=self.cam_prev.getHistogramWidget()
        self.hist.sigLevelsChanged.connect(self.cam_lev_changed)

        self.cam_levels = [0,255]

        self.cam_view_toggle.stateChanged.connect(self.toggle_cam_view)
        self.toggle_cam_view()

        self.cam0_trigger_toggle.stateChanged.connect(self.toggle_cam0_trigger)
        self.cam0_trigger_toggle.setChecked(self.cam.cam.TriggerMode == 'On')


        ################

        self.ft_manager = None

        self.set_path_push.clicked.connect(self.set_path)
        self.exp_path = os.environ['HOME']

        self.preview_push.setCheckable(True)
        self.preview_push.clicked.connect(self.preview)

        self.record_push.setCheckable(True)
        self.record_push.clicked.connect(self.record)


        self.cam_timer = QtCore.QTimer()
        self.cam_timer.timeout.connect(self.cam_updater)
        self.lj_timer = QtCore.QTimer()
        self.lj_timer.timeout.connect(self.lj_updater)
        
    def set_launch_fictrac(self):
        self.do_launch_fictrac = self.launch_fictrac_toggle.isChecked()

    def toggle_cam_view(self):
        self.cam_view = self.cam_view_toggle.isChecked()

    def toggle_cam0_trigger(self):
        self.cam.cam.TriggerMode = 'On' if self.cam0_trigger_toggle.isChecked() else 'Off'

    def toggle_cam1_trigger(self):
        self.ft_cam.cam.TriggerMode = 'On' if self.cam1_trigger_toggle.isChecked() else 'Off'

    def cam_lev_changed(self):
        levels = self.hist.getLevels()
        min_level = max(levels[0], 0)
        max_level = min(levels[1], 255)
        self.cam_levels = (min_level, max_level)
        self.hist.setLevels(min_level, max_level)

    def set_lj_scanrate(self):
        self.lj_scanrate = int(self.lj_sr_edit.text())

    def set_lj_cam_trigger_chans(self):
        self.lj_cam_trigger_chans = self.lj_cam_trigger_chan_edit.text().split(',')

    def set_lj_chans(self):
        self.lj_chans = self.lj_chan_edit.text().split(',')
        self.lj_chan_preview_drop.clear()
        self.lj_chan_preview_drop.addItems(['None'] + self.lj_chans)

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
            self.lj.start_stream(do_record=False, aScanListNames=self.lj_chans, scanRate=self.lj_scanrate, dataQ_len_sec=15)
            self.cam_fn_prev = 0
            self.cam_timer.start()
            self.cam.start()
            self.cam.start_preview()

            if self.do_launch_fictrac:
                self.launch_fictrac(ft_bin=self.ft_params['bin'], ft_config=self.ft_params['config'], cwd=self.exp_path)
 
        else:
            print("Turning preview off")
            self.lj_timer.stop()
            self.lj.stop_stream()
            self.cam_timer.stop()
            self.cam.stop_preview()
            self.cam.stop()

            if self.ft_manager is not None:
                self.ft_manager.close()
                self.ft_manager = None

                # delete fictrac output
                fictrac_files = sorted([x for x in os.listdir(self.exp_path) if x[0:7]=='fictrac'])
                for i in range(len(fictrac_files)):
                    os.remove(os.path.join(self.exp_path, fictrac_files[i]))

    def record(self):
        state = self.record_push.isChecked()
        if state:
            if self.preview_push.isChecked(): # preview was on
                self.preview_push.click()

            self.lj_timer.start()
            self.lj.start_stream(do_record=True, record_filepath=self.lj_write_path, aScanListNames=self.lj_chans, scanRate=self.lj_scanrate, dataQ_len_sec=15)
            self.cam_fn_prev = 0
            self.cam_timer.start()
            self.cam.start()
            self.cam.start_rec()

            if self.do_launch_fictrac:
                self.launch_fictrac(ft_bin=self.ft_params['bin'], ft_config=self.ft_params['config'], cwd=self.exp_path)

            print('Experiment Started')        
        else:
            self.lj_timer.stop()
            self.lj.stop_stream()
            self.cam.stop_rec()
            self.cam.stop()

            if self.ft_manager is not None:
                self.ft_manager.close()
                self.ft_manager = None

            print('Experiment Finished')

    def launch_fictrac(self, ft_bin, ft_config, cwd=None):
        self.ft_manager = FtManager(ft_bin=ft_bin, ft_config=ft_config, cwd=cwd)

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
        self.exp_path = os.path.join(self.filepath,self.expt_name)
        os.mkdir(self.exp_path)

        self.cam.set_video_out_path(os.path.join(self.exp_path,f'{self.expt_name}.mp4'))
        self.lj_write_path=os.path.join(self.exp_path,f'{self.expt_name}.csv')

        print(self.lj_write_path)

    def cam_updater(self):
        if self.cam_view and self.cam.fn > self.cam_fn_prev:
            self.cam_prev.clear()
            self.cam_prev.setImage(self.cam.frame.T, autoLevels=False, levels=self.cam_levels, autoHistogramRange=False)
            self.cam_prev.setLevels(self.cam_levels[0],self.cam_levels[1])
            self.cam_fn_prev = self.cam.fn

    def set_lj_chan_preview(self):
        self.lj_chan_preview_idx = self.lj_chan_preview_drop.currentIndex()
        if self.lj_chan_preview_idx == 0: # None
            self.lj.stop_collect_dataQ()
            self.lj_show_preview = False
        else:
            self.lj_chan_preview_idx -= 1 # Not None; subtract index by 1 to correct for the None
            self.lj.start_collect_dataQ()
            self.lj_show_preview = True

    def lj_updater(self):
        if self.lj_show_preview:

            self.lj_data = list(self.lj.dataQ)[self.lj_chan_preview_idx:-1:len(self.lj_chans)]
            try:
                self.lj_curve.setData(self.lj_data[-self.lj_slider_val:])
            except:
                self.lj_curve.setData(self.lj_data)
            self.lj_prev.show() 

def main():
    app = QApplication(sys.argv)
    form = FLUI()
    form.show()
    app.exec_()


if __name__ == '__main__':
    main()
