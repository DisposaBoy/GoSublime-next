from . import about
from . import ev
from . import gs
from . import hl
from . import kv
from . import mg9
from . import sh
from . import vu
import base64
import copy
import os
import re
import string
import sublime

DOMAIN = '9o'

_builtins = {}

class Wr(object):
	def __init__(self, view, ctx='', interp=True, scope='', outlined=False):
		self.vv = vu.V(view)
		self.ctx = ctx
		self.interp = interp
		self.scope = scope
		self.outlined = outlined

	def write(self, s):
		self.vv.write(s=s, ctx=self.ctx, interp=self.interp, scope=self.scope, outlined=self.outlined)

class Cmd(object):
	def __init__(self, sess, cn, cb=None, set_stream=None):
		self.cid = ''
		self.attrs = []
		self.input = ''
		self.dirty = False
		self.fn = ''
		self.discard_stdout = False
		self.discard_stderr = False
		self.save = False
		self.set_stream = set_stream
		self.stream = True
		self.wd = ''
		self.env = {}
		self.hl = {}
		self.cfg = {}
		self.switch = []
		self.switch_ok = True
		self.ui = {}
		self.final = ''
		self.cmd = ''
		self.args = []
		self.res = {}
		self.ok = True
		self.cl = {
			'all': [],
			'any': [],
			'each': [],
		}
		self.sess = sess
		self.wd = sess.wd
		self.cbl = []
		self.errs = []
		self.visited = []
		self.f = None
		self.g = None
		self.exec_opts = {}

		self.cb(cb)
		self.merge(cn)

	def cb(self, cb):
		if gs.callable(cb):
			self.cbl.append(cb)

	def merge(self, cn):
		if gs.is_a_string(cn):
			v = self.sess.cmds.get(cn)
			if v is not None:
				# allow the user to specify a command without a `cmd`entry:
				# default the name in the `cmds` object
				if not self.cmd:
					self.cmd = cn

				if v in self.visited:
					self.visited.append(v)
					self.final = 'error/recursion'
					self.errs.append('recursive command definition: %s' % self.visited_names())
					return

				cn = v

		if gs.is_a_string(cn):
			# same as above "allow the user..."
			if not self.cmd:
				self.cmd = cn

			# break the recursion
			cn = {}
		elif gs.is_a(cn, []):
			cn = {'cmd': cn[0], 'args': cn[1:]}
		elif not gs.is_a(cn, {}):
			self.final = 'error/invalid-type'
			self.errs.append('invalid command type. want object, array or string, got %s' % type(cn))
			return

		if not self.cid:
			self.cid = cn.get('cid') or ''

		if not self.input:
			self.input = cn.get('input') or ''

		if not self.discard_stdout:
			self.discard_stdout = cn.get('discard_stdout') is True

		if not self.discard_stderr:
			self.discard_stderr = cn.get('discard_stderr') is True

		if not self.stream:
			self.stream = cn.get('stream') is True

		if not self.save:
			self.save = cn.get('save') is True

		self.switch_ok = bool(cn.get('switch_ok', self.switch_ok))

		for k in self.cl:
			x = cn.get(k)
			if x:
				self.cl[k].insert(0, Cmd(self.sess, x))

		if not self.wd:
			self.wd = cn.get('wd') or ''

		self.update_d(self.ui, cn, 'ui')
		self.update_d(self.hl, cn, 'hl')
		self.update_d(self.cfg, cn, 'cfg')
		self.update_d(self.env, cn, 'env')
		self.update_l(self.switch, cn, 'switch')
		self.update_l(self.args, cn, 'args')
		self.update_l(self.attrs, cn, 'attrs')

		if not self.final:
			self.final = cn.get('final') or self.final

		cm = cn.get('cmd', '')
		self.cmd = cm or self.cmd

		if cm and not self.final:
			if len(self.visited) > 100:
				self.final = 'error/max-depth'
				self.errs.append('max command resolution depth reached: %s' % self.visited_names())
				return

			self.visited.append(cn)
			self.merge(cm)

		if self.final in ('', 'builtin'):
			f = builtin(self.cmd)
			if f:
				self.f = f
				self.final = 'builtin'

	def visited_names(self):
		return ' -> '.join('{%s}' % v.get('cmd', '<anon>') for v in self.visited)

	def update_d(self, p, d, q_name):
		q = gs.dval(d.get(q_name), {})
		for k in q:
			if not p.get(k):
				p[k] = copy.deepcopy(q[k])

	def update_l(self, p, d, q_name):
		q = gs.dval(d.get(q_name), [])
		if q:
			l = p[:]
			del p[:]

			if q_name == 'switch':
				for v in q:
					if gs.is_a_string(v):
						v = {'case': [v]}

					p.append(v)
			else:
				p.extend(q.copy())

			p.extend(l)

	def start(self, cb=None):
		if self.errs:
			self.fail('\n'.join(self.errs))
			return

		self.env = sh.env(self.env)

		for k in self.env:
			self.env[k] = self.exp(self.env[k])

		for k in self.hl:
			self.hl[k] = self.exp(self.hl[k])

		for sw in self.switch:
			attr = sw.get('attr')
			if attr:
				for k in attr:
					attr[k] = self.exp(attr[k])

		if self.final == 'sh':
			l = sh.cmd(' '.join(gs.lst(c.cmd, c.args)))
			c.cmd = l[0]
			c.args = l[1:]
		else:
			self.cmd = self.exp(self.cmd)
			self.args = [self.exp(v) for v in self.args]

		if self.save:
			self.sess.save_all(self.wd)

		if self.input is True:
			vv = self.sess.vv
			self.input = vv.src()
			self.fn = vv.vfn()
			self.dirty = vv.view().is_dirty()
		elif not gs.is_a_string(self.input):
			self.input = ''

		self.cb(cb)
		self.g = self.gen()
		self.resume()

	def gen(self):
		f = self.f or exec_c

		ev.debug(DOMAIN, {
			'k': 'start',
			'f': f,
		})
		yield f(self)

		if self.ok:
			for x in self.cl['all']:
				ev.debug(DOMAIN, {
					'k': 'all',
					'c': x,
				})
				yield x.start(self.call_resume)
				self.ok = x.ok
				if not x.ok:
					break
		else:
			for x in self.cl['any']:
				ev.debug(DOMAIN, {
					'k': 'any',
					'c': x,
				})
				yield x.start(self.call_resume)
				self.ok = x.ok
				if x.ok:
					break

		for x in self.cl['each']:
			ev.debug(DOMAIN, {
				'k': 'each',
				'c': x,
			})
			yield x.start(self.call_resume)

		for f in self.cbl:
			ev.debug(DOMAIN, {
				'k': 'cb',
				'cb': f,
			})
			yield f(self)

		if self.hl:
			ev.debug(DOMAIN, {
				'k': 'hl',
				'hl': self.hl,
				'attrs': self.attrs,
			})
			gs.do(DOMAIN, self.do_hl)

	def resume(self, ok=None):
		if ok in (True, False):
			self.ok = ok

		gs.do(DOMAIN, lambda: next(self.g, None))

	def call_resume(self, c):
		c.resume()
		self.resume()

	def done(self, s=''):
		if s:
			self.sess.writeln(s)

		self.resume(True)

	def fail(self, s=''):
		if s:
			self.errs.append(s)
			self.sess.error(s)

		self.resume(False)

	def exp(self, s):
		if gs.is_a_string(s):
			return string.Template(s).safe_substitute(self.env)

		return s

	def do_hl(self):
		ctx = self.hl.get('ctx')
		if not ctx:
			return

		hl.clear(ctx)

		for a in self.attrs:
			a = gs.dval(a, {})
			message = a.get('message', '').strip()
			fn = a.get('fn')
			dnm = a.get('dirname')
			bnm = a.get('basename')

			if not fn and bnm:
				if dnm:
					fn = os.path.join(dnm, bnm)
				else:
					fn = bnm

			if fn and fn != '<stdin>':
				fn = gs.abspath(fn, self.sess.wd)
			else:
				fn = self.sess.vv.vfn()

			if fn and message:
				hl.add(hl.Note(
					ctx = ctx,
					fn = fn,
					pos = a.get('pos'),
					message = message,
				))

		hl.refresh()

class Sess(object):
	def __init__(self, wr=None, wd='', win=None, view=None, cmds={}):
		self.vv = vu.active(win=win, view=view)
		self.wr = wr or Wr(None)
		self.wd = wd or gs.basedir_or_cwd(self.vv.fn())
		d = gs.settings_dict()
		self.cmds = d.get('default_commands', {})
		self.cmds.update(cmds or d.get('commands', {}))

	def cmd(self, cn, cb=None, set_stream=None):
		return Cmd(self, cn, cb=cb, set_stream=set_stream)

	def save_all(self, wd):
		if self.vv.view() is None:
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

	def write(self, s):
		self.wr.write('%s' % s)

	def writeln(self, s):
		self.wr.write('%s\n' % s)

	def error(self, s):
		self.wr.write('Error: %s\n' % s)

def builtin(nm, f=None):
	f = gs.callable(f)
	if f:
		_builtins[nm] = f

	return _builtins.get(nm)

def gs_init(_={}):
	pass

def chunk(s):
	try:
		return gs.ustr(base64.b64decode(s)) or ''
	except Exception:
		return s or ''

def _visible_c(c, basename):
	return not (basename.startswith(('.', 'gs.')) or c.ui.get('hidden'))

def exec_c(c):
	if not c.cmd:
		c.fail('invalid command')
		return

	uid = gs.uid()
	st = ''
	stream = c.set_stream
	if stream is None:
		stream = c.stream

	if stream:
		st = '%s.exec.stream' % uid
		def stream_f(res, err):
			for s in res.get('Chunks', []):
				c.sess.write(chunk(s))

			return not res.get('End')

		mg9.on(st, stream_f)

	cid = c.cid
	if not cid:
		cid = '%s.exec.cid' % uid

	c.exec_opts = {
		'Stream': st,
		'Cid': cid,
		'Dirty': c.dirty,
		'Fn': c.fn,
		'Input': c.input,
		'Env': c.env,
		'Wd': c.sess.wd,
		'Cmd': c.cmd,
		'Args': c.args,
		'Switch': c.switch,
		'SwitchOk': c.switch_ok,
		'DiscardStdout': c.discard_stdout,
		'DiscardStderr': c.discard_stderr,
	}

	tid = gs.begin(
		DOMAIN,
		'[ %s ] # %s %s' % (gs.simple_fn(c.sess.wd), c.cmd, c.args),
		set_status=False,
		cancel=lambda: mg9.acall('cancel', {'Cid': cid}, None)
	)

	def f(res, err):
		try:
			c.attrs.extend(gs.dval(res.get('Attrs'), []))
			c.res = res
			chunks = res.get('Chunks', [])
			if chunks:
				for s in chunks[:-1]:
					c.sess.write(chunk(s))

				s = chunk(chunks[-1])
				if s.endswith('\n'):
					c.sess.write(s)
				else:
					c.sess.writeln(s)

			if err:
				c.fail(err)
			else:
				c.resume(res.get('Ok'))
		except Exception:
			gs.print_traceback()
		finally:
			gs.end(tid)

	mg9.acall('exec', c.exec_opts, f)

def _hk(view, e):
	ss = Sess(view=view)
	fx = ss.vv.ext()

	# file_sync is triggered for file_loaded and file_saved, so don't call `gs.on-lint` again
	if e == 'sync':
		el = ['gs.on-sync']
	else:
		el = ['gs.on-%s' % e, 'gs.on-lint']

	for k in el:
		for v in set((k+fx, k)):
			cn = ss.cmds.get(v)
			# check for `None`, not `falsey value`; empty command objects refer to system commands and builtins
			if cn is not None:
				ss.cmd(cn, set_stream=False).start()
				ev.debug(DOMAIN, {
					'k': 'hk',
					'hook': v,
				})

def quick_commands():
	ss = Sess()
	l = []
	titles = {}
	for nm in ss.cmds:
		c = ss.cmd(nm)
		if _visible_c(c, nm):
			title = c.ui.get('title') or nm
			titles[title] = nm
			l.append(title)

	if not l:
		gs.show_quick_panel([['', 'No overlay commands found']])
		return

	aso = gs.aso()
	qk = 'quick_commands_used'
	qm = aso.get(qk, {})

	def kf(k):
		if k in qm:
			return (0, len(qm) - qm[k], k)
		return (1, 0, k)

	l.sort(key=kf)

	def f(i, win):
		if i < 0:
			return

		k = l[i]
		nm = titles[k]
		win.run_command('gs9o_win_open', {
			'run': [nm],
			'focus_view': False,
			'save_hist': True,
		})

		qm[k] = qm.get(k, 0) + 1
		aso.set(qk, qm)
		gs.save_aso()

	gs.show_quick_panel(l, f)


ev.file_sync += lambda view: _hk(view, 'sync')
ev.file_loaded += lambda view: _hk(view, 'load')
ev.file_saved += lambda view: _hk(view, 'save')
ev.view_updated += lambda view: _hk(view, 'change')
ev.view_activated += lambda view: _hk(view, 'activate')
