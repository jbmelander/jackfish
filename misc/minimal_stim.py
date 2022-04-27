import matplotlib.pyplot as plt
import time
import numpy as np
from psychopy import visual, core  # import some libraries from PsychoPy
import sys

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

win = visual.Window(size=[pw,ph],screen=int(screen), monitor="wn", units="pix",fullscr=True,waitBlanking=False)
# pd = visual.Circle(win, radius=0.2, units="pix", pos=[width,height], fillColor="black")
# pd.draw()

g = visual.ImageStim(win,image=np.ones((height,width)),size=[pw*2,ph*2])
g.setAutoDraw(True)

while True:
    for i in range(100):
        if i == 1:
            g.image = np.ones((height,width))
        else:
            g.image = np.ones((height,width))*-1
        #     g.image = imgs[i]+1
        #     g.draw()
        # else:
        #     g.image = imgs[i]-1
        #     g.draw()
            # pd.setColor('white')
            # pd.draw()
        vbl = win.flip()
      
