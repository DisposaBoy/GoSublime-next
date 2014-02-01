import copy
import sublime

_sublime_settings = None
_project_settings = {}
_view_settings = {}

defaults = {
	'suggest_packages': False,
	'folders': [],
	'active_fn': '',
	'active_vfn': '',
	'env': {},
	'fmt_on_save': False,
	'fmt_cmd': [],
	'shell': [],
	"autocomplete_snippets": False,
	"default_snippets": [],
	"snippets": [],
}

def merge(base, ml):
	d = {}

	for m in ml:
		if not hasattr(m, 'get'):
			continue

		for bk in base:
			dv = d.get(bk)
			mv = m.get(bk)
			if dv is None and isinstance(mv, type(base[bk])):
				d[bk] = copy.deepcopy(mv)
			elif isinstance(dv, dict) and isinstance(mv, dict):
				for k in mv:
					v = mv[k]
					if v is not None and dv.get(k) is None:
						dv[k] = copy.deepcopy(v)

	return d

def sync_vv(vv):
	global _project_settings
	global _view_settings

	_project_settings = vv.setting('GoSublime', {})
	_view_settings = {
		'active_fn': vv.fn(),
		'active_vfn': vv.vfn(),
		'folders': vv.folders(),
	}

	sync_all()

def sync_all():
	globals().update(merge(defaults, [_view_settings, _project_settings, _sublime_settings, defaults]))

def gs_init(m={}):
	global _sublime_settings

	_sublime_settings = sublime.load_settings("GoSublime.sublime-settings")
	_sublime_settings.clear_on_change("GoSublime.cfg")
	_sublime_settings.add_on_change("GoSublime.cfg", sync_all)

	sync_all()

sync_all()
