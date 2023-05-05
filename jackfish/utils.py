import os
import subprocess
from enum import Enum
from PyQt5.QtWidgets import QMessageBox

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

Status = Enum('Status', ['STANDBY', 'RECORDING', 'PREVIEWING'])

def message_window(title="Alert", text=""):
    msg = QMessageBox()
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.exec_()

def check_nvidia_gpu():
    try:
        subprocess.check_output('nvidia-smi')
        print('Nvidia GPU detected!')
        return True
    except Exception: # this command not being found can raise quite a few different errors depending on the configuration
        print('No Nvidia GPU in system!')
        return False

def get_ffmpeg_location():
    try:
        path = subprocess.check_output("which ffmpeg", shell=True).decode()
        parent_dir = path[:path.rindex(os.sep)]
        print(f'FFMPEG found in {parent_dir}')
        return parent_dir
    except Exception:
        print("Couldn't find FFMPEG.")
        return None
