import tkinter as tk
import queue, threading
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
import time
import numpy as np
import cv2
from simple_pyspin import Camera


def get_img_dimensions(cam):
    # Reversed from numpy convension
    width = cam.__getattr__('Width')
    height = cam.__getattr__('Height')
    return width, height

def get_img_framerate(cam):
    framerate = cam.__getattr__('AcquisitionFrameRate')
    return framerate

def get_img_dtype(cam):
    dtype = cam.__getattr__('PixelFormat')
    return dtype

def init_writer(savepath,framerate,img_shape,codecs='mp4v'):
    fourcc = cv2.VideoWriter_fourcc(*codecs)
    writer=cv2.VideoWriter(savepath,fourcc,framerate,img_shape)
    return writer

class FJWriter:
    def __init__(self,savepath,framerate,img_shape,codecs='mp4v'):
        self.kill = False

        self.writer = init_writer(savepath,framerate,img_shape,codecs)
        
        self.image_queue = queue.Queue()
        self.write_thread = threading.Thread(target=self.write)
        self.write_thread.start()

    def write(self):
        while not self.kill:
            deq = self.image_queue.get()
            if deq is None:
                print('Empty')
                break
            else:
                frame_color = cv2.cvtColor(deq,cv2.COLOR_GRAY2BGR)
                self.writer.write(frame_color)
                self.image_queue.task_done()
