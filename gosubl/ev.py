from . import gs
from . import kv
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


kvs = kv.M()

def kvm(k):
	return kvs.get(k, lambda: (kv.M(), True))

def df_mod_sig(view):
	def f():
		sublime.set_timeout(lambda: view_updated(view), 0)

	sig = Signal(500)
	sig += f
	return (sig, True)

def sig_mod(view):
	sig = kvm(view.id()).get('mod-sig', lambda: df_mod_sig(view))
	sig()

def lc(view):
	m = kvm(view.id())
	sel = gs.sel(view).begin()
	row, _ = view.rowcol(sel)
	if m.put('last-row', row) != row:
		sublime.set_timeout(lambda: line_changed(view), 0)

def df_mov_sig(view):
	def f():
		sublime.set_timeout(lambda: cursor_moved(view), 0)
		sublime.set_timeout(lambda: lc(view), 0)

	sig = Signal(500)
	sig += f
	return (sig, True)

def sig_mov(view, reset_last_row=False):
	m = kvm(view.id())

	if reset_last_row:
		m.delete('last-row')

	sig = m.get('mov-sig', lambda: df_mov_sig(view))
	sig()

debug = Event()
init = Event()
view_updated = Event()
line_changed = Event()
cursor_moved = Event()
