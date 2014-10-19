from . import about
from . import cfg
from . import ev
from . import gs
from . import gsq
from . import sh
from . import ui
from . import vu
import atexit
import base64
import hashlib
import json
import os
import re
import shutil
import sublime
import subprocess
import threading
import time

DOMAIN = 'GoSublime.mg9'
REQUEST_PREFIX = '%s.rqst.' % DOMAIN
PROC_ATTR_NAME = 'mg9.proc'
TAG = about.VERSION
INSTALL_VERSION = about.VERSION

def gs_init(m={}):
	atexit.register(killSrv)
	gsq.do(DOMAIN, _install, msg='Installing MarGo', set_status=True)

class Request(object):
	def __init__(self, f, method='', token=''):
		self.f = f
		self.tm = time.time()
		self.method = method
		if token:
			self.token = token
		else:
			self.token = gs.uid()

	def header(self, arg={}):
		return {
			'method': self.method,
			'token': self.token,
			'oob': gs.is_a(arg, {}) and arg.get('oob') is True,
		}

def _inst_state():
	return gs.attr(_inst_name(), '')

def _inst_name():
	return 'mg9.install.%s' % INSTALL_VERSION

def sanity_check_sl(sl):
	n = 0
	for p in sl:
		n = max(n, len(p[0]))

	t = '%d' % n
	t = '| %'+t+'s: %s'
	indent = '| %s> ' % (' ' * n)

	a = '~%s' % os.sep
	b = os.path.expanduser(a)

	return [t % (k, gs.ustr(v).replace(b, a).replace('\n', '\n%s' % indent)) for k,v in sl]

def sanity_check(env={}, error_log=False):
	if not env:
		env = sh.env()

	ns = '(not set)'

	sl = [
		('install state', _inst_state()),
		('sublime.version', sublime.version()),
		('sublime.channel', sublime.channel()),
		('about.ann', gs.attr('about.ann', '')),
		('about.version', gs.attr('about.version', '')),
		('version', about.VERSION),
		('platform', about.PLATFORM),
		('~bin', '%s' % sh.bin_dir()),
		('go.exe', '%s (%s)' % _tp(sh.which('go') or 'go')),
		('margo.exe', '%s (%s)' % _tp(sh.which('margo') or 'margo')),
		('go.version', sh.GO_VERSION),
		('GOROOT', '%s' % env.get('GOROOT', ns)),
		('GOPATH', '%s' % env.get('GOPATH', ns)),
		('MARGOPATH', '%s' % env.get('MARGOPATH', ns)),
		('GOBIN', env.get('GOBIN', ns)),
		('cfg.shell', str(gs.lst(cfg.shell))),
		('env.shell', env.get('SHELL', '')),
		('shell.cmd', str(sh.cmd('${CMD}'))),
	]

	if error_log:
		try:
			with open(gs.home_path('log.txt'), 'r') as f:
				s = f.read().strip()
				sl.append(('error log', s))
		except Exception:
			pass

	return sl

def _sb(s):
	bdir = sh.bin_dir()
	if s.startswith(bdir):
		s = '~bin%s' % (s[len(bdir):])
	return s

def _tp(s):
	return (_sb(s), ('ok' if os.path.exists(s) else 'missing'))

def _mg_exists():
	return bool(sh.which('margo'))

def build_mg():
	gobin = sh.bin_dir()
	gopath = sh.getenv('MARGOPATH')
	wd = gobin
	env = {
		'CGO_ENABLED': '0',
		'GOBIN': gobin,
		'GOPATH': gopath,
	}

	# do a cleanup just-in-case there are old packages built by other other versions of the Go compiler lying around...
	# we don't really care if it fails
	for p in gopath.split(os.pathsep):
		if p:
			pat = './gosubli.me/...'
			if p == gs.dist_path():
				pat = './...'
			clean = sh.Command(['go', 'clean', '-i', '-x', pat])
			clean.wd = p
			clean.env = {'GOPATH': p}
			clean.run()

	f = gs.setting('_build_flags') or ['-v', '-x']
	args = gs.lst('go', 'build', '-tags', 'gosublime', f, '-o', sh.exe('margo'), 'gosubli.me/margo')

	build = sh.Command(args)
	build.wd = wd
	build.env = env

	ev.debug('%s.build' % DOMAIN, {
		'cmd': build.cmd_lst,
		'cwd': build.wd,
	})

	cr = build.run()

	m_out = 'cmd: `%s`\nstdout: `%s`\nstderr: `%s`\nexception: `%s`' % (
		cr.cmd_lst,
		cr.out.strip(),
		cr.err.strip(),
		cr.exc,
	)

	if cr.ok and _mg_exists():
		if cfg._dev:
			print('GoSublime MarGo build: %s\n' % m_out)

		return 'ok'

	err_prefix = 'MarGo build failed'
	ui.error(DOMAIN, '%s\n%s' % (err_prefix, m_out))

	sl = [
		('GoSublime error', '\n'.join((
			err_prefix,
			'This is possibly a bug or miss-configuration of your environment.',
			'For more help, please file an issue with the following build output',
			'at: https://github.com/DisposaBoy/GoSublime/issues/new',
			'or alternatively, you may send an email to: gosublime@dby.me',
			'\n',
			m_out,
		)))
	]
	sl.extend(sanity_check({}, False))
	gs.show_output('GoSublime', '\n'.join(sanity_check_sl(sl)), overlay=False)

	return m_out

def _install(maybe=False):
	if _inst_state() != "":
		return

	start = time.time()

	gs.set_attr(_inst_name(), 'busy')
	m_out = 'ok' if _mg_exists() else build_mg()
	gs.set_attr(_inst_name(), 'done')

	if m_out == 'ok':
		ev.margo_ready()
		if maybe:
			return

	e = sh.env()
	a = [
		'GoSublime init %s (%0.3fs)' % (INSTALL_VERSION, time.time() - start),
	]

	sl = [('install margo', m_out)]
	sl.extend(sanity_check(e))
	a.extend(sanity_check_sl(sl))
	gs.println(*a)

	_check_env(e)
	killSrv()
	_cleanup()

def _check_env(e):
	missing = [k for k in ('GOROOT', 'GOPATH') if not e.get(k)]
	if missing:
		missing_message = '\n'.join([
			'Missing required environment variables: %s' % ' '.join(missing),
			'See the `Quirks` section of USAGE.md for info',
		])

		cb = lambda ok: gs.show_output(DOMAIN, missing_message, merge_domain=True, print_output=False)
		ui.error(DOMAIN, missing_message)
		vu.open(gs.dist_path('USAGE.md')).focus(pat='^Quirks', cb=cb)

def _cleanup():
	try:
		vdir, vnm = os.path.split(sh.vdir())
		for nm in os.listdir(vdir):
			fn = os.path.join(vdir, nm)
			if nm != vnm and os.path.isdir(fn):
				try:
					gs.println("GoSublime: removing old directory: `%s'" % fn)
					shutil.rmtree(fn)
				except Exception:
					pass

	except Exception:
		pass

def calltip(fn, src, pos, quiet, f):
	t = None
	if not quiet:
		t = ui.task(DOMAIN, 'Fetching calltips')

	def cb(res, err):
		if t:
			t.end()

		res = gs.dval(res.get('Candidates'), [])
		f(res, err)

	return acall('gocode_calltip', _complete_opts(fn, src, pos, True), cb)

def complete(fn, src, pos):
	builtins = (gs.setting('autocomplete_builtins') is True or gs.setting('complete_builtins') is True)
	res, err = bcall('gocode_complete', _complete_opts(fn, src, pos, builtins))
	res = {
		'Candidates': gs.dval(res.get('Candidates'), []),
		'Suggestions': gs.dval(res.get('Suggestions'), []),
	}
	return res, err

def _complete_opts(fn, src, pos, builtins):
	nv = sh.env()
	return {
		'Dir': gs.basedir_or_cwd(fn),
		'Builtins': builtins,
		'Fn':  fn or '',
		'Src': src or '',
		'Pos': pos or 0,
		'Home': sh.vdir(),
		'Autoinst': gs.setting('autoinst'),
		'InstallSuffix': gs.setting('installsuffix'),
		'Env': {
			'GOROOT': nv.get('GOROOT', ''),
			'GOPATH': nv.get('GOPATH', ''),
		},
	}

def fmt(fn, src):
	st = gs.settings_dict()
	a = {
		'Fn': fn or '',
		'Src': src or '',
	}
	if cfg.fmt_cmd:
		a['Cmd'] = cfg.fmt_cmd[0]
		a['Args'] = cfg.fmt_cmd[1:]
	res, err = bcall('fmt', a)
	return res.get('Src', ''), err

def import_paths(fn, src, f):
	t = ui.task(DOMAIN, 'Fetching import paths')
	def cb(res, err):
		t.end()
		f(res, err)

	acall('import_paths', {
		'oob': True,
		'fn': fn or '',
		'src': src or '',
		'env': sh.env(),
		'WantPkgNames': gs.setting('use_named_imports'),
		'UseLegacyImports': gs.setting('use_legacy_imports'),
		'InstallSuffix': gs.setting('installsuffix'),
	}, cb)

def pkg_name(fn, src):
	res, err = bcall('pkg', {
		'fn': fn or '',
		'src': src or '',
	})
	return res.get('name'), err

def pkg_dirs(f):
	t = ui.task(DOMAIN, 'Fetching pkg dirs')
	def cb(res, err):
		t.end()
		f(res, err)

	acall('pkg_dirs', {
		'env': sh.env(),
	}, cb)

def a_posdef(fn, pos, f):
	t = ui.task(DOMAIN, 'posdef')
	def cb(res, err):
		t.end()
		f(res, err)

	m = sh.env()
	acall('posdef', {
		'Fn': fn,
		'Pos': pos,
		'Env': {
			'GOPATH': m.get('GOPATH'),
			'GOROOT': m.get('GOROOT'),
		},
		'InstallSuffix': gs.setting('installsuffix'),
	}, cb)

def a_pkgpaths(exclude, f):
	t = ui.task(DOMAIN, 'Fetching pkg paths')
	def cb(res, err):
		t.end()
		f(res, err)

	m = sh.env()
	acall('pkgpaths', {
		'env': {
			'GOPATH': m.get('GOPATH'),
			'GOROOT': m.get('GOROOT'),
		},
		'exclude': exclude,
		'WantPkgNames': gs.setting('use_named_imports'),
	}, cb)

def declarations(fn, src, pkg_dir, f):
	t = ui.task(DOMAIN, 'Fetching declarations')
	def cb(res, err):
		t.end()
		f(res, err)

	return acall('declarations', {
		'fn': fn or '',
		'src': src,
		'env': sh.env(),
		'pkgDir': pkg_dir,
	}, cb)

def imports(fn, src, toggle):
	return bcall('imports', {
		'autoinst': gs.setting('autoinst'),
		'env': sh.env(),
		'fn': fn or '',
		'src': src or '',
		'toggle': toggle or [],
	})

def doc(fn, src, offset, f):
	t = ui.task(DOMAIN, 'Fetching doc info')
	def cb(res, err):
		t.end()
		f(res, err)

	acall('doc', {
		'fn': fn or '',
		'src': src or '',
		'offset': offset or 0,
		'env': sh.env(),
	}, cb)

def share(src, f):
	warning = 'Are you sure you want to share this file. It will be public on play.golang.org'
	if sublime.ok_cancel_dialog(warning):
		acall('share', {'Src': src or ''}, f)
	else:
		f({}, 'Share cancelled')

def acall(method, arg, cb):
	gs.mg9_send_q.put((method, arg, cb))

def bcall(method, arg):
	if _inst_state() != "done":
		return {}, 'Blocking call(%s) aborted: Install is not done' % method

	q = gs.queue.Queue()
	acall(method, arg, lambda r,e: q.put((r, e)))
	try:
		res, err = q.get(True, 1)
		return res, err
	except:
		return {}, 'Blocking Call(%s): Timeout' % method

def expand_jdata(v):
	if gs.is_a(v, {}):
		for k in v:
			v[k] = expand_jdata(v[k])
	elif gs.is_a(v, []):
		v = [expand_jdata(e) for e in v]
	else:
		if gs.PY3K and isinstance(v, bytes):
			v = gs.ustr(v)

		if gs.is_a_string(v) and v.startswith('base64:'):
			try:
				v = gs.ustr(base64.b64decode(v[7:]))
			except Exception:
				v = ''
				ui.trace(DOMAIN)
	return v

def _recv():
	while True:
		try:
			ln = gs.mg9_recv_q.get()
			try:
				ln = ln.strip()
				if ln:
					res_tm = time.time()
					r, _ = gs.json_decode(ln, {})
					dec_tm = time.time()
					token = r.get('token', '')
					tag = r.get('tag', '')
					k = REQUEST_PREFIX+token
					req = gs.attr(k, {})
					gs.del_attr(k)
					if req and req.f:
						if tag != TAG:
							ui.error(DOMAIN, "\n".join([
								"GoSublime/MarGo appears to be out-of-sync.",
								"Maybe restart Sublime Text.",
								"Received tag `%s', expected tag `%s'. " % (tag, TAG),
							]))

						err = r.get('error', '')

						ev.debug(DOMAIN, {
							'_mode': 'response',
							'method': req.method,
							'tag': tag,
							'token': token,
							'req dur': '%0.3fs' % (res_tm - req.tm),
							'dec dur': '%0.3fs' % (dec_tm - res_tm),
							'err': err,
							'size': '%0.1fK' % (len(ln)/1024.0),
						})

						try:
							oob_fn = r.get('oob_fn')
							if oob_fn:
								ev.debug(DOMAIN, {
									'_mode': 'oob-response',
									'method': req.method,
									'token': token,
									'oob_fn': oob_fn,
								})

								try:
									with open(oob_fn) as f:
										dat = json.load(f) or {}
								except Exception:
									dat = {}
									ui.trace(DOMAIN)
								finally:
									try:
										os.remove(oob_fn)
									except Exception:
										ui.trace(DOMAIN)
							else:
								dat = r.get('data', {})

							dat = expand_jdata(dat)
							keep = req.f(dat, err) is True
							if keep:
								req.tm = time.time()
								gs.set_attr(k, req)
						except Exception:
							ui.trace(DOMAIN)
					else:
						ev.debug(DOMAIN, 'Ignoring margo: token: %s' % token)
			except Exception:
				ui.trace(DOMAIN)
		except Exception:
			ui.trace(DOMAIN)
			break

def _send():
	while True:
		try:
			try:
				method, arg, cb = gs.mg9_send_q.get()

				proc = gs.attr(PROC_ATTR_NAME)
				if not proc or proc.poll() is not None:
					killSrv()

					_install(True)

					while _inst_state() == "busy":
						time.sleep(0.100)

					cmd = [
						'margo',
						'-oom', gs.setting('margo_oom', 0),
						'-poll', 30,
						'-tag', TAG,
					]

					c = sh.Command(cmd)
					c.stderr = gs.LOGFILE
					c.env = {
						'XDG_CONFIG_HOME': sh.vdir(),
					}

					pr = c.proc()
					if pr.ok:
						proc = pr.p
						err = ''
					else:
						proc = None
						err = 'Exception: %s' % pr.exc

					if err or not proc or proc.poll() is not None:
						killSrv()
						_call(cb, {}, 'Abort. Cannot start MarGo: %s' % err)

						continue

					gs.set_attr(PROC_ATTR_NAME, proc)
					gsq.launch(DOMAIN, lambda: _read_stdout(proc))

				req = Request(f=cb, method=method)
				gs.set_attr(REQUEST_PREFIX+req.token, req)

				header, err = gs.json_encode(req.header(arg))
				if err:
					_cb_err(cb, 'Failed to construct ipc header: %s' % err)
					continue

				body, err = gs.json_encode(arg)
				if err:
					_cb_err(cb, 'Failed to construct ipc body: %s' % err)
					continue

				ev.debug(DOMAIN, {
					'_mode': 'request',
					'header': req.header(),
					'body': arg,
				})

				ln = '%s %s\n' % (header, body)

				try:
					if gs.PY3K:
						proc.stdin.write(bytes(ln, 'UTF-8'))
					else:
						proc.stdin.write(ln)

				except Exception as ex:
					_cb_err(cb, 'Cannot talk to MarGo: %s' % err)
					killSrv()
					ui.trace(DOMAIN)

			except Exception:
				killSrv()
				ui.trace(DOMAIN)
		except Exception:
			ui.trace(DOMAIN)
			break

def _call(cb, res, err):
	try:
		cb(res, err)
	except Exception:
		ui.trace(DOMAIN)

def _cb_err(cb, err):
	ui.error(DOMAIN, err)
	_call(cb, {}, err)


def _read_stdout(proc):
	try:
		while True:
			ln = proc.stdout.readline()
			if not ln:
				break

			gs.mg9_recv_q.put(gs.ustr(ln))
	except Exception:
		ui.trace(DOMAIN)

		proc.stdout.close()
		proc.wait()
		proc = None

def killSrv():
	p = gs.del_attr(PROC_ATTR_NAME)
	if p:
		try:
			p.stdout.close()
		except Exception:
			pass

		try:
			p.stdin.close()
		except Exception:
			pass

def on(token, cb):
	req = Request(f=cb, token=token)
	gs.set_attr(REQUEST_PREFIX+req.token, req)

def _dump(res, err):
	gs.println(json.dumps({
		'res': res,
		'err': err,
	}, sort_keys=True, indent=2))

if not gs.checked(DOMAIN, 'launch ipc threads'):
	gsq.launch(DOMAIN, _send)
	gsq.launch(DOMAIN, _recv)

def on_mg_msg(res, err):
	msg = res.get('message', '')
	if msg:
		print('GoSublime: MarGo: %s' % msg)
		ui.note('MarGo', msg)

	return True

def on_ignore(res, err):
	return True

def mg_status(res, _):
	k = res.get('Key', '?')
	s = res.get('Text', '')
	dmn = 'MarGo'

	if k == 'margo.error':
		ui.error(dmn, s)
	elif k == 'margo.note':
		ui.note(dmn, s)
	else:
		ui.status.drawer(k).set_text(s)

	return True

def mg_open(res, _):
	def f():
		vu.open(res.get('fn'))

	gs.do(DOMAIN, f)

	return True


on('margo.message', on_mg_msg)
on('margo.poll', on_ignore)
on('margo.hello', on_ignore)
on('margo.bye-ni', on_ignore)
on('margo.status', mg_status)
on('margo.open', mg_open)
