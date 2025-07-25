import os
import queue, threading
import warnings
import numpy as np
import matplotlib.pyplot as plt
import time
# import cv2

from PyQt5.QtCore import QThread, pyqtSignal

import skvideo
import skvideo.io
import json
from simple_pyspin import Camera
import PySpin

class FlirCam(QThread):
    # custom signal that a new frame is available
    new_frame_signal = pyqtSignal(bool)

    def __init__(self, serial_number=0, attrs_json_fn=None, ffmpeg_location='/usr/bin'):
        '''
        serial_number: int or str (defalult: 0) If an int, the index of the camera to acquire. If a string, the serial number of the camera.
        '''
        self.cam = Camera(index=serial_number)
        self.cam.init()
        self.serial_number = self.get_cam_serial_number()
        self.release_trigger_on_start = False
        self.release_trigger_delay = 0
        self.restore_trigger_mode_on_stop = False
        self.writer_gpu = -1

        if ffmpeg_location is not None and os.path.exists(ffmpeg_location):
            skvideo.setFFmpegPath(ffmpeg_location)
        else:
            print(f'FFMPEG directory {ffmpeg_location} does not exist')

        if attrs_json_fn is not None:
            self.set_cam_attrs_from_json(attrs_json_fn, n_repeat=3)
        else:
            # Following lines are run in set_cam_attrs_from_json in above case.
            self.start(release_trigger_mode=False)
            self.dtype = self.get_img_dtype()
            self.x, self.y = self.get_img_dimensions()
            self.framerate = self.get_acquisition_framerate()
            self.stop()

        assert self.dtype[-1] == '8', 'Data should be in proper bit depth'
        
        self.video_out_path = None
        self.t = time.time()

    def get_cam_serial_number(self):
        cam = self.cam
        serial_number_candidates = [x for x in cam.camera_attributes.keys() if "serialnumber" in x.lower()]
        if len(serial_number_candidates) == 0:
            if 'DeviceID' in cam.camera_attributes.keys():
                print('Using DeviceID instead of SerialNumber.')
                return cam.__getattr__('DeviceID')
        elif len(serial_number_candidates) > 1:
            print(f'Found {len(serial_number_candidates)} serial number candidates; using first one.')
        
        serial_number = cam.__getattr__(serial_number_candidates[0])
        return serial_number

    def gen_cam_attrs_json(self):
        cam = self.cam

        attrs_dict = {}
        for k in cam.camera_attributes.keys():
            print(k)
            if 'power' not in k.lower() and 'pwr' not in k.lower():
                access_info = cam.get_info(k)['access']
                if isinstance(access_info, str) and 'read' in access_info:
                    attrs_dict[k] = cam.get_info(k)['value']

        out_fn = f"{self.serial_number}_attrs.json" if self.serial_number is not None else "cam_attrs.json"
        with open(out_fn, "w") as outfile:
            json.dump(attrs_dict, outfile)

    def gen_cam_doc(self):
        cam = self.cam
        with open(f'{self.serial_number}_doc.md', 'w') as f:
            f.write(cam.document())

    def set_cam_attrs_from_json(self, json_path, n_repeat=3):
        '''
        n_repeat: # of times to set the values, in case the first few passes don't set the values (e.g. dependence on other values)
        '''
        with open(json_path, 'r') as f:
            attrs_dict = json.load(f)
        
        # Change offsets to 0 to ensure that change in binning can occur
        self.set_cam_attr('OffsetX', 0)
        self.set_cam_attr('OffsetY', 0)

        if 'camera_attrs' in attrs_dict:
            cam_attrs = attrs_dict['camera_attrs']
            for _ in range(n_repeat):
                for (k,v) in cam_attrs.items():
                    attr_value_result = self.set_cam_attr(k, v)
        if 'control_attrs' in attrs_dict:
            control_attrs = attrs_dict['control_attrs']
            if 'ReleaseTriggerModeOnStart' in control_attrs and control_attrs['ReleaseTriggerModeOnStart']:
                self.release_trigger_on_start = True
            if 'ReleaseTriggerModeDelay' in control_attrs:
                self.release_trigger_delay = control_attrs['ReleaseTriggerModeDelay']
            if 'writer_gpu' in control_attrs:
                self.writer_gpu = control_attrs['writer_gpu']

        # Get key attributes from camera
        self.start(release_trigger_mode=False)
        self.dtype = self.get_img_dtype()
        self.x, self.y = self.get_img_dimensions()
        self.framerate = self.get_acquisition_framerate()
        self.stop()

    def get_cam_attr(self, attr_name):
        return self.cam.__getattr__(attr_name)

    def set_cam_attr(self, attr_name, attr_val):
        cam = self.cam

        print(f'Trying to write {attr_name}...')

        restore_trigger_mode = False
        if attr_name == 'AcquisitionFrameRate' and self.cam.__getattr__('TriggerMode') == 'On':
            print(f'Temporarily turning off TriggerMode to set AcquisitionFrameRate')
            self.set_cam_attr('TriggerMode', 'Off')
            restore_trigger_mode = True

        # check that attr_name is in cam.camera_attributes
        if attr_name not in cam.camera_attributes.keys():
            print('Attribute not in camera.')
            return
        
        attr_info = cam.get_info(attr_name)

        # check that attr_name can be set
        if 'write' not in attr_info['access']:
            print('Attribute is not writeable.')
            return

        # check that the node type is the type of attr_val
        # if attribute is of type enum, check that attr_val is valid
        if attr_info['type'] == 'enum':
            print(attr_val)
            print(attr_info['entries'])
            assert attr_val in attr_info['entries']
        elif attr_info['type'] == 'float':
            assert isinstance(attr_val, float)
        elif attr_info['type'] == 'int':
            assert isinstance(attr_val, int)
        elif attr_info['type'] == 'string':
            assert isinstance(attr_val, str)
        elif attr_info['type'] == 'bool':
            assert isinstance(attr_val, bool)
        elif attr_info['type'] == 'command':
            print('Attribute type command is unknown.')
            return
        else:
            print('Attribute type unknown.')
            return
        
        print('Setting attribute.')
        cam.__setattr__(attr_name, attr_val)

        if restore_trigger_mode:
            print(f'Restoring TriggerMode.')
            self.set_cam_attr('TriggerMode', 'On')

        return cam.__getattr__(attr_name)

    def start(self, release_trigger_mode=True):
        self.cam.start()
        if release_trigger_mode and self.release_trigger_on_start and self.cam.__getattr__('TriggerMode') == 'On':
            self.release_trigger_mode_after_delay()
            self.restore_trigger_mode_on_stop = True

    def release_trigger_mode_after_delay(self):
        def helper():
            time.sleep(self.release_trigger_delay)
            self.set_cam_attr('TriggerMode', 'Off')
        threading.Thread(target=helper, daemon=True).start()

    def stop(self):
        if self.cam.__getattr__('TriggerMode') == 'On':
            self.set_cam_attr('TriggerMode', 'Off')
            self.restore_trigger_mode_on_stop = True
        self.cam.stop()
        if self.restore_trigger_mode_on_stop:
            self.set_cam_attr('TriggerMode', 'On')
            self.restore_trigger_mode_on_stop = False

    def get_acquisition_framerate(self):
        framerate = None
        if 'AcquisitionResultingFrameRate' in self.cam.camera_attributes and PySpin.IsReadable(self.cam.camera_attributes['AcquisitionResultingFrameRate']):
            framerate = self.cam.__getattr__('AcquisitionResultingFrameRate')
        elif 'AcquisitionFrameRate' in self.cam.camera_attributes and PySpin.IsReadable(self.cam.camera_attributes['AcquisitionFrameRate']):
            framerate = self.cam.__getattr__('AcquisitionFrameRate')
        elif self.cam.__getattr__('TriggerMode') == 'On':
            self.set_cam_attr('TriggerMode', 'Off')
            if 'AcquisitionResultingFrameRate' in self.cam.camera_attributes and PySpin.IsReadable(self.cam.camera_attributes['AcquisitionResultingFrameRate']):
                framerate = self.cam.__getattr__('AcquisitionResultingFrameRate')
            elif 'AcquisitionFrameRate' in self.cam.camera_attributes and PySpin.IsReadable(self.cam.camera_attributes['AcquisitionFrameRate']):
                framerate = self.cam.__getattr__('AcquisitionFrameRate')
            else:
                warnings.warn('Could not find framerate attribute.')
            self.set_cam_attr('TriggerMode', 'On')
        else:
            warnings.warn('Could not find framerate attribute.')
        
        return framerate

    def get_img_dimensions(self):
        # Reversed from numpy convension
        x = self.cam.__getattr__('Width')
        y = self.cam.__getattr__('Height')
        return x, y

    def get_img_dtype(self):
        return self.cam.__getattr__('PixelFormat')
    
    def set_video_out_path(self, path=None):
        if path is None:
            path = os.path.expanduser(f'~/cam_{self.serial_number}.mp4')
        self.video_out_path = path
        print(f"Cam {str(self.serial_number)} video out path: {self.video_out_path}")

    def grab_frame(self, wait=True):
        try:
            # PySpin image contains information about the frame, such as timestamp, gain, exposure, etc.
            image = self.cam.get_image(wait=wait)

            frame_ts_cpu = time.time()            
            frame = image.GetNDArray()
            frame_ts = image.GetTimeStamp() / 1e9 # in seconds
            frame_num = self.frame_num + 1
            
            self.frame_num = frame_num
            self.frame = frame
            self.frame_ts = frame_ts

            # Emit the signal with the new QImage
            self.new_frame_signal.emit(True)

            return frame, frame_num, frame_ts, frame_ts_cpu
        
        except PySpin.SpinnakerException as e:
            # print(f'Error: {e}')
            print(f"Cam {str(self.serial_number)}: Awaiting frame...")
            return None

    def start_preview(self):
        def preview_callback():
            while self.do_preview:
                self.grab_frame()

        self.frame_num = 0
        self.do_preview = True
        self.preview_thread = threading.Thread(target=preview_callback, daemon=True).start()
        print(f"Cam {str(self.serial_number)}: Camera preview started.")

    def stop_preview(self):
        self.do_preview = False
        print(f"Cam {str(self.serial_number)}: Camera preview ended.")

    def start_rec(self, use_nvenc=False):
        def rec_callback():
            # Assume this loop is fast enough to keep up with framerate
            while self.do_record:
                # grab_frame() returns None if there is no frame to grab
                result = self.grab_frame()
                if result is not None:
                    frame, frame_num, frame_ts, frame_ts_cpu = result
                    self.img_queue.put((frame, frame_num, frame_ts, frame_ts_cpu))
                    self.total_frames_grabbed += 1
                else:
                    pass

            print(f"Cam {str(self.serial_number)}: Record thread completed.")

        def rec_writer():
            print(f"Cam {str(self.serial_number)}: writer started")
            while self.do_record or self.img_queue.qsize()>0:
                # If recording has ended and still writing, OR queue size is abnormally large (> 1000)
                if not self.do_record or self.img_queue.qsize() > 1000:
                    print(f"Cam {str(self.serial_number)}: Number of images remaining in queue: {self.img_queue.qsize()}")
                try:
                    # block=True is important for preventing the writer thread from taking too much
                    #    clock time away from other threads
                    frame, frame_num, frame_ts, frame_ts_cpu = self.img_queue.get(block=True, timeout=(1/self.framerate)*10)

                    # frame_color = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                    # self.video_writer.write(frame_color)
                    self.video_writer.writeFrame(frame)
                    self.frame_info_writer.write(f'{frame_num} {frame_ts} {frame_ts_cpu}\n')
                    self.total_frames_written += 1
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"Cam {str(self.serial_number)}: Unexpected exception {e} occurred in rec writer thread.")

            self.video_writer.close()
            self.frame_info_writer.close()
        
            print(f"Cam {str(self.serial_number)}: Writer thread completed.")
            print(f"Cam {str(self.serial_number)}: Total frames grabbed = {self.total_frames_grabbed}")
            print(f"Cam {str(self.serial_number)}: Total frames written = {self.total_frames_written}")

        self.total_frames_grabbed = 0
        self.total_frames_written = 0

        self.img_queue = queue.Queue()
        # fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        # self.video_writer = cv2.VideoWriter(self.video_out_path, fourcc, int(self.framerate), (self.x, self.y))
        self.video_writer = skvideo.io.FFmpegWriter(self.video_out_path, 
                                                    inputdict={'-framerate':str(int(self.framerate))}, 
                                                    outputdict={'-vcodec': 'h264_nvenc', '-tune': 'hq', '-gpu': str(self.writer_gpu)} if use_nvenc else {'-vcodec': 'libx264', '-tune': 'film'})
        self.frame_info_writer = open(self.video_out_path.replace('.mp4', '.txt'), 'w')

        self.frame_num = 0
        self.do_record = True
        self.record_thread = threading.Thread(target=rec_callback, daemon=True)
        self.writer_thread = threading.Thread(target=rec_writer, daemon=True)
        self.writer_thread.start()
        self.record_thread.start()
        print(f"Cam {str(self.serial_number)}: Camera record started.")
    
    def stop_rec(self):
        print(f"Cam {str(self.serial_number)}: Stopping camera record.")

        self.do_record = False

    def close(self):
        self.cam.close()

# t = time.time()
# cam = JFCam()
# cam.start()

# cam.start_rec()
# cam.do_record= True
# time.sleep(20)
# cam.do_record=False
# cam.stop_rec()
# cam.close()
# # cam.start_rec()
# # time.sleep(30)

# cam.stop_rec()


