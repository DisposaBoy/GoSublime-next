from gosubl import about
from gosubl import cfg
from gosubl import gs
from gosubl import kv
from gosubl import mg9
from gosubl import nineo
from gosubl import sh
from gosubl import ui
from gosubl import vu
import datetime
import glob
import json
import os
import re
import shlex
import string
import sublime
import sublime_plugin
import uuid
import webbrowser

DOMAIN = "9o"
AC_OPTS = sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS
SPLIT_FN_POS_PAT = re.compile(r'(.+?)(?:[:](\d+))?(?:[:](\d+))?$')
URL_SCHEME_PAT = re.compile(r'^[\w.+-]+://')
URL_PATH_PAT = re.compile(r'^(?:[\w.+-]+://|(?:www|(?:\w+\.)*(?:golang.org|godoc.org|gosubli.me)))')
HIST_EXPAND_PAT = re.compile(r'^(\^+)\s*(\d+)$')
WORD_SEPARATORS = "./\\()\"'-:,;<>~!@#$%&*|+=[]{}`~?"
HOURGLASS = u'\u231B'

word_sep_pat = re.compile('^([%s]+)' % re.escape(WORD_SEPARATORS))

DEFAULT_COMMANDS = [
	'help',
	'run',
	'build',
	'replay',
	'clear',
	'tskill',
	'tskill replay',
	'tskill go',
	'go',
	'go build',
	'go clean',
	'go doc',
	'go env',
	'go fix',
	'go fmt',
	'go get',
	'go install',
	'go list',
	'go run',
	'go test',
	'go tool',
	'go version',
	'go vet',
	'go help',
	'settings',
	'env',
	'share',
	'hist',
	'hist erase',
	'cd',
]
DEFAULT_CL = [(s, s+' ') for s in DEFAULT_COMMANDS]
MIDDOT = u' \u00B7 '

stash = {}

class Sess(nineo.Sess):
	def error(self, s):
		# the display of errors will be handled by end_c()
		pass

def active_wd(win=None):
	vv = vu.active(win=win)
	return vv.dir() or gs.getwd()

def _hkey(wd):
	name = cfg.nineo_instance
	if name:
		wd = name
	return '9o.hist.%s' % wd

def _wdid(wd):
	name = cfg.nineo_instance
	if name:
		return name
	return '9o://%s' % wd


class EV(sublime_plugin.EventListener):
	def on_query_completions(self, view, _, locations):
		pos = locations[0]
		if view.score_selector(pos, 'text.9o') == 0:
			return []

		if view.substr(locations[0]-2) == '$':
			return ([('$'+k, '\$'+k+' ') for k in sh.env()], AC_OPTS)

		cl = set()

		slash = os.path.sep
		# the prefix passed tho us by definition doesn't contain slash because it's not a word char
		p = view.substr(sublime.Region(view.line(pos).begin(), pos))
		p = p.split()[-1].lstrip(' #')
		file_only_comp = p.startswith('.') or slash in p

		if not p.startswith(('.', slash)):
			p = '.'+slash+p

		rm = ''
		m = word_sep_pat.match(p)
		if m:
			rm = m.group(1)

		try:
			for fn in glob.iglob(p+'*'):
				space = ' '
				if os.path.isdir(fn):
					space = ''
					fn += '/'

				cl.add((fn, fn[len(rm):]+space))
		except Exception:
			pass

		if not file_only_comp:
			hkey = _hkey(view.settings().get('9o.wd', ''))
			cl.update((k, k+' ') for k in gs.dval(gs.aso().get(hkey), []))
			cl.update((k, k+' ') for k in builtins())
			cl.update(DEFAULT_CL)

		return ([cl_esc(e) for e in sorted(cl)], AC_OPTS)

def fn_esc(fn):
	# surely this is enough... surely...
	return fn.replace('\\', '\\\\').replace(' ', '\\ ')

def cl_esc(e):
	return (e[0], e[1].replace('$', '\\$'))

class Gs9oBuildCommand(sublime_plugin.WindowCommand):
	def is_enabled(self):
		view = gs.active_valid_go_view(self.window)
		return view is not None

	def run(self):
		view = self.window.active_view()
		args = {'run': gs.setting('build_command', ['^1'])} if gs.is_pkg_view(view) else {}
		view.run_command('gs9o_open', args)

class Gs9oInsertLineCommand(sublime_plugin.TextCommand):
	def run(self, edit, after=True):
		insln = lambda: self.view.insert(edit, gs.sel(self.view).begin(), "\n")
		if after:
			self.view.run_command("move_to", {"to": "hardeol"})
			insln()
		else:
			self.view.run_command("move_to", {"to": "hardbol"})
			insln()
			self.view.run_command("move", {"by": "lines", "forward": False})


class Gs9oMoveHist(sublime_plugin.TextCommand):
	def run(self, edit, up):
		view = self.view
		pos = gs.sel(view).begin()
		if view.score_selector(pos, 'prompt.9o') <= 0:
			return

		aso = gs.aso()
		vs = view.settings()
		wd = vs.get('9o.wd')
		hkey = _hkey(wd)
		hist = [s for s in gs.dval(aso.get(hkey), []) if s.strip()]
		if not hist:
			return

		r = view.extract_scope(pos)
		cmd = view.substr(r).strip('#').strip()
		try:
			idx = hist.index(cmd) + (-1 if up else 1)
			found = True
		except Exception:
			idx = -1
			found = False

		if cmd and not found:
			hist.append(cmd)
			aso.set(hkey, hist)
			gs.save_aso()

		if idx >= 0 and idx < len(hist):
			cmd = hist[idx]
		elif up:
			if not found:
				cmd = hist[-1]
		else:
			cmd = ''

		view.replace(edit, r, '# %s \n' % cmd)
		n = view.line(r.begin()).end()
		view.sel().clear()
		view.sel().add(sublime.Region(n, n))

class Gs9oInitCommand(sublime_plugin.TextCommand):
	def run(self, edit, wd=None):
		v = self.view
		vs = v.settings()

		if not wd:
			wd = vs.get('9o.wd', active_wd(win=v.window()))

		wd = gs.abspath(wd)
		was_empty = v.size() == 0
		s = '[ %s ] # \n' % gs.simple_fn(wd).replace('#', '~')

		if was_empty:
			v.insert(edit, 0, 'GoSublime %s 9o: type `help` for help and command documentation\n\n%s' % (about.VERSION, s))
		else:
			v.insert(edit, v.size(), '\n'+s)

		v.sel().clear()
		n = v.size()-1
		v.sel().add(sublime.Region(n, n))

		opts = {
			"rulers": [],
			"fold_buttons": True,
			"fade_fold_buttons": False,
			"gutter": True,
			"margin": 0,
			# pad mostly so the completion menu shows on the first line
			"line_padding_top": 1,
			"line_padding_bottom": 1,
			"tab_size": 2,
			"word_wrap": True,
			"indent_subsequent_lines": True,
			"line_numbers": False,
			"auto_complete": True,
			"auto_complete_selector": "text",
			"highlight_line": True,
			"draw_indent_guides": True,
			"scroll_past_end": True,
			"indent_guide_options": ["draw_normal", "draw_active"],
			"word_separators": WORD_SEPARATORS,
		}
		opts.update(cfg.nineo_settings)

		for opt in opts:
			vs.set(opt, opts[opt])

		vs.set("9o", True)
		vs.set("9o.wd", wd)

		color_scheme = cfg.nineo_color_scheme
		if color_scheme:
			if color_scheme == "default":
				vs.erase("color_scheme")
			else:
				vs.set("color_scheme", color_scheme)
		else:
			vs.set("color_scheme", "")

		v.set_syntax_file(gs.tm_path('9o'))

		if was_empty:
			v.show(0)
		else:
			v.show(v.size()-1)

		os.chdir(wd)

class GsQuickCommandsCommand(sublime_plugin.WindowCommand):
	def run(self):
		nineo.quick_commands()

class Gs9oOpenCommand(sublime_plugin.TextCommand):
	def run(self, edit, wd=None, run=[], save_hist=False, focus_view=True):
		self.view.window().run_command('gs9o_win_open', {
			'wd': wd,
			'run': run,
			'save_hist': save_hist,
			'focus_view': focus_view,
		})

class Gs9oWinOpenCommand(sublime_plugin.WindowCommand):
	def run(self, wd=None, run=[], save_hist=False, focus_view=True):
		win = self.window
		wid = win.id()
		if not wd:
			wd = active_wd(win=win)

		id = _wdid(wd)
		st = stash.setdefault(wid, {})
		v = st.get(id)
		if v is None:
			v = win.get_output_panel(id)
			st[id] = v

		win.run_command("show_panel", {"panel": ("output.%s" % id)})

		if focus_view:
			win.focus_view(v)

		v.run_command('gs9o_init', {'wd': wd})

		if run:
			v.run_command('gs9o_paste_exec', {'cmd': ' '.join((shlex.quote(s) for s in run)), 'save_hist': save_hist})

class Gs9oPasteExecCommand(sublime_plugin.TextCommand):
	def run(self, edit, cmd, save_hist=False):
		view = self.view
		view.insert(edit, view.line(view.size()-1).end(), cmd)
		view.sel().clear()
		view.sel().add(view.line(view.size()-1).end())
		_exec(view, edit, save_hist)

class Gs9oOpenSelectionCommand(sublime_plugin.TextCommand):
	def is_enabled(self):
		pos = gs.sel(self.view).begin()
		return self.view.score_selector(pos, 'text.9o') > 0

	def run(self, edit):
		actions = []
		v = self.view
		sel = gs.sel(v)
		if (sel.end() - sel.begin()) == 0:
			pos = sel.begin()
			inscope = lambda p: v.score_selector(p, 'path.9o') > 0
			if inscope(pos):
				actions.append(v.substr(v.extract_scope(pos)))
			else:
				pos -= 1
				if inscope(pos):
					actions.append(v.substr(v.extract_scope(pos)))
				else:
					line = v.line(pos)
					for cr in v.find_by_selector('path.9o'):
						if line.contains(cr):
							actions.append(v.substr(cr))
		else:
			actions.append(v.substr(sel))

		act_on(v, actions)

def act_on(view, actions):
	for a in actions:
		if act_on_path(view, a):
			break

def act_on_path(view, path):
	vv = vu.open(fn=path, win=view.window())
	if vv.has_view():
		return True

	if URL_PATH_PAT.match(path):
		if path.lower().startswith('gs.packages://'):
			vv = vu.open(fn=os.path.join(gs.packages_dir(), path[14:]), win=view.window())
			return vv.has_view()

		try:
			if not URL_SCHEME_PAT.match(path):
				path = 'http://%s' % path
			ui.note(DOMAIN, 'open url: %s' % path)
			webbrowser.open_new_tab(path)
			return True
		except Exception:
			ui.trace(DOMAIN)

		return False

	ui.note(DOMAIN, "Invalid path `%s'" % path)
	return False


def _exparg(s, m):
	s = string.Template(s).safe_substitute(m)
	s = os.path.expanduser(s)
	return s

class Gs9oExecCommand(sublime_plugin.TextCommand):
	def is_enabled(self):
		pos = gs.sel(self.view).begin()
		return self.view.score_selector(pos, 'text.9o') > 0

	def run(self, edit, save_hist=False):
		_exec(self.view, edit, save_hist)

def _exec(view, edit, save_hist=False):
	pos = gs.sel(view).begin()
	line = view.line(pos)
	wd = view.settings().get('9o.wd')

	try:
		os.chdir(wd)
	except Exception:
		ui.trace(DOMAIN)

	ln = view.substr(line).split('#', 1)
	if len(ln) == 2:
		cmd = ln[1].strip()
		if cmd:
			vs = view.settings()
			aso = gs.aso()
			hkey = _hkey(wd)
			hist = gs.dval(aso.get(hkey), [])

			m = HIST_EXPAND_PAT.match(cmd)
			if m:
				pfx = m.group(1)
				hl = len(hist)
				idx = hl - int(m.group(2))
				cmd = ''
				if idx >= 0 and idx < hl:
					cmd = hist[idx]

				if pfx == '^' or not cmd:
					view.replace(edit, line, ('%s# %s' % (ln[0], cmd)))
					return
			elif save_hist:
				try:
					hist.remove(cmd)
				except ValueError:
					pass
				hist.append(cmd)
				aso.set(hkey, hist)
				gs.save_aso()

		if not cmd:
			view.run_command('gs9o_init')
			return

		line = view.full_line(pos)
		ctx = '9o.exec.%s' % gs.uid()
		view.replace(edit, line, ('[`%s`]\n' % cmd))
		view.run_command('gs9o_init')
		ep = view.full_line(line.begin()).end()
		view.add_regions(ctx, [sublime.Region(ep, ep)], '')
		hellip = u'[ \u22EF ]'
		ep += 1
		view.insert(edit, ep, hellip+'\n\n')
		view.add_regions(ctx+'.done', [sublime.Region(ep, ep+len(hellip))], '')

		cli = cmd.split(' ', 1)
		if cli[0] == 'sh':
			a = cli[1].strip() if len(cli) == 2 else ''
			mk_cmd(view, wd, ctx, sh.cmd(a)).start()
			return

		nv = sh.env()
		a = [_exparg(s, nv) for s in shlex.split(gs.astr(cmd))]
		f = builtins().get(a[0])
		if f:
			f(view, edit, a[1:], wd, ctx)
		else:
			mk_cmd(view, wd, ctx, a).start()

	else:
		view.insert(edit, gs.sel(view).begin(), '\n')

class Gs9oPushOutput(sublime_plugin.TextCommand):
	def run(self, edit, rkey, output, hourglass_repl=''):
		view = self.view
		output = '\t%s' % gs.ustr(output).strip().replace('\r', '').replace('\n', '\n\t')
		regions = view.get_regions(rkey)
		if regions:
			line = view.line(regions[0].begin())
			lsrc = view.substr(line).replace(HOURGLASS, (hourglass_repl or '| done'))
			view.replace(edit, line, lsrc)
			r = line
			if output.strip():
				line = view.line(regions[0].begin())
				view.insert(edit, line.end(), '\n%s' % output)
				r = view.get_regions(rkey)[0]
		else:
			n = view.size()
			view.insert(edit, n, '\n%s' % output)
			r = sublime.Region(n, view.size())

		if cfg.nineo_show_end:
			view.show(r.end())
		else:
			view.show(r.begin())

class Gs9oShowCtx(sublime_plugin.TextCommand):
	def run(self, edit, ctx):
		rl = self.view.get_regions(ctx) or [sublime.Region(0, self.view.size())]
		if cfg.nineo_show_end:
			pt = rl[-1].end()
		else:
			pt = rl[0].begin()

		self.view.show(pt)

class Gs9oRunManyCommand(sublime_plugin.TextCommand):
	def run(self, edit, wd=None, commands=[], save_hist=False, focus_view=False):
		for run in commands:
			self.view.run_command("gs9o_open", {
				'run': run,
				'wd': wd,
				'save_hist': save_hist,
				'focus_view': focus_view,
			})

def builtins():
	m = gs.gs9o.copy()

	g = globals()
	for k, v in g.items():
		if k.startswith('cmd_'):
			k = k[4:].replace('_', '-')
			if k and k not in m:
				m[k] = v

	return m

def push_output(view, rkey, output, hourglass_repl=''):
	def f():
		view.run_command('gs9o_push_output', {
			'rkey': rkey,
			'output': output,
			'hourglass_repl': hourglass_repl,
		})

	sublime.set_timeout(f, 0)

def end_c(c):
	err = kv.filter_join(c.errs, '\n')
	if c.errs:
		err = 'Error: %s\n' % err

	st = kv.filter_join((c.res.get('Dur'), c.res.get('Mem')), MIDDOT)
	if st:
		st = '[ %s ]\n' % st

	status = ''.join((err, st))
	ss = c.sess
	ctx = ss.wr.ctx
	dctx = ctx+'.done'
	view = ss.wr.vv.view()

	rl = view.get_regions(ctx)
	if rl:
		r = view.full_line(rl[-1])
		if not view.substr(r).strip():
			view.run_command('gs_replace', {
				'begin': r.begin(),
				'end': r.end(),
				's': '',
			})

	rl = view.get_regions(dctx)
	if rl:
		r = view.full_line(rl[-1])
		view.run_command('gs_replace', {
			'begin': r.begin(),
			'end': r.end(),
			's': status,
		})
		view.add_regions(dctx, [view.line(r.begin())], '')
	else:
		ss.write(status)

	view.run_command('gs9o_show_ctx', {'ctx': ctx})
	c.resume()

def mk_cmd(view, wd, ctx, cn):
	wr = nineo.Wr(view=view, ctx=ctx)
	ss = Sess(wd=wd, wr=wr)
	return ss.cmd(cn, cb=end_c)

def cmd_reset(view, edit, args, wd, rkey):
	push_output(view, rkey, '')
	view.erase(edit, sublime.Region(0, view.size()))
	view.run_command('gs9o_init')

def cmd_clear(view, edit, args, wd, rkey):
	cmd_reset(view, edit, args, wd, rkey)

def cmd_tskill(view, edit, args, wd, rkey):
	if len(args) == 0:
		sublime.set_timeout(lambda: sublime.active_window().run_command("gs_show_tasks"), 0)
		push_output(view, rkey, '')
		return

	l = []
	for k in args:
		k = k.lstrip('#')
		l.append('task %s canceled: %s' % (k, ('yes' if ui.taskd.cancel(k) else 'no')))

	push_output(view, rkey, '\n'.join(l))

def _env_settings(d, view, edit, args, wd, rkey):
	if len(args) > 0:
		m = {}
		for k in args:
			m[k] = d.get(k)
	else:
		m = d

	s = '\n'.join((
		'Default Settings file: gs.packages://GoSublime/GoSublime.sublime-settings (do not edit this file)',
		'User settings file: gs.packages://User/GoSublime.sublime-settings (add/change your settings here)',
		json.dumps(m, sort_keys=True, indent=4),
	))
	push_output(view, rkey, s)

def cmd_settings(view, edit, args, wd, rkey):
	_env_settings(gs.settings_dict(), view, edit, args, wd, rkey)

def cmd_env(view, edit, args, wd, rkey):
	_env_settings(sh.env(), view, edit, args, wd, rkey)

def cmd_hist(view, edit, args, wd, rkey):
	aso = gs.aso()
	hkey = _hkey(wd)

	s = 'hist: invalid args: %s' % args

	if len(args) == 0:
		hist = gs.dval(aso.get(hkey), [])
		hist.reverse()
		hlen = len(hist)
		s = '\n'.join('^%d: %s' % (i+1, v) for i,v in enumerate(hist))
	elif len(args) == 1:
		if args[0] == 'erase':
			aso.erase(hkey)
			gs.save_aso()
			s = ''

	push_output(view, rkey, s)
