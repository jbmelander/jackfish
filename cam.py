import tkinter as tk
import queue, threading
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
import time
import numpy as np
import cv2
from simple_pyspin import Camera

class FJCam:
    def __init__(self):
        self.cam = Camera()

        self.atts = {}

        self.x, self.y = self.get_img_dimensions()
        self.framerate = self.get_img_framerate()
        self.cam.VideoMode = "Mode0"
        self.cam.Width = cam.SensorWidth // 2
        self.cam.Height = cam.SensorHeight // 2
        self.cam.OffsetX = cam.SensorWidth // 4
        self.cam.OffsetY = cam.SensorHeight // 4
        self.cam.AcquisitionFrameRateEnabled = True
        self.cam.AcquisitionFrameRateAuto = 'Off'
        self.cam.AcquisitionFrameRate=20
        self.cam.ExposureMode = 'Timed'
        self.cam.ExposureAuto = 'Continuous'

        self.cam.LineSelector = 'Line1'
        self.cam.LineMode = 'Strobe'
        self.cam.StrobeEnabled = True
        self.cam.StrobeDuration = 3000  # microseconds
        self.cam.start()

    def grab(self):
        return self.cam.get_array()

    def set_att(self,att,val):
        self.cam.__setattr__(att,val)

    def get_img_framerate(self)(self):
        # Reversed from numpy convension
        self.framerate = self.cam.__getattr__('AcquisitionFrameRate')

    def get_img_dimensions(self):
        # Reversed from numpy convension
        self.x = self.cam.__getattr__('Width')
        self.y = self.cam.__getattr__('Height')

    def get_img_dtype(self):
        self.dtype = self.cam.__getattr__('PixelFormat')
            
# def init_writer(savepath,framerate,img_shape,codecs='mp4v'):
#     fourcc = cv2.VideoWriter_fourcc(*codecs)
#     writer=cv2.VideoWriter(savepath,fourcc,framerate,img_shape)
#     return writer

# class FJWriter:
#     def __init__(self,savepath,framerate,img_shape,codecs='mp4v'):
#         self.kill = False

#         self.writer = init_writer(savepath,framerate,img_shape,codecs)
        
#         self.image_queue = queue.Queue()
#         self.write_thread = threading.Thread(target=self.write)
#         self.write_thread.start()

#     def write(self):
#         while not self.kill:
#             deq = self.image_queue.get()
#             if deq is None:
#                 print('Empty')
#                 break
#             else:
#                 frame_color = cv2.cvtColor(deq,cv2.COLOR_GRAY2BGR)
#                 self.writer.write(frame_color)
#                 self.image_queue.task_done()
