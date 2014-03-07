from . import cfg
from . import ev
from . import gs
from . import kv
from . import vu
from os.path import relpath, dirname, normpath
import re
import sublime

DOMAIN = 'GoSublime: Highlights'
STATUS_DOMAIN = 'gs-hl-status'
REGION_DOMAIN_NORM = 'gs-hl-region-norm'
REGION_DOMAIN_EMPTY = 'gs-hl-region-empty'
REGION_DOMAIN_VERBOSE = 'gs-hl-region-verbose'

REGION_DOMAINS = {
	REGION_DOMAIN_NORM: sublime.DRAW_EMPTY_AS_OVERWRITE,
	REGION_DOMAIN_EMPTY: sublime.HIDDEN,
}

if gs.ST3:
	REGION_DOMAINS[REGION_DOMAIN_VERBOSE] = sublime.DRAW_SQUIGGLY_UNDERLINE | sublime.DRAW_NO_OUTLINE | sublime.DRAW_NO_FILL
else:
	REGION_DOMAINS[REGION_DOMAIN_VERBOSE] = sublime.DRAW_OUTLINED

_pos_rx = re.compile(r'([0-9]+)')

class M(kv.M):
	def m(self, k):
		return self.get(k, df_m)

	def l(self, k):
		return self.get(k, df_l)

kvs = M()

class Note(object):
	def __init__(self, **kw):
		self.ctx = kw.get('ctx', '')
		self.row = kw.get('row', 0)
		self.fn = kw.get('fn', '')
		self.col = kw.get('col', 0)

		pos = kw.get('pos')
		if pos:
			m = _pos_rx.findall(pos)
			if m:
				self.row = max(0, int(m[0])-1)

				if len(m) > 1:
					self.col = max(0, int(m[1])-1)

		self.message = kw.get('message', '').strip()

	def is_valid(self):
		return self.message and self.ctx and self.row >= 0 and self.col >= 0

def df_l():
	return ([], True)

def df_m():
	return (M(), True)

def refresh(view=None):
	vv = vu.active(view=view)
	if not vv.has_view():
		return

	view = vv.view()
	seen = {}
	regions = {
		REGION_DOMAIN_NORM: [],
		REGION_DOMAIN_EMPTY: [],
		REGION_DOMAIN_VERBOSE: [],
	}

	for nl in kvs.m(vv.vfn()).values():
		if nl:
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
				elif cfg.hl_verbose:
					regions[REGION_DOMAIN_VERBOSE].append(sublime.Region(pt, line.end()))
				else:
					regions[REGION_DOMAIN_NORM].append(r)

	for k, rl in regions.items():
		if rl:
			view.add_regions(k, rl, 'lint error invalid', 'dot', REGION_DOMAINS[k])
		else:
			view.erase_regions(k)

	lc(vv)

def add(*nl):
	for n in nl:
		if n.is_valid():
			kvs.m(n.fn).l(n.row).append(n)

def clear_view(view):
	vv = vu.V(view)
	fl = (vv.fn(), vv.vfn())
	kvs.filter(lambda k, v: None if k in fl else v)

def clear(*cl):
	def filter_rows(_, nl):
		return [n for n in nl if n.ctx not in cl]

	def filter_ents(_, m):
		m.filter(filter_rows)
		return m

	kvs.filter(filter_ents)

def show_messages(view):
	vv = vu.active(view=view)
	vfn = vv.vfn()
	items = []
	gotos = {}

	def rel(s):
		t = gs.relpath(s, vv.dir())
		if t.startswith('.'):
			return s
		return t

	def push(notes, fn, row):
		if fn == vfn:
			ents = ['Line %s' % (row+1)]
		else:
			ents = ['%s:%s' % (rel(fn), row+1)]

		col = -1
		for n in notes.get(row, []):
			if n.message:
				ents.extend(n.message.split('\n'))
				if col < 0:
					col = n.col

		if len(ents) > 1:
			gotos[len(items)] = (fn, row, col)
			items.append(ents)

	def key(k):
		if k in (vv.fn(), vfn):
			return (1, k)
		if dirname(normpath(k)) == vv.dir():
			return (2, k)
		return (3, k)

	d = kvs.dict()
	for fn in sorted(d.keys(), key=key):
		notes = d[fn].dict()
		rows = sorted(notes.keys())
		if rows:
			active_row, _ = gs.rowcol(view)
			closest_row = rows[0]
			distance = abs(active_row - closest_row)

			for row in rows[1:]:
				dist = abs(active_row - row)
				if dist < distance:
					distance = dist
					closest_row = row

			push(notes, fn, closest_row)
			rows.remove(closest_row)

			for row in rows:
				push(notes, fn, row)

	if items:
		n = max(map(len, items))
		for l in items:
			l.extend('' for i in range(n - len(l)))

		def cb(i, win):
			p = gotos.get(i)
			if p:
				fn, row, col = p
				vu.open(fn).focus(row=row, col=col)

		gs.show_quick_panel(items, cb)
	else:
		gs.notify(DOMAIN, 'No messages to display')


def gs_init(m={}):
	pass

def lc(vv):
	row, _ = vv.rowcol()
	vfn = vv.vfn()
	m = kvs.m(vfn)
	s = ''
	ico = ''

	d = vv.dir()
	if d:
		for fn in kvs.keys():
			if fn != vfn and dirname(normpath(fn)) == d:
				ico += u'\u272A '
				break

	if len(m) > 0:
		ico += u'\u2605 '
		nl = m.get(row)
		if nl:
			for n in nl:
				if n:
					s = n.message+' '
					break

	# todo: make this display globally as well
	vv.view().set_status(STATUS_DOMAIN, ico+s)

ev.line_changed += lambda view: lc(vu.V(view))
ev.view_activated += refresh
ev.file_sync += refresh
ev.view_closed += clear_view
# note-to-self: don't cleanup the old views when they close...
# we want to preserve the old errors so they're highlighted after they're re-opened
