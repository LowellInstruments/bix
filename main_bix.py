import sys
from PyQt6.QtCore import (
    QThreadPool, QObject,
    pyqtSignal, QRunnable, pyqtSlot,
)
from PyQt6.QtGui import QScreen
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QFileDialog,
    QListWidgetItem
)

from bix.constants import PATH_ALIAS_FILE, mac_test, RVN_SCC_4, FOL_BIL
from bix.gui.gui import Ui_MainWindow
import setproctitle
from bix.gui.populate import populate_cal_table
from ble.ble import *
from ble.ble_linux import ble_linux_disconnect_by_mac
import toml



g_mac = mac_test()
g_busy = False
# todo: manage python versions here
loop = asyncio.get_event_loop()




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



class Worker(QRunnable):

    def _ser(self, e: str):
        self.signals.error.emit(f'error {e}')


    async def wb_connect(self):
        mac = g_mac
        rv = await connect_by_mac(mac)
        if rv == 0:
            self._ser('connecting')
            return
        d = {}
        rv, v = await cmd_glt()
        if rv:
            self._ser('glt')
            return
        d['glt'] = v
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
        self.signals.connected.emit()


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
        d = {}
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
        rv, v = await cmd_bat()
        if rv:
            self._ser('bat')
            return
        d['bat'] = v
        # todo: do accelerometer
        d['acc'] = 'N/A'
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



    @pyqtSlot()
    def run(self):
        for fn in self.ls_fn:
            global g_busy
            g_busy = True
            print("thread start")
            loop.run_until_complete(fn())
            print("thread complete")
            g_busy = False


    def __init__(self, ls_op, *args, **kwargs):
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
        }
        self.ls_fn = []
        if type(ls_op) is str:
            ls_op = [ls_op]
        for i in ls_op:
            self.ls_fn.append(d[i])
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()



class Bix(QMainWindow, Ui_MainWindow):

    def dec_is_busy(fxn):
        def wrapper(self, *args, **kwargs):
            if g_busy:
                return
            self.lbl_gui_busy.setText('busy')
            fxn(self, *args, **kwargs)
        return wrapper


    def on_click_btn_test(self):
        self.pages.setCurrentIndex(1)


    def _load_file_logger_aliases(self, p=PATH_ALIAS_FILE):
        self.lst_known_macs.clear()
        try:
            data = toml.load(p)
            d = data['aliases']
            for k, v in d.items():
                self.lst_known_macs.addItem(f'{k} - {v}')

        except (Exception, ) as e:
            self.lst_known_macs.addItem(f'error: logger aliases file -> {e}')


    def open_dialog_import_macs(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            'Select file with MAC list',
            FOL_BIL,
            'TOML Files (*.toml)'
        )

        # import the MAC file content
        _it = QListWidgetItem(f'error: importing file {str(path)}')
        self._load_file_logger_aliases(path)


    def slot_signal_done(self):
        self.lbl_gui_busy.setText('done')


    def slot_signal_error(self, e):
        print(f'logger {e}')
        self.lbl_sts.setText(f'{e}')


    def slot_signal_status(self, s):
        print(f'logger is {s}')
        self.lbl_sts.setText(s)


    def slot_signal_gcc(self, s):
        print('rxed gcc', s)
        self.lbl_table.setText('Table calibration contents')
        s = s[6:]
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
        for i, v in enumerate(d.items()):
            k, _ = v
            d[k] = s[(i * 5):(i * 5) + 5]
        populate_cal_table(self, d)


    def slot_signal_gcf(self, s):
        print('rxed gcf', s)
        self.lbl_table.setText('Table profile contents')
        s = s[6:]
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
        for i, k, _ in enumerate(d.items()):
            d[k] = s[(i * 5):(i * 5) + 5]
        populate_cal_table(self, d)


    def slot_signal_connected(self):
        self.pages.setCurrentIndex(1)
        print('GUI connected')


    def slot_signal_disconnected(self):
        self.pages.setCurrentIndex(0)
        print('GUI disconnected')


    def slot_signal_info(self, d: dict):
        self.lbl_sn.setText(d['sn'])
        self.lbl_mac.setText(d['mac'])
        self.lbl_gfv.setText(d['gfv'])
        glt = d['glt']
        self.lbl_type.setText(glt)
        self.tbl_gcc.setVisible(glt in ('TDO', 'CTD'))


    def slot_signal_sensors(self, d: dict):
        v = str(d['gst'])
        self.lbl_gst.setText(str(v))
        print(f'GST {v}')
        v = str(d['gsp'])
        self.lbl_gsp.setText(str(v))
        print(f'GSP {v}')
        v = str(d['bat'])
        self.lbl_bat.setText(str(v))
        print(f'BAT {v}')
        v = str(d['acc'])
        self.lbl_acc.setText(str(v))
        print(f'ACC {v}')


    # -------------------
    # GUI button clicks
    # -------------------

    # def _create_worker(self, s):
    #     w = Worker(s)
    #     w.signals.connected.connect(self.slot_signal_connected)
    #     w.signals.info.connect(self.slot_signal_info)
    #     w.signals.sensors.connect(self.slot_signal_sensors)
    #     w.signals.done.connect(self.slot_signal_done)
    #     w.signals.disconnected.connect(self.slot_signal_disconnected)
    #     w.signals.error.connect(self.slot_signal_error)
    #     w.signals.status.connect(self.slot_signal_status)
    #     w.signals.gcc.connect(self.slot_signal_gcc)
    #     w.signals.gcf.connect(self.slot_signal_gcf)
    #     self.threadpool.start(w)

    def _create_worker(self, ls_s):
        w = Worker(ls_s)
        w.signals.connected.connect(self.slot_signal_connected)
        w.signals.info.connect(self.slot_signal_info)
        w.signals.sensors.connect(self.slot_signal_sensors)
        w.signals.done.connect(self.slot_signal_done)
        w.signals.disconnected.connect(self.slot_signal_disconnected)
        w.signals.error.connect(self.slot_signal_error)
        w.signals.status.connect(self.slot_signal_status)
        w.signals.gcc.connect(self.slot_signal_gcc)
        w.signals.gcf.connect(self.slot_signal_gcf)
        self.threadpool.start(w)


    def on_click_lst_known_macs(self):
        global g_mac
        _it = self.lst_known_macs.currentItem().text()
        g_mac = str(_it.split(' - ')[0])


    @dec_is_busy
    def on_click_btn_connect(self, _):
        if g_mac == mac_test():
            self.lbl_connect.setText(f'connecting hard-coded {g_mac}')
        else:
            self.lbl_connect.setText(f'connecting {g_mac}')
        self._create_worker([
            'wb_connect',
            'wb_sensors',
            'wb_gcc'])


    @dec_is_busy
    def on_click_btn_disconnect(self, _):
        self._create_worker('wb_disconnect')


    @dec_is_busy
    def on_click_btn_sensors(self, _):
        self._create_worker('wb_sensors')


    @dec_is_busy
    def on_click_btn_run(self, _):
        self._create_worker('wb_run')


    @dec_is_busy
    def on_click_btn_stop(self, _):
        self._create_worker('wb_stop')


    @dec_is_busy
    def on_click_btn_sts(self, _):
        self._create_worker('wb_sts')


    @dec_is_busy
    def on_click_btn_frm(self, _):
        self._create_worker('wb_frm')


    @dec_is_busy
    def on_click_btn_led(self, _):
        self._create_worker('wb_led')


    @dec_is_busy
    def on_click_btn_gcc(self, _):
        self._create_worker('wb_gcc')


    @dec_is_busy
    def on_click_btn_gcf(self, _):
        self._create_worker('wb_gcf')


    def __init__(self):
        super(Bix, self).__init__()
        self.setupUi(self)
        self.setWindowTitle("BIX")
        self.setCentralWidget(self.pages)
        self.pages.setCurrentIndex(0)
        center = QScreen.availableGeometry(QApplication.primaryScreen()).center()
        geo = self.frameGeometry()
        geo.moveCenter(center)
        self.setFixedWidth(1024)
        self.setFixedHeight(768)

        # async stuff
        self.threadpool = QThreadPool()

        # buttons
        self.btn_connect.clicked.connect(self.on_click_btn_connect)
        self.btn_disconnect.clicked.connect(self.on_click_btn_disconnect)
        self.btn_sensors.clicked.connect(self.on_click_btn_sensors)
        self.btn_test.clicked.connect(self.on_click_btn_test)
        self.btn_rws.clicked.connect(self.on_click_btn_run)
        self.btn_sws.clicked.connect(self.on_click_btn_stop)
        self.btn_sts.clicked.connect(self.on_click_btn_sts)
        self.btn_frm.clicked.connect(self.on_click_btn_frm)
        self.btn_import_macs.clicked.connect(self.open_dialog_import_macs)
        self.lst_known_macs.itemClicked.connect(self.on_click_lst_known_macs)
        self.btn_led.clicked.connect(self.on_click_btn_led)
        self.btn_gcc.clicked.connect(self.on_click_btn_gcc)
        self.btn_gcf.clicked.connect(self.on_click_btn_gcf)


        # be sure we are disconnected
        # todo: remove this
        ble_linux_disconnect_by_mac(g_mac)

        # import macs list
        self._load_file_logger_aliases()
        self.lst_known_macs.clearSelection()



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

