import sublime
import threading
import time
import traceback

class Event(object):
	def __init__(self):
		self.lst = []
		self.lck = threading.Lock()
		self.post_add = None

	def __call__(self, *args, **kwargs):
		with self.lck:
			l = self.lst[:]

		for f in l:
			try:
				f(*args, **kwargs)
			except Exception:
				print(traceback.format_exc())

		return self

	def __iadd__(self, f):
		with self.lck:
			self.lst.append(f)

		if self.post_add:
			try:
				self.post_add(self, f)
			except Exception:
				print(traceback.format_exc())

		return self

	def __isub__(self, f):
		with self.lck:
			self.lst.remove(f)

		return self

class Signal(Event):
	def __init__(self, delay_ms):
		Event.__init__(self)

		self.n = 0

		self.delay = max(10, delay_ms)
		self.deadline = 0
		self.running = False

	def __call__(self):
		with self.lck:
			self.deadline = (self.tms() + self.delay)

		self._sched()

	def tms(self):
		return int(time.time() * 1000)

	def _sched(self, ms=0):
		with self.lck:
			if not self.running:
				if ms <= 0:
					ms = self.delay

				self.running = True
				sublime.set_timeout(self._timedout, ms)

	def _timedout(self):
		with self.lck:
			self.running = False
			deadline = self.deadline

		ms = deadline - self.tms()
		if ms <= 0:
			Event.__call__(self)
		else:
			self._sched(ms)

debug = Event()
init = Event()
modified = Event()
line_changed = Event()
