import sys
import os

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QFileDialog

from jackfish.devices.cameras.flir import FlirCam
from cam_gui import Ui_CamWindow

from jackfish import utils
from jackfish.utils import Status

class CamUI(QtWidgets.QFrame, Ui_CamWindow):

    def __init__(self, serial_number=None, device_name=None, attrs_json_path=None, parent=None, barcode=None):
        super(CamUI, self).__init__(None)
        self.setupUi(self)

        self.parent = parent
        self.barcode = barcode
        self.attrs_json_path = attrs_json_path

        self.status = Status.STANDBY
        
        img_path = os.path.join(utils.ROOT_DIR, 'assets/pach.jpg')
        self.pachanoi.setPixmap(QPixmap(img_path))
        self.pachanoi.setScaledContents(True)
        self.pachanoi.setObjectName("label")

        if serial_number is None: serial_number = 0

        self.cam = FlirCam(serial_number=serial_number, attrs_json_fn=attrs_json_path)
        self.serial_number = self.cam.serial_number
        
        self.setWindowTitle(f'Camera {device_name} ({self.cam.serial_number})')

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.preview_updater)

        self.fn_prev = 0

        # self.init_push.setCheckable(True)
        # self.init_push.clicked.connect(self.init_cam)
        # self.load_attrs_push.setCheckable(True)
        # self.load_attrs_push.clicked.connect(self.load_attrs)

        self.trigger_toggle.stateChanged.connect(self.toggle_trigger)
        self.trigger_toggle.setChecked(self.cam.cam.TriggerMode == 'On')

        self.gain_edit.editingFinished.connect(self.edit_gain)
        self.gain_edit.setText('Auto' if self.cam.cam.GainAuto == 'Continuous' else f'{self.cam.cam.Gain:.2f}')

        self.exposure_edit.returnPressed.connect(self.edit_exposure)
        self.exposure_edit.setText(f'{int(self.cam.cam.ExposureTime)/1000} ms')

        self.exposure_push.setEnabled(True)
        self.exposure_push.clicked.connect(self.auto_expose)

        self.fr_edit.setText(f'{self.cam.framerate}')
        self.fr_edit.returnPressed.connect(self.change_framerate)

        self.hist = self.preview.getHistogramWidget()
        self.hist.sigLevelsChanged.connect(self.lev_changed)

        self.levels = [0,255]

        self.preview_toggle.stateChanged.connect(self.toggle_preview)
        self.toggle_preview()

        self.resizeEvent(None)

    def init_cam(self):
        if self.cam is not None:
            self.cam.close()
        self.cam = FlirCam(serial_number=0) # TODO

    def start(self, record=False):
        if self.status != Status.STANDBY:
            utils.message_window("Error", "Currently recording or previewing.")
        self.fn_preview = 0
        self.timer.start()
        self.cam.start()
        if record:
            self.cam.start_rec()
            self.status = Status.RECORDING
        else:
            self.cam.start_preview()
            self.status = Status.PREVIEWING
        self.update_ui()

    def stop(self):
        if self.status == Status.STANDBY:
            utils.message_window("Error", "Already on standby.")
        self.timer.stop()
        if self.status == Status.RECORDING:
            self.cam.stop_rec()
        elif self.status == Status.PREVIEWING:
            self.cam.stop_preview()
        self.cam.stop()
        self.status = Status.STANDBY
        self.update_ui()

    def change_framerate(self):
        new_fr = self.fr_edit.text()
        new_fr = int(new_fr)
        
        self.cam.set_cam_attr('AcquisitionFrameRate', new_fr)
        print('Changed fr')

    def set_write_path(self, dir, file_name=None):
        self.timer.stop()
        if file_name is None:
            file_name = f'cam_{self.cam.serial_number}.mp4'
        self.cam.set_video_out_path(os.path.join(dir, file_name))

    # def load_attrs(self):
    #     self.attrs_json_path,_ = QFileDialog.getOpenFileName(self, "Open json file", filter="JSON files (*.json)")
    #     print(self.attrs_json_path)
    #     self.cam.set_cam_attrs_from_json(self.attrs_json_path, n_repeat=3)

    def toggle_preview(self):
        self.preview_on = self.preview_toggle.isChecked()

    def toggle_trigger(self):
        self.cam.cam.TriggerMode = 'On' if self.trigger_toggle.isChecked() else 'Off'

    def edit_gain(self):
        gain_txt = self.gain_edit.text()
        if gain_txt.lower()=='auto':
            self.cam.cam.GainAuto = 'Continuous'
            self.gain_edit.setText('Auto')
        elif gain_txt.isnumeric():
            self.cam.cam.GainAuto = 'Off'
            self.cam.cam.Gain = float(gain_txt)
            self.gain_edit.setText(f'{self.cam.cam.Gain:.2f}')
        else:
            self.gain_edit.setText(f'{self.cam.cam.Gain:.2f}')
    
    def auto_expose(self):
        self.cam.set_cam_attr('ExposureAuto', 'Once')
        self.exposure_edit.setText(f'{float(self.cam.cam.ExposureTime)/1000:.3f} ms')

    def edit_exposure(self):
        exposure_txt = self.exposure_edit.text()

        if exposure_txt.isnumeric():
            new_exposure = float(exposure_txt*1000)
            print(new_exposure)
            self.cam.set_cam_attr('ExposureAuto', 'Off')
            self.cam.set_cam_attr('ExposureTime', new_exposure)
            self.exposure_edit.setText(f'{float(self.cam.cam.ExposureTime)/1000:.3f} ms')
        else:
            self.exposure_edit.setText(f'{float(self.cam.cam.ExposureTime)/1000:.3f} ms')

    def lev_changed(self):
        levels = self.hist.getLevels()
        min_level = max(levels[0], 0)
        max_level = min(levels[1], 255)
        self.levels = (min_level, max_level)
        self.hist.setLevels(min_level, max_level)

    def preview_updater(self):
        if self.preview_on and self.cam.fn > self.fn_preview:
            self.preview.clear()
            self.preview.setImage(self.cam.frame.T, autoLevels=False, levels=self.levels, autoHistogramRange=False)
            self.preview.setLevels(self.levels[0],self.levels[1])
            self.fn_preview = self.cam.fn

    def resizeEvent(self, event):
        frame_size = self.frameGeometry()
        frame_width = frame_size.width ()
        frame_height = frame_size.height()

        preview_width = frame_width-240
        preview_height = frame_height-60
        
        self.preview.setGeometry(QtCore.QRect(10, 10, preview_width, preview_height))
        self.control_frame.setGeometry(QtCore.QRect(preview_width+20, 10, self.control_frame.width(), preview_height))

        QtWidgets.QFrame.resizeEvent(self, event)
        
    def update_ui(self):
        if self.status == Status.RECORDING: # If recording...
            pass
        elif self.status == Status.PREVIEWING: # If previewing...
            pass
        elif self.status == Status.STANDBY: # If standby...
            pass
        else:
            utils.message_window(text="Invalid status.")

    def closeEvent(self, event): # do not change name, super override
        if self.status == Status.RECORDING: # If recording...
            event.ignore()
        elif self.status == Status.PREVIEWING: # If previewing...
            event.ignore()
        elif self.status == Status.STANDBY: # If standby...
            self.cam.close()
            self.parent.child_close_event(self.barcode)
        else:
            utils.message_window(text="Invalid status.")

        # if self.status != Status.STANDBY:
        #     self.stop()
        # self.cam.close()
        # self.parent.child_close_event(self.barcode)

def main():
    app = QApplication(sys.argv)
    form = CamUI()
    form.show()
    app.exec_()

if __name__ == '__main__':
    main()
