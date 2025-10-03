import os
from pathlib import Path

import pandas as pd
from PyQt6 import QtGui, QtCore
from PyQt6.QtCore import (
    QThreadPool,
    QTimer, QUrl, QPoint,
)
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QFileDialog, QMessageBox, QMenu, QGridLayout,
)
from bix.utils import (
    mac_test,
    FOL_BIL,
    create_profile_dictionary,
    create_calibration_dictionary,
    DEF_ALIASES_FILE_PATH, global_get,
)
from bix.gui.gui import Ui_MainWindow
import setproctitle
from bix.gui.tables import (
    fill_calibration_table,
    fill_profile_table,
    fill_logger_aliases_table
)
from bix.worker_ble import WorkerBle
from ble.ble import *
from ble.ble_linux import (
    ble_linux_disconnect_by_mac,
    ble_linux_get_bluez_version
)
import toml
import sys
import pyqtgraph as pg
from datetime import datetime
import plotly.graph_objects as go
from PyQt6.QtWebEngineWidgets import QWebEngineView
from lix.ascii85 import ascii85_to_num as a2n
from lix.pressure import LixFileConverterP
from lix.temperature import LixFileConverterT





class MyPlotWidget(pg.PlotWidget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scene().sigMouseClicked.connect(self.mouse_clicked)

    def mouse_clicked(self, mouse_click_event):
        print('clicked plot 0x{:x}, event: {}'.format(id(self), mouse_click_event))
        ev = mouse_click_event
        print('x = {}'.format(self.mapToView(ev.pos()).x()))
        ts = self.mapToView(ev.pos()).x()
        print(f't = {datetime.fromtimestamp(ts)}')
        print('y = {}'.format(self.mapToView(ev.pos()).y()))



class Bix(QMainWindow, Ui_MainWindow):

    def gui_show_bluez_version(self):
        if platform.system() != 'Linux':
            return
        v = ble_linux_get_bluez_version()
        if v < '5.66':
            self.lbl_bluez_version.setStyleSheet('color: red')
            self.lbl_bluez_version.setText(f'caution: bluez v{v} < 5.66')
        else:
            self.lbl_bluez_version.setText(f'bluez v{v}')


    @staticmethod
    def gui_show_error_message(desc, solution):
        m = QMessageBox()
        m.setIcon(QMessageBox.Icon.Critical)
        m.setText(desc)
        m.setInformativeText(solution)
        m.setWindowTitle("BIX Error")
        m.setStandardButtons(QMessageBox.StandardButton.Ok)
        m.exec()


    @staticmethod
    def _get_version():
        d = toml.load('pyproject.toml')
        return d['project']['version']


    def on_click_btn_test(self):
        self.pages.setCurrentIndex(1)


    def _load_toml_file(self, s):
        p, _ = QFileDialog.getOpenFileName(self, s, FOL_BIL, 'TOML Files (*.toml)')
        bn = os.path.basename(p)
        try:
            print(f'trying to load TOML file {bn}')
            return toml.load(p)
        except (Exception, ) as e:
            self.gui_show_error_message(
                desc=f'error: opening TOML file {bn}',
                solution=f'fix {e}'
            )


    def dialog_import_macs(self):
        return self._load_toml_file('Select file with MAC list')


    def dialog_import_file_calibration(self):
        return self._load_toml_file('Select file with SCC info')


    def dialog_import_file_profile(self):
        return self._load_toml_file('Select file with PROFILE info')


    def dialog_import_file_behavior(self):
        return self._load_toml_file('Select file with BEHAVIOR info')


    def dialog_import_file_csv_to_plot(self):
        p, _ = QFileDialog.getOpenFileName(
            self,
            'Choose CSV file',
            FOL_BIL,
            'CSV Files (*.csv)'
        )
        return p


    def slot_signal_done(self):
        self.lbl_busy.setStyleSheet('color: black')
        self.lbl_busy.setText('done')


    def slot_signal_result(self, s):
        self.lbl_result.setText(s)


    def slot_signal_gui_status(self, s):
        self.lbl_busy.setStyleSheet('color: gray;')
        self.lbl_busy.setText(s)


    def slot_signal_download(self, s):
        self.lbl_download.setText(s)


    def slot_signal_error(self, e):
        print(f'slot {e}')
        self.lbl_busy.setStyleSheet('color: red')
        self.lbl_busy.setText(f'{e}')


    def slot_signal_status(self, s):
        print(f'logger is {s}')
        self.lbl_sts.setText(s)


    def slot_signal_gcc(self, s):
        s = s[6:]
        d = create_calibration_dictionary()
        for i, v in enumerate(d.items()):
            k, _ = v
            d[k] = s[(i * 5):(i * 5) + 5]
        fill_calibration_table(self, d)


    def slot_signal_gcf(self, s):
        s = s[6:]
        d = create_profile_dictionary()
        for i, v in enumerate(d.items()):
            k, _ = v
            d[k] = s[(i * 5):(i * 5) + 5]
        fill_profile_table(self, d)


    def slot_signal_connected(self):
        self.pages.setCurrentIndex(1)
        self.lbl_connecting.setText('')


    def slot_signal_disconnected(self):
        self.lbl_connecting.setText('')
        self.pages.setCurrentIndex(0)


    def slot_signal_cannot_connect(self, mac):
        self.pages.setCurrentIndex(0)
        self.lbl_connecting.setStyleSheet('color: red')
        self.lbl_connecting.setText(f'can\'t connect {mac}')


    def slot_signal_info(self, d: dict):
        self.lbl_sn.setText(d['sn'])
        self.lbl_mac.setText(d['mac'])
        self.lbl_gfv.setText(d['gfv'])
        glt = d['glt']
        self.lbl_glt.setText(glt)
        self.lbl_sts.setText(d['sts'])
        self.table.setVisible(glt in ('TDO', 'CTD'))


    def slot_signal_sensors(self, d: dict):
        glt = self.lbl_glt.text()
        self.lbl_gst.setVisible(False)
        self.lbl_gsp.setVisible(False)
        self.lbl_acc.setVisible(False)
        self.lbl_gsc.setVisible(False)
        self.lbl_gdo.setVisible(False)

        if glt in ('TDO', 'CTD'):
            self.lbl_gst.setVisible(True)
            self.lbl_gsp.setVisible(True)
            self.lbl_acc.setVisible(True)

            # do conversion with default values
            v = str(d['gst'])
            tmr = a2n("7VZ<2")
            tma = a2n("3g?gQ")
            tmb = a2n("3HFKd")
            tmc = a2n("1S#M`")
            tmd = a2n("1ps%'")
            lct = LixFileConverterT(tma, tmb, tmc, tmd, tmr)
            vtc = '{:.2f}'.format(float(lct.convert(d['gst'])))
            s = f'Temperature\n\n{vtc} °C\n({v})'
            self.lbl_gst.setText(s)
            print(f'GST {v} counts')
            print(f'GST {vtc} Celsius')


            v = str(d['gsp'])
            pra = a2n("5po'i")
            prb = a2n("!!!!!")
            lcp = LixFileConverterP(pra, prb)
            vpd = '{:.2f}'.format(lcp.convert(d['gsp'])[0])
            s = f'Pressure\n\n{vpd} dbar\n({v})'
            self.lbl_gsp.setText(s)
            print(f'GSP {v} counts')
            print(f'GSP {vpd} decibar')

            vax = str(d['gax'])
            vay = str(d['gay'])
            vaz = str(d['gaz'])
            s = f'Accelerometer\nX = {vax}\nY = {vay}\nZ = {vaz}'
            self.lbl_acc.setText(s)
            print(f'ACC {vax}, {vay}, {vaz}')



        if glt == 'CTD':
            self.lbl_gsc.setVisible(True)
            v = d['gsc']
            print(f'GSC {v}')
            v = v.decode()
            c0 = v[2:4] + v[0:2]
            c1 = v[6:8] + v[4:6]
            c2 = v[10:12] + v[8:10]
            c3 = v[14:16] + v[12:14]
            c0 = int(c0, 16)
            c1 = int(c1, 16)
            c2 = int(c2, 16)
            c3 = int(c3, 16)
            s = f'Conductivity\nV12 {c0}\nV21 {c1}\nC21 {c2}\nC12 {c3}\n'
            self.lbl_gsc.setText(s)



        if glt.startswith('DO'):
            self.lbl_gdo.setVisible(True)
            v = str(d['gdo'])
            s = f'DOC\n\n{v}\n\nmg/l'
            self.lbl_gdo.setText(s)
            print(f'GDO {v}')



        # these values match DDH
        v = d['bat']
        if glt == 'TDO':
            v *= .5454
        if glt == 'CTD':
            v *= .5454
        if glt.startswith('DO'):
            v *= .4545

        v = int(v)
        s = f'{v} mV'
        self.lbl_bat.setText(s)
        print(f'BAT {s}')



    # -------------------
    # GUI button clicks
    # -------------------

    @staticmethod
    def dec_gui_busy(fxn):
        def wrapper(self, *args, **kwargs):
            # prevent smashing GUI buttons
            if global_get('busy'):
                return
            self.lbl_busy.setText('busy')
            # calls GUI button function such as _on_click_btn_leds()
            fxn(self, *args, **kwargs)
        return wrapper


    def wrk(self, ls_operations, d_args=None):
        w = WorkerBle(ls_operations, d_args)
        w.signals.connected.connect(self.slot_signal_connected)
        w.signals.cannot_connect.connect(self.slot_signal_cannot_connect)
        w.signals.info.connect(self.slot_signal_info)
        w.signals.sensors.connect(self.slot_signal_sensors)
        w.signals.done.connect(self.slot_signal_done)
        w.signals.result.connect(self.slot_signal_result)
        w.signals.gui_status.connect(self.slot_signal_gui_status)
        w.signals.disconnected.connect(self.slot_signal_disconnected)
        w.signals.error.connect(self.slot_signal_error)
        w.signals.logger_status.connect(self.slot_signal_status)
        w.signals.gcc.connect(self.slot_signal_gcc)
        w.signals.gcf.connect(self.slot_signal_gcf)
        w.signals.download.connect(self.slot_signal_download)
        # run() in Worker class, which signals results to our slot_signals_x()
        self.threadpool.start(w)


    @dec_gui_busy
    def on_click_btn_connect(self, _):
        mac = mac_test()
        h_s = 'hard-coded'
        r = self.tbl_known_macs.currentRow()
        if r and r != -1:
            mac = self.tbl_known_macs.item(r, 0).text()
            h_s = ''

        # style
        self.lbl_connecting.setStyleSheet('color: rgb(87, 170, 255);')



        # be sure we are disconnected
        if ble_linux_is_mac_already_connected(mac):
            s = f'pre-leave {mac}'
            print(s)
            self.lbl_connecting.setText(s)
            QApplication.processEvents()
            ble_linux_disconnect_by_mac(mac)


        self.lbl_connecting.setText(f'connecting {mac} {h_s}')
        self.wrk([
            'wb_connect',
            'wb_sensors',
            'wb_gcc'],
            {'mac': mac}
        )


    @dec_gui_busy
    def on_click_btn_disconnect(self, _):
        self.wrk('wb_disconnect')


    @dec_gui_busy
    def on_click_btn_sensors(self, _):
        glt = self.lbl_glt.text()
        self.wrk('wb_sensors', {'glt': glt})


    @dec_gui_busy
    def on_click_btn_mts(self, _):
        self.wrk('wb_mts')


    @dec_gui_busy
    def on_click_btn_gec(self, _):
        self.wrk('wb_gec')


    @dec_gui_busy
    def on_click_btn_mux(self, _):
        self.wrk('wb_mux')


    @dec_gui_busy
    def on_click_btn_osc(self, _):
        self.wrk('wb_osc')


    @dec_gui_busy
    def on_click_btn_gci(self, _):
        self.wrk('wb_gci')


    @dec_gui_busy
    def on_click_btn_run(self, _):
        self.wrk('wb_run')


    @dec_gui_busy
    def on_click_btn_stop(self, _):
        self.wrk('wb_stop')


    @dec_gui_busy
    def on_click_btn_sts(self, _):
        self.wrk('wb_sts')


    @dec_gui_busy
    def on_click_btn_frm(self, _):
        dlg = QMessageBox(self)
        dlg.setWindowTitle('Be careful with this format command')
        dlg.setText("Delete all files in logger?")
        dlg.setIcon(QMessageBox.Icon.Warning)
        dlg.setStandardButtons(QMessageBox.StandardButton.Ok |
                               QMessageBox.StandardButton.Cancel)
        dlg.setFixedWidth(400)
        if dlg.exec() == QMessageBox.StandardButton.Ok:
            self.wrk('wb_frm')


    @dec_gui_busy
    def on_click_btn_led(self, _):
        self.wrk('wb_led')


    @dec_gui_busy
    def on_click_btn_log(self, _):
        self.wrk('wb_log')


    @dec_gui_busy
    def on_click_btn_gcc(self, _):
        self.wrk('wb_gcc')


    @dec_gui_busy
    def on_click_btn_gcf(self, _):
        self.wrk('wb_gcf')


    @dec_gui_busy
    def on_click_btn_scf(self, _):
        # d = self.dialog_import_file_profile()
        # if not d:
        #     return
        bp = self.btn_scf.mapToGlobal(QtCore.QPoint(0, 0))
        x = bp.x() + 25
        y = bp.y() + 25
        p = QPoint(x, y)
        self.context_menu_scf.exec(p)



    @dec_gui_busy
    def on_click_btn_download(self, _):
        self.lbl_download.setText('')
        bp = self.btn_download.mapToGlobal(QtCore.QPoint(0, 0))
        x = bp.x() + 25
        y = bp.y() + 25
        p = QPoint(x, y)
        self.context_menu_dl.exec(p)



    @dec_gui_busy
    def on_click_btn_download_normal(self, _):
        self.wrk('wb_download_normal')


    @dec_gui_busy
    def on_click_btn_download_fast(self, _):
        self.wrk('wb_download_fast')



    @dec_gui_busy
    def on_click_btn_scf_slow(self, _):
        d = create_profile_dictionary()
        d['RVN'] = "00004"
        d['PFM'] = "00001"
        d['SPN'] = "00001"
        d['SPT'] = "00060"
        d['DRO'] = "00004"
        d['DRU'] = "00004"
        d['DRF'] = "00001"
        d['DSO'] = "14400"
        d['DSU'] = "00600"
        self.wrk(['wb_scf', 'wb_gcf'], d)


    @dec_gui_busy
    def on_click_btn_scf_mid(self, _):
        d = create_profile_dictionary()
        d['RVN'] = "00004"
        d['PFM'] = "00001"
        d['SPN'] = "00001"
        d['SPT'] = "00060"
        d['DRO'] = "00002"
        d['DRU'] = "00002"
        d['DRF'] = "00001"
        d['DSO'] = "07200"
        d['DSU'] = "00300"
        self.wrk(['wb_scf', 'wb_gcf'], d)


    @dec_gui_busy
    def on_click_btn_scf_fast(self, _):
        d = create_profile_dictionary()
        d['RVN'] = "00004"
        d['PFM'] = "00001"
        d['SPN'] = "00001"
        d['SPT'] = "00060"
        d['DRO'] = "00002"
        d['DRU'] = "00002"
        d['DRF'] = "00001"
        d['DSO'] = "03600"
        d['DSU'] = "00060"
        self.wrk(['wb_scf', 'wb_gcf'], d)


    @dec_gui_busy
    def on_click_btn_scf_fixed_5_min(self, _):
        d = create_profile_dictionary()
        d['RVN'] = "00004"
        d['PFM'] = "00000"
        d['SPN'] = "00001"
        d['SPT'] = "00300"
        d['DRO'] = "00002"
        d['DRU'] = "00002"
        d['DRF'] = "00001"
        d['DSO'] = "03600"
        d['DSU'] = "00060"
        self.wrk(['wb_scf', 'wb_gcf'], d)


    @dec_gui_busy
    def on_click_btn_scc(self, _):
        d = self.dialog_import_file_calibration()
        if not d:
            return
        self.wrk(
            ['wb_scc', 'wb_gcc'],
            d['calibration']
        )


    @dec_gui_busy
    def on_click_btn_beh(self, _):
        d = self.dialog_import_file_behavior()
        if not d:
            return
        self.wrk(
            ['wb_beh'],
            d['behavior']
        )


    def on_click_btn_plot(self, _):

        # point to CSV file or hard-code it
        # p = self.dialog_import_file_csv_to_plot()
        p = '/home/kaz/Downloads/dl_bil_v5/2508701_BIL_20250930_161818_TDO.csv'
        if not p:
            return
        bn = os.path.basename(p)


        # remove OLD graph
        self.lay.removeWidget(self.gr)
        self.gr = MyPlotWidget(
            # viewBox=CustomViewBox(),
            axisItems={'bottom': pg.DateAxisItem()})
        self.lay.addWidget(self.gr)
        self.gr.setBackground("white")



        # infer logger type from filename
        glt = 'DOX'
        if 'TDO' in bn:
            glt = 'TDO'
        elif 'CTD' in bn:
            glt = 'CTD'


        # load CSV data, transform X-axis to seconds
        df = pd.read_csv(p)
        x = df['ISO 8601 Time'].values
        xf = []
        for i in x:
            dt = datetime.strptime(i, '%Y-%m-%dT%H:%M:%S.000Z').timestamp()
            xf.append(dt)


        # set pen to None to remove the line between plotted data points
        pen = pg.mkPen(color=(255, 0, 0))


        # ----------------
        # plot data points
        # ----------------
        if glt == 'TDO':
            m = 'Temperature (C)'
            y1 = df[m].values
            m = 'Pressure (dbar)'
            y2 = df[m].values
            self.gr.plot(xf, y1, pen=None, symbol='o', symbolSize=5, symbolPen='b')




        # set title of the plot
        bn = os.path.basename(p)
        self.lbl_plot.setText(bn)


        # allow mouse events in the plot
        self.gr.setVisible(True)
        view_box = self.gr.plotItem.vb
        view_box.setMouseEnabled(x=True, y=True)


    def on_click_btn_import_macs(self, _):
        d = self.dialog_import_macs()
        if not d:
            return
        d = d['aliases']
        fill_logger_aliases_table(self, d)


    def timer_cb(self):
        # show download progress
        try:
            with open(DEV_SHM_DL_PROGRESS, 'r') as f:
                v = f.read()
                self.progressBar.setValue(int(float(v)))
        except FileNotFoundError:
            self.progressBar.setValue(0)

        # animated busy
        s = self.lbl_busy.text().split(' ')[0]
        if global_get('busy') and 'done' not in s:
            v = (int(time.time()) % 3) + 1
            self.lbl_busy.setText(s + ' ' + ('.' * v))

        # always on correct tab
        if not is_connected():
            if self.pages.currentIndex() != 0:
                print('moving to proper logger GUI page')
                self.pages.setCurrentIndex(0)



    def __init__(self):
        super(Bix, self).__init__()
        self.setupUi(self)
        self.setWindowTitle("BIX - Lowell Instruments")
        self.threadpool = QThreadPool()
        self.setFixedWidth(1024)
        self.setFixedHeight(768)
        self.timer = QTimer()
        self.timer.timeout.connect(self.timer_cb)
        self.timer.start(1000)
        self.pages.setCurrentIndex(0)
        self.tabs.setCurrentIndex(0)
        self.lbl_gui_version.setText('v' + self._get_version())
        self.gui_show_bluez_version()
        if os.path.exists(DEV_SHM_DL_PROGRESS):
            os.unlink(DEV_SHM_DL_PROGRESS)
        self.progressBar.setValue(0)
        self.lbl_download.setText('')
        center = QtGui.QGuiApplication.primaryScreen().geometry().center()
        self.move(center - self.rect().center())
        self.maps_webview = QWebEngineView()
        settings = self.maps_webview.page().settings()
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        self.lay_maps.addWidget(self.maps_webview)



        # auto-import MAC aliases file
        if os.path.exists(DEF_ALIASES_FILE_PATH):
            print(f'auto-importing alias file {DEF_ALIASES_FILE_PATH}')
            d = toml.load(DEF_ALIASES_FILE_PATH)
            d = d['aliases']
            fill_logger_aliases_table(self, d)



        # buttons
        self.btn_connect.clicked.connect(self.on_click_btn_connect)
        self.btn_disconnect.clicked.connect(self.on_click_btn_disconnect)
        self.btn_sensors.clicked.connect(self.on_click_btn_sensors)
        self.btn_test.clicked.connect(self.on_click_btn_test)
        self.btn_rws.clicked.connect(self.on_click_btn_run)
        self.btn_sws.clicked.connect(self.on_click_btn_stop)
        self.btn_sts.clicked.connect(self.on_click_btn_sts)
        self.btn_frm.clicked.connect(self.on_click_btn_frm)
        self.btn_led.clicked.connect(self.on_click_btn_led)
        self.btn_log.clicked.connect(self.on_click_btn_log)
        self.btn_gcc.clicked.connect(self.on_click_btn_gcc)
        self.btn_gcf.clicked.connect(self.on_click_btn_gcf)
        self.btn_scc.clicked.connect(self.on_click_btn_scc)
        self.btn_scf.clicked.connect(self.on_click_btn_scf)
        self.btn_beh.clicked.connect(self.on_click_btn_beh)
        self.btn_import_macs.clicked.connect(self.on_click_btn_import_macs)
        self.btn_download.clicked.connect(self.on_click_btn_download)
        self.btn_mts.clicked.connect(self.on_click_btn_mts)
        self.btn_gec.clicked.connect(self.on_click_btn_gec)
        self.btn_mux.clicked.connect(self.on_click_btn_mux)
        self.btn_osc.clicked.connect(self.on_click_btn_osc)
        self.btn_gci.clicked.connect(self.on_click_btn_gci)
        self.btn_plot.clicked.connect(self.on_click_btn_plot)
        # context SCF menu
        self.context_menu_scf = QMenu(self)
        _scf_slow = self.context_menu_scf.addAction("profile slow")
        _scf_mid = self.context_menu_scf.addAction("profile mid")
        _scf_fast = self.context_menu_scf.addAction("profile fast")
        _scf_fixed_5_min = self.context_menu_scf.addAction("profile fixed_5_min")
        _scf_slow.triggered.connect(self.on_click_btn_scf_slow)
        _scf_mid.triggered.connect(self.on_click_btn_scf_mid)
        _scf_fast.triggered.connect(self.on_click_btn_scf_fast)
        _scf_fixed_5_min.triggered.connect(self.on_click_btn_scf_fixed_5_min)
        # context download menu
        self.context_menu_dl = QMenu(self)
        _dl_slow = self.context_menu_dl.addAction("download normal")
        _dl_fast = self.context_menu_dl.addAction("download fast")
        _dl_slow.triggered.connect(self.on_click_btn_download_normal)
        _dl_fast.triggered.connect(self.on_click_btn_download_fast)


        # plots of pressure, temperature, CSV files
        self.gr = MyPlotWidget(
            # viewBox=CustomViewBox(),
            axisItems={'bottom': pg.DateAxisItem()})
        self.gr.setVisible(False)


        # debug: uncomment when needed
        self.btn_test.setVisible(False)

        # maps
        my_map = go.Scattermap(
            lat=['45.5017', '46'],
            lon=['-73.5673', '-74'],
            mode='markers',
            marker=go.scattermap.Marker(
                size=14
            ),
            text=['Montreal', 'pepi'],
        )
        fig = go.Figure(my_map)
        fig.update_layout(
            margin=dict(
                l=0,
                r=0,
                b=0,
                t=0,
                pad=0
            ),
            hovermode='closest',
            map=dict(
                bearing=0,
                center=go.layout.map.Center(
                    lat=45,
                    lon=-73
                ),
                pitch=0,
                zoom=5
            )
        )
        fig.write_html('/tmp/a.html')
        url = QUrl.fromLocalFile('/tmp/a.html')
        self.maps_webview.load(url)




def main_bix():
    setproctitle.setproctitle('main_bix')
    app = QApplication(sys.argv)
    ex = Bix()
    ex.show()
    rv = app.exec()
    sys.exit(rv)



if __name__ == "__main__":
    assert sys.version_info >= (3, 9)
    main_bix()

