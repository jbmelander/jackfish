import os
import matplotlib.pyplot as plt
import queue, threading
import matplotlib.pyplot as plt
import time
import numpy as np
import cv2
import json
from simple_pyspin import Camera

class JFCam:
    def __init__(self, cam_index=0, attrs_json_fn=None, video_out_path=None):
        '''
        cam_index: int or str (defalult: 0) If an int, the index of the camera to acquire. If a string, the serial number of the camera.
        '''
        self.cam = Camera(index=cam_index)
        self.cam.init()
        self.serial_number = self.get_cam_serial_number()
        if attrs_json_fn is not None:
            self.set_cam_attrs_from_json(attrs_json_fn, n_repeat=3)

        self.set_video_out_path(video_out_path)

        self.start()
        self.get_img_dtype()
        self.get_img_dimensions()
        self.get_img_framerate()
        self.stop()

        assert self.dtype[-1] == '8', 'Data should be in proper bit depth'
        
        self.video_out_path = None

    def get_cam_serial_number(self):
        cam = self.cam
        serial_number_candidates = [x for x in cam.camera_attributes.keys() if "serialnumber" in x.lower()]
        if len(serial_number_candidates) != 1:
            print(f'Found {len(serial_number_candidates)} serial number candidates.')
            return None
        else:
            serial_number = cam.__getattr__(serial_number_candidates[0])
            return serial_number


    # def gen_cam_attrs_json(self):
    #     cam = self.cam

    #     attrs_dict = {}
    #     for k in cam.camera_attributes.keys():
    #         print(k)
    #         if 'power' not in k.lower() and 'pwr' not in k.lower():
    #             access_info = cam.get_info(k)['access']
    #             if isinstance(access_info, str) and 'read' in access_info:
    #                 attrs_dict[k] = cam.get_info(k)['value']

    #     out_fn = f"{self.serial_number}_attrs.json" if self.serial_number is not None else "cam_attrs.json"
    #     with open(out_fn, "w") as outfile:
    #         json.dump(attrs_dict, outfile)

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
        for _ in range(n_repeat):
            for (k,v) in attrs_dict.items():
                attr_value_result = self.set_cam_attr(k, v)

    def set_cam_attr(self, attr_name, attr_val):
        cam = self.cam

        print(f'Trying to write {attr_name}...')

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
        return cam.__getattr__(attr_name)

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
            path = os.path.expanduser(f'~/{self.serial_number}_test.mp4')
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

