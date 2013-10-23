from . import about
from . import gs
from . import hl
from . import kv
from . import mg9
from . import sh
from . import vu
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
		# todo: implement this
		print(s)

class Session(object):
	def __init__(self, wr, wd='', win=None, view=None, args=[]):
		self.wr = wr
		self.vv = vu.active(win=win, view=view)
		self.wd = wd or gs.basedir_or_cwd(self.vv.fn())
		self.args = args
		self.input = ''
		self.user_args = True

	def _highlight(self, c, res):
		if not gs.is_a(res, {}):
			gs.debug(DOMAIN, {
				'err': 'res is not a dict',
				'res': res,
				'c': c,
			})
			return

		# todo: do we really want to reject `None` here? (i.e shoul we defaut to [])
		attrs = res.get('attrs')
		if not gs.is_a(attrs, []):
			gs.debug(DOMAIN, {
				'err': 'attrs is not a list',
				'attrs': attrs,
				'c': c,
			})
			return

		nd = {}
		cd = {}

		for a in attrs:
			if not gs.is_a(a, {}):
				continue

			ctx = a.get('gs.highlight')
			if not ctx:
				continue

			fn = a.get('fn')
			if fn and fn != '<stdin>':
				fn = gs.abspath(fn, c['wd'])
			else:
				fn = self.vv.vfn()

			cd.setdefault(fn, []).append(ctx)
			nd.setdefault(fn, []).append(hl.Note(
				ctx = ctx,
				fn = fn,
				pos = a.get('pos'),
				message = a.get('message') or '',
				scope = a.get('gs.scope') or '',
				icon = a.get('gs.icon') or ''
			))

		if nd:
			views = {}
			for win in sublime.windows():
				for view in win.views():
					vfn = gs.view_fn(view)
					if vfn in nd:
						views[vfn] = view

			for vfn in views:
				view = views[vfn]
				hl.clear_notes(view, cd[vfn])
				hl.add_notes(view, nd[vfn])

	def _cb(self, c, cb):
		def f(res, err):
			gs.do(DOMAIN, self._highlight(c, res))

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

		return f

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
		c['_wd'] = c['wd']
		c['PWD'] = c['wd']
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
		if self.vv.view is None:
			return

		if not wd:
			wd = self.wd
			if not wd:
				return

		for view in self.vv.sibling_views():
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
		env = sh.env()
		env.update(c.get('env', {}))
		env.update({
			'_fn': self.vv.fn(),
			'_vfn': self.vv.vfn(),
		})
		c['env'] = env

	def c_save(self, c):
		if c.get('save') is True:
			self.save_all(c.get('wd'))

		# cache the input *after* it's saved so any event hander mutations are picked up
		self.input = self.vv.src()

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
		l = []
		for sw in gs.lst(c.get('switch')):
			if gs.is_a(sw, {}):
				cs = sw.get('case')
				if not gs.is_a(cs, []):
					if cs in ('', None):
						sw['case'] = []
					elif gs.is_a_string(cs):
						sw['case'] = [cs]
					else:
						continue

			l.append(sw)

		c['switch'] = l


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

		user_args = c.get('user_args', self.user_args)
		self.user_args = False
		if user_args:
			c['args'].extend([self.expand(v, c['env']) for v in self.args])

		if c.get('sh') is True:
			l = sh.cmd(' '.join(gs.lst(c['cmd'], c['args'])))
			c['cmd'] = l[0]
			c['args'] = l[1:]

		uid = gs.uid()

		if not c.get('cid'):
			c['cid'] = uid

		self.c_save(c)
		self.c_input(c)

		f = self._cb(c, cb)
		b = self.c_can_use_builtin(c)
		if b:
			gs.do(DOMAIN, lambda: b(self, c, f))
		else:
			def stream(res, err):
				out = res.get('out')
				if out is not None:
					self.write(out)

				return not res.get('eof')

			if c.get('stream') is False:
				c['stream'] = ''
			else:
				c['stream'] = '%s.stream' % uid
				mg9.on(c['stream'], stream)

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
			builtin(nm[9:].replace('__', '.').replace('_', '-'), g[nm])

def _dbg_cb(keys=[]):
	def f(res, err):
		if keys:
			r = {}
			for k in keys:
				r[k] = res.get(k, '<nil>')
		else:
			r = res

		print({
			'res': r,
			'err': err,
		})

	return f


def _ret(f, res, err):
	if res.get('ok') is None:
		res['ok'] = not err

	gs.do(DOMAIN, lambda: f(res, err))

def _builtin_gs__version(ss, c, f):
	ss.writeln(about.VERSION)
	_ret(f, {}, '')
