from gosubl import ev
from gosubl import gs
from gosubl import cfg
import gstest
import sublime
import sublime_plugin

DOMAIN = 'GsEV'

class EV(sublime_plugin.EventListener):
	def _se(self, k, view):
		try :
			ev.sublime_event(k, view)
		except AttributeError:
			pass

	def on_pre_save(self, view):
		view.run_command('gs_fmt')
		sublime.set_timeout(lambda: do_set_syntax(view), 0)

	def on_post_save(self, view):
		self._se('on_post_save', view)
		sublime.set_timeout(lambda: do_post_save(view), 0)

	def on_close(self, view):
		self._se('on_close', view)
		sublime.set_timeout(do_sync_active_view, 0)

	def on_activated(self, view):
		sublime.set_timeout(do_sync_active_view, 0)
		self._se('on_activated', view)
		sublime.set_timeout(lambda: do_set_syntax(view), 0)

	def on_new(self, view):
		sublime.set_timeout(do_sync_active_view, 0)

	def on_load(self, view):
		sublime.set_timeout(do_sync_active_view, 0)
		self._se('on_load', view)
		sublime.set_timeout(lambda: do_set_syntax(view), 0)

	def on_modified(self, view):
		self._se('on_modified', view)

	def on_selection_modified(self, view):
		self._se('on_selection_modified', view)

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

def do_post_save(view):
	if not gs.is_pkg_view(view):
		return

	for c in gs.setting('on_save', []):
		cmd = c.get('cmd', '')
		args = c.get('args', {})
		msg = 'running on_save command %s' % cmd
		tid = gs.begin(DOMAIN, msg, set_status=False)
		try:
			view.run_command(cmd, args)
		except Exception as ex:
			gs.notice(DOMAIN, 'Error %s' % ex)
		finally:
			gs.end(tid)

def do_sync_active_view():
	try:
		view = sublime.active_window().active_view()
	except Exception:
		return

	win = view.window()
	cfg.folders = win.folders()

	fn = view.file_name() or ''
	vfn = gs.view_fn(view)
	gs.set_attr('active_fn', fn)
	gs.set_attr('active_vfn', vfn)

	if fn:
		gs.set_attr('last_active_fn', fn)
		if fn.lower().endswith('.go'):
			gs.set_attr('last_active_go_fn', fn)

	if win is not None and view in win.views():
		m = {}
		psettings = view.settings().get('GoSublime')
		if psettings and gs.is_a(psettings, {}):
			m = gs.mirror_settings(psettings)
		gs.set_attr('last_active_project_settings', gs.dval(m, {}))

def do_set_syntax(view):
	fn = view.file_name()
	if not fn:
		return

	xm = gs.setting('set_extension_syntax', {})
	xl = list(xm.keys())
	xl.sort()
	xl.sort(key=lambda k: -len(k))

	fn = fn.lower()
	for k in xl:
		if fn.endswith(k):
			v = xm[k]
			v = gs.tm_path(v) or v
			if v:
				view.set_syntax_file(v)

