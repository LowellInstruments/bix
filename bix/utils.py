import asyncio
import pathlib
from PyQt6.QtCore import QObject, pyqtSignal



PATH_ALIAS_FILE = pathlib.Path.home() / 'Downloads' / 'bil_v2_logger_aliases.toml'
RVN_SCC_4 = "00004"
FOL_BIL = str(pathlib.Path.home() / 'Downloads/dl_bil_v5')
# todo: manage python versions here
loop = asyncio.get_event_loop()
# loop = asyncio.new_event_loop()




class WorkerSignals(QObject):
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    info = pyqtSignal(object)
    error = pyqtSignal(str)
    sensors = pyqtSignal(object)
    status = pyqtSignal(str)
    done = pyqtSignal()
    gcc = pyqtSignal(object)
    gcf = pyqtSignal(object)



def create_profile_dictionary():
    d = {
        # order must match firmware
        'RVN': RVN_SCC_4,
        'PFM': 0,
        'SPN': 0,
        'SPT': 0,
        'DRO': 0,
        'DRU': 0,
        'DRF': 0,
        'DSO': 0,
        'DSU': 0,
    }
    return d


def create_calibration_dictionary():
    d = {
        # 15000: '7VZ<2'
        # 1: '5C`_6'
        # 0: '!!!!!'
        "RVN": RVN_SCC_4,
        "TMO": 0,
        "TMR": 15000,
        "TMA": 1,
        "TMB": 0,
        "TMC": 0,
        "TMD": 0,
        "AXX": 1,
        "AXY": 0,
        "AXZ": 0,
        "AXV": 0,
        "AXC": 0,
        "AYX": 0,
        "AYY": 1,
        "AYZ": 0,
        "AYV": 0,
        "AYC": 0,
        "AZX": 0,
        "AZY": 0,
        "AZZ": 1,
        "AZV": 0,
        "AZC": 0,
        "TMX": 0,
        "TMY": 0,
        "TMZ": 0,
        "PRA": 1,
        "PRB": 0,
        "PRC": "+0000",
        "PRD": "+0000",
        "DCO": 0,
        "NCO": 0,
        "DHU": 0,
        "DCD": 0,
    }
    return d



def mac_test():
    mt = "D0:2E:AB:D9:29:48"  # TDO bread
    # mt = "F0:5E:CD:25:92:F1"  # TDO 2508700 *
    # mt = "F0:5E:CD:25:A1:16"    # TDO 2508701
    # mt = "F0:5E:CD:25:92:9D"    # TDO 2508702
    return mt
