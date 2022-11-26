import os
from enum import Enum
from PyQt5.QtWidgets import QMessageBox

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

Status = Enum('Status', ['STANDBY', 'RECORDING', 'PREVIEWING'])

def message_window(title="Alert", text=""):
    msg = QMessageBox()
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.exec_()
