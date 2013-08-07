from . import ev
from . import gs
from . import kv
import sublime

DOMAIN = 'GoSublime: Lint'
STATUS_DOMAIN = 'gs-lint-status'
REGION_DOMAIN_NORM = 'gs-lint-region-norm'
REGION_DOMAIN_EMPTY = 'gs-lint-region-empty'
REGION_DOMAINS = {
	REGION_DOMAIN_NORM: sublime.DRAW_EMPTY_AS_OVERWRITE,
	REGION_DOMAIN_EMPTY: sublime.HIDDEN,
}

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
	return kvm(view).get(row, df_note_list)

def _update_regions(view, m):
	show_icon = False
	seen = {}
	regions = {
		REGION_DOMAIN_NORM: [],
		REGION_DOMAIN_EMPTY: [],
	}

	for nl in m.dict().values():
		if nl:
			show_icon = True

			p = nl[0].pos
			if p.row not in seen:
				line = view.line(view.text_point(p.row, 0))
				sp = line.begin()
				ep = line.end()
				pt = sp

				# get the first non-whitespace column (putting a marker on tabs is ugly)
				s = view.substr(line)
				nc = len(s) - len(s.lstrip())

				if nc <= p.col:
					pt = sp + p.col

				if pt <= sp or pt > ep:
					regions[REGION_DOMAIN_EMPTY].append(sublime.Region(sp, sp))
				else:
					regions[REGION_DOMAIN_NORM].append(sublime.Region(pt, pt))

	for k, rl in regions.items():
		view.add_regions(k, rl, 'lint error invalid', 'dot', REGION_DOMAINS[k])

	lc(view, show_icon)

def add_notes(view, nl):
	m = kvm(view)

	for n in nl:
		m.get(n.pos.row, df_note_list).append(n)

	_update_regions(view, m)

def df_note_list():
	return ([], True)

def clear_notes(view, ctx):
	m = kvm(view)
	m.filter(lambda _, nl: [n for n in nl if n.ctx != ctx])
	_update_regions(view, m)

def gs_init(m={}):
	pass

def lc(view, show_icon=False):
	sel = gs.sel(view)
	row, _ = view.rowcol(sel.begin())
	m = kvm(view)
	s = ''

	if show_icon or len(m) > 0:
		nl = m.get(row)
		if nl:
			for n in nl:
				if n:
					s = ' %s: %s' % (n.ctx, n.message)
					break

		s = u'\u2622%s' % s

	view.set_status(STATUS_DOMAIN, s)

def mod(view):
	pass

ev.line_changed += lc
ev.view_updated += mod
