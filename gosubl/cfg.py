import copy
import sublime

_sublime_settings = None
_project_settings = {}
_view_settings = {}

defaults = {
	'active_fn': '',
	'active_vfn': '',
	'autocomplete_snippets': False,
	'commands': {},
	'default_commands': {},
	'default_snippets': [],
	'env': {},
	'fmt_cmd': [],
	'fmt_on_save': False,
	'folders': [],
	'nineo_color_scheme': '',
	'nineo_instance': '',
	'nineo_settings': {},
	'nineo_show_end': False,
	'shell': [],
	'snippets': [],
	'suggest_packages': False,
}

globals().update(defaults)

def merge(base, ml, val=lambda m, k: m.get(k)):
	d = {}

	for m in ml:
		if not hasattr(m, 'get'):
			continue

		for bk in base:
			dv = val(d, bk)
			mv = val(m, bk)
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

def val(m, k):
	if k.startswith('nineo_'):
		k = '9o_'+k[6:]

	return m.get(k)

def sync_all():
	globals().update(merge(defaults, [
		_view_settings,
		_project_settings,
		_sublime_settings,
		defaults,
	], val=val))

def gs_init(m={}):
	global _sublime_settings

	_sublime_settings = sublime.load_settings("GoSublime.sublime-settings")
	_sublime_settings.clear_on_change("GoSublime.cfg")
	_sublime_settings.add_on_change("GoSublime.cfg", sync_all)

	sync_all()

sync_all()
