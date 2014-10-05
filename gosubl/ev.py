from . import cfg
from . import gs
from . import kv
from . import ui
from . import vu
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
				ui.trace(DOMAIN)

		return self

	def __iadd__(self, f):
		if not gs.callable(f):
			return

		with self.lck:
			self.lst.append(f)

		if self.post_add:
			try:
				self.post_add(self, f)
			except Exception:
				ui.trace(DOMAIN)

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

def df_act_sig(view):
	def f():
		gs.do(DOMAIN, lambda: view_activated(view))
		gs.do(DOMAIN, lambda: lc(view))

		fn = view.file_name()
		if fn:
			vs = view.settings()
			old_fn = vs.get('gs.ev.file_name')
			vs.set('gs.ev.old_file_name', old_fn)
			vs.set('gs.ev.file_name', fn)
			if old_fn and old_fn != fn:
				gs.do(DOMAIN, lambda: file_renamed(view))
				gs.do(DOMAIN, lambda: file_sync(view))


	sig = Signal(1000)
	sig += f
	return (sig, True)

def sig_act(view):
	if ignore_view(view):
		return

	sig = kvm(view.id()).get('act-sig', lambda: df_act_sig(view))
	sig()

def df_mod_sig(view):
	def f():
		gs.do(DOMAIN, lambda: view_updated(view))

	sig = Signal(1000)
	sig += f
	return (sig, True)

def df_mod_fast_sig(view):
	def f():
		gs.do(DOMAIN, lambda: view_updated_fast(view))

	sig = Signal(250)
	sig += f
	return (sig, True)

def sig_mod(view):
	if ignore_view(view):
		return

	sig = kvm(view.id()).get('mod-sig', lambda: df_mod_sig(view))
	sig()

	fast_sig = kvm(view.id()).get('mod-fast-sig', lambda: df_mod_fast_sig(view))
	fast_sig()

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
	return not vu.V(view).perma()

def df_sav_sig(view):
	def f():
		gs.do(DOMAIN, lambda: file_saved(view))
		gs.do(DOMAIN, lambda: file_sync(view))

	sig = Signal(100)
	sig += f
	return (sig, True)

def sig_sav(view):
	if ignore_view(view):
		return

	m = kvm(view.id())

	sig = m.get('sav-sig', lambda: df_sav_sig(view))
	sig()

def df_lod_sig(view):
	def f():
		gs.do(DOMAIN, lambda: file_loaded(view))
		gs.do(DOMAIN, lambda: file_sync(view))

	sig = Signal(1000)
	sig += f
	return (sig, True)

def sig_lod(view):
	if ignore_view(view):
		return

	m = kvm(view.id())

	sig = m.get('lod-sig', lambda: df_lod_sig(view))
	sig()

def sublime_event(k, view):
	if k in ('on_activated', 'on_post_save', 'on_load', 'on_close'):
		gs.do(DOMAIN, cfg.sync_vv(vu.active()))

	if not opts.margo_ready and k in ('on_load', 'on_activated'):
		return

	sig = ev_map.get(k)
	if sig:
		sig(view)
	elif k == 'on_close':
		view_closed(view)

def margo_ready():
	opts.margo_ready = True

	for win in sublime.windows():
		for view in win.views():
			if not view.is_loading():
				sig_lod(view)
				# at this point ST might still be loading, so we don't know what the real active view
				# will be... but it should be safe to sig_act all loaded views (ST doesn't that anyway)
				sig_act(view)

	gs.ready = True
	ready()

opts = kv.O(
	margo_ready = False
)

debug = Event()
init = Event()
view_updated = Event()
view_updated_fast = Event()
view_activated = Event()
view_closed = Event()
file_saved = Event()
file_loaded = Event()
file_sync = Event()
file_renamed = Event()
line_changed = Event()
cursor_moved = Event()
ready = Event()

ev_map = {
	'on_post_save': sig_sav,
	'on_activated': sig_act,
	'on_load': sig_lod,
	'on_modified': sig_mod,
	'on_selection_modified': sig_mov,
}
