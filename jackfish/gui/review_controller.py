import sys
import os
import time
import json
import numpy as np

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QApplication, QFileDialog

from review_gui import Ui_ReviewUI

from jackfish import utils
from jackfish.utils import Status

class REVUI(QtWidgets.QFrame, Ui_ReviewUI):
    def __init__(self,parent=None):
        super(REVUI, self).__init__(None)
        self.setupUi(self)
        self.parent=parent

        self.load_data_push.clicked.connect(self.load_data)
        self.dropdown_one.currentIndexChanged.connect(self.update_indx)
        self.dropdown_two.currentIndexChanged.connect(self.update_indx)
        self.dropdown_three.currentIndexChanged.connect(self.update_indx)

        self.start_sec_edit.returnPressed.connect(self.update_indx)
        self.end_sec_edit.returnPressed.connect(self.update_indx)
        
        self.dropdowns = [self.dropdown_one, self.dropdown_two, self.dropdown_three]

        self.main_plot = self.plot_one
        self.PI = self.main_plot.getPlotItem()
        self.PI.getViewBox().setBackgroundColor([240, 240, 240])
        
        self.norm_check.stateChanged.connect(self.update_indx)
    
    def normalize(self,signal):
        """ Takes a vector and squashes values between 0 and 1 """
        lo = signal.min()
        signal = signal -  lo
        hi = signal.max()
        signal = signal / hi
        return signal


    def update_indx(self):
        indxs = []
        for dropdown in self.dropdowns:
            indx = dropdown.currentIndex()
            indxs.append(indx)
        
        start_samples = int(float(self.start_sec_edit.text())*self.sample_rate)
        end_samples = int(float(self.end_sec_edit.text())*self.sample_rate)
        
        if self.norm_check.checkState()==2:
            self.plot_data = [self.normalize(self.daq_data[start_samples:end_samples,i]) for i in indxs]

        if self.norm_check.checkState()==0:
            self.plot_data = [self.daq_data[start_samples:end_samples,i] for i in indxs]
        
        self.main_plot.clear()

        cols = []
        cols.append([20,60,200])
        cols.append([60,100,60])
        cols.append([200,20,60])
        for i in range(3):
            self.main_plot.plot(self.plot_data[i], pen=cols[i])

        del self.plot_data




    def load_data(self):
        json_fn, _ = QFileDialog.getOpenFileName(self, "Select preset json file.", os.path.expanduser('~'))
        if json_fn == "":
            return
        else:

            self.data_path = json_fn
            
            with open(self.data_path,'r') as f:
                self.meta = json.loads(f.readline())

            dir_path, filename = os.path.split(self.data_path)
            filename = os.path.splitext(filename)[0]
            numpy_filename = filename + '.npy'
            if os.path.exists(os.path.join(dir_path,numpy_filename)):
                self.daq_data = np.load(os.path.join(dir_path,numpy_filename))
                pass
            else:
                temp = []
                with open(self.data_path,'r') as f:
                    for i, line in enumerate(f):
                        if i==0:
                            self.meta = json.loads(line)
                        else:
                            line_arr = [float(z) for z in line.split()]
                            temp.append(line_arr)
                temp = np.array(temp)
                np.save(os.path.join(dir_path,numpy_filename), temp)

                self.daq_data = temp
        
        print(self.meta.keys())
        self.channels = self.meta['input_channels']
        self.sample_rate = float(self.meta['scan_rate'])
        
        print(self.sample_rate)
        for chan, nickname in self.channels.items():
            [dropdown.addItem(nickname) for dropdown in self.dropdowns]

        [dropdown.setCurrentIndex(0) for dropdown in self.dropdowns]



def main():
    # app = QApplication(sys.argv)
    form = REVUI()
    form.show()
    # app.exec_()

if __name__ == '__main__':
    main()
