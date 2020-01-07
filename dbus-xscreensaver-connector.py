#!/usr/bin/python
import re
import subprocess
from threading import Thread


class Handler:
    _SIGNAL_REGEX = r'\b(?:signal|method call|method return)\b time=[\d,.]* sender=[\w,.,:,(,), ]* -> destination=[\w,.,:,(,), ]* serial=[(,),\w]* path=[\w,' \
                    r'\/]*; interface=([\w,.]*); member=([\w,_,-]*)?(?:reply_serial=([\d]*))?'
    _PARAM_REGEX = r'\s*string "([^"]+)"'

    IFACES = ["org.freedesktop.PowerManagement.Inhibit", "org.freedesktop.ScreenSaver"]
    INHIBIT_MEMBER = "Inhibit"
    UN_INHIBIT_MEMBER = "UnInhibit"
    ORIGIN_BLACKLIST = ['My SDL application', '/usr/bin/gpmdp']

    MONITOR_CMD = ["dbus-monitor", "--session"]
    XSCREENSAVER_CMD = ["xscreensaver", "-no-splash"]

    def __init__(self):

        self._xscreensaver = None
        self.toggle_xscreensaver(True)

        try:
            self._start_monitor_threads()
        finally:
            self.toggle_xscreensaver(False)

    def toggle_xscreensaver(self, val):

        if val:
            if self._xscreensaver is None:
                self._xscreensaver = subprocess.Popen(self.XSCREENSAVER_CMD)
        else:
            if self._xscreensaver is not None:
                self._xscreensaver.terminate()
                self._xscreensaver.wait()
            self._xscreensaver = None

    def _start_monitor_threads(self):

        def _monitor_thread(monitor_interface):

            iface = member = p1 = p2 = None

            for line in self._run_monitor(monitor_interface):
                m = re.match(self._SIGNAL_REGEX, line)
                if m:
                    iface = m[1]
                    member = m[2]
                    p1 = p2 = None
                else:
                    m = re.match(self._PARAM_REGEX, line)
                    if m:
                        if p1 is not None:
                            p2 = m[1]
                        else:
                            p1 = m[1]

                if self._handle(iface, member, p1, p2):
                    iface = member = p1 = p2 = None

        threads = [Thread(target=_monitor_thread, args=(i,)) for i in self.IFACES]
        for t in threads:
            t.daemon = True
            t.start()
        for t in threads:
            t.join()

    def _run_monitor(self, monitor_interface):

        monitor_cmd = self.MONITOR_CMD + [f"interface={monitor_interface}"]
        with subprocess.Popen(monitor_cmd, stdout=subprocess.PIPE, universal_newlines=True) as p:

            for stdout_line in p.stdout:
                yield stdout_line

            p.stdout.close()

            return_code = p.wait()
            if return_code:
                raise subprocess.CalledProcessError(return_code, monitor_cmd)

    def _handle(self, iface, member, p1, p2):

        if iface in self.IFACES:
            if member == self.INHIBIT_MEMBER and p1 is not None and p2 is not None:
                if any(s for s in self.ORIGIN_BLACKLIST if s in p1):
                    print(f'App is blacklisted... iface: [{iface}], member: [{member}], app: [{p1}], reason: [{p2}]')
                else:
                    print(f'Toggling xscreensaver OFF... iface: [{iface}], member: [{member}], app: [{p1}], reason: [{p2}]')
                    self.toggle_xscreensaver(False)
                    return True
            elif member == self.UN_INHIBIT_MEMBER:
                print(f'Toggling xscreensaver ON! iface... [{iface}], member: [{member}]')
                self.toggle_xscreensaver(True)
                return True


if __name__ == '__main__':

    from dbus.mainloop.glib import DBusGMainLoop
    from gi.repository import GLib

    DBusGMainLoop(set_as_default=True)
    handler = Handler()
    mainLoop = GLib.MainLoop()

    try:
        mainLoop.run()
    except KeyboardInterrupt:
        print("keyboard interrupt received")
    except Exception as e:
        print("Unexpected exception occurred: '{}'".format(str(e)))
    finally:
        mainLoop.quit()
