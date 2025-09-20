from PyQt6.QtWidgets import QTableWidgetItem


def populate_cal_table(app, d):
    app.tbl_gcc.clear()
    app.tbl_gcc.setColumnCount(3)
    app.tbl_gcc.setHorizontalHeaderLabels(['a', 'b', 'c'])
    app.tbl_gcc.setRowCount(len(d))

    i = 0
    for k, v in d.items():
        print(k, v)
        vi, v85 = v
        app.tbl_gcc.setItem(i, 0, QTableWidgetItem(k))
        app.tbl_gcc.setItem(i, 1, QTableWidgetItem(str(vi)))
        app.tbl_gcc.setItem(i, 2, QTableWidgetItem(str(v85)))
        i += 1
