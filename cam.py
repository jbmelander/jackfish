import os
import matplotlib.pyplot as plt
import queue, threading
import matplotlib.pyplot as plt
import time
import numpy as np
import cv2
from simple_pyspin import Camera

class FJCam:
    def __init__(self):
        self.mp4_path = os.path.expanduser('~/test.mp4')
        self.cam = Camera()
        self.cam.init()
        self.atts = {}

        self.cam.PixelFormat = 'Mono8'
        self.cam.VideoMode = "Mode1"
        # self.cam.Width = self.cam.SensorWidth // 2
        # self.cam.Height = self.cam.SensorHeight // 2
        # self.cam.OffsetX = self.cam.SensorWidth // 4
        # self.cam.OffsetY = self.cam.SensorHeight // 4
        # self.cam.AcquisitionFrameRateEnabled = True
        # self.cam.AcquisitionFrameRateAuto = 'On'
        # self.cam.AcquisitionFrameRate=
        self.cam.ExposureMode = 'Timed'
        self.cam.ExposureAuto = 'Continuous'

        self.cam.LineSelector = 'Line1'
        self.cam.LineMode = 'Strobe'
        self.cam.StrobeEnabled = True
        self.cam.StrobeDuration = 3000  # microseconds

        self.cam.start()
        self.get_img_dtype()
        self.get_img_dimensions()
        self.get_img_framerate()

        assert self.dtype[-1] == '8', 'Data should be in proper bit depth'
        
        self.mp4_path = None
        
    def grab(self):
        return self.cam.get_array().T

    def set_att(self,att,val):
        self.cam.__setattr__(att,val)

    def get_img_framerate(self):
        # Reversed from numpy convension
        self.framerate = self.cam.__getattr__('AcquisitionFrameRate')

    def get_img_dimensions(self):
        # Reversed from numpy convension
        self.x = self.cam.__getattr__('Width')
        self.y = self.cam.__getattr__('Height')

    def get_img_dtype(self):
        self.dtype = self.cam.__getattr__('PixelFormat')
    
    def init_writer(self):
        fourcc = cv2.VideoWriter_fourcc('M','P','4','V')
        writer=cv2.VideoWriter(self.mp4_path,fourcc,self.framerate,(self.x,self.y))
        self.writer = writer
    
    def rec(self):
        self.fn = 0
        self.init_writer()

        self.image_queue = queue.Queue()
        self.write_thread = threading.Thread(target=self.write,daemon=True).start()
        
        while self.do_record:
            frame = self.cam.get_array()
            print(frame.shape)
            print(self.x)
            print(self.y)
            self.image_queue.put(frame)

        self.image_queue.join()#
        self.writer.release()
        print('finished')

    def write(self):
        while True:
            deq = self.image_queue.get()
            self.fn += 1
            print(self.fn)
            frame_color = cv2.cvtColor(deq,cv2.COLOR_GRAY2BGR)
            self.writer.write(frame_color)
            self.image_queue.task_done()
    


