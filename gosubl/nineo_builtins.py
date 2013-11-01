from . import about
from . import nineo

def gs_init(_={}):
	g = globals()
	for nm in list(g.keys()):
		if nm.startswith('bi_'):
			nineo.builtin(nm[9:].replace('__', '.').replace('_', '-'), g[nm])

def _do_cl(c, k):
	if c.args:
		c.ok = k != 'any'
		for cn in c.args:
			c.cl[k].append(c.sess.cmd(cn, cb=c.cb_step, set_stream=c.set_stream))
	else:
		c.ok = True

	c.step()

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
		c.step(sublime.ok_cancel_dialog(' '.join(c.args)))
	else:
		c.fail('Usage: confirm <message>')

def bi_gs__cmdump(c):
	s = '`%s`' % c.sess.cmd(c.args).__dict__
	print(s)
	c.done(s)

def bi_gs__cmdebug(c):
	def cb(x):
		print(x.__dict__)
		c.step(x.ok)

	c.sess.cmd(c.args, cb=cb, set_stream=c.set_stream).start()

def bi_echo(c, ok=True):
	if c.args and c.args[0] == '-n':
		c.sess.write(' '.join(c.args[1:]))
	else:
		c.sess.writeln(' '.join(c.args))

	c.step(ok)

def bi_fail(c):
	bi_echo(c, False)
