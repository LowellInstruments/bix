from PyQt6 import QtCore
from PyQt6.QtWidgets import QTableWidgetItem, QHeaderView, QTableWidget
from bix.utils import ascii85_to_num


def fill_calibration_table(app, d):
    app.lbl_table.setText(f'Calibration table')
    app.table.clear()
    app.table.setColumnCount(3)
    app.table.setHorizontalHeaderLabels(['tag', 'value', 'ascii85'])
    app.table.setRowCount(len(d))

    for i, k_v in enumerate(d.items()):
        k, v = k_v
        _it = QTableWidgetItem(k)
        _it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        app.table.setItem(i, 0, _it)
        f_str = str(ascii85_to_num(v))
        _it = QTableWidgetItem(f_str)
        _it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        app.table.setItem(i, 1, _it)
        _it = QTableWidgetItem(v)
        _it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        app.table.setItem(i, 2, _it)

    h = app.table.horizontalHeader()
    h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    h.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
    h.setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    app.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)


def fill_profile_table(app, d):
    app.lbl_table.setText(f'Profile table')
    app.table.clear()
    app.table.setColumnCount(2)
    app.table.setHorizontalHeaderLabels(['tag', 'value'])
    app.table.setRowCount(len(d))

    for i, k_v in enumerate(d.items()):
        k, v = k_v
        _it = QTableWidgetItem(k)
        _it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        app.table.setItem(i, 0, _it)
        _it = QTableWidgetItem(v)
        _it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        app.table.setItem(i, 1, _it)

    h = app.table.horizontalHeader()
    h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    h.setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    app.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

