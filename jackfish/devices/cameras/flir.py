import os
import queue, threading
import numpy as np
import matplotlib.pyplot as plt
import time
import cv2
import json
from simple_pyspin import Camera

class FlirCam:
    def __init__(self, serial_number=0, attrs_json_fn=None):
        '''
        serial_number: int or str (defalult: 0) If an int, the index of the camera to acquire. If a string, the serial number of the camera.
        '''
        self.cam = Camera(index=serial_number)
        self.cam.init()
        self.serial_number = self.get_cam_serial_number()
        self.release_trigger_on_start = False
        self.release_trigger_delay = 0
        self.restore_trigger_mode_on_stop = False

        if attrs_json_fn is not None:
            self.set_cam_attrs_from_json(attrs_json_fn, n_repeat=3)

        self.start(release_trigger_mode=False)
        self.get_img_dtype()
        self.get_img_dimensions()
        self.get_img_framerate()
        self.stop()



        assert self.dtype[-1] == '8', 'Data should be in proper bit depth'
        
        self.video_out_path = None
        self.t = time.time()

    def get_cam_serial_number(self):
        cam = self.cam
        serial_number_candidates = [x for x in cam.camera_attributes.keys() if "serialnumber" in x.lower()]
        if len(serial_number_candidates) != 1:
            print(f'Found {len(serial_number_candidates)} serial number candidates.')
            return None
        else:
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

    def get_img_framerate(self):
        if self.cam.__getattr__('TriggerMode') == 'On':
            self.set_cam_attr('TriggerMode', 'Off')
            self.framerate = self.cam.__getattr__('AcquisitionFrameRate')
            self.set_cam_attr('TriggerMode', 'On')
        else:
            self.framerate = self.cam.__getattr__('AcquisitionFrameRate')

    def get_img_dimensions(self):
        # Reversed from numpy convension
        self.x = self.cam.__getattr__('Width')
        self.y = self.cam.__getattr__('Height')

    def get_img_dtype(self):
        self.dtype = self.cam.__getattr__('PixelFormat')
    
    def set_video_out_path(self, path=None):
        if path is None:
            path = os.path.expanduser(f'~/cam_{self.serial_number}.mp4')
        self.video_out_path = path
        print(f"Cam video out path: {self.video_out_path}")

    def grab_frame(self, wait=True):
        self.frame = self.cam.get_array(wait=wait)
        self.fn+=1

    def start_preview(self):
        def preview_callback():
            while self.do_preview:
                self.grab_frame()

        self.fn = 0
        self.do_preview = True
        self.preview_thread = threading.Thread(target=preview_callback, daemon=True).start()
        print("Camera preview started.")

    def stop_preview(self):
        self.do_preview = False
        print("Camera preview ended.")

    def start_rec(self):
        def rec_callback():
            while self.do_record:
                self.grab_frame()
                self.img_queue.put(self.frame)

        def rec_writer():
            print('worker started')
            while self.do_record:
                frame = self.img_queue.get(block=True)

                frame_color = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                self.writer.write(frame_color)
                
        self.img_queue = queue.Queue()
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(self.video_out_path, fourcc, int(self.framerate), (self.x, self.y))

        self.fn = 0
        self.do_record = True
        self.record_thread = threading.Thread(target=rec_callback, daemon=True).start()
        self.writer_thread = threading.Thread(target=rec_writer, daemon=True).start()
        print("Camera record started.")
    
    def stop_rec(self):
        self.do_record = False
        time.sleep(2) # give rec_callback time to finish writing frame
        self.writer.release()
        print("Camera record finished.")

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


