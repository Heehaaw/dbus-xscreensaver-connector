#!/usr/bin/python

import re
import subprocess


class Handler:
	SIGNAL_REGEX = r'\b(?:signal|method call|method return)\b time=[\d,.]* sender=[\w,.,:,(,), ]* -> destination=[\w,.,:,(,), ]* serial=[(,),\w]* path=[\w,\/]*; interface=([\w,.]*); member=([\w,_,-]*)?(?:reply_serial=([\d]*))?'
	PARAM_REGEX = r'\s*string "([^"]+)"'

	IFACE = "org.freedesktop.ScreenSaver"
	INHIBIT_MEMBER = "Inhibit"
	UN_INHIBIT_MEMBER = "UnInhibit"
	ORIGIN_BLACKLIST = ['My SDL application']

	MONITOR_CMD = ["dbus-monitor", "--session", "interface='org.freedesktop.ScreenSaver'"]
	XSCREENSAVER_CMD = ["xscreensaver", "-no-splash"]

	def __init__(self):

		self.xscreensaver = None
		self.toggleXscreensaver(True)

		try:

			iface = member = p1 = p2 = None

			for line in self.runMonitor():
				m = re.match(self.SIGNAL_REGEX, line)
				if m:
					iface = m[1]
					member = m[2]
					p1 = p2 = None
				else:
					m = re.match(self.PARAM_REGEX, line)
					if m:
						if p1 is not None:
							p2 = m[1]
						else:
							p1 = m[1]

				if self.handle(iface, member, p1, p2):
					iface = member = p1 = p2 = None

		finally:
			self.toggleXscreensaver(False)

	def runMonitor(self):

		with subprocess.Popen(self.MONITOR_CMD, stdout=subprocess.PIPE, universal_newlines=True) as p:

			for stdout_line in p.stdout:
				yield stdout_line

			p.stdout.close()

			return_code = p.wait()
			if return_code:
				raise subprocess.CalledProcessError(return_code, self.MONITOR_CMD)

	def toggleXscreensaver(self, val):

		if val and self.xscreensaver is None:
			self.xscreensaver = subprocess.Popen(self.XSCREENSAVER_CMD)
		else:
			if self.xscreensaver is not None:
				self.xscreensaver.terminate()
			self.xscreensaver = None

	def handle(self, iface, member, p1, p2):

		if iface == self.IFACE:
			if member == self.INHIBIT_MEMBER and p1 is not None and p2 is not None:
				print(self.ORIGIN_BLACKLIST)
				if any(s for s in self.ORIGIN_BLACKLIST if s in p1):
					print(f'App is blacklisted... iface: [{iface}], member: [{member}], app: [{p1}], reason: [{p2}]')
				else:
					print(f'Toggling xscreensaver OFF... iface: [{iface}], member: [{member}], app: [{p1}], reason: [{p2}]')
					self.toggleXscreensaver(False)
					return True
			elif member == self.UN_INHIBIT_MEMBER:
				print(f'Toggling xscreensaver ON! iface... [{iface}], member: [{member}]')
				self.toggleXscreensaver(True)
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
