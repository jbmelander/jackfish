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
        
        if 'DeviceSerialNumber' in list(self.cam.camera_attributes.keys()):
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
                self.cam.Gain = 25.0

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

    def grab_frame(self):
        try:
            self.frame = self.cam.get_array(wait=False)
            # print('after grab')
            return 0 #success
        except:
            return 1 #fail

    def start_preview(self):
        self.fn = 0
        self.do_preview = True
        self.preview_thread = threading.Thread(target=self.preview_callback, daemon=True).start()

    def preview_callback(self):
        while self.do_preview:
            if self.grab_frame() == 0:
                self.fn += 1

    def stop_preview(self):
        self.do_preview = False
        print("Preview finished.")

    def start_rec(self):
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(self.video_out_path, fourcc, int(self.framerate), (self.x, self.y))

        self.fn = 0
        self.do_record = True
        self.record_thread = threading.Thread(target=self.rec_callback, daemon=True).start()

    def rec_callback(self):
        while self.do_record:
            if self.grab_frame() == 0:
                frame_color = cv2.cvtColor(self.frame, cv2.COLOR_GRAY2BGR)
                self.writer.write(frame_color)
                self.fn += 1
                # print(self.fn)
    
    def stop_rec(self):
        self.do_record = False
        time.sleep(2) # give rec_callback time to finish writing frame
        self.writer.release()
        print("Recording finished.")

    def close(self):
        self.cam.close()

