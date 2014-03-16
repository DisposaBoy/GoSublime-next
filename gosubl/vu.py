from . import kv
from os.path import dirname, normpath, splitext, isfile
import re
import sublime

_fn = re.compile(r'^(?P<fn>.+?)(?:[:](?P<line>[\d+]+)(?:[:](?P<column>[\d+]+))?)?\s*$')
_vfn_id = re.compile(r'gs\.view#(\d+)')

class V(object):
	def __init__(self, view, win=None):
		self.v = view
		self.w = win

	def temp(self):
		if self.v is None:
			return False

		return not self.perma()

	def perma(self):
		if self.v is None:
			return False

		win = self.v.window()
		if win is None:
			return False

		if self.v not in win.views():
			return False

		vs = self.v.settings()
		if vs.get('is_widget') or vs.get('9o'):
			return False

		return True

	def fn(self):
		if self.v is None:
			return ''

		return self.v.file_name() or ''

	def splitext(self):
		return splitext(self.fn())

	def ext(self):
		return splitext(self.vfn())[1]

	def vfn(self):
		if self.v is None:
			return ''

		fn = self.fn()
		if fn:
			return fn

		fn = self.v.name() or ''
		return 'gs.view#%s,%s' % (self.v.id(), fn.replace(' ', '_'))

	def dir(self):
		return dirname(normpath(self.fn()))

	def src(self):
		if self.v is None:
			return ''

		return self.v.substr(sublime.Region(0, self.v.size()))

	def size(self):
		return self.v.size() if self.v is not None else 0

	def is_empty(self):
		if self.v is None:
			return True

		return self.v.find(r'\S', 0) is not None

	def scope_name(self, pos=0):
		if self.v is None:
			return ''

		return self.v.scope_name(pos)

	def view(self):
		return self.v

	def window(self):
		if self.v is None:
			return self.w

		return self.v.window()

	def has_view(self):
		return self.v is not None

	def has_window(self):
		return self.window() is not None

	def sibling_views(self):
		win = self.window()
		if win is not None:
			return win.views()

		return []

	def setting(self, k, default=None):
		if self.v is not None:
			return self.v.settings().get(k, default)

		return default

	def folders(self):
		try:
			return self.window().folders()
		except Exception:
			return []

	def sel(self, i=0):
		return sel(self.v, i)

	def rowcol(self):
		return rowcol(self.v)

	def write(self, s, pt=-1, ctx='', interp=False, scope='', outlined=False):
		return self.write_all([s], pt, ctx, interp, scope, outlined)

	def write_all(self, sl, pt=-1, ctx='', interp=False, scope='', outlined=False):
		if not self.has_view():
			return False

		self.v.run_command('gs_write_all', {
			'sl': sl,
			'pt': pt,
			'ctx': ctx,
			'interp': interp,
			'scope': scope,
			'outlined': outlined,
		})
		return True

	def focus(self, row=0, col=0, pat='^package ', cb=None):
		win = self.window()
		view = self.view()
		if None in (win, view):
			if cb:
				cb(False)
			return

		if self.v.is_loading():
			sublime.set_timeout(lambda: self.focus(row=row, col=col, pat=pat, cb=cb), 100)
			return

		win.focus_view(view)
		if row <= 0 and col <= 0 and pat:
			r = view.find(pat, 0)
			if r:
				row, col = view.rowcol(r.begin())

		view.run_command("gs_goto_row_col", { "row": row, "col": col })
		if cb:
			cb(True)

def ve_replace(view, edit, begin, end, s):
	view.replace(edit, sublime.Region(begin, end), s)

def ve_write(view, edit, sl, pt=-1, ctx='', interp=False, scope='', outlined=False):
	if not sl:
		return

	n = view.size()
	rl = view.get_regions(ctx) if ctx else []
	ep = int(pt)
	if ep < 0:
		ep = rl[-1].end() if rl else n

	lr = view.line(ep)
	out = [view.substr(lr)]
	for s in sl:
		# todo: maybe make this behave more like a real console and handle \b
		if interp and s.startswith('\r'):
			out[-1] = s.lstrip('\r')
		else:
			out.append(s)

	view.replace(edit, lr, ''.join(out))

	if ctx:
		sp = rl[0].begin() if rl else lr.begin()
		ep += view.size() - n
		flags = sublime.DRAW_OUTLINED if outlined else sublime.HIDDEN
		view.add_regions(ctx, [sublime.Region(sp, ep)], scope, '', flags)

def active(win=None, view=None):
	if view is None:
		if win is None:
			win = sublime.active_window()

		if win is not None:
			view = win.active_view()

	return V(view)

def open(fn='', id=-1, view=None, win=None):
	vv, loc = find_loc(fn=fn, id=id, view=view, win=win)
	if not vv.has_view() and isfile(loc.fn):
		if win is None:
			win = sublime.active_window()
		vv = V(win.open_file(loc.fn), win=win)

	if vv.has_view():
		vv.focus(loc.row, loc.col)

	return vv

def find(fn='', id=-1, view=None, win=None):
	vv, _ = find_loc(fn=fn, id=id, view=view, win=win)
	return vv

def find_loc(fn='', id=-1, view=None, win=None):
	loc = mk_loc()
	if view is not None:
		return (V(view, win=win), loc)

	match = None
	if id >= 0:
		match = lambda v: v.id() == id
	else:
		loc = parse(fn)
		if loc.ok:
			if loc.id >= 0:
				match = lambda v: v.id() == loc.id
			else:
				match = lambda v: v.file_name() == loc.fn
		else:
			match = lambda v: v.file_name() == fn

	if win is None:
		win = sublime.active_window()

	for v in win.views():
		if match(v):
			return (V(v, win=win), loc)

	return (V(None, win=win), loc)

def sel(view, i=0):
	try:
		s = view.sel()
		if s is not None and i < len(s):
			return s[i]
	except Exception:
		pass

	return sublime.Region(0, 0)

def rowcol(view):
	try:
		return view.rowcol(sel(view).begin())
	except Exception:
		return (0, 0)

def mk_loc():
	return kv.O(
		ok=False,
		id=-1,
		fn='',
		row=0,
		col=0,
		pos=''
	)

def get_num(m, k):
	try:
		return int(m.get(k))
	except Exception:
		return 0

def parse(s):
	loc = mk_loc()
	m = _fn.search(s or '')
	if m:
		m = m.groupdict()
		loc.ok = True
		loc.id = get_num(m, 'id')
		loc.row = max(0, get_num(m, 'line')-1)
		loc.col = max(0, get_num(m, 'column')-1)
		loc.pos = '%s:%s' % (loc.row, loc.col)
		loc.fn = m.get('fn', '')

		vm = _vfn_id.search(loc.fn)
		if vm:
			loc.id = int(vm.group(1))
			loc.fn = ''

	return loc

def is_vfn(s):
	return 'gs.view#' in s

def gs_init(m={}):
	pass
