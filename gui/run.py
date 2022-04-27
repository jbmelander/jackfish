from PyQt5 import QtCore, QtGui, QtWidgets
from functools import partial
from PyQt5.QtWidgets import QApplication
import sys
import core


class FLUI(QtWidgets.QMainWindow, core.Ui_MainWindow):
    def __init__(self, parent=None):
        super(FLUI, self).__init__(parent)
        self.setupUi(self)
        
        self.cams = []
        self.init_cam0_push.clicked.connect(partial(self.init_cam,0))
        self.init_cam1_push.clicked.connect(partial(self.init_cam,1))
        self.init_lj_push.clicked.connect(self.init_lj)

    def init_cam(self,num):
        pass
    def init_lj(self):
        pass



def main():
    app = QApplication(sys.argv)
    form = FLUI()
    form.show()
    app.exec_()


if __name__ == '__main__':
    main()
