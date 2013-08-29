from . import ev
from . import gs
from . import kv
from collections import namedtuple
import sublime

DOMAIN = 'GoSublime: Highlights'
STATUS_DOMAIN = 'gs-hl-status'
REGION_DOMAIN_NORM = 'gs-hl-region-norm'
REGION_DOMAIN_EMPTY = 'gs-hl-region-empty'
REGION_DOMAINS = {
	REGION_DOMAIN_NORM: sublime.DRAW_EMPTY_AS_OVERWRITE,
	REGION_DOMAIN_EMPTY: sublime.HIDDEN,
}

kvs = kv.M()

Note = namedtuple('Note', 'ctx row col kind message')

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

			n = nl[0]
			if n.row not in seen:
				line = view.line(view.text_point(n.row, 0))
				sp = line.begin()
				ep = line.end()

				# get the first non-whitespace column (putting a marker on tabs is ugly)
				s = view.substr(line)
				nc = len(s) - len(s.lstrip())

				# always try to place a marker
				# if n.col is on indentation, we move to the first non-white position
				# this means we don't depend on being able to show an icon in the gutter
				# (our icon can be overridden by other regions/plugins)
				pt = sp + max(nc, n.col)
				r = sublime.Region(pt, pt)

				if pt < sp or pt > ep:
					regions[REGION_DOMAIN_EMPTY].append(r)
				else:
					regions[REGION_DOMAIN_NORM].append(r)

	for k, rl in regions.items():
		view.add_regions(k, rl, 'lint error invalid', 'dot', REGION_DOMAINS[k])

	lc(view, show_icon)

def add_notes(view, nl):
	m = kvm(view)

	for n in nl:
		m.get(n.row, df_note_list).append(n)

	_update_regions(view, m)

def df_note_list():
	return ([], True)

def clear_notes(view, cl, update=True):
	m = kvm(view)
	m.filter(lambda _, nl: [n for n in nl if n.ctx not in cl])

	if update:
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
					if n.kind:
						s = ' %s: %s' % (n.kind, n.message)
					else:
						s = ' %s' % (n.message)

					break

		s = u'\u2622%s' % s

	view.set_status(STATUS_DOMAIN, s)

def mod(view):
	pass

ev.line_changed += lc
ev.view_updated += mod
