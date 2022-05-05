import matplotlib.pyplot as plt
import time
import numpy as np
from psychopy import visual, core  # import some libraries from PsychoPy
import sys

og_time = time.time()
# screen = sys.argv[1]
screen = 1
#create a window
wins = []
gs = []
factor=20
n=10

pw = 1920
ph = 1080
width,height = int(1920/factor),int(1080/factor)

win = visual.Window(size=[pw,ph],screen=int(screen), monitor="wn", units="pix",fullscr=True,waitBlanking=True)


print(win.getActualFrameRate())
# pd = visual.Circle(win, radius=0.2, units="pix", pos=[width,height], fillColor="black")
# pd.draw()

# g = visual.rect.Rect(win,colorSpace='rgb')
# g = visual.ImageStim(win,image=np.ones((height,width)),size=[pw*2,ph*2]
# g.setAutoDraw(True)

x = np.random.uniform(low=-0.4,high=0.4,size=144)
z = []
for xi in x:
    for i in range(3):
        z = np.append(z,xi)
x = z



z = []
for i in range(3):
    z.append(x)

z = np.array(z)
x = z
    
np.save('/home/baccuslab/jbm_005/stim_20.npy',x)

    # y = np.array([1,1,1])
# yy = []

# for xi in x:
#     yy = np.append(yy,y*xi)

t = []
for i in range(20):
    for i in range(x.shape[1]):
        win.color = x[:,i]
        vbl = win.flip()
        t.append(vbl)
    for i in range(int(144/4)):
        win.color = [-1,-1,-1]
        vbl = win.flip()
        t.append(vbl)
      

t = np.array(t)
np.save('/home/baccuslab/jbm_005/time_20.npy',t)
