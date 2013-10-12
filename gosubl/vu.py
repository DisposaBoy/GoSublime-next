import sublime

class V(object):
	def __init__(self, view):
		self.view = view

	def perma(self):
		if self.view is None:
			return False

		win = self.view.window()
		if win is None:
			return False

		# todo: check transient and 9o, is_scratch, non-overlay should be implied below
		return self.view in win.windows()

	def fn(self):
		if self.view is None:
			return ''

		return self.view.file_name() or ''

	def vfn(self):
		if self.view is None:
			return ''

		return self.view.file_name() or 'gs.view://%s' % self.view.id()

	def src(self):
		if self.view is None:
			return ''

		return self.view.substr(sublime.Region(0, self.view.size()))

def active(win=None, view=None):
	if view is None:
		if win is None:
			win = sublime.active_window()

		if win is not None:
			view = win.active_view()

	return V(view)
