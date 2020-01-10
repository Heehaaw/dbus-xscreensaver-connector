#!/usr/bin/python
import subprocess
from threading import Timer

import dbus


class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


PM_IFACE = 'org.freedesktop.PowerManagement.Inhibit'
PM_PATH = '/org/freedesktop/PowerManagement/Inhibit'
SS_IFACE = 'org.freedesktop.ScreenSaver'
MATCH_STRINGS = [
    # f"eavesdrop=true, interface='{PM_IFACE}', path='{PM_PATH}'",
    f"eavesdrop=true, interface='{SS_IFACE}', path='/org/freedesktop/ScreenSaver'",
    f"eavesdrop=true, interface='{SS_IFACE}', path='/ScreenSaver'"
]
INHIBIT_MEMBER = "Inhibit"
UN_INHIBIT_MEMBER = "UnInhibit"

ORIGIN_BLACKLIST = ['My SDL application', '/usr/bin/gpmdp']

XSCREENSAVER_CMD = ["xscreensaver", "-no-splash"]
XSCREENSAVER_DISRUPT_CMD = ["xscreensaver-command", "-deactivate"]
DISRUPT_TIMER_SECONDS = 540

timer = None
xscreensaver = None


def disrupt_xscreensaver():
    print(f'Disrupting xscreensaver - [{DISRUPT_TIMER_SECONDS}]s passed')
    subprocess.Popen(XSCREENSAVER_DISRUPT_CMD).wait()


def toggle_xscreensaver(val):
    global xscreensaver, timer

    if val:
        if timer is not None and timer.is_alive():
            print('Stopping the disrupt timer')
            timer.cancel()
            timer.join()
            timer = None
    elif timer is None or not timer.is_alive():
        print('Starting the disrupt timer')
        timer = RepeatTimer(DISRUPT_TIMER_SECONDS, disrupt_xscreensaver)
        timer.start()


def handle(_, message):
    iface = message.get_interface()
    member = message.get_member()

    p1 = p2 = None
    args = message.get_args_list()
    if len(args) >= 2:
        p1, p2 = args

    if member == INHIBIT_MEMBER:
        if p1 is not None and any(b for b in ORIGIN_BLACKLIST if b in p1):
            print(f'App is blacklisted... iface: [{iface}], member: [{member}], app: [{p1}], reason: [{p2}]')
        else:
            print(f'Toggling xscreensaver OFF... iface: [{iface}], member: [{member}], app: [{p1}], reason: [{p2}]')
            toggle_xscreensaver(False)
            return True

    elif member == UN_INHIBIT_MEMBER:
        print(f'Toggling xscreensaver ON... iface: [{iface}], member: [{member}]')
        toggle_xscreensaver(True)
        return True


if __name__ == '__main__':
    from dbus.mainloop.glib import DBusGMainLoop
    from gi.repository import GLib

    DBusGMainLoop(set_as_default=True)

    bus = dbus.SessionBus()
    mainLoop = GLib.MainLoop()

    try:
        xscreensaver = subprocess.Popen(XSCREENSAVER_CMD)
        toggle_xscreensaver(True)

        for s in MATCH_STRINGS:
            bus.add_match_string(s)
        bus.add_message_filter(handle)

        mainLoop.run()

    except KeyboardInterrupt:
        print("keyboard interrupt received")
    except Exception as e:
        print("Unexpected exception occurred: '{}'".format(str(e)))
    finally:
        xscreensaver.terminate()
        xscreensaver.wait()
        mainLoop.quit()
