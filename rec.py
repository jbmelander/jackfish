from cam_utils import get_img_dimensions, get_img_framerate, get_img_dtype, FJWriter
import tkinter as tk
import queue
import threading
from simple_pyspin import Camera
import time
from PIL import Image, ImageTk

if __name__ == '__main__':
    with Camera() as cam:
        # Set a custom Video Mode
        cam.VideoMode = "Mode0"
        cam.Width = cam.SensorWidth // 2
        cam.Height = cam.SensorHeight // 2
        cam.OffsetX = cam.SensorWidth // 4
        cam.OffsetY = cam.SensorHeight // 4
        cam.AcquisitionFrameRateAuto = 'Off'
        cam.AcquisitionFrameRateEnabled = True
        cam.AcquisitionFrameRate=60
        cam.ExposureMode = 'Timed'
        cam.ExposureAuto = 'Continuous'
        

        cam.LineSelector = 'Line1'
        cam.LineMode = 'Strobe'


        window = tk.Tk()
        window.title("camera acquisition")
        window.geometry('1000x1000')

        textlbl = tk.Label(window, text="elapsed time: ")
        textlbl.grid(column=0, row=0)
        imglabel = tk.Label(window) # make Label widget to hold image
        imglabel.place(x=10, y=20) #pixels from top-left
        window.update() #update TCL tasks to make window appear
        #cam.Binning
        
        # Width and height throttle framerate

        width,height = get_img_dimensions()
        framerate = get_img_framerate()    
        dtype = get_img_dtype()
        
        assert dtype[-1] == '8', 'Data should be in proper bit depth'

        savepath= '/home/baccuslab/queuedUp.mp4'
        fjw = FJWriter(savepath,framerate,(width,height))
        tStart = time.time()
        
        # MUST TURN ON HERE - STARTS STROBING IMMEDIATELY
        cam.StrobeEnabled = True
        cam.StrobeDuration = 3000  # microseconds
        cam.start()
        for i in range(10):
            frame = cam.get_array()
            fjw.image_queue.put(frame)
            
            if i==int(framerate)*5:
                expt = cam.__getattr__('ExposureTime')
                # print(expt)
                # cam.ExposureTime = expt/4
                print('exposured')
            if i%(framerate/10) == 0: #update screen every 10 frames 
                timeElapsed = str(time.time() - tStart)
                timeElapsedStr = "elapsed time: " + timeElapsed[0:5] + " sec"
                textlbl.configure(text=timeElapsedStr)
                I = ImageTk.PhotoImage(Image.fromarray(frame))
                imglabel.configure(image=I)
                imglabel.image = I #keep reference to image
                window.update() #update on screen (this must be called from main thread)

        cam.StrobeEnabled = False
        fjw.kill=True

    fjw.image_queue.join()#
    fjw.write_thread.join()
    window.destroy()
