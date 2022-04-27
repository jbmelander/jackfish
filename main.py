import numpy as np
import time
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QApplication, QFileDialog
from PyQt5.QtGui import QPixmap, QImage
import cv2
from functools import partial
import sys
import gui

cap = cv2.VideoCapture(0)
class FLUI(QtWidgets.QMainWindow, gui.Ui_MainWindow):
    def __init__(self, parent=None):
        super(FLUI, self).__init__(parent)
        self.setupUi(self)
        

        self.set_path_push.clicked.connect(self.set_path)

        self.data = [0]
        self.curve = self.lj_prev.getPlotItem().plot()
        self.curve.setData(self.data)
        self.lj_prev.show()

        self.cam_timer = QtCore.QTimer()
        self.cam_timer.timeout.connect(self.cam_updater)
        self.lj_timer = QtCore.QTimer()
        self.lj_timer.timeout.connect(self.lj_updater)

        self.cam_timer.start()
        self.lj_timer.start()

    def set_path(self):
        self.cam_timer.stop()
        self.lj_timer.stop()
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getSaveFileName(self,"QFileDialog.getOpenFileName()", "","All Files (*)", options=options)
        if fileName:
            print(fileName)

        self.filepath = fileName
        self.filepath_label.setText(self.filepath)
        self.cam_timer.start()
        self.lj_timer.start()

    def cam_updater(self):
        self.cam_prev.clear()
        ret, frame = cap.read()
        self.frame = frame.mean(2).T
        self.cam_prev.setImage(self.frame)

    def lj_updater(self):
        self.data = np.append(self.data,np.random.randn(2))
        self.curve.setData(self.data)
        self.lj_prev.show()         

def main():
    app = QApplication(sys.argv)
    form = FLUI()
    form.show()
    app.exec_()


if __name__ == '__main__':
    main()
