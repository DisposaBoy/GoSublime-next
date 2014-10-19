from gosubl import cfg
from gosubl import gs
from gosubl import gspatch
from gosubl import hl
from gosubl import mg9
from gosubl import ui
from gosubl import vu
import datetime
import os
import sublime
import sublime_plugin

DOMAIN = 'GoSublime'

class GsCommentForwardCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		self.view.run_command("toggle_comment", {"block": False})
		self.view.run_command("move", {"by": "lines", "forward": True})

class GsStartNextLineCommentCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		self.view.run_command("run_macro_file", {"file": "Packages/Default/Add Line.sublime-macro"})
		self.view.run_command("toggle_comment", {"block": False})

class GsFmtCommand(sublime_plugin.TextCommand):
	def is_enabled(self):
		fn = self.view.file_name() or ''
		return fn.endswith('.go') or gs.is_go_source_view(self.view)

	def run(self, edit):
		vsize = self.view.size()
		src = self.view.substr(sublime.Region(0, vsize))
		if not src.strip():
			return

		src, err = mg9.fmt(self.view.file_name(), src)
		if err:
			gs.println(DOMAIN, "cannot fmt file. error: `%s'" % err)
			return

		if not src.strip():
			return

		_, err = gspatch.merge(self.view, vsize, src, edit)
		if err:
			msg = 'PANIC: Cannot fmt file. Check your source for errors (and maybe undo any changes).'
			sublime.error_message("%s: %s: Merge failure: `%s'" % (DOMAIN, msg, err))

class GsFmtSaveCommand(sublime_plugin.TextCommand):
	def is_enabled(self):
		return gs.is_go_source_view(self.view)

	def run(self, edit):
		self.view.run_command("gs_fmt")
		sublime.set_timeout(lambda: self.view.run_command("save"), 0)

class GsFmtPromptSaveAsCommand(sublime_plugin.TextCommand):
	def is_enabled(self):
		return gs.is_go_source_view(self.view)

	def run(self, edit):
		self.view.run_command("gs_fmt")
		sublime.set_timeout(lambda: self.view.run_command("prompt_save_as"), 0)

class GsNewGoFileCommand(sublime_plugin.WindowCommand):
	def run(self):
		pkg_name = 'main'
		view = gs.active_valid_go_view()
		try:
			basedir = gs.basedir_or_cwd(view and view.file_name())
			for fn in os.listdir(basedir):
				if fn.endswith('.go'):
					name, _ = mg9.pkg_name(os.path.join(basedir, fn), '')
					if name:
						pkg_name = name
						break
		except Exception:
			ui.trace('GsNewGoFile')

		self.window.new_file().run_command('gs_create_new_go_file', {
			'pkg_name': pkg_name,
			'file_name': 'main.go',
		})

class GsCreateNewGoFileCommand(sublime_plugin.TextCommand):
	def run(self, edit, pkg_name, file_name):
		view = self.view
		view.set_name(file_name)
		view.set_syntax_file(gs.tm_path('go'))
		view.replace(edit, sublime.Region(0, view.size()), 'package %s\n' % pkg_name)
		view.sel().clear()
		view.sel().add(view.find(pkg_name, 0, sublime.LITERAL))

class GsShowTasksCommand(sublime_plugin.WindowCommand):
	def run(self):
		ents, cb = ui.task_ents()
		gs.show_quick_panel(ents, cb)

class GsOpenHomePathCommand(sublime_plugin.WindowCommand):
	def run(self, fn):
		self.window.open_file(gs.home_path(fn))

class GsOpenDistPathCommand(sublime_plugin.WindowCommand):
	def run(self, fn):
		self.window.open_file(gs.dist_path(fn))

class GsSanityCheckCommand(sublime_plugin.WindowCommand):
	def run(self):
		s = 'GoSublime Sanity Check\n\n%s' % '\n'.join(mg9.sanity_check_sl(mg9.sanity_check({}, True)))
		gs.show_output('GoSublime', s)

class GsSetOutputPanelContentCommand(sublime_plugin.TextCommand):
	def run(self, edit, content, syntax_file, scroll_end, replace):
		panel = self.view
		panel.set_read_only(False)

		if replace:
			panel.replace(edit, sublime.Region(0, panel.size()), content)
		else:
			panel.insert(edit, panel.size(), content+'\n')

		panel.sel().clear()
		pst = panel.settings()
		pst.set("rulers", [])
		pst.set("fold_buttons", True)
		pst.set("fade_fold_buttons", False)
		pst.set("gutter", False)
		pst.set("line_numbers", False)

		if syntax_file:
			if syntax_file == 'GsDoc':
				panel.set_syntax_file(gs.tm_path('doc'))
				panel.run_command("fold_by_level", { "level": 1 })
			else:
				panel.set_syntax_file(syntax_file)

		panel.set_read_only(True)

		if scroll_end:
			panel.show(panel.size())

class GsInsertContentCommand(sublime_plugin.TextCommand):
	def run(self, edit, pos, content):
		pos = int(pos) # un-fucking-believable
		self.view.insert(edit, pos, content)

class GsWriteAllCommand(sublime_plugin.TextCommand):
	def run(self, edit, sl, pt=-1, ctx='', interp=False, scope='', outlined=False):
		vu.ve_write(self.view, edit, sl, pt=int(pt), ctx=ctx, interp=interp, scope=scope, outlined=outlined)

class GsWriteCommand(sublime_plugin.TextCommand):
	def run(self, edit, s, pt=-1, ctx='', interp=False, scope='', outlined=False):
		vu.ve_write(self.view, edit, [s], pt=int(pt), ctx=ctx, interp=interp, scope=scope, outlined=outlined)

class GsReplaceCommand(sublime_plugin.TextCommand):
	def run(self, edit, begin, end, s):
		# convert begin and end to ints because the api might(will) pass them as a float
		vu.ve_replace(self.view, edit, int(begin), int(end), s)

class GsPatchImportsCommand(sublime_plugin.TextCommand):
	def run(self, edit, pos, content, added_path=''):
		pos = int(pos) # un-fucking-believable
		view = self.view
		dirty, err = gspatch.merge(view, pos, content, edit)
		if err:
			ui.error(DOMAIN, err)
			if dirty:
				sublime.set_timeout(lambda: view.run_command('undo'), 0)
		elif dirty:
			k = 'last_import_path.%s' % vu.V(view).vfn()
			if added_path:
				gs.set_attr(k, added_path)
			else:
				gs.del_attr(k)

class GsShowMessagesCommand(sublime_plugin.TextCommand):
	def run(self, _edit):
		hl.show_messages(self.view)

