import pathlib


PATH_ALIAS_FILE = pathlib.Path.home() / 'Downloads' / 'bil_v2_logger_aliases.toml'



def mac_test():
    # mt = "D0:2E:AB:D9:29:48"  # TDO bread
    # mt = "F0:5E:CD:25:92:F1"    # TDO 2508700 *
    mt = "F0:5E:CD:25:A1:16"    # TDO 2508701
    return mt
