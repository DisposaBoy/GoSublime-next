from . import ev

DOMAIN = 'GoSublime: Lint'

def gs_init(m={}):
	pass

def lc(view):
	pass

def mod(view):
	pass

ev.line_changed += lc
ev.view_updated += mod
