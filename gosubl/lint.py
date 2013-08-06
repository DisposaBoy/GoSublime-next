from . import ev
from . import gs
from . import kv

DOMAIN = 'GoSublime: Lint'
STATUS_DOMAIN = 'gs-lint-status'

kvs = kv.M()

class Pos(object):
	def __init__(self, row, col):
		self.row = row
		self.col = col

class Note(object):
	def __init__(self, ctx, pos, message):
		self.ctx = ctx
		self.pos = pos
		self.message = message

def df_kvm():
	return (kv.M(), True)

def kvm(view):
	return kvs.get(gs.view_fn(view), df_kvm)

def notes(view):
	return kvm(view).values()

def row_notes(view, row):
	return kvm(view).get(row, df_note_set)

def add_note(view, n):
	# todo: fix this race? does it actually matter?
	kvm(view).get(n.pos.row, df_note_set).add(n)
	lc(view)

def df_note_set():
	return (set(), True)

def clear_notes(view, ctx):
	kvm(view).filter(lambda _, ns: set((n for n in ns if n.ctx != ctx)))
	lc(view)

def gs_init(m={}):
	pass

def lc(view):
	sel = gs.sel(view)
	row, _ = view.rowcol(sel.begin())
	m = kvm(view)

	s = ''
	l = len(m)
	if l > 0:
		ns = m.get(row)
		if ns:
			for n in ns:
				if n:
					s = ' %s: %s' % (n.ctx, n.message)
					break

		s = u'\u2622%s' % s

	view.set_status(STATUS_DOMAIN, s)

def mod(view):
	pass

ev.line_changed += lc
ev.view_updated += mod
