import os
from PyQt6.QtCore import QRunnable, pyqtSlot
from bix.utils import WorkerSignals, PATH_BIL_FOLDER, global_set
from ble.ble import *
from lix.ascii85 import num_to_ascii85
from lix.lix import parse_lid_v2_data_file, decode_accelerometer_measurement

loop = asyncio.new_event_loop()



class WorkerBle(QRunnable):

    def _ser(self, e: str):
        self.signals.error.emit(f'error, {e}')


    async def _bad_we_are_running(self, s):
        rv, v = await cmd_sts()
        if rv:
            self._ser(f'sts while {s}')
            return True
        if v == 'running':
            self._ser(f'{s} while running')
            return True
        return False


    async def wb_download_normal(self):
        if await self._bad_we_are_running('download'):
            return

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
            el = int(time.time())
            print(f'downloading file {i + 1} / {n}')
            self.signals.download.emit(f'get {name}\nfile {i + 1} of {n}')
            rv, data = await cmd_dwl(size)
            if rv:
                self._ser('dwl')
                return
            print(f'saving {name}')
            dst_filename = f'{PATH_BIL_FOLDER}/{name}'
            with open(dst_filename, 'wb') as f:
                f.write(data)
            el = int(time.time()) - el
            el = el if el else 1
            print('download speed = {} KB/s'.format((size / 1000) / el))

            time.sleep(1)

            # convert
            if dst_filename.endswith('.lid') and 'dummy' not in dst_filename:
                bn = os.path.basename(dst_filename)
                print(f'BIX converting {bn}')
                try:
                    self.signals.gui_status.emit('converting')
                    parse_lid_v2_data_file(dst_filename)
                except (Exception, ) as ex:
                    print(f'error converting {dst_filename} -> {ex}')
                    self._ser('converting')
                    return

        self.signals.done.emit()



    async def wb_download_fast(self):
        if await self._bad_we_are_running('download_fast'):
            return

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
            el = int(time.time())
            print(f'downloading fast file {i + 1} / {n}')
            self.signals.download.emit(f'get {name}\nfile {i + 1} of {n}')
            rv, data = await cmd_dwf(size)
            if rv:
                self._ser('dwf')
                return
            print(f'saving fast {name}')
            dst_filename = f'{PATH_BIL_FOLDER}/{name}'
            with open(dst_filename, 'wb') as f:
                f.write(data)
            el = int(time.time()) - el
            el = el if el else 1
            print('download fast speed = {} KB/s'.format((size / 1000) / el))

            time.sleep(1)

            # convert
            if dst_filename.endswith('.lid') and 'dummy' not in dst_filename:
                bn = os.path.basename(dst_filename)
                print(f'BIX converting {bn}')
                try:
                    self.signals.gui_status.emit('converting')
                    parse_lid_v2_data_file(dst_filename)
                except (Exception, ) as ex:
                    print(f'error converting {dst_filename} -> {ex}')
                    self._ser('converting')
                    return

        self.signals.done.emit()


    async def wb_disconnect(self):
        await disconnect()
        self.signals.disconnected.emit()
        self.signals.done.emit()



    async def wb_run(self):
        if await self._bad_we_are_running('RUN'):
            return

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
        self.signals.logger_status.emit('running')
        self.signals.done.emit()


    async def wb_stp(self):
        g = ("-3.333333", "-4.444444", None, None)
        rv = await cmd_sws(g)
        if rv:
            self._ser('sws')
            return
        self.signals.logger_status.emit('stopped')
        self.signals.done.emit()


    async def wb_mts(self):
        if await self._bad_we_are_running('MTS'):
            return
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
        self.signals.result.emit(f'GEC {v}')


    async def wb_mux(self):
        rv, v = await cmd_mux()
        if rv:
            self._ser('mux')
            return
        print('MUX rv, v', rv, v)
        self.signals.done.emit()
        i = int(v)
        s = ''
        if i == 0:
            s = f'MUX {i} = all open'
        elif i == 1:
            s = f'MUX {i} = all shorted'
        elif i == 2:
            s = f'MUX {i} = Cout'
        self.signals.result.emit(s)


    async def wb_gci(self):
        rv, v = await cmd_gci()
        if rv:
            self._ser('gci')
            return
        print('GCI rv, v', rv, v)
        self.signals.done.emit()
        i = int(v)
        self.signals.result.emit(f'GCI = {i} ms')


    async def wb_osc(self):
        rv, v = await cmd_osc()
        if rv:
            self._ser('osc')
            return
        print('OSC rv, v', rv, v)
        self.signals.done.emit()
        i = int(v)
        self.signals.result.emit(f'OSC = {i}')


    async def wb_sts(self):
        rv, v = await cmd_sts()
        if rv:
            self._ser('sts')
            return
        self.signals.logger_status.emit(v)
        self.signals.done.emit()


    async def wb_frm(self):
        if await self._bad_we_are_running('format'):
            return
        rv = await cmd_frm()
        if rv:
            self._ser('frm')
        self.signals.done.emit()


    async def wb_led(self):
        rv = await cmd_led()
        if rv:
            self._ser('led')
        self.signals.done.emit()


    async def wb_log(self):
        rv, v = await cmd_log()
        if rv:
            self._ser('log')
            return
        self.signals.done.emit()
        self.signals.result.emit(f'LOG {v}')



    async def wb_sensors(self):
        d = {
            'bat': '',
            'gst': '',
            'gsp': '',
            'gsc': '',
            'gdo': '',
            'gax': '',
            'gay': '',
            'gaz': '',
        }

        if not is_connected():
            self._ser('not connected while sensors')
            return

        rv, v = await cmd_bat()
        if rv:
            self._ser('bat while sensors')
            return
        d['bat'] = v

        rv, g_glt = await cmd_glt()
        if rv:
            self._ser('glt')
            return
        d['glt'] = v

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

            rv, v = await cmd_gsa()
            if rv:
                self._ser('gsa')
                return
            vax = decode_accelerometer_measurement(v[-6:-4])
            vay = decode_accelerometer_measurement(v[-4:-2])
            vaz = decode_accelerometer_measurement(v[-2:])
            d['gax'] = vax
            d['gay'] = vay
            d['gaz'] = vaz



        if g_glt == 'CTD':
            pass
            # rv, v = await cmd_gsc()
            # if rv:
            #     self._ser('gsc')
            #     return
            # d['gsc'] = v

        if g_glt.startswith('DO'):
            rv, v = await cmd_gdx()
            if rv:
                self._ser('gdx')
                return
            d['gdo'] = v

        self.signals.sensors.emit(d)
        self.signals.done.emit()


    async def wb_gcc(self):
        if not is_connected():
            self._ser('not connected while GCC')
            return
        if await self._bad_we_are_running('GCC'):
            return
        rv, s = await cmd_gcc()
        if rv:
            self._ser('gcc')
            return
        self.signals.gcc.emit(s)
        self.signals.done.emit()


    async def wb_gcf(self):
        if await self._bad_we_are_running('GCF'):
            return
        rv, s = await cmd_gcf()
        if rv:
            self._ser('gcf')
            return
        self.signals.gcf.emit(s)
        self.signals.done.emit()


    async def wb_scc(self):
        if await self._bad_we_are_running('SCC'):
            return
        d = self.d_args
        rv = 0
        for k, v in d.items():
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
        if await self._bad_we_are_running('SCF'):
            return
        d = self.d_args
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
        if await self._bad_we_are_running('BEH'):
            return
        d = self.d_args
        for k, v in d.items():
            rv = await cmd_beh(k, v)
            if rv:
                self._ser(f'beh, tag {k}')
                break
        self.signals.done.emit()



    async def wb_connect(self):
        mac = self.d_args['mac']
        rv = await connect_by_mac(mac)
        if rv == 0:
            self._ser('connecting')
            self.signals.cannot_connect.emit(mac)
            return
        self.signals.connected.emit()

        # we are connected, get logger info
        self.signals.gui_status.emit('querying')
        d = {}
        rv, v = await cmd_sts()
        if rv:
            self._ser('sts')
            return
        d['sts'] = v

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


    @pyqtSlot()
    def run(self):
        for fn in self.ls_fn:
            print('th_start', fn.__name__)
            global_set('busy', 1)
            loop.run_until_complete(fn())
            global_set('busy', 0)
            print('th_end', fn.__name__)


    def __init__(self, ls_gui_cmd, d_args):
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
            'wb_log': self.wb_log,
            'wb_gcc': self.wb_gcc,
            'wb_gcf': self.wb_gcf,
            'wb_scc': self.wb_scc,
            'wb_scf': self.wb_scf,
            'wb_beh': self.wb_beh,
            'wb_download_normal': self.wb_download_normal,
            'wb_download_fast': self.wb_download_fast,
            'wb_mts': self.wb_mts,
            'wb_gec': self.wb_gec,
            'wb_mux': self.wb_mux,
            'wb_osc': self.wb_osc,
            'wb_gci': self.wb_gci
        }
        self.ls_fn = []
        if type(ls_gui_cmd) is str:
            ls_gui_cmd = [ls_gui_cmd]
        for i in ls_gui_cmd:
            self.ls_fn.append(d[i])
        self.d_args = d_args
        self.signals = WorkerSignals()
