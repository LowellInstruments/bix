from PyQt6 import QtCore
from PyQt6.QtWidgets import QTableWidgetItem, QHeaderView, QAbstractItemView


def _populate_table(app, d, title):

    app.lbl_table.setText(f'{title} table')
    app.table.clear()
    app.table.setColumnCount(3)
    app.table.setHorizontalHeaderLabels(['a', 'b', 'c'])
    app.table.setRowCount(len(d))

    i = 0
    for k, v in d.items():
        _it = QTableWidgetItem(k)
        _it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        app.table.setItem(i, 0, _it)
        _it = QTableWidgetItem(str(v))
        _it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        app.table.setItem(i, 1, _it)
        _it = QTableWidgetItem(str('a85'))
        _it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        app.table.setItem(i, 2, _it)
        i += 1

    h = app.table.horizontalHeader()
    h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    h.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
    h.setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

    # make table non-editable
    app.table.setEditTriggers(QAbstractItemView.EditTriggers.NoEditTriggers)




def fill_calibration_table(app, d):
    return _populate_table(app, d, 'Calibration')


def fill_profile_table(app, d):
    return _populate_table(app, d, 'Profile')