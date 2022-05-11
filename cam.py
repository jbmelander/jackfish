import os
import matplotlib.pyplot as plt
import queue, threading
import matplotlib.pyplot as plt
import time
import numpy as np
import cv2
from simple_pyspin import Camera

class FJCam:
    def __init__(self, cam_index=1, video_out_path=None):
        self.cam = Camera(index=cam_index)
        self.cam.init()
        self.atts = {}

        self.set_video_out_path(video_out_path)
        
        if 'DeviceSerialNumber' in list(self.cam.__dir__()):
            if self.cam.DeviceSerialNumber == '20243355': # 40hr Side camera
                print('Initializing side cam')
                self.cam.PixelFormat = 'Mono8'

                self.cam.BinningHorizontal = 2
                self.cam.BinningVertical = 2

                self.cam.ExposureMode = 'Timed'
                self.cam.ExposureAuto = 'Off'
                self.cam.ExposureTime = 3200.0 # Resulting frame rate ~300

                self.cam.Width = self.cam.WidthMax
                self.cam.Height = self.cam.HeightMax

                self.cam.LineSelector = 'Line1' #FIO2
                self.cam.LineMode = 'Output'
                self.cam.LineSource = 'ExposureActive'

                self.cam.GainAuto = 'Off'
                self.cam.Gain = 38.0

                self.cam.GammaEnable = False

                self.cam.TriggerSelector = 'AcquisitionStart'
                self.cam.TriggerMode = 'On'
                self.cam.TriggerSource = 'Line0'  #FIO3
                self.cam.TriggerActivation = 'RisingEdge'

                self.cam.AcquisitionFrameRateEnable = True
                self.cam.AcquisitionFrameRate = 350.0
        
            elif self.cam.DeviceSerialNumber == '20243354': # 40hr Top camera
                print('Initializing top cam')
                self.cam.PixelFormat = 'Mono8'

                self.cam.BinningHorizontal = 4
                self.cam.BinningVertical = 4

                self.cam.ExposureMode = 'Timed'
                self.cam.ExposureAuto = 'Off'
                self.cam.ExposureTime = 3200.0 # Resulting frame rate ~300

                self.cam.Width = self.cam.WidthMax
                self.cam.Height = self.cam.HeightMax

                self.cam.LineSelector = 'Line1' #FIO0
                self.cam.LineMode = 'Output'
                self.cam.LineSource = 'ExposureActive'

                self.cam.GainAuto = 'Off'
                self.cam.Gain = 30.0

                self.cam.GammaEnable = False

                self.cam.TriggerSelector = 'AcquisitionStart'
                self.cam.TriggerMode = 'On'
                self.cam.TriggerSource = 'Line0' #FIO1
                self.cam.TriggerActivation = 'RisingEdge'

                self.cam.AcquisitionFrameRateEnable = True
                self.cam.AcquisitionFrameRate = 350.0

        else: # Josh camera
            print('Initializing Josh cam')
            self.cam.PixelFormat = 'Mono8'
            self.cam.VideoMode = "Mode1"
            # self.cam.Width = self.cam.SensorWidth // 2
            # self.cam.Height = self.cam.SensorHeight // 2
            # self.cam.OffsetX = self.cam.SensorWidth // 4
            # self.cam.OffsetY = self.cam.SensorHeight // 4
            self.cam.AcquisitionFrameRateEnabled = True
            # self.cam.AcquisitionFrameRateAuto = 'On'
            self.cam.AcquisitionFrameRate=10
            self.cam.ExposureMode = 'Timed'
            self.cam.ExposureAuto = 'Continuous'

            self.cam.LineSelector = 'Line1'
            self.cam.LineMode = 'Strobe'
            self.cam.StrobeEnabled = True
            self.cam.StrobeDuration = 3000  # microseconds

        self.start()
        self.get_img_dtype()
        self.get_img_dimensions()
        self.get_img_framerate()
        self.stop()

        assert self.dtype[-1] == '8', 'Data should be in proper bit depth'
        
        self.video_out_path = None

    def start(self):
        self.cam.start()

    def stop(self):
        self.cam.stop()

    def grab(self, wait=True):
        return self.cam.get_array(wait=wait).T

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
    
    def set_video_out_path(self, path=None):
        if path is None:
            path = os.path.expanduser('~/test.mp4')
        self.video_out_path = path
        print(path)

    def start_rec(self):
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(self.video_out_path, fourcc, int(self.framerate), (self.x, self.y))

        self.fn = 0
        self.do_record = True
        self.record_thread = threading.Thread(target=self.rec_callback, daemon=True).start()

    def rec_callback(self):
        while self.do_record:
            try:
                frame = self.cam.get_array(wait=False)
                frame_color = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                self.writer.write(frame_color)
                self.fn += 1
                # print(self.fn)
            except:
                # print('No frame acquired')
                pass

    def stop_rec(self):
        self.do_record = False
        self.writer.release()
        print("Recording finished.")




    def init_writer(self):
        fourcc = cv2.VideoWriter_fourcc(*'MP4V')
        writer=cv2.VideoWriter(self.video_out_path,fourcc,self.framerate,(self.x,self.y))
        self.writer = writer
    
    def rec(self, wait=True):
        self.fn = 0
        self.init_writer()

        self.image_queue = queue.Queue()
        self.write_thread = threading.Thread(target=self.write,daemon=True).start()
        
        while self.do_record:
            frame = self.cam.get_array(wait=wait)
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
    
    def close(self):
        self.cam.close()

