from os.path import dirname, normpath
import sublime

class V(object):
	def __init__(self, view):
		self.v = view

	def perma(self):
		if self.v is None:
			return False

		win = self.v.window()
		if win is None:
			return False

		# todo: check transient and 9o, is_scratch, non-overlay should be implied below
		return self.v in win.views()

	def fn(self):
		if self.v is None:
			return ''

		return self.v.file_name() or ''

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


def active(win=None, view=None):
	if view is None:
		if win is None:
			win = sublime.active_window()

		if win is not None:
			view = win.active_view()

	return V(view)
