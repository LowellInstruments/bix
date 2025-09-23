from PyQt6 import QtCore
from PyQt6.QtWidgets import QTableWidgetItem, QHeaderView




def _populate_table(app, d, title):

    app.lbl_table.setText(f'{title} table')
    app.tbl_gcc.clear()
    app.tbl_gcc.setColumnCount(3)
    app.tbl_gcc.setHorizontalHeaderLabels(['a', 'b', 'c'])
    app.tbl_gcc.setRowCount(len(d))

    i = 0
    for k, v in d.items():
        _it = QTableWidgetItem(k)
        _it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        app.tbl_gcc.setItem(i, 0, _it)
        _it = QTableWidgetItem(str(v))
        _it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        app.tbl_gcc.setItem(i, 1, _it)
        _it = QTableWidgetItem(str('a85'))
        _it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        app.tbl_gcc.setItem(i, 2, _it)
        i += 1

    h = app.tbl_gcc.horizontalHeader()
    h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    h.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
    h.setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)




def fill_calibration_table(app, d):
    return _populate_table(app, d, 'Calibration')


def fill_profile_table(app, d):
    return _populate_table(app, d, 'Profile')