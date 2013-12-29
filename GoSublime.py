import os
import sublime
import sys
import traceback

st2 = (sys.version_info[0] == 2)
dist_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, dist_dir)

ANN = ''
VERSION = ''
fn = os.path.join(dist_dir, 'gosubl', 'about.py')
execErr = ''
try:
	with open(fn) as f:
		code = compile(f.read(), fn, 'exec')
		exec(code)
except Exception:
	execErr = "Error: failed to exec about.py: Exception: %s" % traceback.format_exc()
	print("GoSublime: %s" % execErr)

def plugin_loaded():
	from gosubl import about
	from gosubl import sh
	from gosubl import ev
	from gosubl import gs
	from gosubl import mg9
	from gosubl import hl
	from gosubl import nineo
	from gosubl import nineo_builtins

	if VERSION != about.VERSION:
		gs.show_output('GoSublime-main', '\n'.join([
			'GoSublime has been updated.',
			'New version: `%s`, current version: `%s`' % (VERSION, about.VERSION),
			'Please restart Sublime Text to complete the update.',
			execErr,
		]))
		return

	if gs.attr('about.version'):
		gs.show_output('GoSublime-main', '\n'.join([
			'GoSublime appears to have been updated.',
			'New ANNOUNCE: `%s`, current ANNOUNCE: `%s`' % (ANN, about.ANN),
			'You may need to restart Sublime Text.',
		]))
		return

	mods = [
		('gs', gs),
		('sh', sh),
		('mg9', mg9),
		('9o', nineo),
		('hl', hl),
		('9o-builtins', nineo_builtins),
	]

	gs.set_attr('about.version', VERSION)
	gs.set_attr('about.ann', ANN)

	for mod_name, mod in mods:
		print('GoSublime %s: init mod(%s)' % (about.VERSION, mod_name))

		try:
			mod.gs_init({
				'version': VERSION,
				'ann': ANN,
			})
		except TypeError:
			# old versions didn't take an arg
			mod.gs_init()

	ev.init.post_add = lambda e, f: f()
	ev.init()

	def cb():
		aso = gs.aso()
		if about.ANN != aso.get('ann', ''):
			aso.set('ann', about.ANN)
			gs.save_aso()
			gs.focus(gs.dist_path('CHANGELOG.md'))

	sublime.set_timeout(cb, 0)


if st2:
	sublime.set_timeout(plugin_loaded, 0)
