from . import gs
from . import kv
import sublime
import threading
import time

DOMAIN = 'gs.ev'

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
				gs.print_traceback()

		return self

	def __iadd__(self, f):
		with self.lck:
			self.lst.append(f)

		if self.post_add:
			try:
				self.post_add(self, f)
			except Exception:
				gs.print_traceback()

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
				gs.do(DOMAIN, self._timedout, ms)

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
		gs.do(DOMAIN, lambda: view_updated(view))

	sig = Signal(1000)
	sig += f
	return (sig, True)

def sig_mod(view):
	if ignore_view(view):
		return

	sig = kvm(view.id()).get('mod-sig', lambda: df_mod_sig(view))
	sig()

def lc(view):
	m = kvm(view.id())
	sel = gs.sel(view).begin()
	row, _ = view.rowcol(sel)
	if m.put('last-row', row) != row:
		gs.do(DOMAIN, lambda: line_changed(view))

def df_mov_sig(view):
	def f():
		gs.do(DOMAIN, lambda: cursor_moved(view))
		gs.do(DOMAIN, lambda: lc(view))

	sig = Signal(500)
	sig += f
	return (sig, True)

def sig_mov(view, reset_last_row=False):
	if ignore_view(view):
		return

	m = kvm(view.id())

	if reset_last_row:
		m.delete('last-row')

	sig = m.get('mov-sig', lambda: df_mov_sig(view))
	sig()

def ignore_view(view):
	vs = view.settings()
	return vs.get('is_widget') or vs.get('9o')

def df_sav_sig(view):
	def f():
		gs.do(DOMAIN, lambda: file_saved(view))

	sig = Signal(100)
	sig += f
	return (sig, True)

def sig_sav(view):
	if ignore_view(view):
		return

	m = kvm(view.id())

	sig = m.get('sav-sig', lambda: df_sav_sig(view))
	sig()

debug = Event()
init = Event()
view_updated = Event()
file_saved = Event()
line_changed = Event()
cursor_moved = Event()

file_saved += lambda view: sig_mod(view)
