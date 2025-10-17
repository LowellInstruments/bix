import os
import pathlib
from PyQt6.QtCore import QObject, pyqtSignal



def mac_test():
    # mt = "D0:2E:AB:D9:29:48"  # TDO bread
    # mt = "F0:5E:CD:25:92:F1"  # TDO 2508700 *
    # mt = "F0:5E:CD:25:A1:16"    # TDO 2508701
    # mt = "F0:5E:CD:25:92:9D"    # TDO 2508702
    # mt = "F0:5E:CD:25:92:95"    # TDO 2508703 *
    # mt = "F0:5E:CD:25:92:EA" # CTD_JED
    # mt = "F0:5E:CD:25:A2:12"    # 2508705
    # mt = "F0:5E:CD:25:95:D4"    # CTD JOAQUIM
    # mt = "F0:5E:CD:25:A4:0A"    # 2508704
    # mt = "F0:5E:CD:25:97:02"    # 2508706
    mt = "F0:5E:CD:25:95:D5"    # 2508708
    return mt



g_d = {
    'busy': 0
}



PATH_BIL_FOLDER = str(pathlib.Path.home() / 'Downloads/dl_bil_v5')
PATH_BIL_DEF_ALIASES_FILE = f'{PATH_BIL_FOLDER}/bil_v5_logger_aliases.toml'
os.makedirs(PATH_BIL_FOLDER, exist_ok=True)
RVN_SCC_4 = "00004"
print(f'env, PATH_BIL_DEF_ALIASES_FILE = {PATH_BIL_DEF_ALIASES_FILE}')



def global_set(k, v):
    g_d[k] = v



def global_get(k):
    return g_d[k]





class WorkerSignals(QObject):
    connected = pyqtSignal()
    cannot_connect = pyqtSignal(str)
    disconnected = pyqtSignal()
    error = pyqtSignal(str)
    sensors = pyqtSignal(object)
    logger_status = pyqtSignal(str)
    done = pyqtSignal()
    gcc = pyqtSignal(object)
    gcf = pyqtSignal(object)
    download = pyqtSignal(str)
    result = pyqtSignal(str)
    gui_status = pyqtSignal(str)
    cmd_get_info = pyqtSignal(str)




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




if __name__ == '__main__':
    n = 0
