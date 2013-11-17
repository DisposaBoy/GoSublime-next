from os.path import dirname, normpath, splitext
import sublime

class V(object):
	def __init__(self, view):
		self.v = view

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
		return splitext(self.fn())[1]

	def vfn(self):
		if self.v is None:
			return ''

		return self.v.file_name() or 'gs.view://%s' % self.v.id()

	def dir(self):
		return dirname(normpath(self.fn()))

	def src(self):
		if self.v is None:
			return ''

		return self.v.substr(sublime.Region(0, self.v.size()))

	def scope_name(self, pos=0):
		if self.v is None:
			return ''

		return self.v.scope_name(pos)

	def view(self):
		return self.v

	def window(self):
		if self.v is None:
			return None

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

	def sel(self, i=0):
		return sel(self.v, i)

	def rowcol(self):
		return rowcol(self.v)


def active(win=None, view=None):
	if view is None:
		if win is None:
			win = sublime.active_window()

		if win is not None:
			view = win.active_view()

	return V(view)

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
