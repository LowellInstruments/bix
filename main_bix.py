import sys
from PyQt6.QtCore import (
    QThreadPool, QObject,
    pyqtSignal, QRunnable, pyqtSlot,
)
from PyQt6.QtGui import QScreen, QStandardItemModel, QStandardItem
from PyQt6.QtWidgets import QApplication, QMainWindow, QTableWidgetItem
from bix.gui.gui import Ui_MainWindow
import setproctitle
from bix.gui.populate import populate_cal_table
from ble.ble import *
from ble.ble_linux import ble_linux_disconnect_by_mac



g_busy = False
loop = asyncio.get_event_loop()
MAC_TEST = "D0:2E:AB:D9:29:48"



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
        v = self.sb_logger_type.currentText()
        self.frame.setVisible(v in ('TDO', 'CTD'))


    def slot_signal_disconnected(self):
        self.pages.setCurrentIndex(0)
        print('GUI disconnected')


    def slot_signal_info(self, d: dict):
        self.lbl_sn.setText(d['sn'])
        self.lbl_mac.setText(d['mac'])
        self.lbl_gfv.setText(d['gfv'])
        self.lbl_type.setText(d['glt'])


    def slot_signal_sensors(self, d: dict):
        v = str(d['gst'])
        self.lbl_gst.setText(str(v))
        print(f'GST {v}')
        v = str(d['gsp'])
        self.lbl_gsp.setText(str(v))
        print(f'GSP {v}')




    # -------------------
    # GUI button clicks
    # -------------------

    @dec_is_busy
    def on_click_btn_connect(self, _):
        w = Worker('wb_connect')
        w.signals.connected.connect(self.slot_signal_connected)
        w.signals.info.connect(self.slot_signal_info)
        w.signals.sensors.connect(self.slot_signal_sensors)
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
        self.tbl_gcc.clear()
        self.pages.setCurrentIndex(1)


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

        # populate select boxes
        self.sb_logger_type.addItem('TDO')
        self.sb_logger_type.addItem('CTD')
        self.sb_logger_type.addItem('DOX')

        # populate MAC list view
        self.lst_known_macs.addItem('mac1')
        self.lst_known_macs.addItem('mac2')

        # create empty GCC table
        d_scc = {'TMR': (9, 985)}
        populate_cal_table(self, d_scc)
        # populate_gcf_table(self, d_scf)

        # be sure we are disconnected
        ble_linux_disconnect_by_mac(MAC_TEST)




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

