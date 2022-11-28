# jackfish

----
1. Installation and Build
2. Quickstart
3. Contributing
4. Feature Request
---


## 1. Installation and Build
1. Download this repository and install `jackfish` in developer mode with `pip` via:

> git clone https://github.com/jbmelander/jackfish.git
> cd PATH_TO_JF/jackfish/
> pip3 install -e .
> sh build.sh PATH_TO_JF # Compiles *_gui.py files

2. Run jackfish via:
> python3 PATH_TO_JF/jackfish/jackfish/gui/main_controller.py

(I like to set a .bashrc alias so that opening jackfish is as simple as typing `jackfish`. Edit ~/.bashrc and append the line `alias jackfish='python3 PATH_TO_JF/jackfish/jackfish/gui/main_controller.py`

## 2. Quickstart
1. Click `Load Preset` and load `JBM.json`
2. Click `Init DAQ` and `Init Cam` for all cameras you wish to use.
3. Clicking `Preview` should start streaming any initialized cameras and DAQ windows. Make sure everything looks appropriate. 
4. Click `Save Dir` and select the directory you will save data to
5. Click `Expt Name` and give your experiment a unique experiment name
6. Make sure `Preview` is off, click `Record`. To minimize frame drops turn off live viewing for any cameras and select channel `None` in the DAQ UI.






