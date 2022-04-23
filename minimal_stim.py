import matplotlib.pyplot as plt
import time
import numpy as np
from psychopy import visual, core  # import some libraries from PsychoPy

#create a window
wins = []
gs = []
factor=20
n=10

pw = 1920
ph = 1080
width,height = int(1920/factor),int(1080/factor)
imgs = np.random.uniform(-1,1,(n,height,width))
imgs = np.zeros((n,height,width))
imgs2 = np.ones((n,height,width))

win = visual.Window(size=[pw,ph],screen=1, monitor="wn", units="pix",fullscr=True,waitBlanking=False)
# pd = visual.Circle(win, radius=0.2, units="pix", pos=[width,height], fillColor="black")
# pd.draw()

g = visual.ImageStim(win,image=imgs[0],size=[pw*2,ph*2])
g.setAutoDraw(False)

while True:
    for i in range(10):
        if i in [0,1,2]:
            g.image = imgs[i]*-1
            g.draw()
        if i in [3,4,5,6]:
            g.image = imgs[i]
            g.draw()
        else:
            g.image = imgs2[i]
            g.draw()
            # pd.setColor('white')
            # pd.draw()
        vbl = win.flip()
      
