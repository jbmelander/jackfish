# jackfish
1. [Installation and Build](#Installation-and-Build)
2. [Quickstart](#Quickstart)
3. Contributing
4. Feature Request
---


## Installation and Build
1. Download this repository and install `jackfish` in developer mode with `pip`. Then build the guis with the included `build.sh` script. Assuming your download is at PATH_TO_JF (for example, `~/jackfish` or `~/src/jackfish`):

```bash
git clone https://github.com/jbmelander/jackfish.git
cd PATH_TO_JF/
pip3 install -e .
sh build.sh PATH_TO_JF
```
2. Run jackfish via:
```bash
python3 PATH_TO_JF/jackfish/gui/main_controller.py
```

Optional: I like to set a an alias so that opening jackfish is as simple as typing `jackfish` in a terminal. Edit your `~/.bashrc` and append the line `alias jackfish='python3 PATH_TO_JF/jackfish/gui/main_controller.py`. Restart the terminal for changes to take effect.

## Quickstart
1. Click `Load Preset` and load `JBM.json`
2. Click `Init DAQ` and `Init Cam` for all cameras you wish to use.
3. Clicking `Preview` should start streaming any initialized cameras and DAQ windows. Make sure everything looks appropriate. 
4. Click `Save Dir` and select the directory you will save data to
5. Click `Expt Name` and give your experiment a unique experiment name
6. Make sure `Preview` is off, click `Record`. To minimize frame drops turn off live viewing for any cameras and select channel `None` in the DAQ UI.
7. If you wish to capture the start and stop strobes from a camera, make sure it is "frozen" before beginning recording (Freeze checkbox in Cam UI). After recording begins, unfreeze the camera and once again freeze it at the end.






