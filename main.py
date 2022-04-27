import numpy as np
import time
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPixmap, QImage
import cv2
from functools import partial
import sys
import core

cap = cv2.VideoCapture(0)
class FLUI(QtWidgets.QMainWindow, core.Ui_MainWindow):
    def __init__(self, parent=None):
        super(FLUI, self).__init__(parent)
        self.setupUi(self)
        
        self.cams = []
        self.init_cam0_push.clicked.connect(partial(self.init_cam,0))
        self.init_cam1_push.clicked.connect(partial(self.init_cam,1))
        self.init_lj_push.clicked.connect(self.init_lj)

    def init_cam(self,num):
        ret, frame = cap.read()
        frame = frame.mean(2).T
        self.cam_prev.setImage(frame)
        self.cam_prev.show()
        # frame = np.array(frame,dtype='uint8')
        # img = QImage(frame,frame.shape[1], frame.shape[0],QImage.Format_RGB888)
        # self.img.setPixmap(QPixmap.fromImage(img))
    def init_lj(self):
        self.lj_plot_1.clear()
        x = np.arange(0,100)
        y = np.random.randn(100)

        self.lj_plot_1.plot(x,y)
        self.lj_plot_1.setXRange(0,100)
        self.lj_plot_1.setYRange(-5,5)



def main():
    app = QApplication(sys.argv)
    form = FLUI()
    form.show()
    app.exec_()


if __name__ == '__main__':
    main()
