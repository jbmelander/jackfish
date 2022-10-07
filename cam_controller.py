import sys
import os

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QApplication, QFileDialog

from cam import JFCam
from cam_gui import Ui_CamWindow

class CamUI(QtWidgets.QFrame, Ui_CamWindow):
    def __init__(self, cam_index=0, attrs_json_path=None, parent=None, barcode=None):
        super(CamUI, self).__init__(None)
        self.setupUi(self)

        self.parent = parent
        self.barcode = barcode

        self.attrs_json_path = attrs_json_path

        self.cam = JFCam(cam_index=cam_index, attrs_json_fn=attrs_json_path)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.preview_updater)

        self.fn_prev = 0

        self.init_push.setCheckable(True)
        self.init_push.clicked.connect(self.init_cam)
        self.load_attrs_push.setCheckable(True)
        self.load_attrs_push.clicked.connect(self.load_attrs)

        self.trigger_toggle.stateChanged.connect(self.toggle_trigger)
        self.trigger_toggle.setChecked(self.cam.cam.TriggerMode == 'On')

        self.gain_edit.editingFinished.connect(self.edit_gain)
        self.gain_edit.setText('Auto' if self.cam.cam.GainAuto == 'Continuous' else f'{self.cam.cam.Gain:.2f}')

        self.exposure_edit.editingFinished.connect(self.edit_exposure)
        self.exposure_edit.setText('Auto' if self.cam.cam.ExposureAuto == 'Continuous' else f'{self.cam.cam.ExposureTime:.2f}')

        self.hist = self.preview.getHistogramWidget()
        self.hist.sigLevelsChanged.connect(self.lev_changed)

        self.levels = [0,255]

        self.preview_toggle.stateChanged.connect(self.toggle_preview)
        self.toggle_preview()

    def init_cam(self):
        if self.cam is not None:
            self.cam.close()
        self.cam = JFCam(cam_index=0) # TODO

    def start(self, record=False):
        self.fn_preview = 0
        self.timer.start()
        self.cam.start()
        if record:
            self.cam.start_rec()
        else:
            self.cam.start_preview()

    def stop(self, record=False):
        self.timer.stop()
        if record:
            self.cam.stop_rec()
        else:
            self.cam.stop_preview()
        self.cam.stop()

    def set_video_out_path(self, dir, file_name=None):
        self.timer.stop()
        if file_name is None:
            file_name = f'cam_{self.cam.serial_number}.mp4'
        self.cam.set_video_out_path(os.path.join(dir, file_name))

    def load_attrs(self):
        self.attrs_json_path = QFileDialog.getOpenFileName(self, "Open json file", filter="JSON files (*.json)")
        self.cam.set_cam_attrs_from_json(self.attrs_json_path, n_repeat=3)

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

    def edit_exposure(self):
        exposure_txt = self.exposure_edit.text()
        if exposure_txt.lower()=='auto':
            self.cam.cam.ExposureAuto = 'Continuous'
            self.exposure_edit.setText('Auto')
        elif exposure_txt.isnumeric():
            self.cam.cam.ExposureAuto = 'Off'
            self.cam.cam.ExposureTime = float(exposure_txt)
            self.exposure_edit.setText(f'{self.cam.cam.ExposureTime:.2f}')
        else:
            self.exposure_edit.setText(f'{self.cam.cam.ExposureTime:.2f}')

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

    def closeEvent(self, event): # do not change name, super override
        self.cam.close()
        if self.barcode is not None:
            self.parent.camUIs.pop(self.barcode)

def main():
    app = QApplication(sys.argv)
    form = CamUI()
    form.show()
    app.exec_()

if __name__ == '__main__':
    main()
