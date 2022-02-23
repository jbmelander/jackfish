import matplotlib.pyplot as plt
import time
import numpy as np
import cv2
from simple_pyspin import Camera


def get_img_dimensions():
    # Reversed from numpy convension
    with Camera() as cam:
        width = cam.__getattr__('Width')
        height = cam.__getattr__('Height')
        return width, height

def get_img_framerate():
    with Camera() as cam:
        framerate = cam.__getattr__('AcquisitionFrameRate')
        return framerate

def get_img_dtype():
    with Camera() as cam:
        dtype = cam.__getattr__('PixelFormat')
        return dtype

def init_writer(savepath,framerate,img_shape,codecs='mp4v'):
    fourcc = cv2.VideoWriter_fourcc(*codecs)
    writer=cv2.VideoWriter(savepath,fourcc,framerate,img_shape)
    return writer

def movie_qc(savepath):
    cap = cv2.VideoCapture(savepath)

if __name__ == '__main__':

    with Camera() as cam:
        # Set a custom Video Mode
        cam.VideoMode = "Mode0"
        cam.Width = cam.SensorWidth // 8
        cam.Height = cam.SensorHeight // 8
        cam.OffsetX = cam.SensorWidth // 4
        cam.OffsetY = cam.SensorHeight // 4
        cam.start()
        
        # Width and height throttle framerate
        cam.AcquisitionFrameRateEnabled = True
        cam.AcquisitionFrameRateAuto= 'Off'
        cam.AcquisitionFrameRate=500

        width,height = get_img_dimensions()
        framerate = get_img_framerate()    
        dtype = get_img_dtype()
        print(framerate)
        
        assert dtype[-1] == '8', 'Data should be in proper bit depth'

        savepath= '/home/baccuslab/rectest.mp4'
        writer = init_writer(savepath,framerate,(width,height))
        ts = []

        for i in range(int(framerate)*3):
            frame = cam.get_array()
            frame_color = cv2.cvtColor(frame,cv2.COLOR_GRAY2BGR)
            writer.write(frame_color)
            ts.append(time.time())
        cam.stop()
    writer.release()
    
    ts = np.array(ts)
    plt.plot(1/np.diff(ts))
    plt.title(ts[-1]-ts[0])
    plt.show()

    movie_qc(savepath)
