import matplotlib.pyplot as plt
import cv2
from simple_pyspin import Camera
import time, threading, queue, os

from datetime import datetime
import numpy as np
import skvideo

# skvideo.setFFmpegPath('/usr/bin/ffmpeg') #set path to ffmpeg installation before importing io
numImages=10
import skvideo.io
movie_name='/home/baccuslab/testvids/3.avi'
i = 0

def save_img(image_queue,i): #function to save video frames from the queue in a separate thread
    while True:
        if image_queue.empty():
            print('empty')
            break
        else:
            img = image_queue.get()
            print(img.shape)
            print(len(imgs))
            imgs.append(img)
            print(len(imgs))
            # writer.writeFrame(img) 
            image_queue.task_done()



image_queue = queue.Queue() #create queue in memory to store images while asynchronously written to disk
fps = 60
#crfOut = 21 #controls tradeoff between quality and storage, see https://trac.ffmpeg.org/wiki/Encode/H.264 
#ffmpegThreads = 4 #this controls tradeoff between CPU usage and memory usage; video writes can take a long time if this value is low
##crfOut = 18 #this should look nearly lossless
##writer = skvideo.io.FFmpegWriter(movieName, outputdict={'-r': str(FRAME_RATE_OUT), '-vcodec': 'libx264', '-crf': str(crfOut)}) # with frame rate
#writer = skvideo.io.FFmpegWriter(movie_name, outputdict={'-vcodec': 'libx264', '-crf': str(crfOut), '-threads': str(ffmpegThreads)})
crf = 17
with Camera() as cam:
    cam.start()
    array = cam.get_array()
    cam.stop()

width = array.shape[1]
height = array.shape[0]

writer = skvideo.io.FFmpegWriter(movie_name, 
            outputdict={'-r': str(fps), '-c:v': 'libx264', '-crf': str(crf), '-preset': 'ultrafast', '-pix_fmt': 'yuv444p'}
)

save_thread = threading.Thread(target=save_img, args=(image_queue,i))
save_thread.start()  

with Camera() as cam:
    cam.start()
    

    t_start = time.time()

    for i in range(numImages):
        image = cam.get_array() #get pointer to next image in camera buffer; blocks until image arrives via USB; timeout=INF
        print('ha')
        print(image.shape)
        image_queue.put(image) #put next image in queue
        
        if i%5 == 0: #update screen every 10 frames 
            timeElapsed = str(time.time() - t_start)
            timeElapsedStr = "elapsed time: " + timeElapsed[0:5] + " sec"
            
    cam.stop()

# writer.close()
image_queue.join()
print(len(imgs))
