from . import about
from . import gs
from . import kv
from . import mg9
from . import sh
import copy
import os
import string
import sublime

DOMAIN = '9o'

views = kv.M()

completions = []
_builtins = {}

class Writer(object):
	def __init__(self, view):
		self.view = view

	def write(self, s):
		print(self.view, s)

class Session(object):
	def __init__(self, wr, wd):
		try:
			self.view = sublime.active_window().active_view()
			fn = self.view.file_name() or ''
		except AttributeError:
			self.view = None
			fn = ''

		self.wr = wr
		self.wd = wd or gs.basedir_or_cwd(fn)
		self.input = ''

	def mk(self, cn):
		return self._mk(gs.setting('commands', {}), {}, '', cn)

	def _mk_c(self, cmds, seen, base_nm, cn):
		if not cn:
			return ('', {}, 'empty command')

		if gs.is_a(cn, {}):
			return ('', cn, '')

		if gs.is_a(cn, []):
			return ('', {'cmd': cn[0], 'args': cn[1:]}, '')

		if not gs.is_a_string(cn):
			return ('', {}, 'invalid command type %s' % type(cn))

		if cn in seen:
			return (cn, {}, 'recursive command definition: `%s` <-> `%s`' % (base_nm, cn))

		seen[cn] = True
		c = cmds.get(cn, {})
		if c:
			return self._mk_c(cmds, seen, cn, c)

		return ('', {'builtin': True, 'cmd': cn}, '')

	def _mk(self, cmds, seen, base_nm, cn):
		nm, c, err = self._mk_c(cmds, seen, base_nm, cn)
		if not c:
			return ({}, err)

		# we want to avoid any side-effects on the original object as we're going to mutate the
		# object later
		c = copy.deepcopy(c)

		self.c_env(c)
		self.c_wd(c)
		self.c_cmd(c)
		self.c_args(c)
		self.c_switch(c)
		self.c_discard(c)

		nx = c['cmd']
		if self.c_can_expand(c, cmds, nm, nx):
			c['cmd'] = ''

			x, err = self._mk(cmds, seen, nm, nx)
			if err:
				return ({}, err)

			for k in x:
				if k in ('args', 'switch', 'attrs'):
					x[k].extend(c[k])
					c[k] = x[k]
				elif k in ('env'):
					x[k].update(c[k])
					c[k] = x[k]
				else:
					c[k] = x[k]

		return (c, '')

	def save_all(self, wd):
		if self.view is None:
			return

		if not wd:
			wd = self.wd
			if not wd:
				return

		win = self.view.window()
		if win is None:
			return

		for view in win.views():
			if self.view_wd(view) == wd:
				self.save(view)

	def save(self, view):
		if view is not None and view.file_name() and view.is_dirty():
			view.run_command('save')

	def view_wd(self, view):
		if view is None:
			return ''

		fn = view.file_name()
		if not fn:
			return ''

		return self.dir(fn)

	def dir(self, fn):
		return os.path.dirname(os.path.normpath(fn))

	def expand(self, s, env):
		return string.Template(s).safe_substitute(env)

	def c_env(self, c):
		c['env'] = sh.env(c.get('env', {}))

	def c_save(self, c):
		if c.get('save') is True:
			self.save_all(c.get('wd'))

		# cache the input *after* it's saved so any event hander mutations are picked up
		self.input = gs.view_src(self.view)

	def c_input(self, c):
		s = c.get('input') or ''
		c['input'] = self.input if s is True else s

	def c_wd(self, c):
		if c.get('wd'):
			c['wd'] = self.expand(c['wd'], c['env'])
		else:
			c['wd'] = self.wd

	def c_can_use_builtin(self, c):
		if c.get('os') or c.get('sh'):
			return None

		return builtin(c['cmd'])

	def c_can_expand(self, c, cmds, nm, nx):
		if nm == nx:
			return False

		if c.get('builtin'):
			return False

		if c.get('os') or c.get('sh'):
			return False

		return nx in cmds

	def c_cmd(self, c):
		s = c.get('cmd') or ''
		c['cmd'] = self.expand(s, c['env'])

	def c_args(self, c):
		c['args'] = [self.expand(v, c['env']) for v in gs.lst(c.get('args', []))]

	def c_switch(self, c):
		c['switch'] = [v for v in gs.lst(c.get('switch', [])) if v]

	def c_discard(self, c):
		c['discard_stdout'] = c.get('discard_stdout') is True
		c['discard_stderr'] = c.get('discard_stderr') is True

	def write(self, s):
		self.wr.write(s)

	def writeln(self, s):
		self.wr.write('%s\n' % s)

	def error(self, s):
		self.wr.write('Error: %s\n' % s)

	def exec_c(self, c, cb):
		a = {
			'Stream': c['stream'],
			'Cid': c['cid'],
			'Input': c['input'],
			'Env': c['env'],
			'Wd': c['wd'],
			'Cmd': c['cmd'],
			'Args': c['args'],
			'Switch': c['switch'],
			'DiscardStdout': c.get('discard_stdout') is True,
			'DiscardStderr': c.get('discard_stderr') is True,
		}

		tid = gs.begin(
			DOMAIN,
			'[ %s ] # %s %s' % (gs.simple_fn(c['wd']), c['cmd'], c['args']),
			set_status=False,
			cancel=lambda: mg9.acall('cancel', {'cid': c['cid']}, None)
		)

		def f(res, err):
			try:
				gs.do(DOMAIN, lambda: cb(res, err))
			except Exception:
				gs.println(gs.traceback())
			finally:
				gs.end(tid)

		mg9.acall('exec', a, f)

	def start(self, cn, cb):
		c, err = self.mk(cn)
		if err:
			self.error(err)
			return

		if not c:
			self.error('invalid command: `%s`' % cn)
			return

		if c.get('sh') is True:
			l = sh.cmd(' '.join(gs.lst(c['cmd'], c['args'])))
			c['cmd'] = l[0]
			c['args'] = l[1:]

		uid = gs.uid()
		c['stream'] = '%s.stream' % uid
		mg9.on(c['stream'], lambda res, err: self.write(res.get('line')))

		if not c.get('cid'):
			c['cid'] = uid

		self.c_save(c)
		self.c_input(c)

		def f(res, err):
			if err:
				self.error(err)

			cb2 = cb
			then = c.get('then')
			if then:
				def cb2(res, err):
					if err:
						self.error(err)

					self.start(then, cb)

			andor = c.get('and') if res.get('ok') is True else c.get('or')
			if andor:
				self.start(andor, cb2)
			else:
				gs.do(DOMAIN, lambda: cb2(res, err))

		b = self.c_can_use_builtin(c)
		if b:
			gs.do(DOMAIN, lambda: b(self, c, f))
		else:
			self.exec_c(c, f)

def builtin(nm, f=None):
	f = gs.callable(f)
	if f:
		_builtins[nm] = f

	return _builtins.get(nm)

def gs_init(_={}):
	g = globals()
	for nm in list(g.keys()):
		if nm.startswith('_builtin_'):
			builtin('gs.%s' % nm[9:].replace('_', '-'), g[nm])

def _ret(f, res, err):
	gs.do(DOMAIN, lambda: f(res, err))

def _builtin_version(ss, c, f):
	ss.writeln(about.VERSION)
	_ret(f, {}, '')
