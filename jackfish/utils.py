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

def count_nvidia_gpus():
    try:
        ps = subprocess.Popen(('nvidia-smi', '--query-gpu=name', '--format=csv,noheader'), stdout=subprocess.PIPE)
        output = subprocess.check_output(('wc', '-l'), stdin=ps.stdout).decode()
        ps.wait()
        n_gpus = int(output)

        print(f'{n_gpus} Nvidia GPUs detected!')
        return n_gpus
    except Exception: # this command not being found can raise quite a few different errors depending on the configuration
        print('No Nvidia GPU in system!')
        return 0

def get_ffmpeg_location():
    try:
        path = subprocess.check_output("which ffmpeg", shell=True).decode()
        parent_dir = path[:path.rindex(os.sep)]
        print(f'FFMPEG found in {parent_dir}')
        return parent_dir
    except Exception:
        print("Couldn't find FFMPEG.")
        return None
