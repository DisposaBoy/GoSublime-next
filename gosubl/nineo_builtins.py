from . import about
from . import gs
from . import gsq
from . import mg9
from . import nineo
from . import vu
import os
import pprint
import sublime

def gs_init(_={}):
	g = globals()
	p = 'bi_'
	l = len(p)
	for nm in list(g.keys()):
		if nm.startswith(p):
			k = nm[l:].replace('__', '.').replace('_', '-')
			nineo.builtin(k, g[nm])

def _do_cl(c, k):
	if c.args:
		c.ok = k != 'any'
		for cn in c.args:
			c.cl[k].append(c.sess.cmd(cn, set_stream=c.set_stream))
	else:
		c.ok = True

	c.resume()

def bi_all(c):
	_do_cl(c, 'all')

def bi_any(c):
	_do_cl(c, 'any')

def bi_each(c):
	_do_cl(c, 'each')

def bi_version(c):
	c.done(about.VERSION)

def bi_true(c):
	c.done()

def bi_false(c):
	c.fail()

def bi_confirm(c):
	if c.args:
		c.resume(sublime.ok_cancel_dialog(' '.join(c.args)))
	else:
		c.fail('Usage: confirm <message>')

def _dbg_c(c, keys):
	d = c.__dict__
	if keys:
		v = {}
		for k in keys:
			v[k] = d.get(k)
	else:
		v = d

	return pprint.pformat(v)

def bi_gs__cmdump(c):
	if len(c.args) == 0 or not gs.is_a(c.args[0], []):
		c.fail('Usage: gs.cmdump <keys-list> [cmd [args...]]')
		return

	keys = c.args[0]
	args = c.args[1:]
	s = _dbg_c(c, keys)
	print('gs.cmdump: %s' % s)
	c.done(s)

def bi_gs__cmdebug(c):
	if len(c.args) == 0 or not gs.is_a(c.args[0], []):
		c.fail('Usage: gs.cmdebug <keys-list> [cmd [args...]]')
		return

	keys = c.args[0]
	args = c.args[1:]

	def cb(x):
		print('gs.cmdebug: %s' % _dbg_c(x, keys))
		x.resume()
		c.resume(x.ok)

	c.sess.cmd(args, cb=cb, set_stream=c.set_stream).start()

def bi_echo(c, ok=True):
	c.sess.write(' '.join(c.args))
	c.resume(ok)

def bi_fail(c):
	bi_echo(c, False)

def bi_gs__synchk(c):
	def f(res, err):
		errs = res.get('Errors', [])
		if errs:
			for e in errs:
				c.attrs.append({
					'fn': e.get('Fn', ''),
					'message': e.get('Message', ''),
					'pos': '%s:%s' % (e.get('Line', -1), e.get('Column', 0)),
				})

			c.fail()
		else:
			c.done()

	if c.args:
		files = [{'Fn': fn} for fn in c.args]
	else:
		vv = c.sess.vv
		fn = vv.fn()
		if fn and not vv.view().is_dirty():
			files = [{'Fn': fn}]
		else:
			files = [{'Src': vv.src()}]

		if not c.hl:
			c.hl = {
				'ctx': 'gs.synchk:%s' % vv.vfn(),
			}

	mg9.acall('synchk', {'Files': files}, f)

def bi_go(c):
	if c.args and c.args[0] in ('build', 'install', 'run', 'test', 'vet'):
		c.sess.save_all(c.wd)
		if not c.hl.get('ctx'):
			s = 'compile'
			if c.args[0] == 'vet':
				s = 'vet'

			c.hl['ctx'] = ' '.join(('go', s, c.env.get('_wd_or_vfn', '')))

	# note: do *not* resume c, we're *switching* to exec_c, not *starting* a new command
	nineo.exec_c(c)

def bi_cd(c):
	try:
		wd = gs.abspath(' '.join(c.args), dir=c.wd)
		os.chdir(wd)
		c.sess.wr.vv.view().run_command('gs9o_init', {'wd': wd})
		c.done()
	except Exception as ex:
		c.fail('Cannot chdir: %s' % ex)

def bi_help(c):
	vu.open(gs.dist_path('9o.md'))
	c.done()

def bi_share(c):
	vv = vu.active()
	view = vv.view()
	if view is None or view.score_selector(0, 'source.go') <= 0:
		c.fail('not sharing non-go src')
		return

	def f(res, err):
		if err:
			c.fail(err)
		else:
			s = res.get('Url', '').strip()
			if s:
				sublime.set_clipboard(s)
				c.done(s + ' (url copied to the clipboard)')
			else:
				c.fail('no url received')

	mg9.share(vv.src(), f)

def bi_gs__build_margo(c):
	def f():
		out = mg9.build_mg()
		if out == 'ok':
			mg9.killSrv()
			c.done('ok')
		else:
			c.fail(out)

	gsq.do('GoSublime', f, msg='Rebuilding MarGo')
