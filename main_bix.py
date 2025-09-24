import os

import pandas as pd
from PyQt6 import QtGui
from PyQt6.QtCore import (
    QThreadPool,
    QRunnable, pyqtSlot, QTimer,
)
from PyQt6.QtGui import QScreen
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QFileDialog, QMessageBox,
)
from pyqtgraph import DateAxisItem

from bix.utils import (
    mac_test,
    FOL_BIL, loop, WorkerSignals,
    create_profile_dictionary, create_calibration_dictionary, num_to_ascii85, DEF_ALIASES_FILE_PATH
)
from bix.gui.gui import Ui_MainWindow
import setproctitle
from bix.gui.tables import fill_calibration_table, fill_profile_table
from ble.ble import *
from ble.ble_linux import ble_linux_disconnect_by_mac
import toml
from lix.lix import parse_file_lid_v5
import sys
import matplotlib
matplotlib.use('QtAgg')
import pyqtgraph as pg
from datetime import datetime



os.makedirs(FOL_BIL, exist_ok=True)
g_mac = mac_test()
g_busy = False
g_d = {}
g_glt = ''



class Worker(QRunnable):

    def _ser(self, e: str):
        self.signals.error.emit(f'error {e}')


    async def wb_download(self):
        rv, d = await cmd_dir()
        if rv:
            self._ser('dir')
            return
        print('DIR d', d)
        n = len(d)

        if n == 0:
            self.signals.download.emit('no files')
            self.signals.done.emit()
            return

        for i, name_size in enumerate(d.items()):
            name, size = name_size
            rv = await cmd_dwg(name)
            if rv:
                self._ser('dwg')
                return
            time.sleep(1)
            print(f'downloading file {i + 1} / {n}')
            self.signals.download.emit(f'file {i + 1} / {n}')
            rv, data = await cmd_dwl(size)
            if rv:
                self._ser('dwl')
                return
            print(f'saving {name}')
            dst_filename = f'{FOL_BIL}/{name}'
            with open(dst_filename, 'wb') as f:
                f.write(data)
            time.sleep(1)

            # convert
            # todo: maybe as thread?
            if dst_filename.endswith('.lid'):
                bn = os.path.basename(dst_filename)
                print(f'BIX converting {bn}')
                try:
                    self.signals.converting.emit()
                    parse_file_lid_v5(dst_filename)
                except (Exception, ) as ex:
                    print(f'error converting {dst_filename} -> {ex}')

        self.signals.done.emit()


    async def wb_connect(self):
        mac = g_mac
        rv = await connect_by_mac(mac)
        if rv == 0:
            self._ser('connecting')
            return
        self.signals.connected.emit()

        d = {}
        rv, v = await cmd_glt()
        if rv:
            self._ser('glt')
            return
        d['glt'] = v
        global g_glt
        g_glt = v

        rv, v = await cmd_gfv()
        if rv:
            self._ser('gfv')
            return
        d['gfv'] = v

        rv, v = await cmd_mac()
        if rv:
            self._ser('mac')
            return
        d['mac'] = v

        rv, v = await cmd_rli()
        if rv:
            self._ser('rli')
            return
        d['sn'] = v['SN']

        self.signals.info.emit(d)
        self.signals.done.emit()


    async def wb_disconnect(self):
        await disconnect()
        self.signals.disconnected.emit()
        self.signals.done.emit()


    async def wb_run(self):
        rv = await cmd_stm()
        if rv:
            self._ser('stm')
            return
        rv = await cmd_dns('BIL')
        if rv:
            self._ser('dns')
            return
        rv = await cmd_fds()
        if rv:
            self._ser('fds')
            return
        g = ("-3.333333", "-4.444444", None, None)
        rv = await cmd_rws(g)
        print('run rv', rv)
        if rv:
            self._ser('rws')
            return
        self.signals.status.emit('running')
        self.signals.done.emit()


    async def wb_stp(self):
        g = ("-3.333333", "-4.444444", None, None)
        rv = await cmd_sws(g)
        if rv:
            self._ser('sws')
            return
        self.signals.status.emit('stopped')
        self.signals.done.emit()


    async def wb_mts(self):
        rv = await cmd_mts()
        if rv:
            self._ser('mts')
            return
        self.signals.done.emit()


    async def wb_gec(self):
        rv, v = await cmd_gec()
        if rv:
            self._ser('gec')
            return
        print('GEC rv, v', rv, v)
        self.signals.done.emit()


    async def wb_sts(self):
        rv, v = await cmd_sts()
        if rv:
            self._ser('sts')
            return
        self.signals.status.emit(v)
        self.signals.done.emit()


    async def wb_frm(self):
        rv = await cmd_frm()
        if rv:
            self._ser('frm')
        self.signals.done.emit()


    async def wb_led(self):
        rv = await cmd_led()
        if rv:
            self._ser('led')
        self.signals.done.emit()


    async def wb_sensors(self):
        d = {
            'bat': '',
            'gst': '',
            'gsp': '',
            'acc': '',
            'gsc': '',
            'gdo': ''
        }

        rv, v = await cmd_bat()
        if rv:
            self._ser('bat')
            return
        d['bat'] = v

        if g_glt in ('TDO', 'CTD'):
            rv, v = await cmd_gst()
            if rv:
                self._ser('gst')
                return
            d['gst'] = v
            rv, v = await cmd_gsp()
            if rv:
                self._ser('gsp')
                return
            d['gsp'] = v
            # todo: do accelerometer

        if g_glt == 'CTD':
            rv, v = await cmd_gsc()
            if rv:
                self._ser('gsc')
                return
            d['gsc'] = v

        if g_glt.startswith('DO'):
            rv, v = await cmd_gdx()
            if rv:
                self._ser('gdx')
                return
            d['gdo'] = v

        self.signals.sensors.emit(d)
        self.signals.done.emit()


    async def wb_gcc(self):
        rv, s = await cmd_gcc()
        if rv:
            self._ser('gcc')
            return
        self.signals.gcc.emit(s)
        self.signals.done.emit()


    async def wb_gcf(self):
        rv, s = await cmd_gcf()
        if rv:
            self._ser('gcf')
            return
        self.signals.gcf.emit(s)
        self.signals.done.emit()


    async def wb_scc(self):
        d = g_d
        rv = 0
        for k, v in d.items():
            # todo: see we want to enforce MAC
            if k == 'MAC':
                continue
            if type(v) is not str:
                v = num_to_ascii85(v)
            rv = await cmd_scc(k, v)
            if rv:
                self._ser(f'scc, tag {k}')
                break
        if rv == 0:
            rv, s = await cmd_gcc()
            if rv:
                self._ser('gcc after scc')
                return
            self.signals.gcc.emit(s)
        self.signals.done.emit()


    async def wb_scf(self):
        d = g_d
        rv = 0
        for k, v in d.items():
            rv = await cmd_scf(k, v)
            if rv:
                self._ser(f'scf, tag {k}')
                break
        if rv == 0:
            rv, s = await cmd_gcf()
            if rv:
                self._ser('gcf after scf')
                return
            self.signals.gcf.emit(s)
        self.signals.done.emit()


    async def wb_beh(self):
        d = g_d
        for k, v in d.items():
            rv = await cmd_beh(k, v)
            if rv:
                self._ser(f'beh, tag {k}')
                break
        self.signals.done.emit()


    @pyqtSlot()
    def run(self):
        for fn in self.ls_fn:
            global g_busy
            g_busy = True
            print("thread start")
            loop.run_until_complete(fn())
            print("thread complete")
            g_busy = False


    def __init__(self, ls_gui_cmd, *args, **kwargs):
        super().__init__()
        d = {
            'wb_connect': self.wb_connect,
            'wb_disconnect': self.wb_disconnect,
            'wb_sensors': self.wb_sensors,
            'wb_run': self.wb_run,
            'wb_stop': self.wb_stp,
            'wb_sts': self.wb_sts,
            'wb_frm': self.wb_frm,
            'wb_led': self.wb_led,
            'wb_gcc': self.wb_gcc,
            'wb_gcf': self.wb_gcf,
            'wb_scc': self.wb_scc,
            'wb_scf': self.wb_scf,
            'wb_beh': self.wb_beh,
            'wb_download': self.wb_download,
            'wb_mts': self.wb_mts,
            'wb_gec': self.wb_gec
        }
        self.ls_fn = []
        if type(ls_gui_cmd) is str:
            ls_gui_cmd = [ls_gui_cmd]
        for i in ls_gui_cmd:
            self.ls_fn.append(d[i])
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()



class MyPlotWidget(pg.PlotWidget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scene().sigMouseClicked.connect(self.mouse_clicked)

    def mouse_clicked(self, mouseClickEvent):
        print('clicked plot 0x{:x}, event: {}'.format(id(self), mouseClickEvent))
        ev = mouseClickEvent
        print('x = {}'.format(self.mapToView(ev.pos()).x()))
        ts = self.mapToView(ev.pos()).x()
        print(f't = {datetime.fromtimestamp(ts)}')
        print('y = {}'.format(self.mapToView(ev.pos()).y()))



class Bix(QMainWindow, Ui_MainWindow):

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
            self.lst_known_macs.addItem(f'error: opening TOML file {bn} -> {e}')


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


    def slot_signal_converting(self):
        self.lbl_busy.setStyleSheet('color: yellow')
        self.lbl_busy.setText('converting')


    def slot_signal_download(self, s):
        self.lbl_download.setText(s)


    def slot_signal_error(self, e):
        print(f'logger {e}')
        self.lbl_busy.setStyleSheet('color: red')
        self.lbl_busy.setText(f'{e}')


    def slot_signal_status(self, s):
        print(f'logger is {s}')
        self.lbl_sts.setText(s)


    def slot_signal_gcc(self, s):
        self.lbl_table.setText('Table calibration contents')
        # todo: move all this inside function fill()
        s = s[6:]
        d = create_calibration_dictionary()
        for i, v in enumerate(d.items()):
            k, _ = v
            d[k] = s[(i * 5):(i * 5) + 5]
        fill_calibration_table(self, d)


    def slot_signal_gcf(self, s):
        self.lbl_table.setText('Table profile contents')
        s = s[6:]
        d = create_profile_dictionary()
        for i, v in enumerate(d.items()):
            k, _ = v
            d[k] = s[(i * 5):(i * 5) + 5]
        fill_profile_table(self, d)


    def slot_signal_connected(self):
        self.pages.setCurrentIndex(1)
        print('GUI connected')
        self.lbl_connecting.setText('')


    def slot_signal_disconnected(self):
        self.pages.setCurrentIndex(0)
        print('GUI disconnected')


    def slot_signal_info(self, d: dict):
        self.lbl_sn.setText(d['sn'])
        self.lbl_mac.setText(d['mac'])
        self.lbl_gfv.setText(d['gfv'])
        glt = d['glt']
        self.lbl_glt.setText(glt)
        self.table.setVisible(glt in ('TDO', 'CTD'))


    def slot_signal_sensors(self, d: dict):

        # show some sensors, some not
        v = self.lbl_glt.text()
        self.lbl_gst.setVisible(False)
        self.lbl_gsp.setVisible(False)
        self.lbl_acc.setVisible(False)
        self.lbl_gsc.setVisible(False)
        self.lbl_gdo.setVisible(False)

        if v in ('TDO', 'CTD'):
            self.lbl_gst.setVisible(True)
            self.lbl_gsp.setVisible(True)
            self.lbl_acc.setVisible(True)

            v = str(d['gst'])
            s = f'Temperature\n\n{v}\n\nCelsius'
            self.lbl_gst.setText(s)
            print(f'GST {v}')

            v = str(d['gsp'])
            s = f'Pressure\n\n{v}\n\ndbar'
            self.lbl_gsp.setText(s)
            print(f'GSP {v}')

            v = str(d['acc'])
            s = f'Accelerometer\n\n{v}'
            self.lbl_acc.setText(s)
            print(f'ACC {v}')

        if v == 'CTD':
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

        if v.startswith('DO'):
            self.lbl_gdo.setVisible(True)
            v = str(d['gdo'])
            s = f'DOC\n\n{v}\n\nmg/l'
            self.lbl_gdo.setText(s)
            print(f'GDO {v}')


        v = str(d['bat'])
        s = f'{v} mV'
        self.lbl_bat.setText(s)
        print(f'BAT {v}')



    # -------------------
    # GUI button clicks
    # -------------------

    @staticmethod
    def dec_gui_busy(fxn):
        def wrapper(self, *args, **kwargs):
            # prevent smashing GUI buttons
            if g_busy:
                return
            self.lbl_busy.setText('busy')
            # calls GUI button function such as _on_click_btn_leds()
            fxn(self, *args, **kwargs)
        return wrapper


    def wrk(self, ls_s):
        # calls constructor in Worker class and bind its signals
        w = Worker(ls_s)
        w.signals.connected.connect(self.slot_signal_connected)
        w.signals.info.connect(self.slot_signal_info)
        w.signals.sensors.connect(self.slot_signal_sensors)
        w.signals.done.connect(self.slot_signal_done)
        w.signals.converting.connect(self.slot_signal_converting)
        w.signals.disconnected.connect(self.slot_signal_disconnected)
        w.signals.error.connect(self.slot_signal_error)
        w.signals.status.connect(self.slot_signal_status)
        w.signals.gcc.connect(self.slot_signal_gcc)
        w.signals.gcf.connect(self.slot_signal_gcf)
        w.signals.download.connect(self.slot_signal_download)
        # run() in Worker class, which signals results to our slot_signals_x()
        self.threadpool.start(w)


    def on_click_lst_known_macs(self):
        global g_mac
        _it = self.lst_known_macs.currentItem().text()
        g_mac = str(_it.split(' - ')[0])


    @dec_gui_busy
    def on_click_btn_connect(self, _):
        if g_mac == mac_test():
            self.lbl_connecting.setText(f'connecting hard-coded {g_mac}')
        else:
            self.lbl_connecting.setText(f'connecting {g_mac}')
        self.wrk([
            'wb_connect',
            'wb_sensors',
            'wb_gcc'])


    @dec_gui_busy
    def on_click_btn_disconnect(self, _):
        self.wrk('wb_disconnect')


    @dec_gui_busy
    def on_click_btn_sensors(self, _):
        self.wrk('wb_sensors')


    @dec_gui_busy
    def on_click_btn_download(self, _):
        self.lbl_download.setText('')
        self.wrk('wb_download')


    @dec_gui_busy
    def on_click_btn_mts(self, _):
        self.wrk('wb_mts')


    @dec_gui_busy
    def on_click_btn_gec(self, _):
        self.wrk('wb_gec')


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
        dlg.setWindowTitle("Are you sure?")
        dlg.setText("This deletes all files in  logger!")
        dlg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        dlg.setIcon(QMessageBox.Icon.Question)
        if dlg.exec() == QMessageBox.StandardButton.Yes:
            self.wrk('wb_frm')


    @dec_gui_busy
    def on_click_btn_led(self, _):
        self.wrk('wb_led')


    @dec_gui_busy
    def on_click_btn_gcc(self, _):
        self.wrk('wb_gcc')


    @dec_gui_busy
    def on_click_btn_gcf(self, _):
        self.wrk('wb_gcf')


    @dec_gui_busy
    def on_click_btn_scf(self, _):
        d = self.dialog_import_file_profile()
        if not d:
            return
        self.table.clear()
        global g_d
        g_d = d['profiling']
        self.wrk('wb_scf')


    @dec_gui_busy
    def on_click_btn_scc(self, _):
        d = self.dialog_import_file_calibration()
        if not d:
            return
        self.table.clear()
        global g_d
        g_d = d['calibration']
        self.wrk('wb_scc')


    @dec_gui_busy
    def on_click_btn_beh(self, _):
        d = self.dialog_import_file_behavior()
        if not d:
            return
        global g_d
        g_d = d['behavior']
        self.wrk('wb_beh')


    def on_click_btn_plot(self, _):
        p = self.dialog_import_file_csv_to_plot()
        # p = '/home/kaz/Downloads/dl_bil_v2/F0-5E-CD-25-92-F1/2508700_BIL_20250923_184053_TDO.csv'
        if not p:
            return
        self.lay.removeWidget(self.gr)
        self.gr = MyPlotWidget(
            # viewBox=CustomViewBox(),
            axisItems={'bottom': pg.DateAxisItem()})
        self.lay.addWidget(self.gr)
        df = pd.read_csv(p)
        x = df['ISO 8601 Time'].values
        y = df['raw ADC Pressure'].values
        xf = []
        for i in x:
            dt = datetime.strptime(i, '%Y-%m-%dT%H:%M:%S.000Z').timestamp()
            xf.append(dt)
        self.gr.plot(xf, y, pen='b', symbol='o', symbolSize=5, name="My Data")
        self.gr.setBackground("white")
        pen = pg.mkPen(color=(255, 0, 0))
        bn = os.path.basename(p)
        self.lbl_plot.setText(bn)
        self.gr.setVisible(True)

        view_box = self.gr.plotItem.vb
        view_box.setMouseEnabled(x=True, y=True)


    def on_click_btn_import_macs(self, _):
        d = self.dialog_import_macs()
        if not d:
            return
        self.lst_known_macs.clear()
        d = d['aliases']
        for k, v in d.items():
            self.lst_known_macs.addItem(f'{k} - {v}')


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
        if g_busy and 'done' not in s:
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
        self.setWindowTitle("BIX")
        self.threadpool = QThreadPool()
        self.setFixedWidth(1024)
        self.setFixedHeight(768)
        self.lbl_gui_version.setText('v' + self._get_version())
        if os.path.exists(DEV_SHM_DL_PROGRESS):
            os.unlink(DEV_SHM_DL_PROGRESS)
        self.progressBar.setValue(0)
        self.lbl_download.setText('')


        # buttons
        self.btn_connect.clicked.connect(self.on_click_btn_connect)
        self.btn_disconnect.clicked.connect(self.on_click_btn_disconnect)
        self.btn_sensors.clicked.connect(self.on_click_btn_sensors)
        self.btn_test.clicked.connect(self.on_click_btn_test)
        self.btn_rws.clicked.connect(self.on_click_btn_run)
        self.btn_sws.clicked.connect(self.on_click_btn_stop)
        self.btn_sts.clicked.connect(self.on_click_btn_sts)
        self.btn_frm.clicked.connect(self.on_click_btn_frm)
        self.lst_known_macs.itemClicked.connect(self.on_click_lst_known_macs)
        self.btn_led.clicked.connect(self.on_click_btn_led)
        self.btn_gcc.clicked.connect(self.on_click_btn_gcc)
        self.btn_gcf.clicked.connect(self.on_click_btn_gcf)
        self.btn_scc.clicked.connect(self.on_click_btn_scc)
        self.btn_scf.clicked.connect(self.on_click_btn_scf)
        self.btn_beh.clicked.connect(self.on_click_btn_beh)
        self.btn_import_macs.clicked.connect(self.on_click_btn_import_macs)
        self.btn_download.clicked.connect(self.on_click_btn_download)
        self.btn_mts.clicked.connect(self.on_click_btn_mts)
        self.btn_gec.clicked.connect(self.on_click_btn_gec)
        self.btn_plot.clicked.connect(self.on_click_btn_plot)



        # be sure we are disconnected
        # todo: remove this
        ble_linux_disconnect_by_mac(g_mac)

        # create timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.timer_cb)
        self.timer.start(1000)

        # plots
        self.gr = MyPlotWidget(
            # viewBox=CustomViewBox(),
            axisItems={'bottom': pg.DateAxisItem()})
        self.gr.setVisible(False)


        # what to show upon boot
        self.pages.setCurrentIndex(0)
        self.tabs.setCurrentIndex(0)


        # auto-import MAC file
        self.lst_known_macs.clear()
        if os.path.exists(DEF_ALIASES_FILE_PATH):
            print(f'auto-importing alias file {DEF_ALIASES_FILE_PATH}')
            d = toml.load(DEF_ALIASES_FILE_PATH)
            d = d['aliases']
            for k, v in d.items():
                self.lst_known_macs.addItem(f'{k} - {v}')


        # uncomment when needed
        self.btn_test.setVisible(False)


        # move window
        center = QtGui.QGuiApplication.primaryScreen().geometry().center()
        self.move(center - self.rect().center())



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

