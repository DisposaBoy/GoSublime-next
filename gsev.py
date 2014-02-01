from gosubl import ev
from gosubl import gs
import gstest
import sublime_plugin

class EV(sublime_plugin.EventListener):
	def on_pre_save(self, view):
		view.run_command('gs_fmt')

	def on_post_save(self, view):
		ev.sublime_event('on_post_save', view)

	def on_close(self, view):
		ev.sublime_event('on_close', view)

	def on_activated(self, view):
		ev.sublime_event('on_activated', view)

	def on_new(self, view):
		ev.sublime_event('on_new', view)

	def on_load(self, view):
		ev.sublime_event('on_load', view)

	def on_modified(self, view):
		ev.sublime_event('on_modified', view)

	def on_selection_modified(self, view):
		ev.sublime_event('on_selection_modified', view)

class GsOnLeftClick(sublime_plugin.TextCommand):
	def run(self, edit):
		view = self.view
		if gs.is_go_source_view(view):
			if not gstest.handle_action(view, 'left-click'):
				view.run_command('gs_posdef')
		elif view.score_selector(gs.sel(view).begin(), "text.9o") > 0:
			view.window().run_command("gs9o_open_selection")

class GsOnRightClick(sublime_plugin.TextCommand):
	def run(self, edit):
		view = self.view
		if gs.is_go_source_view(view):
			if not gstest.handle_action(view, 'right-click'):
				view.run_command('gs_doc', {"mode": "hint"})
