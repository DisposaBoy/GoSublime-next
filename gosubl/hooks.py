from . import ev
from . import gs
import fnmatch

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

	for m in gs.setting('hooks').get(k, []):
		# todo: impl fn/glob matching

		cmd = m.get('cmd', [])
		if cmd and _scope_ok(view, m):
			inp = m.get('input')
			if inp:
				if inp is True:
					inp = gs.view_src(view)
				else:
					inp = gs.astr(inp)
			else:
				inp = ''

			l.append({
				'run': cmd,
				'save_hist': m.get('hist', False),
				'focus_view': m.get('focus', False),
				'input': inp,
			})

	return l

def _hk(view, k):
	for a in _hooks(view, k):
		view.run_command('gs9o_open', a)

def gs_init(m={}):
	pass

ev.file_saved += lambda view: _hk(view, 'save')
ev.view_updated += lambda view: _hk(view, 'change')
