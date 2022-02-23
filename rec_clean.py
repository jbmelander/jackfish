import tkinter as tk
import queue, threading
from PIL import Image, ImageTk
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



if __name__ == '__main__':

    with Camera() as cam:
        # Set a custom Video Mode
        cam.VideoMode = "Mode0"
        cam.Width = cam.SensorWidth // 2
        cam.Height = cam.SensorHeight // 2
        cam.OffsetX = cam.SensorWidth // 4
        cam.OffsetY = cam.SensorHeight // 4

        window = tk.Tk()
        window.title("camera acquisition")
        window.geometry('1000x1000')

        textlbl = tk.Label(window, text="elapsed time: ")
        textlbl.grid(column=0, row=0)
        imglabel = tk.Label(window) # make Label widget to hold image
        imglabel.place(x=10, y=20) #pixels from top-left
        window.update() #update TCL tasks to make window appear
        #cam.Binning
        cam.start()
        
        # Width and height throttle framerate
        cam.AcquisitionFrameRateEnabled = True
        cam.AcquisitionFrameRateAuto= 'Off'
        cam.AcquisitionFrameRate=30

        width,height = get_img_dimensions()
        framerate = get_img_framerate()    
        dtype = get_img_dtype()
        
        assert dtype[-1] == '8', 'Data should be in proper bit depth'

        savepath= '/home/baccuslab/queuedUp.mp4'
        fjw = FJWriter(savepath,framerate,(width,height))
        tStart = time.time()
        

        for i in range(int(framerate)*60):
            frame = cam.get_array()
            fjw.image_queue.put(frame)

            if i%(framerate/10) == 0: #update screen every 10 frames 
                timeElapsed = str(time.time() - tStart)
                timeElapsedStr = "elapsed time: " + timeElapsed[0:5] + " sec"
                textlbl.configure(text=timeElapsedStr)
                I = ImageTk.PhotoImage(Image.fromarray(frame))
                imglabel.configure(image=I)
                imglabel.image = I #keep reference to image
                window.update() #update on screen (this must be called from main thread)

        fjw.kill=True


    fjw.image_queue.join()#
    fjw.write_thread.join()
    window.destroy()
