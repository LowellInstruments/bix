import asyncio
import sys
from PyQt6.QtCore import (
    QRunnable,
    pyqtSlot,
    QThreadPool,
    QObject,
    pyqtSignal
)
from PyQt6.QtGui import QScreen
from PyQt6.QtWidgets import QApplication, QMainWindow
from bix.gui.gui import Ui_MainWindow
import setproctitle
from ble.ble import connect_by_mac, cmd_gfv, disconnect



loop = asyncio.get_event_loop()
g_busy = False



def dec_is_busy(fxn):
    def wrapper(*args, **kwargs):
        if g_busy:
            return
        fxn(*args, **kwargs)
    return wrapper



class WorkerSignals(QObject):
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    result = pyqtSignal(object)



class Worker(QRunnable):
    def __init__(self, operation, *args, **kwargs):
        super().__init__()
        d = {
            'wb_connect': self.wb_connect,
            'wb_disconnect': self.wb_disconnect,
            # 'command': gui_ble_command,
        }
        self.fn = d[operation]
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()


    async def wb_connect(self):
        await connect_by_mac("D0:2E:AB:D9:29:48")
        rv = await cmd_gfv()
        print(rv)
        if rv:
            self.signals.connected.emit()


    async def wb_disconnect(self):
        await disconnect()
        self.signals.disconnected.emit()


    @pyqtSlot()
    def run(self):
        global g_busy
        g_busy = True
        print("Thread start")
        loop.run_until_complete(self.fn())
        print("Thread complete")
        g_busy = False



class Bix(QMainWindow, Ui_MainWindow):

    def on_click_btn_connect(self):
        worker = Worker('wb_connect')
        self.threadpool.start(worker)
        self.pages.setCurrentIndex(1)


    @dec_is_busy
    def on_click_btn_disconnect(self):
        worker = Worker('wb_disconnect')
        self.threadpool.start(worker)
        self.pages.setCurrentIndex(0)


    def __init__(self):
        super(Bix, self).__init__()
        self.setupUi(self)
        self.setWindowTitle("Lowell Instruments' BIX")
        self.setCentralWidget(self.pages)
        self.pages.setCurrentIndex(0)

        center = QScreen.availableGeometry(QApplication.primaryScreen()).center()
        geo = self.frameGeometry()
        geo.moveCenter(center)
        self.move(geo.topLeft())
        self.setFixedWidth(1024)
        self.setFixedHeight(768)

        # buttons
        self.btn_connect.clicked.connect(self.on_click_btn_connect)
        self.btn_disconnect.clicked.connect(self.on_click_btn_disconnect)


        self.threadpool = QThreadPool()


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

