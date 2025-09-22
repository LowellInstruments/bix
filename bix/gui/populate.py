import pathlib

from PyQt6 import QtCore
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTableWidgetItem, QHeaderView

FOL_BIL = str(pathlib.Path.home() / 'Downloads/dl_bil_v5')



def populate_cal_table(app, d):
    app.tbl_gcc.clear()
    app.tbl_gcc.setColumnCount(3)
    app.tbl_gcc.setHorizontalHeaderLabels(['a', 'b', 'c'])
    app.tbl_gcc.setRowCount(len(d))

    i = 0
    for k, v in d.items():
        print(k, v)
        vi, v85 = v
        _it = QTableWidgetItem(k)
        _it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        app.tbl_gcc.setItem(i, 0, _it)
        _it = QTableWidgetItem(str(vi))
        _it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        app.tbl_gcc.setItem(i, 1, _it)
        _it = QTableWidgetItem(str(v85))
        _it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        app.tbl_gcc.setItem(i, 2, _it)
        i += 1

    h = app.tbl_gcc.horizontalHeader()
    h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    h.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
    h.setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
