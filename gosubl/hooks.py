from . import ev
from . import gs
from . import nineo

DOMAIN = 'gs.hooks'

_scope_aliases = {
	'go': 'source.go',
}

def _scope_ok(view, m):
	try:
		s = m.get('scope') or 'go'
		s = _scope_aliases.get(s, s)
		return s and view.score_selector(0, s) > 0
	except Exception:
		error_traceback(NAME)
		return False

def _hooks(view, k):
	if view is None:
		return []

	l = []

	for c in gs.setting('hooks').get(k, []):
		# todo: impl fn/glob matching

		cmd = c.get('cmd', '')
		if cmd and _scope_ok(view, c):
			l.append(c)

	return l

def _hk(view, k):
	for c in _hooks(view, k):
		def f(res, err):
			if err:
				gs.error(DOMAIN, err)
				gs.debug(DOMAIN, {
					'res': res,
					'mode': k,
					'c': c,
				})

		wr = nineo.Writer(None)
		wr.write = lambda s: None

		nineo.Session(wr, view=view).start(c['cmd'], f)

def gs_init(m={}):
	pass

ev.file_saved += lambda view: _hk(view, 'save')
ev.view_updated += lambda view: _hk(view, 'change')
