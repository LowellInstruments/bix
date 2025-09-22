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
from bix.gui.gui import Ui_MainWindow
import setproctitle
from bix.gui.populate import populate_cal_table, FOL_BIL
from ble.ble import *
from ble.ble_linux import ble_linux_disconnect_by_mac



g_mac = 'aaaa'
g_busy = False
MAC_TEST = "D0:2E:AB:D9:29:48"
# todo: manage python versions here
loop = asyncio.get_event_loop()




class WorkerSignals(QObject):
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    info = pyqtSignal(object)
    error = pyqtSignal(str)
    sensors = pyqtSignal(object)



class Worker(QRunnable):

    def __init__(self, operation, *args, **kwargs):
        super().__init__()
        d = {
            'wb_connect': self.wb_connect,
            'wb_disconnect': self.wb_disconnect,
            'wb_sensors': self.wb_sensors,
            # 'command': gui_ble_command,
        }
        self.fn = d[operation]
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()


    def _ser(self, e: str):
        self.signals.error.emit(f'error {e}')


    async def wb_connect(self):
        print('g_mac', g_mac)
        rv = await connect_by_mac(MAC_TEST)
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
        if d['glt'] not in ('TDO', 'CTD'):
            return
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
        self.signals.sensors.emit(d)



    async def wb_disconnect(self):
        await disconnect()
        self.signals.disconnected.emit()



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
        self.signals.sensors.emit(d)


    @pyqtSlot()
    def run(self):
        global g_busy
        g_busy = True
        print("thread start")
        loop.run_until_complete(self.fn())
        print("thread complete")
        g_busy = False



def dec_is_busy(fxn):
    def wrapper(*args, **kwargs):
        if g_busy:
            return
        fxn(*args, **kwargs)
    return wrapper




class Bix(QMainWindow, Ui_MainWindow):

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

    @dec_is_busy
    def on_click_btn_connect(self, _):
        w = Worker('wb_connect')
        w.signals.connected.connect(self.slot_signal_connected)
        w.signals.info.connect(self.slot_signal_info)
        w.signals.sensors.connect(self.slot_signal_sensors)
        global g_mac
        g_mac = 'pepa'
        self.threadpool.start(w)


    @dec_is_busy
    def on_click_btn_disconnect(self, _):
        w = Worker('wb_disconnect')
        w.signals.disconnected.connect(self.slot_signal_disconnected)
        self.threadpool.start(w)


    @dec_is_busy
    def on_click_btn_sensors(self, _):
        w = Worker('wb_sensors')
        w.signals.sensors.connect(self.slot_signal_sensors)
        self.threadpool.start(w)


    def on_click_btn_test(self):
        v = self.lst_known_macs.currentItem().text()
        print(v)
        self.pages.setCurrentIndex(1)


    def open_dialog_import_macs(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            'Select file with MAC list',
            FOL_BIL,
            'TOML Files (*.toml)'
        )


        # import the MAC file content
        _it = QListWidgetItem(f'error: importing file {str(path)}')
        self.lst_known_macs.clear()
        if not path:
            self.lst_known_macs.addItem(_it)
            return
        try:
            with open(path, 'r') as f:
                # todo: read toml
                ll = f.read()
        except (Exception, ):
            self.lst_known_macs.addItem(_it)


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

        # populate MAC list view
        self.lst_known_macs.addItem('mac1')
        self.lst_known_macs.addItem('mac2')

        # create empty GCC table
        d_scc = {'TMR': (9, 985)}
        populate_cal_table(self, d_scc)
        # populate_gcf_table(self, d_scf)

        # CSS stuff
        self.setStyleSheet("""
        QProgressBar {
         height: 50px;
        }
        QProgressBar::chunk {
         height: 50px;
        }
        """)

        # be sure we are disconnected
        # todo: remove this
        ble_linux_disconnect_by_mac(MAC_TEST)

        # import macs list
        self.btn_import_macs.clicked.connect(self.open_dialog_import_macs)





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

