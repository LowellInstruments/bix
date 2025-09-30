import os
from PyQt6.QtCore import QRunnable, pyqtSlot
from bix.utils import WorkerSignals, FOL_BIL, global_get, global_set
from ble.ble import *
from lix.ascii85 import num_to_ascii85
from lix.lix import parse_file_lid_v5



loop = asyncio.new_event_loop()



class WorkerBle(QRunnable):

    def _ser(self, e: str):
        self.signals.error.emit(f'error {e}')



    async def _bad_we_are_running(self, s):
        rv, v = await cmd_sts()
        if rv:
            self._ser(f'sts while {s}')
            return True
        if v == 'running':
            self._ser(f'{s} while running')
            return True
        return False


    async def wb_download(self):
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
            print(f'downloading file {i + 1} / {n}')
            self.signals.download.emit(f'getting\nfile {i + 1} of {n}')
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
        mac = global_get('mac')
        rv = await connect_by_mac(mac)
        if rv == 0:
            self._ser('connecting')
            return
        self.signals.connected.emit()

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
        global_set('glt', v)

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
        if await self._bad_we_are_running('MTS'):
            return
        rv = await cmd_mts()
        if rv:
            self._ser('mts')
            return
        self.signals.done.emit()


    async def wb_gec(self):
        if await self._bad_we_are_running('GEC'):
            return
        rv, v = await cmd_gec()
        if rv:
            self._ser('gec')
            return
        print('GEC rv, v', rv, v)
        self.signals.done.emit()


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
            s = f'MUX {i} = V1 V2'
        elif i == 1:
            s = f'MUX {i} = V2 V1'
        elif i == 2:
            s = f'MUX {i} = C2 C1'
        elif i == 3:
            s = f'MUX {i} = C1 C2'
        elif i == 4:
            s = f'MUX {i} = all shorted'
        elif i == 5:
            s = f'MUX {i} = all open'
        self.signals.result.emit(s)


    async def wb_sts(self):
        rv, v = await cmd_sts()
        if rv:
            self._ser('sts')
            return
        self.signals.status.emit(v)
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

        g_glt = global_get('glt')
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
        d = global_get('table_calibration')
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
        if await self._bad_we_are_running('SCF'):
            return
        d = global_get('table_profile')
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
        d = global_get('table_behavior')
        for k, v in d.items():
            rv = await cmd_beh(k, v)
            if rv:
                self._ser(f'beh, tag {k}')
                break
        self.signals.done.emit()


    @pyqtSlot()
    def run(self):
        for fn in self.ls_fn:
            global_set('busy', 1)
            print("thread start")
            loop.run_until_complete(fn())
            print("thread complete")
            global_set('busy', 0)


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
            'wb_gec': self.wb_gec,
            'wb_mux': self.wb_mux,
        }
        self.ls_fn = []
        if type(ls_gui_cmd) is str:
            ls_gui_cmd = [ls_gui_cmd]
        for i in ls_gui_cmd:
            self.ls_fn.append(d[i])
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
